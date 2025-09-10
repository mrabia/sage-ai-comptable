"""
Outil officiel de calcul TVA collectée selon la norme comptable marocaine
Méthode officielle : TVA collectée = Σ(Crédits 445) - Σ(Débits 445)
JAMAIS de reconstruction HT×taux ni utilisation de feuilles inadaptées
"""

import logging
import json
import re
import unicodedata
from typing import Dict, Any, List, Optional, Union
import pandas as pd
from src.models.user import db, FileAttachment

# Try to import CrewAI tools with fallback
try:
    from crewai.tools import BaseTool
except ImportError:
    try:
        from crewai import BaseTool
    except ImportError:
        # Create a fallback BaseTool class
        class BaseTool:
            def __init__(self, **kwargs):
                for key, value in kwargs.items():
                    setattr(self, key, value)

logger = logging.getLogger(__name__)

# ---------- Utilities: normalization & detection ----------

def _slugify(s: str) -> str:
    """Normalise un en-tête: minuscule, sans accents, espaces -> _, supprime non-alphanum."""
    if s is None:
        return ""
    s = str(s)
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = s.lower().strip()
    s = re.sub(r"[\s\-]+", "_", s)
    s = re.sub(r"[^a-z0-9_]", "", s)
    return s

def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normalise les noms de colonnes pour faciliter la détection"""
    out = df.copy()
    out.columns = [_slugify(c) for c in out.columns]
    return out

# Synonymes d'entêtes après normalisation
COL_MAP = {
    "account": ["code_compte", "compte", "compte_general", "account", "code", "code_cpte"],
    "date":    ["date_ecriture", "date", "date_valeur", "date_piece", "ecriture_date"],
    "debit":   ["debit", "mvt_debit", "montant_debit", "debit_"],
    "credit":  ["credit", "mvt_credit", "montant_credit", "credit_"],
}

def _detect_col(df: pd.DataFrame, keys: List[str]) -> Optional[str]:
    """Détecte une colonne parmi les synonymes possibles"""
    cols = set(df.columns)
    for k in keys:
        if k in cols:
            return k
    # fallback partiel
    for col in df.columns:
        for k in keys:
            if k in col:
                return col
    return None

def _coerce_types(df: pd.DataFrame, date_col: str, debit_col: str, credit_col: str) -> pd.DataFrame:
    """Force le typage des colonnes critiques"""
    out = df.copy()
    if date_col in out.columns:
        out[date_col] = pd.to_datetime(out[date_col], errors="coerce")
    if debit_col in out.columns:
        out[debit_col] = pd.to_numeric(out[debit_col], errors="coerce").fillna(0.0)
    if credit_col in out.columns:
        out[credit_col] = pd.to_numeric(out[credit_col], errors="coerce").fillna(0.0)
    return out

def _filter_period(df: pd.DataFrame, date_col: str, start_dt: pd.Timestamp, end_dt: pd.Timestamp) -> pd.DataFrame:
    """Filtre les données sur la période spécifiée (bornes inclusives)"""
    m = (df[date_col] >= start_dt) & (df[date_col] <= end_dt)
    return df.loc[m].copy()

def _is_tva_account_series(s: pd.Series) -> pd.Series:
    """Vérifie si les comptes commencent par 445 (comptes TVA collectée)"""
    return s.astype(str).str.strip().str.startswith("445")

class TVACollecteeOfficialTool(BaseTool):
    """Outil officiel pour calculer la TVA collectée selon la norme comptable"""
    
    name: str = "tva_collectee_officielle"
    description: str = """
    Calcule la TVA collectée OFFICIELLE selon la norme comptable marocaine.
    
    RÈGLE D'OR NON NÉGOCIABLE:
    TVA collectée = Σ(Crédits 445) - Σ(Débits 445) sur la période demandée.
    
    INTERDICTIONS ABSOLUES:
    - Jamais d'estimation HT/TVA/TTC depuis feuille 'banque' 
    - Jamais d'application de taux fixe (20%, 14%, etc.)
    - Jamais d'utilisation du grand livre complet sans filtrage 445
    
    Paramètres:
    - document_id: ID du fichier Excel contenant le grand livre
    - start_date: Date de début (YYYY-MM-DD)
    - end_date: Date de fin (YYYY-MM-DD) 
    - limit_sheets: Feuilles spécifiques à analyser (optionnel)
    
    Retourne un rapport officiel avec TVA nette, détail par compte 445.
    """
    
    def _run(self, document_id: int, start_date: str = "2025-05-01", end_date: str = "2025-05-31", limit_sheets: str = None) -> str:
        try:
            print(f"🔍 TVACollecteeOfficialTool: Calculing OFFICIAL TVA for file ID {document_id}")
            print(f"📅 Période: {start_date} → {end_date}")
            
            # Récupérer le fichier attaché
            file_attachment = FileAttachment.query.get(document_id)
            if not file_attachment:
                return f"❌ Fichier {document_id} non trouvé"
            
            print(f"✅ Found file: {file_attachment.original_filename}")
            
            if file_attachment.file_extension.lower() not in ['.xlsx', '.xls']:
                return f"❌ Le fichier doit être au format Excel (.xlsx/.xls)"
            
            # Traitement des feuilles limitées
            limit_sheets_list = None
            if limit_sheets:
                limit_sheets_list = [s.strip() for s in limit_sheets.split(',')]
                print(f"📊 Feuilles limitées: {limit_sheets_list}")
            
            return self._compute_tva_officielle(
                file_attachment.file_path,
                start_date,
                end_date,
                limit_sheets_list
            )
            
        except Exception as e:
            logger.error(f"Erreur dans TVACollecteeOfficialTool: {e}")
            return f"❌ Erreur lors du calcul TVA officielle: {str(e)}"
    
    def _compute_tva_officielle(self, file_path: str, start_date: str, end_date: str, limit_sheets: Optional[List[str]]) -> str:
        """
        Calcul officiel : Σ(Crédits 445) - Σ(Débits 445) sur période
        """
        
        print(f"📊 Loading Excel file: {file_path}")
        
        # Parse period
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)
        
        # Lire toutes les feuilles Excel
        try:
            xls = pd.ExcelFile(file_path)
            target_sheets = limit_sheets or xls.sheet_names
            sheets_dict = {}
            for sh in target_sheets:
                try:
                    tmp = pd.read_excel(xls, sheet_name=sh)
                    sheets_dict[sh] = tmp
                    print(f"✅ Loaded sheet '{sh}': {len(tmp)} rows × {len(tmp.columns)} cols")
                except Exception as e:
                    print(f"⚠️ Could not load sheet '{sh}': {e}")
                    continue
                    
        except Exception as e:
            return f"❌ Erreur lors de la lecture du fichier Excel: {str(e)}"
        
        by_sheet: List[Dict[str, Any]] = []
        all_445_rows: List[pd.DataFrame] = []
        
        for sheet_name, raw_df in sheets_dict.items():
            print(f"🔍 Analyzing sheet: {sheet_name}")
            
            if raw_df is None or len(raw_df) == 0:
                by_sheet.append({"sheet": sheet_name, "status": "no_data"})
                print(f"⚠️ Sheet '{sheet_name}': no data")
                continue
            
            df = _normalize_columns(raw_df)
            
            account_col = _detect_col(df, COL_MAP["account"])
            date_col    = _detect_col(df, COL_MAP["date"])
            debit_col   = _detect_col(df, COL_MAP["debit"])
            credit_col  = _detect_col(df, COL_MAP["credit"])
            
            missing = [n for n, c in [
                ("compte", account_col), ("date", date_col), ("debit", debit_col), ("credit", credit_col)
            ] if c is None]
            
            if missing:
                by_sheet.append({
                    "sheet": sheet_name, "status": "missing_columns", "missing": missing
                })
                print(f"❌ Sheet '{sheet_name}': missing columns {missing}")
                continue
            
            df = _coerce_types(df, date_col, debit_col, credit_col)
            df = df[df[date_col].notna()]
            
            # RÈGLE D'OR: Filtrer uniquement les comptes 445 (TVA collectée)
            df_445 = df[_is_tva_account_series(df[account_col])]
            if df_445.empty:
                by_sheet.append({"sheet": sheet_name, "status": "no_445"})
                print(f"⚠️ Sheet '{sheet_name}': no 445 accounts found")
                continue
            
            print(f"✅ Sheet '{sheet_name}': found {len(df_445)} entries with 445 accounts")
            
            # Filtrer sur la période
            df_445p = _filter_period(df_445, date_col, start_dt, end_dt)
            if df_445p.empty:
                by_sheet.append({"sheet": sheet_name, "status": "no_period_data"})
                print(f"⚠️ Sheet '{sheet_name}': no data in period {start_date} to {end_date}")
                continue
            
            print(f"✅ Sheet '{sheet_name}': {len(df_445p)} entries in period")
            
            # Calcul officiel par feuille
            credits = float(df_445p[credit_col].sum())
            debits  = float(df_445p[debit_col].sum())
            tva_net = float(credits - debits)
            count   = int(len(df_445p))
            
            by_sheet.append({
                "sheet": sheet_name, "status": "ok",
                "tva_net": tva_net, "credits": credits, "debits": debits, "count": count
            })
            print(f"📊 Sheet '{sheet_name}': Crédit={credits:.2f}, Débit={debits:.2f}, Net={tva_net:.2f}")
            
            # Préparer pour agrégation globale
            chunk = df_445p[[account_col, credit_col, debit_col]].copy()
            chunk.columns = ["code_compte", "credit", "debit"]
            all_445_rows.append(chunk)
        
        # Agrégation finale
        if all_445_rows:
            big = pd.concat(all_445_rows, axis=0, ignore_index=True)
            big["credit"] = pd.to_numeric(big["credit"], errors="coerce").fillna(0.0)
            big["debit"]  = pd.to_numeric(big["debit"],  errors="coerce").fillna(0.0)
            
            credits_total = float(big["credit"].sum())
            debits_total  = float(big["debit"].sum())
            tva_total     = float(credits_total - debits_total)
            entries_count = int(len(big))
            
            # Top comptes 445
            by_acc = big.groupby("code_compte")[["credit", "debit"]].sum().reset_index()
            by_acc["net"] = by_acc["credit"] - by_acc["debit"]
            by_acc = by_acc.sort_values("net", ascending=False).head(10)
            
        else:
            credits_total = 0.0
            debits_total  = 0.0
            tva_total     = 0.0
            entries_count = 0
            by_acc = pd.DataFrame()
        
        # Générer le rapport officiel
        rapport = self._generate_official_report(
            tva_total, credits_total, debits_total, entries_count,
            start_date, end_date, by_sheet, by_acc
        )
        
        return rapport
    
    def _generate_official_report(self, tva_total: float, credits_total: float, debits_total: float, 
                                entries_count: int, start_date: str, end_date: str,
                                by_sheet: List[Dict], by_acc: pd.DataFrame) -> str:
        """Génère le rapport officiel de TVA collectée"""
        
        rapport = f"=== TVA COLLECTÉE OFFICIELLE ===\n"
        rapport += f"Période: {start_date} → {end_date}\n"
        rapport += f"Méthode: Σ(Crédits 445) – Σ(Débits 445)\n\n"
        
        # Résultats principaux
        rapport += f"💰 RÉSULTAT OFFICIEL:\n"
        rapport += f"• TVA collectée nette: {tva_total:,.2f} MAD\n"
        rapport += f"• Total crédits 445: {credits_total:,.2f} MAD\n"
        rapport += f"• Total débits 445: {debits_total:,.2f} MAD\n"
        rapport += f"• Nombre d'écritures: {entries_count:,}\n\n"
        
        # Détail par feuille
        rapport += f"📊 DÉTAIL PAR FEUILLE:\n"
        sheets_ok = [s for s in by_sheet if s["status"] == "ok"]
        
        for sheet_info in sheets_ok:
            rapport += f"🔹 '{sheet_info['sheet']}':\n"
            rapport += f"    • Crédits: {sheet_info['credits']:,.2f} MAD\n"
            rapport += f"    • Débits: {sheet_info['debits']:,.2f} MAD\n"
            rapport += f"    • Net: {sheet_info['tva_net']:,.2f} MAD\n"
            rapport += f"    • Écritures: {sheet_info['count']:,}\n"
        
        # Feuilles problématiques
        sheets_problems = [s for s in by_sheet if s["status"] != "ok"]
        if sheets_problems:
            rapport += f"\n⚠️ FEUILLES NON EXPLOITABLES:\n"
            for sheet_info in sheets_problems:
                status_msg = {
                    "no_data": "Aucune donnée",
                    "missing_columns": f"Colonnes manquantes: {', '.join(sheet_info.get('missing', []))}",
                    "no_445": "Aucun compte 445 trouvé",
                    "no_period_data": "Aucune donnée sur la période"
                }
                rapport += f"• '{sheet_info['sheet']}': {status_msg.get(sheet_info['status'], 'Erreur inconnue')}\n"
        
        # Top comptes 445
        if not by_acc.empty:
            rapport += f"\n🏆 TOP COMPTES 445 (par contribution):\n"
            for _, row in by_acc.head(5).iterrows():
                rapport += f"• {row['code_compte']}: {row['net']:,.2f} MAD (Cr: {row['credit']:,.2f}, Db: {row['debit']:,.2f})\n"
        
        # Notes de conformité
        rapport += f"\n✅ CONFORMITÉ FISCALE:\n"
        rapport += f"• Méthode officielle respectée (comptes 445 uniquement)\n"
        rapport += f"• Aucune reconstruction HT×taux effectuée\n"
        rapport += f"• Période filtrée avec précision\n"
        rapport += f"• Résultat prêt pour déclaration TVA\n"
        
        # Ligne pour déclaration TVA
        rapport += f"\n📋 DÉCLARATION TVA:\n"
        rapport += f"• Ligne 07 - TVA collectée: {tva_total:,.2f} MAD\n"
        
        # Notes d'utilisation avancée
        rapport += f"\n💡 NOTES:\n"
        rapport += f"• Pour répartition par taux/client: fournir export journal VE\n"
        rapport += f"• Ce calcul est basé uniquement sur les comptes 445 du grand livre\n"
        rapport += f"• Conforme aux normes comptables marocaines\n"
        
        return rapport