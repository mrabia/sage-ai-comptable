import logging
import json
from typing import Dict, Any, Optional, List
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

class ExcelTVACalculatorTool(BaseTool):
    """Outil pour calculer la TVA directement depuis un fichier Excel attaché"""
    
    name: str = "excel_tva_calculator"
    description: str = """
    Calcule la TVA collectée et autres indicateurs fiscaux directement depuis un fichier Excel attaché.
    
    Paramètres:
    - document_id: ID du fichier Excel à analyser
    - tva_rate: Taux de TVA à utiliser (défaut: 20%)
    - account_filters: Comptes à inclure dans le calcul (optionnel)
    
    Retourne un rapport détaillé des calculs de TVA.
    """
    
    def _run(self, document_id: int, tva_rate: float = 20.0, account_filters: str = None) -> str:
        try:
            print(f"🔍 ExcelTVACalculatorTool: Calculating TVA for file ID {document_id}")
            
            # Récupérer le fichier attaché
            file_attachment = FileAttachment.query.get(document_id)
            if not file_attachment:
                return f"❌ Fichier {document_id} non trouvé"
            
            print(f"✅ Found file: {file_attachment.original_filename}")
            
            if file_attachment.file_extension.lower() not in ['.xlsx', '.xls']:
                return f"❌ Le fichier doit être au format Excel (.xlsx/.xls)"
            
            # Lire le fichier Excel
            try:
                excel_data = pd.read_excel(file_attachment.file_path, sheet_name=None, engine='openpyxl')
                print(f"📊 Successfully loaded {len(excel_data)} sheets")
            except Exception as e:
                return f"❌ Erreur lors de la lecture du fichier Excel: {str(e)}"
            
            return self._calculate_tva_from_excel(excel_data, tva_rate, account_filters)
            
        except Exception as e:
            logger.error(f"Erreur dans ExcelTVACalculatorTool: {e}")
            return f"❌ Erreur lors du calcul TVA: {str(e)}"
    
    def _calculate_tva_from_excel(self, excel_data: Dict[str, pd.DataFrame], tva_rate: float, account_filters: str) -> str:
        """Calcule la TVA depuis les données Excel"""
        
        report = f"=== CALCUL TVA COLLECTÉE ===\n"
        report += f"Taux TVA appliqué: {tva_rate}%\n\n"
        
        # Analyser chaque feuille pour trouver des données pertinentes
        tva_results = []
        total_ht = 0
        total_tva = 0
        total_ttc = 0
        
        for sheet_name, df in excel_data.items():
            print(f"🔍 Analyzing sheet: {sheet_name}")
            
            if df.empty:
                continue
                
            # Rechercher des colonnes de montants
            amount_columns = self._find_amount_columns(df)
            client_columns = self._find_client_columns(df)
            date_columns = self._find_date_columns(df)
            
            if amount_columns:
                sheet_result = self._analyze_sheet_for_tva(
                    sheet_name, df, amount_columns, client_columns, date_columns, tva_rate, account_filters
                )
                
                if sheet_result['total_ht'] > 0:
                    tva_results.append(sheet_result)
                    total_ht += sheet_result['total_ht']
                    total_tva += sheet_result['total_tva']
                    total_ttc += sheet_result['total_ttc']
        
        # Générer le rapport
        if not tva_results:
            report += "⚠️ AUCUNE DONNÉE TVA TROUVÉE\n"
            report += "Les feuilles analysées ne contiennent pas de données fiscales exploitables.\n\n"
            report += "SUGGESTIONS:\n"
            report += "- Vérifiez que le fichier contient des colonnes de montants\n"
            report += "- Assurez-vous que les données sont dans un format standardisé\n"
            report += "- Utilisez des en-têtes de colonnes explicites (Montant HT, TVA, etc.)\n"
            return report
        
        # Rapport détaillé par feuille
        report += f"📊 RÉSULTATS PAR FEUILLE:\n\n"
        
        for result in tva_results:
            report += f"🔹 Feuille '{result['sheet_name']}':\n"
            report += f"  • Lignes analysées: {result['rows_processed']}\n"
            report += f"  • Montant HT: {result['total_ht']:,.2f} MAD\n"
            report += f"  • TVA calculée: {result['total_tva']:,.2f} MAD\n"
            report += f"  • Montant TTC: {result['total_ttc']:,.2f} MAD\n"
            
            if result['top_clients']:
                report += f"  • Principaux clients: {', '.join(result['top_clients'][:3])}\n"
            
            report += "\n"
        
        # Totaux globaux
        report += f"💰 TOTAUX CONSOLIDÉS:\n"
        report += f"📈 Total HT: {total_ht:,.2f} MAD\n"
        report += f"🧾 Total TVA collectée: {total_tva:,.2f} MAD (à {tva_rate}%)\n"
        report += f"💵 Total TTC: {total_ttc:,.2f} MAD\n\n"
        
        # Validation et vérifications
        report += f"✅ VÉRIFICATIONS:\n"
        calculated_tva = total_ht * (tva_rate / 100)
        if abs(calculated_tva - total_tva) < 1:  # Tolérance de 1 MAD
            report += f"✓ Cohérence TVA validée: {calculated_tva:.2f} ≈ {total_tva:.2f}\n"
        else:
            report += f"⚠️ Incohérence TVA: calculé {calculated_tva:.2f} vs trouvé {total_tva:.2f}\n"
        
        calculated_ttc = total_ht + total_tva
        if abs(calculated_ttc - total_ttc) < 1:
            report += f"✓ Cohérence TTC validée: {calculated_ttc:.2f} ≈ {total_ttc:.2f}\n"
        else:
            report += f"⚠️ Incohérence TTC: calculé {calculated_ttc:.2f} vs trouvé {total_ttc:.2f}\n"
        
        # Recommandations
        report += f"\n📋 DÉCLARATION TVA - MAI 2025:\n"
        report += f"• Ligne 06 - Opérations imposables: {total_ht:,.2f} MAD\n"
        report += f"• Ligne 07 - TVA collectée: {total_tva:,.2f} MAD\n"
        report += f"• Taux appliqué: {tva_rate}%\n"
        
        return report
    
    def _find_amount_columns(self, df: pd.DataFrame) -> List[str]:
        """Trouve les colonnes contenant des montants"""
        amount_keywords = [
            'montant', 'amount', 'total', 'prix', 'price', 'cost', 'coût',
            'ht', 'ttc', 'tva', 'vat', 'tax', 'taxe', 'crédit', 'credit', 'débit', 'debit',
            'solde', 'balance'
        ]
        
        amount_columns = []
        for col in df.columns:
            col_lower = str(col).lower()
            if any(keyword in col_lower for keyword in amount_keywords):
                # Vérifier que la colonne contient des nombres
                try:
                    pd.to_numeric(df[col], errors='coerce')
                    amount_columns.append(col)
                except:
                    pass
        
        return amount_columns
    
    def _find_client_columns(self, df: pd.DataFrame) -> List[str]:
        """Trouve les colonnes contenant des informations client"""
        client_keywords = ['client', 'customer', 'nom', 'name', 'société', 'company', 'tiers']
        
        client_columns = []
        for col in df.columns:
            col_lower = str(col).lower()
            if any(keyword in col_lower for keyword in client_keywords):
                client_columns.append(col)
        
        return client_columns
    
    def _find_date_columns(self, df: pd.DataFrame) -> List[str]:
        """Trouve les colonnes contenant des dates"""
        date_keywords = ['date', 'écriture', 'facture', 'invoice', 'créat', 'modif']
        
        date_columns = []
        for col in df.columns:
            col_lower = str(col).lower()
            if any(keyword in col_lower for keyword in date_keywords):
                # Vérifier si ça ressemble à une date
                if df[col].dtype == 'datetime64[ns]' or 'datetime' in str(df[col].dtype).lower():
                    date_columns.append(col)
        
        return date_columns
    
    def _analyze_sheet_for_tva(self, sheet_name: str, df: pd.DataFrame, 
                              amount_columns: List[str], client_columns: List[str],
                              date_columns: List[str], tva_rate: float, account_filters: str) -> Dict[str, Any]:
        """Analyse une feuille spécifique pour calculer la TVA"""
        
        result = {
            'sheet_name': sheet_name,
            'rows_processed': 0,
            'total_ht': 0,
            'total_tva': 0,
            'total_ttc': 0,
            'top_clients': []
        }
        
        # Filtrer sur les comptes si spécifié
        working_df = df.copy()
        if account_filters:
            account_list = [acc.strip() for acc in account_filters.split(',')]
            # Rechercher une colonne de compte
            account_col = None
            for col in df.columns:
                if any(keyword in str(col).lower() for keyword in ['compte', 'account', 'code']):
                    account_col = col
                    break
            
            if account_col:
                working_df = df[df[account_col].astype(str).str.contains('|'.join(account_list), na=False)]
        
        # Analyser les montants
        for amount_col in amount_columns:
            try:
                # Convertir en numérique
                amounts = pd.to_numeric(working_df[amount_col], errors='coerce').fillna(0)
                
                # Déterminer le type de montant basé sur le nom de la colonne
                col_lower = amount_col.lower()
                
                if 'tva' in col_lower or 'vat' in col_lower or 'tax' in col_lower:
                    # C'est directement de la TVA
                    result['total_tva'] += amounts.sum()
                elif 'ttc' in col_lower:
                    # C'est du TTC
                    ttc_sum = amounts.sum()
                    result['total_ttc'] += ttc_sum
                    # Calculer HT et TVA
                    ht_calculated = ttc_sum / (1 + tva_rate/100)
                    result['total_ht'] += ht_calculated
                    result['total_tva'] += ttc_sum - ht_calculated
                elif 'ht' in col_lower:
                    # C'est du HT
                    ht_sum = amounts.sum()
                    result['total_ht'] += ht_sum
                    result['total_tva'] += ht_sum * (tva_rate/100)
                    result['total_ttc'] += ht_sum * (1 + tva_rate/100)
                else:
                    # Montant générique, on assume que c'est du HT
                    ht_sum = amounts.sum()
                    if ht_sum > 0:  # Seulement si positif
                        result['total_ht'] += ht_sum
                        result['total_tva'] += ht_sum * (tva_rate/100)
                        result['total_ttc'] += ht_sum * (1 + tva_rate/100)
                
            except Exception as e:
                print(f"Warning: Could not process amount column {amount_col}: {e}")
                continue
        
        # Compter les lignes traitées
        result['rows_processed'] = len(working_df)
        
        # Extraire les principaux clients
        if client_columns:
            for client_col in client_columns:
                try:
                    clients = working_df[client_col].dropna().astype(str)
                    top_clients = clients.value_counts().head(5).index.tolist()
                    result['top_clients'].extend([c for c in top_clients if c not in result['top_clients']])
                except:
                    pass
        
        result['top_clients'] = result['top_clients'][:5]  # Limiter à 5
        
        return result

class ExcelDataExplorerTool(BaseTool):
    """Outil pour explorer et analyser la structure d'un fichier Excel"""
    
    name: str = "excel_data_explorer"
    description: str = """
    Explore en détail la structure et le contenu d'un fichier Excel pour identifier les données comptables.
    
    Paramètres:
    - document_id: ID du fichier Excel à explorer
    - sheet_name: Nom de la feuille spécifique à analyser (optionnel)
    
    Retourne une analyse détaillée des données.
    """
    
    def _run(self, document_id: int, sheet_name: str = None) -> str:
        try:
            print(f"🔍 ExcelDataExplorerTool: Exploring file ID {document_id}")
            
            # Récupérer le fichier attaché
            file_attachment = FileAttachment.query.get(document_id)
            if not file_attachment:
                return f"❌ Fichier {document_id} non trouvé"
            
            if file_attachment.file_extension.lower() not in ['.xlsx', '.xls']:
                return f"❌ Le fichier doit être au format Excel (.xlsx/.xls)"
            
            # Lire le fichier Excel
            try:
                if sheet_name:
                    excel_data = {sheet_name: pd.read_excel(file_attachment.file_path, sheet_name=sheet_name, engine='openpyxl')}
                else:
                    excel_data = pd.read_excel(file_attachment.file_path, sheet_name=None, engine='openpyxl')
            except Exception as e:
                return f"❌ Erreur lors de la lecture du fichier Excel: {str(e)}"
            
            return self._generate_detailed_report(excel_data, file_attachment.original_filename)
            
        except Exception as e:
            logger.error(f"Erreur dans ExcelDataExplorerTool: {e}")
            return f"❌ Erreur lors de l'exploration: {str(e)}"
    
    def _generate_detailed_report(self, excel_data: Dict[str, pd.DataFrame], filename: str) -> str:
        """Génère un rapport détaillé des données Excel"""
        
        report = f"=== EXPLORATION DÉTAILLÉE ===\n"
        report += f"Fichier: {filename}\n"
        report += f"Nombre de feuilles: {len(excel_data)}\n\n"
        
        for sheet_name, df in excel_data.items():
            report += f"📊 FEUILLE '{sheet_name}':\n"
            report += f"  • Dimensions: {len(df)} lignes × {len(df.columns)} colonnes\n"
            
            if df.empty:
                report += "  • Aucune donnée\n\n"
                continue
            
            # Analyse des colonnes
            report += f"  • Colonnes détectées:\n"
            for i, col in enumerate(df.columns, 1):
                col_type = str(df[col].dtype)
                non_null_count = df[col].count()
                null_count = len(df) - non_null_count
                
                report += f"    {i:2d}. {col} ({col_type})\n"
                report += f"        - Valeurs: {non_null_count} remplies, {null_count} vides\n"
                
                # Échantillon de données
                sample_values = df[col].dropna().head(3).astype(str).tolist()
                if sample_values:
                    report += f"        - Échantillon: {', '.join(sample_values)}\n"
                
                # Statistiques pour colonnes numériques
                if pd.api.types.is_numeric_dtype(df[col]):
                    stats = df[col].describe()
                    report += f"        - Min: {stats['min']:,.2f}, Max: {stats['max']:,.2f}, Moyenne: {stats['mean']:,.2f}\n"
            
            # Recherche de patterns comptables
            report += f"  • Analyse comptable:\n"
            
            # Colonnes de montants
            amount_cols = []
            for col in df.columns:
                col_lower = str(col).lower()
                if any(keyword in col_lower for keyword in ['montant', 'amount', 'total', 'prix', 'ht', 'ttc', 'tva', 'crédit', 'débit']):
                    if pd.api.types.is_numeric_dtype(df[col]):
                        amount_cols.append(col)
            
            if amount_cols:
                report += f"    - Colonnes de montants: {', '.join(amount_cols)}\n"
                for col in amount_cols:
                    total = df[col].sum()
                    report += f"      • {col}: {total:,.2f}\n"
            else:
                report += f"    - Aucune colonne de montant évidente\n"
            
            # Colonnes de clients
            client_cols = [col for col in df.columns if any(kw in str(col).lower() for kw in ['client', 'nom', 'société', 'tiers'])]
            if client_cols:
                report += f"    - Colonnes clients: {', '.join(client_cols)}\n"
                for col in client_cols:
                    unique_count = df[col].nunique()
                    report += f"      • {col}: {unique_count} valeurs uniques\n"
            
            # Colonnes de dates
            date_cols = [col for col in df.columns if df[col].dtype == 'datetime64[ns]' or 'date' in str(col).lower()]
            if date_cols:
                report += f"    - Colonnes de dates: {', '.join(date_cols)}\n"
                for col in date_cols:
                    try:
                        min_date = df[col].min()
                        max_date = df[col].max()
                        report += f"      • {col}: de {min_date} à {max_date}\n"
                    except:
                        pass
            
            report += "\n"
        
        return report