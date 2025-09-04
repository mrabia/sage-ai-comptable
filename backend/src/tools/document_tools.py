import logging
from typing import Dict, Any, Optional, List
from crewai.tools import BaseTool
from src.models.document import Document
from src.models.user import db
from src.services.document_processor import DocumentProcessor

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
            # Récupérer le document
            document = Document.query.get(document_id)
            if not document:
                return f"Erreur: Document {document_id} non trouvé"
            
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
            # Récupérer le document
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

