import re
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import json

logger = logging.getLogger(__name__)

class InvoiceExtractor:
    """Service pour extraire intelligemment les données de factures"""
    
    def __init__(self):
        self.currency_symbols = ['€', '$', '£', 'EUR', 'USD', 'GBP']
        self.vat_keywords = ['tva', 'vat', 'tax', 'taxe', 'btw']
        self.total_keywords = ['total', 'montant', 'amount', 'sum', 'somme']
    
    def extract_invoice_data(self, text: str, file_type: str = 'pdf') -> Optional[Dict[str, Any]]:
        """Extrait les données d'une facture à partir du texte"""
        try:
            if not text or len(text.strip()) < 50:
                return None
            
            # Vérifier si c'est probablement une facture
            if not self._is_likely_invoice(text):
                return None
            
            invoice_data = {
                'confidence_score': 0,
                'extraction_method': file_type,
                'extracted_at': datetime.utcnow().isoformat()
            }
            
            # Extraire les différents éléments
            invoice_data.update(self._extract_invoice_number(text))
            invoice_data.update(self._extract_dates(text))
            invoice_data.update(self._extract_client_info(text))
            invoice_data.update(self._extract_amounts(text))
            invoice_data.update(self._extract_line_items(text))
            invoice_data.update(self._extract_supplier_info(text))
            
            # Calculer le score de confiance
            confidence = self._calculate_confidence_score(invoice_data, text)
            invoice_data['confidence_score'] = confidence
            
            # Valider les données extraites
            if confidence < 30:  # Seuil minimum de confiance
                return None
            
            return {'invoice_data': invoice_data}
            
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction de facture: {e}")
            return None
    
    def _is_likely_invoice(self, text: str) -> bool:
        """Détermine si le texte ressemble à une facture"""
        text_lower = text.lower()
        
        # Mots-clés qui indiquent une facture
        invoice_keywords = [
            'facture', 'invoice', 'devis', 'quote', 'quotation',
            'bill', 'receipt', 'reçu', 'note', 'bon de commande'
        ]
        
        # Mots-clés financiers
        financial_keywords = [
            'total', 'montant', 'amount', 'prix', 'price',
            'tva', 'vat', 'tax', 'ht', 'ttc', 'hors taxe', 'toutes taxes'
        ]
        
        # Compter les correspondances
        invoice_matches = sum(1 for keyword in invoice_keywords if keyword in text_lower)
        financial_matches = sum(1 for keyword in financial_keywords if keyword in text_lower)
        
        # Vérifier la présence de montants
        amount_pattern = r'\d+[,.]?\d*\s*[€$£]|\d+[,.]?\d*\s*(EUR|USD|GBP)'
        amount_matches = len(re.findall(amount_pattern, text))
        
        # Vérifier la présence de dates
        date_pattern = r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}'
        date_matches = len(re.findall(date_pattern, text))
        
        # Score de probabilité
        score = invoice_matches * 3 + financial_matches * 2 + min(amount_matches, 5) + min(date_matches, 3)
        
        return score >= 5
    
    def _extract_invoice_number(self, text: str) -> Dict[str, Any]:
        """Extrait le numéro de facture"""
        patterns = [
            r'(?:facture|invoice|bill|n°|no|number|#)\s*:?\s*([A-Z0-9\-_]+)',
            r'(?:ref|référence|reference)\s*:?\s*([A-Z0-9\-_]+)',
            r'([A-Z]{2,}\d{3,})',  # Pattern générique comme ABC123
            r'(\d{4,})'  # Numéro simple de 4 chiffres ou plus
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                # Prendre le premier match qui semble valide
                for match in matches:
                    if len(match) >= 3 and not match.isdigit() or len(match) >= 4:
                        return {
                            'invoice_number': match.strip(),
                            'invoice_number_confidence': 80
                        }
        
        return {'invoice_number': None, 'invoice_number_confidence': 0}
    
    def _extract_dates(self, text: str) -> Dict[str, Any]:
        """Extrait les dates de la facture"""
        date_patterns = [
            r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',
            r'\d{1,2}\s+(?:janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+\d{2,4}',
            r'\d{1,2}\s+(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{2,4}',
            r'\d{2,4}[/-]\d{1,2}[/-]\d{1,2}'
        ]
        
        dates_found = []
        for pattern in date_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            dates_found.extend(matches)
        
        # Nettoyer et dédupliquer les dates
        unique_dates = list(set(dates_found))
        
        result = {
            'invoice_date': None,
            'due_date': None,
            'dates_found': unique_dates,
            'dates_confidence': 70 if unique_dates else 0
        }
        
        # Essayer d'identifier la date de facture et l'échéance
        if unique_dates:
            # Prendre la première date comme date de facture
            result['invoice_date'] = unique_dates[0]
            
            # Si on a plusieurs dates, la dernière pourrait être l'échéance
            if len(unique_dates) > 1:
                result['due_date'] = unique_dates[-1]
        
        return result
    
    def _extract_client_info(self, text: str) -> Dict[str, Any]:
        """Extrait les informations du client"""
        lines = text.split('\n')
        
        # Chercher des sections qui pourraient contenir les infos client
        client_sections = []
        
        for i, line in enumerate(lines):
            line_lower = line.lower().strip()
            if any(keyword in line_lower for keyword in ['client', 'customer', 'bill to', 'facturé à', 'destinataire']):
                # Prendre les lignes suivantes
                section = []
                for j in range(i + 1, min(i + 6, len(lines))):
                    if lines[j].strip():
                        section.append(lines[j].strip())
                    else:
                        break
                if section:
                    client_sections.append('\n'.join(section))
        
        # Extraire les informations
        client_info = {
            'client_name': None,
            'client_address': None,
            'client_email': None,
            'client_phone': None,
            'client_confidence': 0
        }
        
        if client_sections:
            full_client_text = '\n'.join(client_sections)
            
            # Extraire le nom (première ligne non vide)
            first_line = client_sections[0].split('\n')[0].strip()
            if first_line and len(first_line) > 2:
                client_info['client_name'] = first_line
            
            # Extraire l'adresse (lignes suivantes)
            address_lines = []
            for section in client_sections:
                lines = section.split('\n')[1:]  # Ignorer la première ligne (nom)
                address_lines.extend([line.strip() for line in lines if line.strip()])
            
            if address_lines:
                client_info['client_address'] = '\n'.join(address_lines[:3])  # Max 3 lignes
            
            # Extraire l'email
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            email_matches = re.findall(email_pattern, full_client_text)
            if email_matches:
                client_info['client_email'] = email_matches[0]
            
            # Extraire le téléphone
            phone_patterns = [
                r'\b\d{2}[\s.-]?\d{2}[\s.-]?\d{2}[\s.-]?\d{2}[\s.-]?\d{2}\b',
                r'\+33[\s.-]?\d[\s.-]?\d{2}[\s.-]?\d{2}[\s.-]?\d{2}[\s.-]?\d{2}'
            ]
            
            for pattern in phone_patterns:
                phone_matches = re.findall(pattern, full_client_text)
                if phone_matches:
                    client_info['client_phone'] = phone_matches[0]
                    break
            
            # Calculer la confiance
            confidence = 0
            if client_info['client_name']:
                confidence += 40
            if client_info['client_address']:
                confidence += 30
            if client_info['client_email']:
                confidence += 20
            if client_info['client_phone']:
                confidence += 10
            
            client_info['client_confidence'] = confidence
        
        return client_info
    
    def _extract_amounts(self, text: str) -> Dict[str, Any]:
        """Extrait les montants de la facture"""
        # Patterns pour les montants
        amount_patterns = [
            r'(\d+[,.]?\d*)\s*€',
            r'€\s*(\d+[,.]?\d*)',
            r'(\d+[,.]?\d*)\s*EUR',
            r'EUR\s*(\d+[,.]?\d*)',
            r'(\d+[,.]?\d*)\s*(?:TTC|ttc)',
            r'(\d+[,.]?\d*)\s*(?:HT|ht)',
            r'(?:total|montant|amount)\s*:?\s*(\d+[,.]?\d*)',
            r'(\d+[,.]?\d*)\s*(?:total|montant|amount)'
        ]
        
        amounts_found = []
        for pattern in amount_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    # Convertir en float
                    amount_str = match.replace(',', '.')
                    amount = float(amount_str)
                    amounts_found.append(amount)
                except ValueError:
                    continue
        
        # Dédupliquer et trier
        unique_amounts = sorted(list(set(amounts_found)), reverse=True)
        
        result = {
            'total_ttc': None,
            'total_ht': None,
            'tva_amount': None,
            'amounts_found': unique_amounts,
            'amounts_confidence': 60 if unique_amounts else 0
        }
        
        if unique_amounts:
            # Le montant le plus élevé est probablement le total TTC
            result['total_ttc'] = unique_amounts[0]
            
            # Essayer de trouver le montant HT et la TVA
            text_lower = text.lower()
            
            # Chercher spécifiquement les montants HT et TVA
            ht_pattern = r'(?:ht|hors\s*taxe|net)\s*:?\s*(\d+[,.]?\d*)'
            ht_matches = re.findall(ht_pattern, text_lower)
            if ht_matches:
                try:
                    result['total_ht'] = float(ht_matches[0].replace(',', '.'))
                except ValueError:
                    pass
            
            tva_pattern = r'(?:tva|vat|tax|taxe)\s*:?\s*(\d+[,.]?\d*)'
            tva_matches = re.findall(tva_pattern, text_lower)
            if tva_matches:
                try:
                    result['tva_amount'] = float(tva_matches[0].replace(',', '.'))
                except ValueError:
                    pass
            
            # Si on n'a pas trouvé HT et TVA, essayer de les calculer
            if result['total_ttc'] and not result['total_ht']:
                # Supposer une TVA de 20% par défaut
                estimated_ht = result['total_ttc'] / 1.20
                estimated_tva = result['total_ttc'] - estimated_ht
                
                # Vérifier si ces montants sont dans la liste
                for amount in unique_amounts:
                    if abs(amount - estimated_ht) < 1:
                        result['total_ht'] = amount
                    elif abs(amount - estimated_tva) < 1:
                        result['tva_amount'] = amount
        
        return result
    
    def _extract_line_items(self, text: str) -> Dict[str, Any]:
        """Extrait les lignes de détail de la facture"""
        lines = text.split('\n')
        
        # Chercher des tableaux ou listes d'articles
        line_items = []
        
        # Patterns pour identifier les lignes d'articles
        item_patterns = [
            r'(\d+)\s+(.+?)\s+(\d+[,.]?\d*)\s*€',  # Quantité Description Prix
            r'(.+?)\s+(\d+)\s+(\d+[,.]?\d*)',      # Description Quantité Prix
            r'(.+?)\s+(\d+[,.]?\d*)\s*€'           # Description Prix
        ]
        
        for line in lines:
            line = line.strip()
            if not line or len(line) < 10:
                continue
            
            for pattern in item_patterns:
                match = re.search(pattern, line)
                if match:
                    groups = match.groups()
                    
                    if len(groups) == 3:
                        # Essayer de déterminer l'ordre des éléments
                        try:
                            # Tester si le premier groupe est un nombre (quantité)
                            qty = int(groups[0])
                            desc = groups[1].strip()
                            price = float(groups[2].replace(',', '.'))
                            
                            line_items.append({
                                'description': desc,
                                'quantity': qty,
                                'unit_price': price,
                                'total': qty * price
                            })
                        except ValueError:
                            # Essayer l'ordre inverse
                            try:
                                desc = groups[0].strip()
                                qty = int(groups[1])
                                price = float(groups[2].replace(',', '.'))
                                
                                line_items.append({
                                    'description': desc,
                                    'quantity': qty,
                                    'unit_price': price,
                                    'total': qty * price
                                })
                            except ValueError:
                                continue
                    
                    elif len(groups) == 2:
                        # Description et prix seulement
                        try:
                            desc = groups[0].strip()
                            price = float(groups[1].replace(',', '.'))
                            
                            line_items.append({
                                'description': desc,
                                'quantity': 1,
                                'unit_price': price,
                                'total': price
                            })
                        except ValueError:
                            continue
                    
                    break  # Sortir de la boucle des patterns si on a trouvé une correspondance
        
        return {
            'line_items': line_items,
            'line_items_count': len(line_items),
            'line_items_confidence': 70 if line_items else 0
        }
    
    def _extract_supplier_info(self, text: str) -> Dict[str, Any]:
        """Extrait les informations du fournisseur/émetteur"""
        lines = text.split('\n')
        
        # Prendre les premières lignes qui contiennent souvent les infos du fournisseur
        supplier_lines = []
        for i, line in enumerate(lines[:10]):  # Regarder les 10 premières lignes
            line = line.strip()
            if line and len(line) > 3:
                supplier_lines.append(line)
        
        supplier_info = {
            'supplier_name': None,
            'supplier_address': None,
            'supplier_email': None,
            'supplier_phone': None,
            'supplier_confidence': 0
        }
        
        if supplier_lines:
            # Le nom du fournisseur est souvent sur la première ligne
            supplier_info['supplier_name'] = supplier_lines[0]
            
            # L'adresse sur les lignes suivantes
            if len(supplier_lines) > 1:
                address_lines = supplier_lines[1:4]  # Max 3 lignes d'adresse
                supplier_info['supplier_address'] = '\n'.join(address_lines)
            
            # Chercher email et téléphone dans tout le texte du fournisseur
            supplier_text = '\n'.join(supplier_lines)
            
            # Email
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            email_matches = re.findall(email_pattern, supplier_text)
            if email_matches:
                supplier_info['supplier_email'] = email_matches[0]
            
            # Téléphone
            phone_patterns = [
                r'\b\d{2}[\s.-]?\d{2}[\s.-]?\d{2}[\s.-]?\d{2}[\s.-]?\d{2}\b',
                r'\+33[\s.-]?\d[\s.-]?\d{2}[\s.-]?\d{2}[\s.-]?\d{2}[\s.-]?\d{2}'
            ]
            
            for pattern in phone_patterns:
                phone_matches = re.findall(pattern, supplier_text)
                if phone_matches:
                    supplier_info['supplier_phone'] = phone_matches[0]
                    break
            
            # Calculer la confiance
            confidence = 0
            if supplier_info['supplier_name']:
                confidence += 40
            if supplier_info['supplier_address']:
                confidence += 30
            if supplier_info['supplier_email']:
                confidence += 20
            if supplier_info['supplier_phone']:
                confidence += 10
            
            supplier_info['supplier_confidence'] = confidence
        
        return supplier_info
    
    def _calculate_confidence_score(self, invoice_data: Dict[str, Any], text: str) -> int:
        """Calcule un score de confiance global pour l'extraction"""
        score = 0
        
        # Score basé sur les éléments extraits
        if invoice_data.get('invoice_number'):
            score += 15
        
        if invoice_data.get('invoice_date'):
            score += 15
        
        if invoice_data.get('client_name'):
            score += 15
        
        if invoice_data.get('total_ttc'):
            score += 20
        
        if invoice_data.get('line_items'):
            score += 15
        
        if invoice_data.get('supplier_name'):
            score += 10
        
        # Bonus pour la cohérence des données
        if (invoice_data.get('total_ht') and 
            invoice_data.get('tva_amount') and 
            invoice_data.get('total_ttc')):
            
            # Vérifier la cohérence HT + TVA = TTC
            ht = invoice_data['total_ht']
            tva = invoice_data['tva_amount']
            ttc = invoice_data['total_ttc']
            
            if abs((ht + tva) - ttc) < 1:  # Tolérance de 1€
                score += 10
        
        # Pénalité si le texte est trop court
        if len(text) < 200:
            score -= 10
        
        return max(0, min(100, score))
    
    def validate_invoice_data(self, invoice_data: Dict[str, Any]) -> Dict[str, Any]:
        """Valide et nettoie les données extraites"""
        try:
            validated_data = invoice_data.copy()
            
            # Valider les montants
            for amount_field in ['total_ttc', 'total_ht', 'tva_amount']:
                if amount_field in validated_data and validated_data[amount_field]:
                    try:
                        amount = float(validated_data[amount_field])
                        if amount < 0 or amount > 1000000:  # Limites raisonnables
                            validated_data[amount_field] = None
                        else:
                            validated_data[amount_field] = round(amount, 2)
                    except (ValueError, TypeError):
                        validated_data[amount_field] = None
            
            # Valider les dates
            for date_field in ['invoice_date', 'due_date']:
                if date_field in validated_data and validated_data[date_field]:
                    # Ici on pourrait ajouter une validation de format de date
                    pass
            
            # Nettoyer les textes
            for text_field in ['client_name', 'supplier_name', 'invoice_number']:
                if text_field in validated_data and validated_data[text_field]:
                    text_value = str(validated_data[text_field]).strip()
                    if len(text_value) > 200:  # Limiter la longueur
                        text_value = text_value[:200]
                    validated_data[text_field] = text_value
            
            return validated_data
            
        except Exception as e:
            logger.error(f"Erreur lors de la validation: {e}")
            return invoice_data

