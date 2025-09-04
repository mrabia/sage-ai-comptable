import os
import logging
from typing import Optional, Dict, Any
import pdfplumber
import PyPDF2
from io import BytesIO

logger = logging.getLogger(__name__)

class PDFProcessor:
    """Service pour traiter les fichiers PDF"""
    
    def __init__(self):
        self.supported_extensions = ['.pdf']
    
    def extract_text(self, file_path: str) -> Optional[str]:
        """Extrait le texte d'un fichier PDF"""
        try:
            # Méthode 1: Utiliser pdfplumber (meilleur pour les tableaux et la mise en forme)
            text = self._extract_with_pdfplumber(file_path)
            
            if not text or len(text.strip()) < 50:
                # Méthode 2: Fallback avec PyPDF2
                logger.info("Fallback vers PyPDF2 pour l'extraction de texte")
                text = self._extract_with_pypdf2(file_path)
            
            return text.strip() if text else None
            
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction de texte PDF: {e}")
            return None
    
    def _extract_with_pdfplumber(self, file_path: str) -> Optional[str]:
        """Extrait le texte avec pdfplumber"""
        try:
            text_content = []
            
            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            text_content.append(f"--- Page {page_num} ---\n{page_text}\n")
                        
                        # Extraire aussi les tableaux s'il y en a
                        tables = page.extract_tables()
                        for table_num, table in enumerate(tables, 1):
                            if table:
                                text_content.append(f"\n--- Tableau {table_num} (Page {page_num}) ---\n")
                                for row in table:
                                    if row:
                                        # Nettoyer les cellules vides
                                        clean_row = [cell.strip() if cell else '' for cell in row]
                                        text_content.append(' | '.join(clean_row) + '\n')
                                text_content.append('\n')
                    
                    except Exception as e:
                        logger.warning(f"Erreur lors de l'extraction de la page {page_num}: {e}")
                        continue
            
            return ''.join(text_content)
            
        except Exception as e:
            logger.error(f"Erreur avec pdfplumber: {e}")
            return None
    
    def _extract_with_pypdf2(self, file_path: str) -> Optional[str]:
        """Extrait le texte avec PyPDF2"""
        try:
            text_content = []
            
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                for page_num, page in enumerate(pdf_reader.pages, 1):
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            text_content.append(f"--- Page {page_num} ---\n{page_text}\n")
                    except Exception as e:
                        logger.warning(f"Erreur lors de l'extraction de la page {page_num}: {e}")
                        continue
            
            return ''.join(text_content)
            
        except Exception as e:
            logger.error(f"Erreur avec PyPDF2: {e}")
            return None
    
    def extract_metadata(self, file_path: str) -> Dict[str, Any]:
        """Extrait les métadonnées du PDF"""
        try:
            metadata = {}
            
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                # Informations de base
                metadata['num_pages'] = len(pdf_reader.pages)
                
                # Métadonnées du document
                if pdf_reader.metadata:
                    doc_metadata = pdf_reader.metadata
                    metadata['title'] = doc_metadata.get('/Title', '')
                    metadata['author'] = doc_metadata.get('/Author', '')
                    metadata['subject'] = doc_metadata.get('/Subject', '')
                    metadata['creator'] = doc_metadata.get('/Creator', '')
                    metadata['producer'] = doc_metadata.get('/Producer', '')
                    metadata['creation_date'] = str(doc_metadata.get('/CreationDate', ''))
                    metadata['modification_date'] = str(doc_metadata.get('/ModDate', ''))
            
            # Informations avec pdfplumber
            try:
                with pdfplumber.open(file_path) as pdf:
                    # Analyser la première page pour détecter des tableaux
                    if pdf.pages:
                        first_page = pdf.pages[0]
                        tables = first_page.extract_tables()
                        metadata['has_tables'] = len(tables) > 0
                        metadata['num_tables_first_page'] = len(tables)
                        
                        # Détecter si c'est probablement une facture
                        text = first_page.extract_text() or ''
                        invoice_keywords = [
                            'facture', 'invoice', 'devis', 'quote',
                            'total', 'tva', 'ht', 'ttc', 'vat',
                            'montant', 'amount', 'prix', 'price'
                        ]
                        
                        keyword_count = sum(1 for keyword in invoice_keywords 
                                          if keyword.lower() in text.lower())
                        metadata['likely_invoice'] = keyword_count >= 3
                        metadata['invoice_keyword_count'] = keyword_count
            
            except Exception as e:
                logger.warning(f"Erreur lors de l'extraction des métadonnées avancées: {e}")
            
            return metadata
            
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction des métadonnées: {e}")
            return {}
    
    def extract_structured_data(self, file_path: str) -> Dict[str, Any]:
        """Extrait des données structurées du PDF (tableaux, etc.)"""
        try:
            structured_data = {
                'tables': [],
                'text_blocks': [],
                'metadata': self.extract_metadata(file_path)
            }
            
            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    try:
                        # Extraire les tableaux
                        tables = page.extract_tables()
                        for table_num, table in enumerate(tables):
                            if table and len(table) > 1:  # Au moins un en-tête et une ligne
                                # Nettoyer le tableau
                                clean_table = []
                                for row in table:
                                    if row:
                                        clean_row = [cell.strip() if cell else '' for cell in row]
                                        clean_table.append(clean_row)
                                
                                if clean_table:
                                    structured_data['tables'].append({
                                        'page': page_num,
                                        'table_index': table_num,
                                        'headers': clean_table[0] if clean_table else [],
                                        'rows': clean_table[1:] if len(clean_table) > 1 else [],
                                        'num_rows': len(clean_table) - 1,
                                        'num_columns': len(clean_table[0]) if clean_table else 0
                                    })
                        
                        # Extraire les blocs de texte
                        page_text = page.extract_text()
                        if page_text:
                            # Diviser en paragraphes
                            paragraphs = [p.strip() for p in page_text.split('\n\n') if p.strip()]
                            structured_data['text_blocks'].extend([
                                {
                                    'page': page_num,
                                    'content': paragraph,
                                    'length': len(paragraph)
                                }
                                for paragraph in paragraphs
                            ])
                    
                    except Exception as e:
                        logger.warning(f"Erreur lors de l'extraction structurée de la page {page_num}: {e}")
                        continue
            
            return structured_data
            
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction de données structurées: {e}")
            return {}
    
    def is_valid_pdf(self, file_path: str) -> bool:
        """Vérifie si le fichier est un PDF valide"""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                # Tenter de lire la première page
                if len(pdf_reader.pages) > 0:
                    first_page = pdf_reader.pages[0]
                    first_page.extract_text()
                    return True
                return False
        except Exception as e:
            logger.error(f"PDF invalide: {e}")
            return False
    
    def get_page_count(self, file_path: str) -> int:
        """Retourne le nombre de pages du PDF"""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                return len(pdf_reader.pages)
        except Exception as e:
            logger.error(f"Erreur lors du comptage des pages: {e}")
            return 0
    
    def extract_page_text(self, file_path: str, page_number: int) -> Optional[str]:
        """Extrait le texte d'une page spécifique (indexé à partir de 1)"""
        try:
            with pdfplumber.open(file_path) as pdf:
                if 1 <= page_number <= len(pdf.pages):
                    page = pdf.pages[page_number - 1]  # Conversion vers index 0
                    return page.extract_text()
                else:
                    logger.error(f"Numéro de page invalide: {page_number}")
                    return None
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction de la page {page_number}: {e}")
            return None

