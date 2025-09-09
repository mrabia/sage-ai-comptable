"""
Outils d'analyse de fichiers pour les agents AI
Corrélation avec les données Sage et analyse intelligente
"""

from typing import Type, Dict, Any, Optional, List
from pydantic import BaseModel, Field
from crewai.tools import BaseTool
import json
import pandas as pd
import re
from datetime import datetime, timedelta
from src.models.user import FileAttachment, User, db
from src.services.sage_api import SageAPIService
from src.services.sage_auth import SageOAuth2Service
from src.tools.sage_tools import SageBaseTool, sage_api
import logging

logger = logging.getLogger(__name__)

class AnalyzeFileInput(BaseModel):
    """Input schema for file analysis"""
    file_id: int = Field(..., description="ID du fichier à analyser")
    analysis_type: Optional[str] = Field("comprehensive", description="Type d'analyse (comprehensive, financial, sage_correlation)")
    compare_with_sage: Optional[bool] = Field(True, description="Comparer avec les données Sage")
    date_range: Optional[str] = Field(None, description="Plage de dates pour la corrélation (YYYY-MM-DD,YYYY-MM-DD)")
    business_id: Optional[str] = Field(None, description="Sage business ID")

class AnalyzeFileTool(SageBaseTool):
    name: str = "analyze_file"
    description: str = "Analyse avancée d'un fichier avec corrélation des données Sage"
    args_schema: Type[BaseModel] = AnalyzeFileInput

    def _extract_financial_data_from_content(self, content: str, file_type: str) -> Dict[str, Any]:
        """Extraire les données financières du contenu"""
        financial_data = {
            'amounts': [],
            'dates': [],
            'references': [],
            'invoices': [],
            'payments': [],
            'contacts': []
        }
        
        if not content:
            return financial_data
        
        # Regex patterns pour différents types de données
        amount_pattern = r'[\d,]+[\.,]\d{2}[\s]*[€$£]?'
        date_patterns = [
            r'\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}',
            r'\d{4}[\/\-\.]\d{1,2}[\/\-\.]\d{1,2}'
        ]
        invoice_pattern = r'(?:facture|invoice|INV)[:\s]*([A-Z0-9\-]+)'
        reference_pattern = r'(?:ref|référence|reference)[:\s]*([A-Z0-9\-]+)'
        
        # Extraire les montants
        amounts = re.findall(amount_pattern, content, re.IGNORECASE)
        for amount in amounts:
            try:
                # Nettoyer et convertir
                clean_amount = re.sub(r'[^\d,\.]', '', amount)
                clean_amount = clean_amount.replace(',', '.')
                if clean_amount and float(clean_amount) > 0:
                    financial_data['amounts'].append(float(clean_amount))
            except:
                continue
        
        # Extraire les dates
        for pattern in date_patterns:
            dates = re.findall(pattern, content)
            financial_data['dates'].extend(dates)
        
        # Extraire les références de factures
        invoices = re.findall(invoice_pattern, content, re.IGNORECASE)
        financial_data['invoices'] = list(set(invoices))
        
        # Extraire les références générales
        references = re.findall(reference_pattern, content, re.IGNORECASE)
        financial_data['references'] = list(set(references))
        
        return financial_data

    def _correlate_with_sage_data(self, financial_data: Dict[str, Any], credentials: Dict[str, Any], 
                                 business_id: Optional[str], date_range: Optional[str]) -> Dict[str, Any]:
        """Corréler les données extraites avec Sage"""
        correlations = {
            'matching_invoices': [],
            'matching_payments': [],
            'matching_customers': [],
            'amount_matches': [],
            'discrepancies': [],
            'suggestions': []
        }
        
        try:
            # Définir la plage de dates
            from_date = None
            to_date = None
            if date_range and ',' in date_range:
                from_date, to_date = date_range.split(',')
            
            # Rechercher des factures correspondantes
            if financial_data.get('invoices') or financial_data.get('amounts'):
                try:
                    invoices_result = sage_api.get_invoices(
                        credentials, business_id, limit=100, offset=0,
                        from_date=from_date, to_date=to_date
                    )
                    
                    sage_invoices = invoices_result.get('$items', [])
                    
                    # Corréler par référence
                    for file_ref in financial_data.get('invoices', []):
                        for sage_invoice in sage_invoices:
                            sage_ref = sage_invoice.get('reference', '')
                            if file_ref.upper() in sage_ref.upper() or sage_ref.upper() in file_ref.upper():
                                correlations['matching_invoices'].append({
                                    'file_reference': file_ref,
                                    'sage_invoice': {
                                        'id': sage_invoice.get('id'),
                                        'reference': sage_ref,
                                        'total_amount': sage_invoice.get('total_amount'),
                                        'status': sage_invoice.get('status', {}).get('displayed_as'),
                                        'contact': sage_invoice.get('contact', {}).get('displayed_as')
                                    }
                                })
                    
                    # Corréler par montant
                    for file_amount in financial_data.get('amounts', []):
                        for sage_invoice in sage_invoices:
                            sage_amount = float(sage_invoice.get('total_amount', 0))
                            if abs(file_amount - sage_amount) < 0.01:  # Tolérance de 1 centime
                                correlations['amount_matches'].append({
                                    'file_amount': file_amount,
                                    'sage_invoice': {
                                        'reference': sage_invoice.get('reference'),
                                        'amount': sage_amount,
                                        'contact': sage_invoice.get('contact', {}).get('displayed_as')
                                    }
                                })
                
                except Exception as e:
                    correlations['suggestions'].append(f"Impossible de récupérer les factures Sage: {str(e)}")
            
            # Rechercher des paiements correspondants
            if financial_data.get('amounts'):
                try:
                    payments_result = sage_api.get_payments(
                        credentials, business_id, limit=100, offset=0,
                        from_date=from_date, to_date=to_date
                    )
                    
                    sage_payments = payments_result.get('$items', [])
                    
                    for file_amount in financial_data.get('amounts', []):
                        for payment in sage_payments:
                            payment_amount = float(payment.get('total_amount', 0))
                            if abs(file_amount - payment_amount) < 0.01:
                                correlations['matching_payments'].append({
                                    'file_amount': file_amount,
                                    'sage_payment': {
                                        'reference': payment.get('reference'),
                                        'amount': payment_amount,
                                        'date': payment.get('date'),
                                        'bank_account': payment.get('bank_account', {}).get('displayed_as')
                                    }
                                })
                
                except Exception as e:
                    correlations['suggestions'].append(f"Impossible de récupérer les paiements Sage: {str(e)}")
            
            # Analyser les discordances
            total_file_amounts = sum(financial_data.get('amounts', []))
            total_matched_invoices = sum([match['sage_invoice']['total_amount'] 
                                        for match in correlations['matching_invoices'] 
                                        if 'total_amount' in match['sage_invoice']])
            
            if total_file_amounts > 0 and abs(total_file_amounts - total_matched_invoices) > 1.0:
                correlations['discrepancies'].append({
                    'type': 'amount_difference',
                    'file_total': total_file_amounts,
                    'sage_matched_total': total_matched_invoices,
                    'difference': total_file_amounts - total_matched_invoices,
                    'description': f'Différence de {abs(total_file_amounts - total_matched_invoices):.2f}€ entre le fichier et Sage'
                })
            
            # Suggestions d'actions
            if len(correlations['matching_invoices']) == 0 and len(financial_data.get('invoices', [])) > 0:
                correlations['suggestions'].append("Aucune facture Sage ne correspond aux références du fichier - vérifiez les numéros")
            
            if len(correlations['amount_matches']) == 0 and len(financial_data.get('amounts', [])) > 0:
                correlations['suggestions'].append("Aucun montant Sage ne correspond exactement - vérifiez les calculs de TVA")
            
            if len(correlations['discrepancies']) > 0:
                correlations['suggestions'].append("Des écarts ont été détectés - réconciliation recommandée")
                
        except Exception as e:
            logger.error(f"Erreur lors de la corrélation Sage: {str(e)}")
            correlations['error'] = str(e)
        
        return correlations

    def _run(self, file_id: int, analysis_type: Optional[str] = "comprehensive",
             compare_with_sage: Optional[bool] = True, date_range: Optional[str] = None,
             business_id: Optional[str] = None) -> str:
        try:
            credentials = self.get_credentials()
            if not credentials:
                return "❌ Erreur: Aucune connexion Sage détectée. Veuillez vous connecter à Sage d'abord."
            
            # Récupérer le fichier
            file_attachment = FileAttachment.query.get(file_id)
            if not file_attachment:
                return f"❌ Fichier avec l'ID {file_id} non trouvé."
            
            if not file_attachment.is_processed:
                return f"❌ Le fichier '{file_attachment.original_filename}' n'a pas été traité avec succès."
            
            # Récupérer les métadonnées d'analyse
            analysis_metadata = file_attachment.get_analysis_metadata()
            processed_content = file_attachment.processed_content or ""
            
            response_parts = [f"📄 Analyse du fichier: {file_attachment.original_filename}"]
            response_parts.append(f"📊 Type: {analysis_metadata.get('type', 'Inconnu')} | Taille: {file_attachment.file_size} bytes")
            
            # Analyse de base
            if analysis_metadata.get('potential_financial_data'):
                response_parts.append("💰 Document financier détecté")
            
            # Extraire les données financières du contenu
            financial_data = self._extract_financial_data_from_content(
                processed_content, 
                analysis_metadata.get('type', '')
            )
            
            if financial_data['amounts']:
                response_parts.append(f"\n💵 MONTANTS DÉTECTÉS ({len(financial_data['amounts'])}):")
                for amount in financial_data['amounts'][:5]:  # Limiter à 5
                    response_parts.append(f"  • {amount:.2f}€")
                if len(financial_data['amounts']) > 5:
                    response_parts.append(f"  ... et {len(financial_data['amounts']) - 5} autres")
                
                total_amounts = sum(financial_data['amounts'])
                response_parts.append(f"  📊 Total: {total_amounts:.2f}€")
            
            if financial_data['invoices']:
                response_parts.append(f"\n🧾 RÉFÉRENCES DE FACTURES ({len(financial_data['invoices'])}):")
                for ref in financial_data['invoices'][:5]:
                    response_parts.append(f"  • {ref}")
            
            if financial_data['dates']:
                response_parts.append(f"\n📅 DATES DÉTECTÉES ({len(financial_data['dates'])}):")
                for date in list(set(financial_data['dates']))[:5]:
                    response_parts.append(f"  • {date}")
            
            # Analyse spécialisée selon le type de fichier
            if analysis_metadata.get('type') == 'excel' or analysis_metadata.get('type') == 'csv':
                sheets_info = analysis_metadata.get('sheets', analysis_metadata)
                if 'numeric_columns' in sheets_info:
                    response_parts.append(f"\n📊 COLONNES NUMÉRIQUES:")
                    for col in sheets_info['numeric_columns'][:3]:
                        response_parts.append(f"  • {col}")
            
            elif analysis_metadata.get('type') == 'pdf':
                if analysis_metadata.get('has_tables'):
                    tables_count = analysis_metadata.get('tables_count', 0)
                    response_parts.append(f"\n📊 {tables_count} tableau(x) détecté(s) dans le PDF")
            
            # Corrélation avec Sage si demandée
            if compare_with_sage and (financial_data['amounts'] or financial_data['invoices']):
                response_parts.append(f"\n\n🔗 CORRÉLATION AVEC SAGE:")
                
                correlations = self._correlate_with_sage_data(
                    financial_data, credentials, business_id, date_range
                )
                
                if correlations.get('error'):
                    response_parts.append(f"❌ Erreur lors de la corrélation: {correlations['error']}")
                else:
                    # Factures correspondantes
                    if correlations['matching_invoices']:
                        response_parts.append(f"\n✅ FACTURES CORRESPONDANTES ({len(correlations['matching_invoices'])}):")
                        for match in correlations['matching_invoices'][:3]:
                            sage_inv = match['sage_invoice']
                            response_parts.append(f"  • {match['file_reference']} → {sage_inv['reference']} ({sage_inv['total_amount']}€)")
                    
                    # Montants correspondants
                    if correlations['amount_matches']:
                        response_parts.append(f"\n✅ MONTANTS CORRESPONDANTS ({len(correlations['amount_matches'])}):")
                        for match in correlations['amount_matches'][:3]:
                            response_parts.append(f"  • {match['file_amount']:.2f}€ → {match['sage_invoice']['reference']}")
                    
                    # Paiements correspondants
                    if correlations['matching_payments']:
                        response_parts.append(f"\n💳 PAIEMENTS CORRESPONDANTS ({len(correlations['matching_payments'])}):")
                        for match in correlations['matching_payments'][:3]:
                            payment = match['sage_payment']
                            response_parts.append(f"  • {match['file_amount']:.2f}€ → {payment['reference']} ({payment['date']})")
                    
                    # Discordances
                    if correlations['discrepancies']:
                        response_parts.append(f"\n⚠️ DISCORDANCES DÉTECTÉES:")
                        for discrepancy in correlations['discrepancies']:
                            response_parts.append(f"  • {discrepancy['description']}")
                    
                    # Suggestions
                    if correlations['suggestions']:
                        response_parts.append(f"\n💡 RECOMMANDATIONS:")
                        for suggestion in correlations['suggestions'][:3]:
                            response_parts.append(f"  • {suggestion}")
                    
                    # Résumé de la corrélation
                    match_rate = 0
                    if financial_data['amounts'] or financial_data['invoices']:
                        total_items = len(financial_data.get('amounts', [])) + len(financial_data.get('invoices', []))
                        total_matches = len(correlations['matching_invoices']) + len(correlations['amount_matches'])
                        match_rate = (total_matches / total_items * 100) if total_items > 0 else 0
                    
                    if match_rate > 80:
                        response_parts.append(f"\n🎯 Taux de correspondance: {match_rate:.1f}% - Excellente corrélation")
                    elif match_rate > 50:
                        response_parts.append(f"\n🟡 Taux de correspondance: {match_rate:.1f}% - Corrélation partielle")
                    else:
                        response_parts.append(f"\n🔴 Taux de correspondance: {match_rate:.1f}% - Faible corrélation")
            
            # Actions recommandées
            response_parts.append(f"\n\n🎯 ACTIONS RECOMMANDÉES:")
            
            if not financial_data['amounts'] and not financial_data['invoices']:
                response_parts.append("📝 Aucune donnée financière claire détectée - vérifiez le format du fichier")
            elif compare_with_sage and len(correlations.get('matching_invoices', [])) == 0:
                response_parts.append("🔍 Aucune correspondance Sage - vérifiez les références et montants")
            elif financial_data['amounts']:
                response_parts.append("✅ Données financières extraites - prêtes pour l'analyse comptable")
            
            if analysis_metadata.get('type') in ['excel', 'csv'] and analysis_metadata.get('potential_financial_data'):
                response_parts.append("📊 Données structurées détectées - import possible vers Sage")
            
            return "\n".join(response_parts)
            
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse du fichier: {str(e)}")
            return f"❌ Erreur lors de l'analyse du fichier: {str(e)}"

class CompareFilesInput(BaseModel):
    """Input schema for comparing multiple files"""
    file_ids: List[int] = Field(..., description="IDs des fichiers à comparer")
    comparison_type: Optional[str] = Field("financial", description="Type de comparaison (financial, structural)")
    business_id: Optional[str] = Field(None, description="Sage business ID")

class CompareFilesTool(SageBaseTool):
    name: str = "compare_files"
    description: str = "Compare plusieurs fichiers et identifie les différences/similitudes"
    args_schema: Type[BaseModel] = CompareFilesInput

    def _run(self, file_ids: List[int], comparison_type: Optional[str] = "financial",
             business_id: Optional[str] = None) -> str:
        try:
            credentials = self.get_credentials()
            if not credentials:
                return "❌ Erreur: Aucune connexion Sage détectée. Veuillez vous connecter à Sage d'abord."
            
            if len(file_ids) < 2:
                return "❌ Au moins 2 fichiers sont nécessaires pour la comparaison."
            
            # Récupérer les fichiers
            files = []
            for file_id in file_ids:
                file_attachment = FileAttachment.query.get(file_id)
                if file_attachment and file_attachment.is_processed:
                    files.append(file_attachment)
            
            if len(files) < 2:
                return f"❌ Seulement {len(files)} fichier(s) traité(s) trouvé(s) sur {len(file_ids)} demandé(s)."
            
            response_parts = [f"🔄 Comparaison de {len(files)} fichiers:"]
            
            # Lister les fichiers
            for i, file_attachment in enumerate(files, 1):
                response_parts.append(f"{i}. {file_attachment.original_filename} ({file_attachment.get_analysis_metadata().get('type', 'Inconnu')})")
            
            # Analyse comparative des métadonnées
            response_parts.append(f"\n📊 ANALYSE COMPARATIVE:")
            
            types = [f.get_analysis_metadata().get('type') for f in files]
            unique_types = set(types)
            if len(unique_types) == 1:
                response_parts.append(f"✅ Tous les fichiers sont du même type: {list(unique_types)[0]}")
            else:
                response_parts.append(f"📝 Types de fichiers mélangés: {', '.join(unique_types)}")
            
            # Comparaison financière
            if comparison_type == "financial":
                all_financial_data = []
                
                for file_attachment in files:
                    analysis_tool = AnalyzeFileTool()
                    financial_data = analysis_tool._extract_financial_data_from_content(
                        file_attachment.processed_content or "",
                        file_attachment.get_analysis_metadata().get('type', '')
                    )
                    all_financial_data.append({
                        'filename': file_attachment.original_filename,
                        'data': financial_data
                    })
                
                # Comparer les montants
                response_parts.append(f"\n💰 COMPARAISON DES MONTANTS:")
                for i, file_data in enumerate(all_financial_data):
                    amounts = file_data['data']['amounts']
                    total = sum(amounts) if amounts else 0
                    response_parts.append(f"{i+1}. {file_data['filename']}: {len(amounts)} montants, total: {total:.2f}€")
                
                # Rechercher des montants communs
                common_amounts = []
                if len(all_financial_data) >= 2:
                    amounts1 = set(all_financial_data[0]['data']['amounts'])
                    amounts2 = set(all_financial_data[1]['data']['amounts'])
                    common_amounts = amounts1.intersection(amounts2)
                    
                    if common_amounts:
                        response_parts.append(f"\n🔗 MONTANTS COMMUNS ({len(common_amounts)}):")
                        for amount in list(common_amounts)[:5]:
                            response_parts.append(f"  • {amount:.2f}€")
                
                # Comparer les références
                all_invoices = []
                for file_data in all_financial_data:
                    all_invoices.extend(file_data['data']['invoices'])
                
                if all_invoices:
                    unique_invoices = set(all_invoices)
                    response_parts.append(f"\n🧾 RÉFÉRENCES DE FACTURES:")
                    response_parts.append(f"Total: {len(all_invoices)} | Uniques: {len(unique_invoices)}")
                    
                    if len(all_invoices) > len(unique_invoices):
                        response_parts.append(f"⚠️ {len(all_invoices) - len(unique_invoices)} doublons détectés")
            
            # Recommandations
            response_parts.append(f"\n🎯 RECOMMANDATIONS:")
            
            if len(set(types)) > 1:
                response_parts.append("📝 Fichiers de types différents - harmoniser le format si possible")
            
            if comparison_type == "financial" and common_amounts:
                response_parts.append(f"🔍 {len(common_amounts)} montants communs trouvés - vérifiez les doublons")
            
            total_files_with_financial_data = sum(1 for f in files if f.get_analysis_metadata().get('potential_financial_data'))
            if total_files_with_financial_data > 1:
                response_parts.append("💼 Plusieurs fichiers financiers détectés - consolidation recommandée")
            
            return "\n".join(response_parts)
            
        except Exception as e:
            logger.error(f"Erreur lors de la comparaison des fichiers: {str(e)}")
            return f"❌ Erreur lors de la comparaison: {str(e)}"

# Ajouter les outils à la liste des outils Sage
SAGE_FILE_TOOLS = [
    AnalyzeFileTool(),
    CompareFilesTool()
]