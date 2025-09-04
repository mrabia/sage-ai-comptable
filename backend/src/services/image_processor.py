import os
import logging
from typing import Optional, Dict, Any, List
from PIL import Image, ImageEnhance, ImageFilter
import pytesseract
import cv2
import numpy as np

logger = logging.getLogger(__name__)

class ImageProcessor:
    """Service pour traiter les images avec OCR"""
    
    def __init__(self):
        self.supported_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']
        self.supported_languages = ['fra', 'eng']  # Français et anglais
    
    def extract_text(self, file_path: str) -> Optional[str]:
        """Extrait le texte d'une image avec OCR"""
        try:
            # Préprocesser l'image pour améliorer l'OCR
            processed_image = self._preprocess_image(file_path)
            
            if processed_image is None:
                logger.error("Échec du préprocessing de l'image")
                return None
            
            # Configuration Tesseract
            custom_config = r'--oem 3 --psm 6 -l fra+eng'
            
            # Extraire le texte
            text = pytesseract.image_to_string(processed_image, config=custom_config)
            
            if not text or len(text.strip()) < 10:
                # Essayer avec une configuration différente
                logger.info("Tentative avec une configuration OCR alternative")
                custom_config = r'--oem 3 --psm 3 -l fra+eng'
                text = pytesseract.image_to_string(processed_image, config=custom_config)
            
            return text.strip() if text else None
            
        except Exception as e:
            logger.error(f"Erreur lors de l'OCR: {e}")
            return None
    
    def _preprocess_image(self, file_path: str) -> Optional[Image.Image]:
        """Préprocesse l'image pour améliorer la qualité de l'OCR"""
        try:
            # Charger l'image
            image = Image.open(file_path)
            
            # Convertir en RGB si nécessaire
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Redimensionner si l'image est trop petite ou trop grande
            width, height = image.size
            
            # Si l'image est trop petite, l'agrandir
            if width < 800 or height < 600:
                scale_factor = max(800 / width, 600 / height)
                new_width = int(width * scale_factor)
                new_height = int(height * scale_factor)
                image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Si l'image est trop grande, la réduire
            elif width > 3000 or height > 3000:
                scale_factor = min(3000 / width, 3000 / height)
                new_width = int(width * scale_factor)
                new_height = int(height * scale_factor)
                image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Améliorer le contraste
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.2)
            
            # Améliorer la netteté
            enhancer = ImageEnhance.Sharpness(image)
            image = enhancer.enhance(1.1)
            
            # Convertir en niveaux de gris pour l'OCR
            image = image.convert('L')
            
            # Appliquer un filtre de débruitage léger
            image = image.filter(ImageFilter.MedianFilter(size=3))
            
            return image
            
        except Exception as e:
            logger.error(f"Erreur lors du préprocessing: {e}")
            return None
    
    def _preprocess_with_opencv(self, file_path: str) -> Optional[np.ndarray]:
        """Préprocessing avancé avec OpenCV pour les images difficiles"""
        try:
            # Charger l'image avec OpenCV
            image = cv2.imread(file_path)
            
            if image is None:
                return None
            
            # Convertir en niveaux de gris
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Appliquer un filtre gaussien pour réduire le bruit
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            
            # Seuillage adaptatif pour améliorer le contraste
            thresh = cv2.adaptiveThreshold(
                blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                cv2.THRESH_BINARY, 11, 2
            )
            
            # Morphologie pour nettoyer l'image
            kernel = np.ones((2, 2), np.uint8)
            cleaned = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
            
            return cleaned
            
        except Exception as e:
            logger.error(f"Erreur lors du préprocessing OpenCV: {e}")
            return None
    
    def extract_text_with_confidence(self, file_path: str) -> Dict[str, Any]:
        """Extrait le texte avec des informations de confiance"""
        try:
            processed_image = self._preprocess_image(file_path)
            
            if processed_image is None:
                return {'text': '', 'confidence': 0, 'error': 'Échec du préprocessing'}
            
            # Configuration Tesseract avec données de confiance
            custom_config = r'--oem 3 --psm 6 -l fra+eng'
            
            # Extraire le texte avec les données de confiance
            data = pytesseract.image_to_data(
                processed_image, 
                config=custom_config, 
                output_type=pytesseract.Output.DICT
            )
            
            # Calculer la confiance moyenne
            confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            # Extraire le texte
            text = pytesseract.image_to_string(processed_image, config=custom_config)
            
            # Analyser la qualité du texte
            quality_score = self._analyze_text_quality(text)
            
            return {
                'text': text.strip(),
                'confidence': avg_confidence,
                'quality_score': quality_score,
                'word_count': len(text.split()) if text else 0,
                'char_count': len(text) if text else 0
            }
            
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction avec confiance: {e}")
            return {'text': '', 'confidence': 0, 'error': str(e)}
    
    def _analyze_text_quality(self, text: str) -> int:
        """Analyse la qualité du texte extrait (score 0-100)"""
        if not text:
            return 0
        
        score = 50  # Score de base
        
        # Vérifier la présence de mots français/anglais courants
        common_words = [
            'le', 'la', 'les', 'de', 'du', 'des', 'et', 'à', 'un', 'une',
            'the', 'and', 'or', 'of', 'to', 'in', 'for', 'with', 'on',
            'facture', 'invoice', 'total', 'date', 'client', 'montant'
        ]
        
        words = text.lower().split()
        common_word_count = sum(1 for word in words if word in common_words)
        
        if len(words) > 0:
            common_word_ratio = common_word_count / len(words)
            score += int(common_word_ratio * 30)
        
        # Pénaliser les caractères étranges
        strange_chars = sum(1 for char in text if not (char.isalnum() or char.isspace() or char in '.,;:!?-()[]{}'))
        if len(text) > 0:
            strange_char_ratio = strange_chars / len(text)
            score -= int(strange_char_ratio * 40)
        
        # Bonus pour la longueur raisonnable
        if 50 <= len(text) <= 5000:
            score += 10
        
        return max(0, min(100, score))
    
    def extract_structured_data(self, file_path: str) -> Dict[str, Any]:
        """Extrait des données structurées de l'image"""
        try:
            # Extraire le texte avec confiance
            ocr_result = self.extract_text_with_confidence(file_path)
            
            if not ocr_result['text']:
                return {'error': 'Aucun texte détecté'}
            
            text = ocr_result['text']
            
            # Analyser la structure du document
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            
            structured_data = {
                'raw_text': text,
                'lines': lines,
                'line_count': len(lines),
                'confidence': ocr_result['confidence'],
                'quality_score': ocr_result['quality_score'],
                'metadata': self.extract_metadata(file_path)
            }
            
            # Détecter des patterns spécifiques
            patterns = self._detect_patterns(text)
            structured_data.update(patterns)
            
            return structured_data
            
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction de données structurées: {e}")
            return {'error': str(e)}
    
    def _detect_patterns(self, text: str) -> Dict[str, Any]:
        """Détecte des patterns spécifiques dans le texte"""
        import re
        
        patterns = {}
        
        # Détecter les dates
        date_patterns = [
            r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',
            r'\d{1,2}\s+\w+\s+\d{2,4}',
            r'\d{2,4}[/-]\d{1,2}[/-]\d{1,2}'
        ]
        
        dates = []
        for pattern in date_patterns:
            dates.extend(re.findall(pattern, text))
        patterns['detected_dates'] = list(set(dates))
        
        # Détecter les montants
        amount_patterns = [
            r'\d+[,.]?\d*\s*€',
            r'€\s*\d+[,.]?\d*',
            r'\d+[,.]?\d*\s*EUR',
            r'\d+[,.]?\d*\s*TTC',
            r'\d+[,.]?\d*\s*HT'
        ]
        
        amounts = []
        for pattern in amount_patterns:
            amounts.extend(re.findall(pattern, text))
        patterns['detected_amounts'] = list(set(amounts))
        
        # Détecter les numéros (facture, commande, etc.)
        number_patterns = [
            r'N°\s*\d+',
            r'Facture\s*:?\s*\d+',
            r'Invoice\s*:?\s*\d+',
            r'Devis\s*:?\s*\d+'
        ]
        
        numbers = []
        for pattern in number_patterns:
            numbers.extend(re.findall(pattern, text, re.IGNORECASE))
        patterns['detected_numbers'] = list(set(numbers))
        
        # Détecter les emails
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        patterns['detected_emails'] = list(set(emails))
        
        # Détecter les numéros de téléphone
        phone_patterns = [
            r'\b\d{2}[\s.-]?\d{2}[\s.-]?\d{2}[\s.-]?\d{2}[\s.-]?\d{2}\b',
            r'\+33[\s.-]?\d[\s.-]?\d{2}[\s.-]?\d{2}[\s.-]?\d{2}[\s.-]?\d{2}'
        ]
        
        phones = []
        for pattern in phone_patterns:
            phones.extend(re.findall(pattern, text))
        patterns['detected_phones'] = list(set(phones))
        
        return patterns
    
    def extract_metadata(self, file_path: str) -> Dict[str, Any]:
        """Extrait les métadonnées de l'image"""
        try:
            metadata = {}
            
            with Image.open(file_path) as image:
                # Informations de base
                metadata['format'] = image.format
                metadata['mode'] = image.mode
                metadata['size'] = image.size
                metadata['width'] = image.width
                metadata['height'] = image.height
                
                # Informations EXIF si disponibles
                if hasattr(image, '_getexif') and image._getexif():
                    exif_data = image._getexif()
                    if exif_data:
                        metadata['has_exif'] = True
                        # Extraire quelques données EXIF importantes
                        metadata['exif_data'] = {
                            'datetime': exif_data.get(306),  # DateTime
                            'software': exif_data.get(305),  # Software
                            'make': exif_data.get(271),      # Make
                            'model': exif_data.get(272)      # Model
                        }
                else:
                    metadata['has_exif'] = False
                
                # Calculer la résolution approximative
                total_pixels = image.width * image.height
                metadata['total_pixels'] = total_pixels
                metadata['megapixels'] = round(total_pixels / 1000000, 2)
                
                # Estimer la qualité pour l'OCR
                if image.width >= 800 and image.height >= 600:
                    metadata['ocr_quality_estimate'] = 'good'
                elif image.width >= 400 and image.height >= 300:
                    metadata['ocr_quality_estimate'] = 'medium'
                else:
                    metadata['ocr_quality_estimate'] = 'poor'
            
            return metadata
            
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction des métadonnées: {e}")
            return {}
    
    def is_valid_image(self, file_path: str) -> bool:
        """Vérifie si le fichier est une image valide"""
        try:
            with Image.open(file_path) as image:
                image.verify()
                return True
        except Exception as e:
            logger.error(f"Image invalide: {e}")
            return False
    
    def get_image_info(self, file_path: str) -> Dict[str, Any]:
        """Retourne des informations complètes sur l'image"""
        try:
            info = {
                'is_valid': self.is_valid_image(file_path),
                'metadata': self.extract_metadata(file_path),
                'file_size': os.path.getsize(file_path)
            }
            
            return info
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des informations: {e}")
            return {'error': str(e)}

