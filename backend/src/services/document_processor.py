import os
import threading
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from src.models.document import Document
from src.models.user import db
# Graceful import for PDF processor
try:
    from src.services.pdf_processor import PDFProcessor, PDF_PROCESSING_AVAILABLE
    PDF_PROCESSOR_AVAILABLE = True
except ImportError:
    PDFProcessor = None
    PDF_PROCESSING_AVAILABLE = False
    PDF_PROCESSOR_AVAILABLE = False
from src.services.csv_processor import CSVProcessor
from src.services.excel_processor import ExcelProcessor
from src.services.invoice_extractor import InvoiceExtractor

# Graceful import for image processor
try:
    from src.services.image_processor import ImageProcessor, IMAGE_PROCESSING_AVAILABLE
    IMAGE_PROCESSOR_AVAILABLE = True
except ImportError:
    ImageProcessor = None
    IMAGE_PROCESSING_AVAILABLE = False
    IMAGE_PROCESSOR_AVAILABLE = False

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DocumentProcessor:
    """Service principal pour le traitement de documents"""
    
    def __init__(self):
        self.processors = {
            'csv': CSVProcessor(),
            'excel': ExcelProcessor()
        }
        
        # Add PDF processor only if available
        if PDF_PROCESSOR_AVAILABLE and PDFProcessor:
            self.processors['pdf'] = PDFProcessor()
        else:
            logger.warning("PDF processor not available - PDF processing will be skipped")
        
        # Add image processor only if available
        if IMAGE_PROCESSOR_AVAILABLE and ImageProcessor:
            self.processors['image'] = ImageProcessor()
        else:
            logger.warning("Image processor not available - image processing will be skipped")
            
        self.invoice_extractor = InvoiceExtractor()
    
    def process_document_async(self, document_id: int):
        """Lance le traitement d'un document en arrière-plan"""
        thread = threading.Thread(
            target=self._process_document_thread,
            args=(document_id,),
            daemon=True
        )
        thread.start()
        logger.info(f"Traitement asynchrone démarré pour le document {document_id}")
    
    def _process_document_thread(self, document_id: int):
        """Thread de traitement d'un document"""
        try:
            with db.app.app_context():
                self.process_document(document_id)
        except Exception as e:
            logger.error(f"Erreur dans le thread de traitement du document {document_id}: {e}")
    
    def process_document(self, document_id: int) -> Dict[str, Any]:
        """Traite un document et extrait les données"""
        try:
            # Récupérer le document
            document = Document.query.get(document_id)
            if not document:
                raise ValueError(f"Document {document_id} non trouvé")
            
            # Vérifier que le fichier existe
            if not os.path.exists(document.file_path):
                raise FileNotFoundError(f"Fichier {document.file_path} non trouvé")
            
            # Marquer le traitement comme démarré
            document.set_processing_status('processing')
            db.session.commit()
            
            logger.info(f"Début du traitement du document {document_id} ({document.file_type})")
            
            # Sélectionner le processeur approprié
            processor = self.processors.get(document.file_type)
            if not processor:
                raise ValueError(f"Aucun processeur disponible pour le type {document.file_type}")
            
            # Extraire le texte brut
            extracted_text = processor.extract_text(document.file_path)
            
            # Extraire les données structurées selon le type de document
            extracted_data = {}
            confidence_score = 50  # Score par défaut
            
            if document.file_type in ['pdf', 'image']:
                # Tenter d'extraire des données de facture
                try:
                    invoice_data = self.invoice_extractor.extract_invoice_data(
                        extracted_text, 
                        document.file_type
                    )
                    if invoice_data:
                        extracted_data.update(invoice_data)
                        confidence_score = invoice_data.get('confidence_score', 70)
                except Exception as e:
                    logger.warning(f"Échec de l'extraction de facture: {e}")
            
            elif document.file_type in ['csv', 'excel']:
                # Extraire les données tabulaires
                try:
                    tabular_data = processor.extract_structured_data(document.file_path)
                    if tabular_data:
                        extracted_data.update(tabular_data)
                        confidence_score = 90  # Les données tabulaires sont généralement fiables
                except Exception as e:
                    logger.warning(f"Échec de l'extraction de données tabulaires: {e}")
            
            # Ajouter des métadonnées de traitement
            extracted_data['processing_metadata'] = {
                'processed_at': datetime.utcnow().isoformat(),
                'processor_version': '1.0',
                'file_type': document.file_type,
                'original_filename': document.original_filename,
                'text_length': len(extracted_text) if extracted_text else 0
            }
            
            # Sauvegarder les résultats
            document.set_extracted_data(
                text=extracted_text,
                data=extracted_data,
                confidence=confidence_score
            )
            document.set_processing_status('completed')
            
            db.session.commit()
            
            logger.info(f"Traitement terminé avec succès pour le document {document_id}")
            
            return {
                'success': True,
                'document_id': document_id,
                'extracted_text_length': len(extracted_text) if extracted_text else 0,
                'extracted_data_keys': list(extracted_data.keys()),
                'confidence_score': confidence_score
            }
            
        except Exception as e:
            logger.error(f"Erreur lors du traitement du document {document_id}: {e}")
            
            # Marquer le traitement comme échoué
            try:
                document = Document.query.get(document_id)
                if document:
                    document.set_processing_status('failed')
                    document.set_extracted_data(
                        data={'error': str(e), 'failed_at': datetime.utcnow().isoformat()}
                    )
                    db.session.commit()
            except Exception as db_error:
                logger.error(f"Erreur lors de la mise à jour du statut d'échec: {db_error}")
            
            return {
                'success': False,
                'document_id': document_id,
                'error': str(e)
            }
    
    def get_processing_status(self, document_id: int) -> Dict[str, Any]:
        """Récupère le statut de traitement d'un document"""
        try:
            document = Document.query.get(document_id)
            if not document:
                return {'error': 'Document non trouvé'}
            
            return {
                'document_id': document_id,
                'status': document.processing_status,
                'started_at': document.processing_started_at.isoformat() if document.processing_started_at else None,
                'completed_at': document.processing_completed_at.isoformat() if document.processing_completed_at else None,
                'confidence_score': document.confidence_score,
                'has_extracted_data': bool(document.extracted_data)
            }
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du statut: {e}")
            return {'error': str(e)}
    
    def reprocess_document(self, document_id: int) -> Dict[str, Any]:
        """Relance le traitement d'un document"""
        try:
            document = Document.query.get(document_id)
            if not document:
                return {'error': 'Document non trouvé'}
            
            # Réinitialiser les données de traitement
            document.set_processing_status('pending')
            document.extracted_text = None
            document.extracted_data = None
            document.confidence_score = None
            document.processing_started_at = None
            document.processing_completed_at = None
            
            db.session.commit()
            
            # Relancer le traitement
            self.process_document_async(document_id)
            
            return {
                'success': True,
                'message': 'Retraitement démarré',
                'document_id': document_id
            }
            
        except Exception as e:
            logger.error(f"Erreur lors du retraitement: {e}")
            return {'error': str(e)}
    
    def get_supported_formats(self) -> Dict[str, Any]:
        """Retourne les formats supportés et leurs capacités"""
        return {
            'pdf': {
                'description': 'Documents PDF',
                'capabilities': ['text_extraction', 'invoice_extraction'],
                'mime_types': ['application/pdf']
            },
            'image': {
                'description': 'Images (JPEG, PNG)',
                'capabilities': ['ocr', 'invoice_extraction'],
                'mime_types': ['image/jpeg', 'image/png', 'image/jpg']
            },
            'csv': {
                'description': 'Fichiers CSV',
                'capabilities': ['structured_data_extraction', 'client_import', 'product_import'],
                'mime_types': ['text/csv', 'application/csv']
            },
            'excel': {
                'description': 'Fichiers Excel',
                'capabilities': ['structured_data_extraction', 'client_import', 'product_import'],
                'mime_types': [
                    'application/vnd.ms-excel',
                    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                ]
            }
        }
    
    def extract_accounting_data(self, document_id: int) -> Dict[str, Any]:
        """Extrait spécifiquement les données comptables d'un document"""
        try:
            document = Document.query.get(document_id)
            if not document:
                return {'error': 'Document non trouvé'}
            
            if document.processing_status != 'completed':
                return {'error': 'Document non traité ou traitement en cours'}
            
            if not document.extracted_data:
                return {'error': 'Aucune donnée extraite disponible'}
            
            # Extraire les données comptables selon le type de document
            accounting_data = {}
            
            if 'invoice_data' in document.extracted_data:
                invoice_data = document.extracted_data['invoice_data']
                accounting_data = {
                    'type': 'invoice',
                    'client_name': invoice_data.get('client_name'),
                    'client_address': invoice_data.get('client_address'),
                    'invoice_number': invoice_data.get('invoice_number'),
                    'invoice_date': invoice_data.get('invoice_date'),
                    'due_date': invoice_data.get('due_date'),
                    'total_ht': invoice_data.get('total_ht'),
                    'total_ttc': invoice_data.get('total_ttc'),
                    'tva_amount': invoice_data.get('tva_amount'),
                    'line_items': invoice_data.get('line_items', [])
                }
            
            elif 'clients_data' in document.extracted_data:
                clients_data = document.extracted_data['clients_data']
                accounting_data = {
                    'type': 'clients_import',
                    'clients': clients_data.get('clients', []),
                    'total_clients': len(clients_data.get('clients', []))
                }
            
            elif 'products_data' in document.extracted_data:
                products_data = document.extracted_data['products_data']
                accounting_data = {
                    'type': 'products_import',
                    'products': products_data.get('products', []),
                    'total_products': len(products_data.get('products', []))
                }
            
            else:
                # Données génériques
                accounting_data = {
                    'type': 'generic',
                    'extracted_text': document.extracted_text,
                    'raw_data': document.extracted_data
                }
            
            accounting_data['confidence_score'] = document.confidence_score
            accounting_data['document_id'] = document_id
            accounting_data['original_filename'] = document.original_filename
            
            return accounting_data
            
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction des données comptables: {e}")
            return {'error': str(e)}

