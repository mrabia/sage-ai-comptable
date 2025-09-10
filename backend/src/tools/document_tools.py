import logging
import json
from typing import Dict, Any, Optional, List
from src.models.document import Document
from src.models.user import db, FileAttachment
from src.services.document_processor import DocumentProcessor

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

class DocumentAnalysisTool(BaseTool):
    """Outil pour analyser un document uploadé"""
    
    name: str = "document_analysis"
    description: str = """
    Analyse un document uploadé par l'utilisateur et extrait les données pertinentes.
    
    Paramètres:
    - document_id: ID du document à analyser
    
    Retourne les données extraites du document avec un score de confiance.
    """
    
    def _run(self, document_id: int) -> str:
        try:
            print(f"🔍 DocumentAnalysisTool: Analyzing file with ID {document_id}")
            
            # D'abord chercher dans FileAttachment (nouveau système)
            file_attachment = FileAttachment.query.get(document_id)
            if file_attachment:
                print(f"✅ Found FileAttachment: {file_attachment.original_filename}")
                
                # Si pas de contenu traité, on traite maintenant
                if not file_attachment.processed_content:
                    print("⚠️ No processed content, processing file now...")
                    return self._process_file_attachment(file_attachment)
                else:
                    print("✅ Using existing processed content")
                    return self._format_file_attachment_analysis(file_attachment)
            
            # Fallback vers l'ancien système Document
            document = Document.query.get(document_id)
            if not document:
                return f"Erreur: Document {document_id} non trouvé"
            
            print(f"✅ Found Document: {document.original_filename}")
            
            # Vérifier le statut de traitement
            if document.processing_status == 'pending':
                return f"Document {document_id} en cours de traitement. Veuillez patienter."
            
            if document.processing_status == 'failed':
                return f"Échec du traitement du document {document_id}. Erreur: {document.extracted_data.get('error', 'Erreur inconnue') if document.extracted_data else 'Erreur inconnue'}"
            
            if document.processing_status != 'completed':
                return f"Document {document_id} non traité. Statut: {document.processing_status}"
            
            # Récupérer les données extraites
            if not document.extracted_data:
                return f"Aucune donnée extraite pour le document {document_id}"
            
            # Formater les résultats pour l'agent
            result = {
                'document_id': document_id,
                'original_filename': document.original_filename,
                'file_type': document.file_type,
                'confidence_score': document.confidence_score,
                'extracted_data': document.extracted_data
            }
            
            # Créer un résumé textuel pour l'agent
            summary = f"Document analysé: {document.original_filename} (Type: {document.file_type})\n"
            summary += f"Score de confiance: {document.confidence_score}%\n\n"
            
            # Ajouter les détails selon le type de données
            if 'invoice_data' in document.extracted_data:
                invoice = document.extracted_data['invoice_data']
                summary += "=== FACTURE DÉTECTÉE ===\n"
                if invoice.get('invoice_number'):
                    summary += f"Numéro: {invoice['invoice_number']}\n"
                if invoice.get('invoice_date'):
                    summary += f"Date: {invoice['invoice_date']}\n"
                if invoice.get('client_name'):
                    summary += f"Client: {invoice['client_name']}\n"
                if invoice.get('total_ttc'):
                    summary += f"Total TTC: {invoice['total_ttc']}€\n"
                if invoice.get('total_ht'):
                    summary += f"Total HT: {invoice['total_ht']}€\n"
                if invoice.get('tva_amount'):
                    summary += f"TVA: {invoice['tva_amount']}€\n"
                
                if invoice.get('line_items'):
                    summary += f"\nLignes de détail ({len(invoice['line_items'])}):\n"
                    for item in invoice['line_items'][:3]:  # Afficher max 3 lignes
                        summary += f"- {item.get('description', 'N/A')} x{item.get('quantity', 1)} = {item.get('total', 0)}€\n"
            
            elif 'clients_data' in document.extracted_data:
                clients = document.extracted_data['clients_data']
                summary += f"=== DONNÉES CLIENTS DÉTECTÉES ===\n"
                summary += f"Nombre de clients: {clients.get('total_count', 0)}\n"
                
                if clients.get('clients'):
                    summary += "\nExemples de clients:\n"
                    for client in clients['clients'][:3]:  # Afficher max 3 clients
                        name = client.get('name', 'N/A')
                        email = client.get('email', 'N/A')
                        summary += f"- {name} ({email})\n"
            
            elif 'products_data' in document.extracted_data:
                products = document.extracted_data['products_data']
                summary += f"=== DONNÉES PRODUITS DÉTECTÉES ===\n"
                summary += f"Nombre de produits: {products.get('total_count', 0)}\n"
                
                if products.get('products'):
                    summary += "\nExemples de produits:\n"
                    for product in products['products'][:3]:  # Afficher max 3 produits
                        name = product.get('name', 'N/A')
                        price = product.get('price', 'N/A')
                        summary += f"- {name} ({price})\n"
            
            else:
                summary += "=== DONNÉES GÉNÉRIQUES ===\n"
                if document.extracted_text:
                    text_preview = document.extracted_text[:200] + "..." if len(document.extracted_text) > 200 else document.extracted_text
                    summary += f"Texte extrait: {text_preview}\n"
            
            return summary
            
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse du document: {e}")
            return f"Erreur lors de l'analyse du document {document_id}: {str(e)}"
    
    def _process_file_attachment(self, file_attachment: FileAttachment) -> str:
        """Traite un FileAttachment en utilisant le FileProcessorService"""
        try:
            from src.services.file_processor import file_processor
            
            print(f"🔄 Processing file: {file_attachment.file_path}")
            
            # Traiter le fichier avec le FileProcessorService 
            analysis = file_processor.process_file(file_attachment.file_path)
            
            if 'error' in analysis:
                file_attachment.processing_error = analysis['error']
                file_attachment.is_processed = False
                print(f"❌ Processing error: {analysis['error']}")
            else:
                # Sauvegarder l'analyse dans processed_content
                file_attachment.processed_content = json.dumps(analysis, ensure_ascii=False)
                file_attachment.set_analysis_metadata(analysis)
                file_attachment.is_processed = True
                print("✅ File processed successfully")
            
            # Sauvegarder les changements
            db.session.commit()
            
            return self._format_file_attachment_analysis(file_attachment)
            
        except Exception as e:
            logger.error(f"Erreur lors du traitement du FileAttachment: {e}")
            return f"Erreur lors du traitement du fichier: {str(e)}"
    
    def _format_file_attachment_analysis(self, file_attachment: FileAttachment) -> str:
        """Formate l'analyse d'un FileAttachment pour l'agent"""
        try:
            summary = f"Document analysé: {file_attachment.original_filename}\n"
            summary += f"Type: {file_attachment.file_type}\n"
            summary += f"Taille: {file_attachment.file_size} bytes\n"
            summary += f"Upload: {file_attachment.upload_timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            
            if file_attachment.processing_error:
                summary += f"❌ Erreur de traitement: {file_attachment.processing_error}\n"
                return summary
            
            if not file_attachment.processed_content:
                summary += "⚠️ Aucun contenu traité disponible.\n"
                return summary
            
            # Analyser le contenu traité
            try:
                analysis = json.loads(file_attachment.processed_content)
                
                if analysis.get('type') == 'excel':
                    summary += "=== FICHIER EXCEL DÉTECTÉ ===\n"
                    summary += f"Nombre de feuilles: {analysis.get('sheet_count', 0)}\n"
                    
                    if analysis.get('summary', {}).get('potential_financial_data'):
                        summary += "💰 DONNÉES FINANCIÈRES DÉTECTÉES\n\n"
                    
                    # Détails des feuilles
                    for sheet_name, sheet_info in analysis.get('sheets', {}).items():
                        summary += f"📊 Feuille '{sheet_name}':\n"
                        summary += f"  - {sheet_info.get('rows', 0)} lignes × {sheet_info.get('columns', 0)} colonnes\n"
                        
                        if sheet_info.get('has_financial_indicators'):
                            summary += "  - 💰 Indicateurs financiers détectés\n"
                        
                        # Colonnes
                        columns = sheet_info.get('column_names', [])[:5]  # Max 5 colonnes
                        if columns:
                            summary += f"  - Colonnes: {', '.join(columns)}\n"
                            if len(sheet_info.get('column_names', [])) > 5:
                                summary += f"    ... et {len(sheet_info.get('column_names', [])) - 5} autres\n"
                        
                        # Données échantillon
                        sample_data = sheet_info.get('sample_data', {})
                        if sample_data:
                            summary += "  - Échantillon de données:\n"
                            for col, values in list(sample_data.items())[:3]:  # Max 3 colonnes
                                if values:
                                    summary += f"    {col}: {', '.join(str(v) for v in values[:2])}\n"
                        summary += "\n"
                    
                    # Analyse des colonnes numériques
                    numeric_found = False
                    for sheet_name, sheet_info in analysis.get('sheets', {}).items():
                        if sheet_info.get('numeric_columns'):
                            if not numeric_found:
                                summary += "📈 DONNÉES NUMÉRIQUES:\n"
                                numeric_found = True
                            summary += f"  - {sheet_name}: {', '.join(sheet_info['numeric_columns'])}\n"
                    
                    if numeric_found:
                        summary += "\n"
                    
                    summary += "✅ PRÊT POUR ANALYSE COMPTABLE\n"
                    summary += "Ce fichier Excel contient des données structurées qui peuvent être:\n"
                    summary += "- Analysées pour déclaration TVA\n"
                    summary += "- Importées dans Sage\n"
                    summary += "- Utilisées pour générer des rapports\n"
                    
                elif analysis.get('type') == 'csv':
                    summary += "=== FICHIER CSV DÉTECTÉ ===\n"
                    summary += f"{analysis.get('rows', 0)} lignes × {analysis.get('columns', 0)} colonnes\n"
                    summary += f"Encodage: {analysis.get('encoding', 'N/A')}\n"
                    summary += f"Séparateur: '{analysis.get('separator', 'N/A')}'\n\n"
                    
                    columns = analysis.get('column_names', [])[:5]
                    if columns:
                        summary += f"Colonnes: {', '.join(columns)}\n"
                        if len(analysis.get('column_names', [])) > 5:
                            summary += f"... et {len(analysis.get('column_names', [])) - 5} autres\n"
                    
                    if analysis.get('potential_financial_data'):
                        summary += "💰 DONNÉES FINANCIÈRES DÉTECTÉES\n"
                
                elif analysis.get('type') == 'pdf':
                    summary += "=== FICHIER PDF DÉTECTÉ ===\n"
                    summary += f"Pages: {analysis.get('page_count', 0)}\n"
                    
                    if analysis.get('potential_financial_document'):
                        summary += "💰 DOCUMENT FINANCIER POTENTIEL\n"
                    
                    if analysis.get('has_tables'):
                        summary += f"📊 {analysis.get('tables_count', 0)} tableau(x) détecté(s)\n"
                    
                    if analysis.get('text_sample'):
                        summary += f"\nExtrait: {analysis['text_sample'][:200]}...\n"
                
                else:
                    summary += f"=== FICHIER {analysis.get('type', 'INCONNU').upper()} ===\n"
                    summary += "Analyse générique effectuée.\n"
                
            except json.JSONDecodeError as e:
                summary += f"❌ Erreur lors de l'analyse JSON: {str(e)}\n"
            
            return summary
            
        except Exception as e:
            logger.error(f"Erreur lors du formatage de l'analyse: {e}")
            return f"Erreur lors du formatage de l'analyse: {str(e)}"

class InvoiceExtractionTool(BaseTool):
    """Outil spécialisé pour extraire les données de factures"""
    
    name: str = "invoice_extraction"
    description: str = """
    Extrait spécifiquement les données comptables d'une facture uploadée.
    
    Paramètres:
    - document_id: ID du document facture à analyser
    
    Retourne les données de facture structurées pour intégration dans Sage.
    """
    
    def _run(self, document_id: int) -> str:
        try:
            print(f"🔍 InvoiceExtractionTool: Processing file with ID {document_id}")
            
            # D'abord chercher dans FileAttachment (nouveau système)
            file_attachment = FileAttachment.query.get(document_id)
            if file_attachment:
                print(f"✅ Found FileAttachment: {file_attachment.original_filename}")
                
                # Si pas de contenu traité, traiter d'abord
                if not file_attachment.processed_content:
                    print("⚠️ No processed content, processing file first...")
                    doc_tool = DocumentAnalysisTool()
                    doc_tool._process_file_attachment(file_attachment)
                    # Recharger depuis la DB
                    db.session.refresh(file_attachment)
                
                # Analyser pour données de facture
                return self._extract_invoice_from_file_attachment(file_attachment)
            
            # Fallback vers DocumentProcessor
            processor = DocumentProcessor()
            accounting_data = processor.extract_accounting_data(document_id)
            
            if 'error' in accounting_data:
                return f"Erreur: {accounting_data['error']}"
            
            if accounting_data.get('type') != 'invoice':
                return f"Le document {document_id} ne semble pas être une facture. Type détecté: {accounting_data.get('type', 'inconnu')}"
            
            # Formater les données pour l'agent
            summary = f"=== DONNÉES DE FACTURE EXTRAITES ===\n"
            summary += f"Document: {accounting_data.get('original_filename', 'N/A')}\n"
            summary += f"Confiance: {accounting_data.get('confidence_score', 0)}%\n\n"
            
            # Informations client
            if accounting_data.get('client_name'):
                summary += f"CLIENT:\n"
                summary += f"- Nom: {accounting_data['client_name']}\n"
                if accounting_data.get('client_address'):
                    summary += f"- Adresse: {accounting_data['client_address']}\n"
                if accounting_data.get('client_email'):
                    summary += f"- Email: {accounting_data['client_email']}\n"
                summary += "\n"
            
            # Informations facture
            summary += f"FACTURE:\n"
            if accounting_data.get('invoice_number'):
                summary += f"- Numéro: {accounting_data['invoice_number']}\n"
            if accounting_data.get('invoice_date'):
                summary += f"- Date: {accounting_data['invoice_date']}\n"
            if accounting_data.get('due_date'):
                summary += f"- Échéance: {accounting_data['due_date']}\n"
            summary += "\n"
            
            # Montants
            summary += f"MONTANTS:\n"
            if accounting_data.get('total_ht'):
                summary += f"- Total HT: {accounting_data['total_ht']}€\n"
            if accounting_data.get('tva_amount'):
                summary += f"- TVA: {accounting_data['tva_amount']}€\n"
            if accounting_data.get('total_ttc'):
                summary += f"- Total TTC: {accounting_data['total_ttc']}€\n"
            summary += "\n"
            
            # Lignes de détail
            if accounting_data.get('line_items'):
                summary += f"DÉTAIL ({len(accounting_data['line_items'])} lignes):\n"
                for i, item in enumerate(accounting_data['line_items'][:5], 1):  # Max 5 lignes
                    desc = item.get('description', 'N/A')
                    qty = item.get('quantity', 1)
                    price = item.get('unit_price', 0)
                    total = item.get('total', 0)
                    summary += f"{i}. {desc} - Qté: {qty} - Prix: {price}€ - Total: {total}€\n"
                
                if len(accounting_data['line_items']) > 5:
                    summary += f"... et {len(accounting_data['line_items']) - 5} autres lignes\n"
            
            summary += "\n=== PRÊT POUR INTÉGRATION SAGE ===\n"
            summary += "Ces données peuvent être utilisées pour créer automatiquement:\n"
            summary += "- Un nouveau client (si nécessaire)\n"
            summary += "- Une facture avec lignes de détail\n"
            summary += "- Les écritures comptables associées\n"
            
            return summary
            
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction de facture: {e}")
            return f"Erreur lors de l'extraction de la facture {document_id}: {str(e)}"
    
    def _extract_invoice_from_file_attachment(self, file_attachment: FileAttachment) -> str:
        """Extrait les données de facture depuis un FileAttachment"""
        try:
            if not file_attachment.processed_content:
                return "❌ Fichier non traité. Impossible d'extraire les données de facture."
            
            analysis = json.loads(file_attachment.processed_content)
            
            summary = f"=== EXTRACTION DE FACTURE ===\n"
            summary += f"Document: {file_attachment.original_filename}\n"
            summary += f"Type: {file_attachment.file_type}\n\n"
            
            # Analyser selon le type de fichier
            if analysis.get('type') == 'excel':
                summary += "📊 ANALYSE EXCEL POUR FACTURE:\n"
                
                # Chercher des indicateurs de facture dans les feuilles
                invoice_indicators = []
                for sheet_name, sheet_info in analysis.get('sheets', {}).items():
                    columns = [col.lower() for col in sheet_info.get('column_names', [])]
                    
                    # Indicateurs de facture
                    facture_keywords = ['facture', 'invoice', 'numero', 'number', 'client', 'montant', 'amount', 'total', 'tva', 'vat', 'ht', 'ttc']
                    found_keywords = [kw for kw in facture_keywords if any(kw in col for col in columns)]
                    
                    if found_keywords:
                        invoice_indicators.append({
                            'sheet': sheet_name,
                            'keywords': found_keywords,
                            'rows': sheet_info.get('rows', 0),
                            'columns': sheet_info.get('columns', 0)
                        })
                
                if invoice_indicators:
                    summary += "✅ DONNÉES DE FACTURE POTENTIELLES TROUVÉES:\n\n"
                    
                    for indicator in invoice_indicators:
                        summary += f"📋 Feuille '{indicator['sheet']}':\n"
                        summary += f"  - {indicator['rows']} lignes × {indicator['columns']} colonnes\n"
                        summary += f"  - Mots-clés trouvés: {', '.join(indicator['keywords'])}\n"
                        summary += f"  - Score de confiance facture: {len(indicator['keywords']) * 10}%\n\n"
                    
                    summary += "🔧 EXTRACTION AUTOMATIQUE:\n"
                    summary += "Pour extraire automatiquement les données de facture:\n"
                    summary += "1. Utiliser la commande: create_invoice_from_data\n"
                    summary += "2. Spécifier la feuille Excel à utiliser\n"
                    summary += "3. Mapper les colonnes aux champs de facture\n\n"
                    
                    summary += "💡 COLONNES DÉTECTÉES POUR MAPPING:\n"
                    best_sheet = max(invoice_indicators, key=lambda x: len(x['keywords']))
                    sheet_info = analysis.get('sheets', {}).get(best_sheet['sheet'], {})
                    columns = sheet_info.get('column_names', [])[:10]  # Max 10 colonnes
                    for i, col in enumerate(columns, 1):
                        summary += f"{i}. {col}\n"
                    
                else:
                    summary += "⚠️ PAS DE DONNÉES DE FACTURE ÉVIDENTES\n"
                    summary += "Ce fichier Excel ne semble pas contenir de données de facture structurées.\n"
                    summary += "Il pourrait contenir:\n"
                    summary += "- Des données de stock ou produits\n"
                    summary += "- Des informations clients\n"
                    summary += "- Des rapports financiers généraux\n"
            
            elif analysis.get('type') == 'pdf':
                summary += "📄 ANALYSE PDF POUR FACTURE:\n"
                
                if analysis.get('potential_financial_document'):
                    summary += "✅ Document financier détecté\n"
                    
                    if analysis.get('has_tables'):
                        summary += f"📊 {analysis.get('tables_count', 0)} tableau(x) trouvé(s)\n"
                        summary += "Ces tableaux pourraient contenir des lignes de facture.\n\n"
                    
                    text_sample = analysis.get('text_sample', '')
                    if text_sample:
                        summary += "📝 EXTRAIT DU TEXTE:\n"
                        summary += f"{text_sample[:300]}...\n\n"
                        
                        # Chercher des patterns de facture
                        invoice_patterns = ['facture n°', 'invoice no', 'total ttc', 'total ht', 'tva']
                        found_patterns = [pattern for pattern in invoice_patterns if pattern.lower() in text_sample.lower()]
                        
                        if found_patterns:
                            summary += f"✅ Patterns de facture trouvés: {', '.join(found_patterns)}\n"
                        else:
                            summary += "⚠️ Aucun pattern de facture évident trouvé\n"
                    
                    summary += "\n🔧 EXTRACTION MANUELLE REQUISE:\n"
                    summary += "Pour les PDF, une validation manuelle est recommandée.\n"
                    summary += "Utilisez les données extraites pour créer une facture manuellement.\n"
                else:
                    summary += "❌ Ce PDF ne semble pas être une facture\n"
            
            elif analysis.get('type') == 'csv':
                summary += "📊 ANALYSE CSV POUR FACTURE:\n"
                
                columns = [col.lower() for col in analysis.get('column_names', [])]
                facture_keywords = ['facture', 'invoice', 'numero', 'client', 'montant', 'total', 'tva', 'ht', 'ttc']
                found_keywords = [kw for kw in facture_keywords if any(kw in col for col in columns)]
                
                if found_keywords:
                    summary += f"✅ Colonnes de facture trouvées: {', '.join(found_keywords)}\n"
                    summary += f"📊 {analysis.get('rows', 0)} lignes de données\n\n"
                    
                    summary += "🔧 MAPPING DES COLONNES:\n"
                    for col in analysis.get('column_names', [])[:10]:
                        summary += f"- {col}\n"
                    
                    summary += "\nUtilisez ces colonnes pour créer automatiquement des factures.\n"
                else:
                    summary += "⚠️ Pas de colonnes de facture évidentes dans ce CSV\n"
            
            else:
                summary += f"❌ Type de fichier '{analysis.get('type')}' non supporté pour extraction de facture\n"
            
            return summary
            
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction de facture depuis FileAttachment: {e}")
            return f"Erreur lors de l'extraction de facture: {str(e)}"

class ClientImportTool(BaseTool):
    """Outil pour importer des clients depuis un document"""
    
    name: str = "client_import"
    description: str = """
    Extrait et prépare les données clients d'un document (CSV, Excel) pour import dans Sage.
    
    Paramètres:
    - document_id: ID du document contenant les données clients
    
    Retourne la liste des clients prêts à être importés.
    """
    
    def _run(self, document_id: int) -> str:
        try:
            processor = DocumentProcessor()
            accounting_data = processor.extract_accounting_data(document_id)
            
            if 'error' in accounting_data:
                return f"Erreur: {accounting_data['error']}"
            
            if accounting_data.get('type') != 'clients_import':
                return f"Le document {document_id} ne contient pas de données clients. Type détecté: {accounting_data.get('type', 'inconnu')}"
            
            clients = accounting_data.get('clients', [])
            if not clients:
                return f"Aucun client trouvé dans le document {document_id}"
            
            # Formater les données pour l'agent
            summary = f"=== DONNÉES CLIENTS EXTRAITES ===\n"
            summary += f"Document: {accounting_data.get('original_filename', 'N/A')}\n"
            summary += f"Nombre de clients: {len(clients)}\n"
            summary += f"Confiance: {accounting_data.get('confidence_score', 0)}%\n\n"
            
            # Analyser les champs disponibles
            available_fields = set()
            for client in clients:
                available_fields.update(client.keys())
            
            summary += f"Champs détectés: {', '.join(sorted(available_fields))}\n\n"
            
            # Afficher quelques exemples
            summary += "EXEMPLES DE CLIENTS:\n"
            for i, client in enumerate(clients[:5], 1):  # Max 5 exemples
                summary += f"{i}. "
                if client.get('name'):
                    summary += f"Nom: {client['name']}"
                if client.get('company'):
                    summary += f" - Société: {client['company']}"
                if client.get('email'):
                    summary += f" - Email: {client['email']}"
                if client.get('phone'):
                    summary += f" - Tél: {client['phone']}"
                summary += "\n"
            
            if len(clients) > 5:
                summary += f"... et {len(clients) - 5} autres clients\n"
            
            # Statistiques de qualité
            complete_clients = sum(1 for client in clients if client.get('name') and client.get('email'))
            summary += f"\nQUALITÉ DES DONNÉES:\n"
            summary += f"- Clients avec nom et email: {complete_clients}/{len(clients)}\n"
            
            emails_count = sum(1 for client in clients if client.get('email'))
            phones_count = sum(1 for client in clients if client.get('phone'))
            addresses_count = sum(1 for client in clients if client.get('address'))
            
            summary += f"- Avec email: {emails_count}\n"
            summary += f"- Avec téléphone: {phones_count}\n"
            summary += f"- Avec adresse: {addresses_count}\n"
            
            summary += "\n=== PRÊT POUR IMPORT SAGE ===\n"
            summary += f"Ces {len(clients)} clients peuvent être importés automatiquement dans Sage.\n"
            summary += "L'import créera les fiches clients avec toutes les informations disponibles.\n"
            
            return summary
            
        except Exception as e:
            logger.error(f"Erreur lors de l'import de clients: {e}")
            return f"Erreur lors de l'import de clients du document {document_id}: {str(e)}"

class ProductImportTool(BaseTool):
    """Outil pour importer des produits depuis un document"""
    
    name: str = "product_import"
    description: str = """
    Extrait et prépare les données produits d'un document (CSV, Excel) pour import dans Sage.
    
    Paramètres:
    - document_id: ID du document contenant les données produits
    
    Retourne la liste des produits prêts à être importés.
    """
    
    def _run(self, document_id: int) -> str:
        try:
            processor = DocumentProcessor()
            accounting_data = processor.extract_accounting_data(document_id)
            
            if 'error' in accounting_data:
                return f"Erreur: {accounting_data['error']}"
            
            if accounting_data.get('type') != 'products_import':
                return f"Le document {document_id} ne contient pas de données produits. Type détecté: {accounting_data.get('type', 'inconnu')}"
            
            products = accounting_data.get('products', [])
            if not products:
                return f"Aucun produit trouvé dans le document {document_id}"
            
            # Formater les données pour l'agent
            summary = f"=== DONNÉES PRODUITS EXTRAITES ===\n"
            summary += f"Document: {accounting_data.get('original_filename', 'N/A')}\n"
            summary += f"Nombre de produits: {len(products)}\n"
            summary += f"Confiance: {accounting_data.get('confidence_score', 0)}%\n\n"
            
            # Analyser les champs disponibles
            available_fields = set()
            for product in products:
                available_fields.update(product.keys())
            
            summary += f"Champs détectés: {', '.join(sorted(available_fields))}\n\n"
            
            # Afficher quelques exemples
            summary += "EXEMPLES DE PRODUITS:\n"
            for i, product in enumerate(products[:5], 1):  # Max 5 exemples
                summary += f"{i}. "
                if product.get('name'):
                    summary += f"Nom: {product['name']}"
                if product.get('reference'):
                    summary += f" - Réf: {product['reference']}"
                if product.get('price'):
                    summary += f" - Prix: {product['price']}€"
                if product.get('vat_rate'):
                    summary += f" - TVA: {product['vat_rate']}%"
                summary += "\n"
            
            if len(products) > 5:
                summary += f"... et {len(products) - 5} autres produits\n"
            
            # Statistiques de qualité
            complete_products = sum(1 for product in products if product.get('name') and product.get('price'))
            summary += f"\nQUALITÉ DES DONNÉES:\n"
            summary += f"- Produits avec nom et prix: {complete_products}/{len(products)}\n"
            
            refs_count = sum(1 for product in products if product.get('reference'))
            descriptions_count = sum(1 for product in products if product.get('description'))
            categories_count = sum(1 for product in products if product.get('category'))
            
            summary += f"- Avec référence: {refs_count}\n"
            summary += f"- Avec description: {descriptions_count}\n"
            summary += f"- Avec catégorie: {categories_count}\n"
            
            # Analyse des prix
            prices = [float(p.get('price', 0)) for p in products if p.get('price')]
            if prices:
                min_price = min(prices)
                max_price = max(prices)
                avg_price = sum(prices) / len(prices)
                summary += f"- Prix: min {min_price}€, max {max_price}€, moyenne {avg_price:.2f}€\n"
            
            summary += "\n=== PRÊT POUR IMPORT SAGE ===\n"
            summary += f"Ces {len(products)} produits peuvent être importés automatiquement dans Sage.\n"
            summary += "L'import créera les fiches produits avec prix, TVA et catégories.\n"
            
            return summary
            
        except Exception as e:
            logger.error(f"Erreur lors de l'import de produits: {e}")
            return f"Erreur lors de l'import de produits du document {document_id}: {str(e)}"

class DocumentValidationTool(BaseTool):
    """Outil pour valider la qualité des données extraites"""
    
    name: str = "document_validation"
    description: str = """
    Valide la qualité et la cohérence des données extraites d'un document.
    
    Paramètres:
    - document_id: ID du document à valider
    
    Retourne un rapport de validation avec recommandations.
    """
    
    def _run(self, document_id: int) -> str:
        try:
            print(f"🔍 DocumentValidationTool: Validating file with ID {document_id}")
            
            # D'abord chercher dans FileAttachment (nouveau système)
            file_attachment = FileAttachment.query.get(document_id)
            if file_attachment:
                print(f"✅ Found FileAttachment: {file_attachment.original_filename}")
                
                # Si pas de contenu traité, traiter d'abord
                if not file_attachment.processed_content:
                    print("⚠️ No processed content, processing file first...")
                    doc_tool = DocumentAnalysisTool()
                    doc_tool._process_file_attachment(file_attachment)
                    # Recharger depuis la DB
                    db.session.refresh(file_attachment)
                
                return self._validate_file_attachment(file_attachment)
            
            # Fallback vers l'ancien système Document
            document = Document.query.get(document_id)
            if not document:
                return f"Erreur: Document {document_id} non trouvé"
            
            if document.processing_status != 'completed':
                return f"Document {document_id} non traité. Impossible de valider."
            
            if not document.extracted_data:
                return f"Aucune donnée extraite pour le document {document_id}"
            
            # Rapport de validation
            report = f"=== RAPPORT DE VALIDATION ===\n"
            report += f"Document: {document.original_filename}\n"
            report += f"Type: {document.file_type}\n"
            report += f"Score de confiance global: {document.confidence_score}%\n\n"
            
            # Validation selon le type de données
            if 'invoice_data' in document.extracted_data:
                report += self._validate_invoice_data(document.extracted_data['invoice_data'])
            elif 'clients_data' in document.extracted_data:
                report += self._validate_clients_data(document.extracted_data['clients_data'])
            elif 'products_data' in document.extracted_data:
                report += self._validate_products_data(document.extracted_data['products_data'])
            else:
                report += "VALIDATION GÉNÉRIQUE:\n"
                report += f"- Texte extrait: {len(document.extracted_text)} caractères\n" if document.extracted_text else "- Aucun texte extrait\n"
                report += f"- Données structurées: {'Oui' if document.extracted_data else 'Non'}\n"
            
            # Recommandations générales
            report += "\nRECOMMANDATIONS:\n"
            
            if document.confidence_score < 50:
                report += "⚠️ Score de confiance faible. Vérifiez manuellement les données.\n"
            elif document.confidence_score < 80:
                report += "⚠️ Score de confiance moyen. Validation recommandée.\n"
            else:
                report += "✅ Score de confiance élevé. Données fiables.\n"
            
            if document.file_type == 'image' and document.confidence_score < 70:
                report += "💡 Pour les images, essayez d'améliorer la qualité (résolution, contraste).\n"
            
            if document.file_type == 'pdf' and not document.extracted_text:
                report += "⚠️ PDF sans texte détecté. Pourrait être une image scannée.\n"
            
            return report
            
        except Exception as e:
            logger.error(f"Erreur lors de la validation: {e}")
            return f"Erreur lors de la validation du document {document_id}: {str(e)}"
    
    def _validate_file_attachment(self, file_attachment: FileAttachment) -> str:
        """Valide un FileAttachment et ses données"""
        try:
            report = f"=== RAPPORT DE VALIDATION ===\n"
            report += f"Document: {file_attachment.original_filename}\n"
            report += f"Type: {file_attachment.file_type}\n"
            report += f"Taille: {file_attachment.file_size} bytes\n"
            report += f"Upload: {file_attachment.upload_timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            
            # Vérification du traitement
            if file_attachment.processing_error:
                report += f"❌ ERREUR DE TRAITEMENT:\n{file_attachment.processing_error}\n\n"
                report += "RECOMMANDATIONS:\n"
                report += "- Vérifiez le format du fichier\n"
                report += "- Réessayez l'upload avec un fichier plus petit\n"
                report += "- Contactez le support si le problème persiste\n"
                return report
            
            if not file_attachment.is_processed or not file_attachment.processed_content:
                report += "⚠️ FICHIER NON TRAITÉ\n"
                report += "Le fichier n'a pas encore été analysé.\n\n"
                report += "RECOMMANDATIONS:\n"
                report += "- Attendez quelques instants pour le traitement automatique\n"
                report += "- Relancez l'analyse si nécessaire\n"
                return report
            
            # Analyser le contenu traité
            try:
                analysis = json.loads(file_attachment.processed_content)
                
                report += "✅ TRAITEMENT TERMINÉ\n\n"
                
                # Validation selon le type
                if analysis.get('type') == 'excel':
                    report += self._validate_excel_analysis(analysis)
                elif analysis.get('type') == 'csv':
                    report += self._validate_csv_analysis(analysis)
                elif analysis.get('type') == 'pdf':
                    report += self._validate_pdf_analysis(analysis)
                else:
                    report += self._validate_generic_analysis(analysis)
                
                # Score de qualité global
                quality_score = self._calculate_quality_score(analysis, file_attachment)
                report += f"\n📊 SCORE DE QUALITÉ GLOBAL: {quality_score}%\n\n"
                
                # Recommandations générales
                report += "RECOMMANDATIONS:\n"
                
                if quality_score >= 80:
                    report += "✅ Excellente qualité. Données fiables pour traitement automatique.\n"
                elif quality_score >= 60:
                    report += "⚠️ Qualité correcte. Validation manuelle recommandée pour les données critiques.\n"
                elif quality_score >= 40:
                    report += "⚠️ Qualité moyenne. Vérification manuelle nécessaire.\n"
                else:
                    report += "❌ Qualité faible. Révision complète requise ou re-upload du fichier.\n"
                
                if file_attachment.file_type in ['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'application/vnd.ms-excel']:
                    report += "💡 Conseil Excel: Utilisez des en-têtes clairs et évitez les cellules fusionnées.\n"
                elif file_attachment.file_type == 'text/csv':
                    report += "💡 Conseil CSV: Vérifiez que le délimiteur et l'encodage sont corrects.\n"
                elif file_attachment.file_type == 'application/pdf':
                    report += "💡 Conseil PDF: Les PDF textuels donnent de meilleurs résultats que les scans.\n"
                
            except json.JSONDecodeError as e:
                report += f"❌ Erreur d'analyse des données: {str(e)}\n"
                report += "Le contenu traité semble corrompu. Relancez le traitement.\n"
            
            return report
            
        except Exception as e:
            logger.error(f"Erreur lors de la validation FileAttachment: {e}")
            return f"Erreur lors de la validation: {str(e)}"
    
    def _validate_excel_analysis(self, analysis: Dict[str, Any]) -> str:
        """Valide l'analyse d'un fichier Excel"""
        report = "VALIDATION EXCEL:\n"
        
        sheet_count = analysis.get('sheet_count', 0)
        report += f"✅ {sheet_count} feuille(s) analysée(s)\n"
        
        total_rows = analysis.get('summary', {}).get('total_rows', 0)
        total_columns = analysis.get('summary', {}).get('total_columns', 0)
        report += f"📊 Total: {total_rows} lignes × {total_columns} colonnes\n"
        
        if analysis.get('summary', {}).get('potential_financial_data'):
            report += "💰 Données financières détectées\n"
        
        # Analyser chaque feuille
        sheets = analysis.get('sheets', {})
        problematic_sheets = []
        good_sheets = []
        
        for sheet_name, sheet_info in sheets.items():
            rows = sheet_info.get('rows', 0)
            columns = sheet_info.get('columns', 0)
            
            if rows == 0:
                problematic_sheets.append(f"{sheet_name} (vide)")
            elif columns == 0:
                problematic_sheets.append(f"{sheet_name} (pas de colonnes)")
            elif rows < 2:
                problematic_sheets.append(f"{sheet_name} (pas de données)")
            else:
                good_sheets.append(sheet_name)
        
        if good_sheets:
            report += f"✅ Feuilles exploitables: {', '.join(good_sheets)}\n"
        
        if problematic_sheets:
            report += f"⚠️ Feuilles problématiques: {', '.join(problematic_sheets)}\n"
        
        return report
    
    def _validate_csv_analysis(self, analysis: Dict[str, Any]) -> str:
        """Valide l'analyse d'un fichier CSV"""
        report = "VALIDATION CSV:\n"
        
        rows = analysis.get('rows', 0)
        columns = analysis.get('columns', 0)
        
        if rows == 0:
            report += "❌ Fichier vide\n"
        elif rows < 2:
            report += "⚠️ Pas de données (en-têtes seulement)\n"
        else:
            report += f"✅ {rows} lignes de données\n"
        
        if columns == 0:
            report += "❌ Aucune colonne détectée\n"
        elif columns == 1:
            report += "⚠️ Une seule colonne (délimiteur incorrect?)\n"
        else:
            report += f"✅ {columns} colonnes détectées\n"
        
        encoding = analysis.get('encoding', 'unknown')
        separator = analysis.get('separator', 'unknown')
        report += f"📝 Encodage: {encoding}, Délimiteur: '{separator}'\n"
        
        if analysis.get('potential_financial_data'):
            report += "💰 Données financières potentielles\n"
        
        return report
    
    def _validate_pdf_analysis(self, analysis: Dict[str, Any]) -> str:
        """Valide l'analyse d'un fichier PDF"""
        report = "VALIDATION PDF:\n"
        
        page_count = analysis.get('page_count', 0)
        report += f"📄 {page_count} page(s)\n"
        
        if analysis.get('has_text'):
            report += f"✅ Texte extrait ({analysis.get('text_pages', 0)} pages avec texte)\n"
        else:
            report += "⚠️ Pas de texte extrait (document scanné?)\n"
        
        if analysis.get('has_tables'):
            report += f"📊 {analysis.get('tables_count', 0)} tableau(x) détecté(s)\n"
        else:
            report += "⚠️ Aucun tableau structuré détecté\n"
        
        if analysis.get('potential_financial_document'):
            report += "💰 Document financier potentiel\n"
        
        return report
    
    def _validate_generic_analysis(self, analysis: Dict[str, Any]) -> str:
        """Valide l'analyse générique d'un fichier"""
        report = f"VALIDATION {analysis.get('type', 'GÉNÉRIQUE').upper()}:\n"
        
        if 'error' in analysis:
            report += f"❌ Erreur: {analysis['error']}\n"
        else:
            report += "✅ Fichier traité avec succès\n"
        
        return report
    
    def _calculate_quality_score(self, analysis: Dict[str, Any], file_attachment: FileAttachment) -> int:
        """Calcule un score de qualité pour le fichier"""
        score = 0
        
        # Score de base
        if 'error' not in analysis:
            score += 20
        
        # Score selon le type
        if analysis.get('type') == 'excel':
            sheets = analysis.get('sheets', {})
            for sheet_info in sheets.values():
                if sheet_info.get('rows', 0) > 1:
                    score += 15
                if sheet_info.get('columns', 0) > 1:
                    score += 10
                if sheet_info.get('has_financial_indicators'):
                    score += 15
            score = min(score, 90)  # Max 90 pour Excel
        
        elif analysis.get('type') == 'csv':
            if analysis.get('rows', 0) > 1:
                score += 20
            if analysis.get('columns', 0) > 1:
                score += 20
            if analysis.get('potential_financial_data'):
                score += 20
            score = min(score, 80)  # Max 80 pour CSV
        
        elif analysis.get('type') == 'pdf':
            if analysis.get('has_text'):
                score += 20
            if analysis.get('has_tables'):
                score += 20
            if analysis.get('potential_financial_document'):
                score += 15
            score = min(score, 75)  # Max 75 pour PDF (plus difficile à traiter)
        
        # Bonus pour fichiers récents
        from datetime import datetime, timedelta
        if file_attachment.upload_timestamp > datetime.utcnow() - timedelta(hours=1):
            score += 5
        
        return min(score, 100)
    
    def _validate_invoice_data(self, invoice_data: Dict[str, Any]) -> str:
        """Valide les données de facture"""
        report = "VALIDATION FACTURE:\n"
        
        # Vérifier les champs obligatoires
        required_fields = ['invoice_number', 'client_name', 'total_ttc']
        missing_fields = [field for field in required_fields if not invoice_data.get(field)]
        
        if missing_fields:
            report += f"❌ Champs manquants: {', '.join(missing_fields)}\n"
        else:
            report += "✅ Champs obligatoires présents\n"
        
        # Vérifier la cohérence des montants
        ht = invoice_data.get('total_ht')
        tva = invoice_data.get('tva_amount')
        ttc = invoice_data.get('total_ttc')
        
        if ht and tva and ttc:
            calculated_ttc = ht + tva
            if abs(calculated_ttc - ttc) < 1:  # Tolérance de 1€
                report += "✅ Cohérence des montants validée\n"
            else:
                report += f"⚠️ Incohérence des montants: HT({ht}) + TVA({tva}) ≠ TTC({ttc})\n"
        else:
            report += "⚠️ Montants incomplets pour validation\n"
        
        # Vérifier les lignes de détail
        line_items = invoice_data.get('line_items', [])
        if line_items:
            report += f"✅ {len(line_items)} lignes de détail trouvées\n"
            
            # Vérifier la cohérence des totaux de lignes
            total_lines = sum(item.get('total', 0) for item in line_items)
            if ht and abs(total_lines - ht) < 1:
                report += "✅ Total des lignes cohérent avec HT\n"
            elif ht:
                report += f"⚠️ Total des lignes ({total_lines}) ≠ HT ({ht})\n"
        else:
            report += "⚠️ Aucune ligne de détail trouvée\n"
        
        return report
    
    def _validate_clients_data(self, clients_data: Dict[str, Any]) -> str:
        """Valide les données clients"""
        report = "VALIDATION CLIENTS:\n"
        
        clients = clients_data.get('clients', [])
        if not clients:
            return report + "❌ Aucun client trouvé\n"
        
        report += f"✅ {len(clients)} clients trouvés\n"
        
        # Analyser la qualité des données
        with_name = sum(1 for c in clients if c.get('name'))
        with_email = sum(1 for c in clients if c.get('email'))
        with_phone = sum(1 for c in clients if c.get('phone'))
        with_address = sum(1 for c in clients if c.get('address'))
        
        report += f"- Avec nom: {with_name}/{len(clients)} ({with_name/len(clients)*100:.1f}%)\n"
        report += f"- Avec email: {with_email}/{len(clients)} ({with_email/len(clients)*100:.1f}%)\n"
        report += f"- Avec téléphone: {with_phone}/{len(clients)} ({with_phone/len(clients)*100:.1f}%)\n"
        report += f"- Avec adresse: {with_address}/{len(clients)} ({with_address/len(clients)*100:.1f}%)\n"
        
        # Validation des emails
        valid_emails = 0
        for client in clients:
            email = client.get('email', '')
            if email and '@' in email and '.' in email:
                valid_emails += 1
        
        if with_email > 0:
            report += f"- Emails valides: {valid_emails}/{with_email} ({valid_emails/with_email*100:.1f}%)\n"
        
        return report
    
    def _validate_products_data(self, products_data: Dict[str, Any]) -> str:
        """Valide les données produits"""
        report = "VALIDATION PRODUITS:\n"
        
        products = products_data.get('products', [])
        if not products:
            return report + "❌ Aucun produit trouvé\n"
        
        report += f"✅ {len(products)} produits trouvés\n"
        
        # Analyser la qualité des données
        with_name = sum(1 for p in products if p.get('name'))
        with_price = sum(1 for p in products if p.get('price'))
        with_ref = sum(1 for p in products if p.get('reference'))
        with_desc = sum(1 for p in products if p.get('description'))
        
        report += f"- Avec nom: {with_name}/{len(products)} ({with_name/len(products)*100:.1f}%)\n"
        report += f"- Avec prix: {with_price}/{len(products)} ({with_price/len(products)*100:.1f}%)\n"
        report += f"- Avec référence: {with_ref}/{len(products)} ({with_ref/len(products)*100:.1f}%)\n"
        report += f"- Avec description: {with_desc}/{len(products)} ({with_desc/len(products)*100:.1f}%)\n"
        
        # Validation des prix
        valid_prices = 0
        for product in products:
            try:
                price = float(product.get('price', 0))
                if price > 0:
                    valid_prices += 1
            except (ValueError, TypeError):
                pass
        
        if with_price > 0:
            report += f"- Prix valides: {valid_prices}/{with_price} ({valid_prices/with_price*100:.1f}%)\n"
        
        return report

