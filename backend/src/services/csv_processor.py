import os
import logging
import csv
import chardet
from typing import Optional, Dict, Any, List
import pandas as pd
from io import StringIO

logger = logging.getLogger(__name__)

class CSVProcessor:
    """Service pour traiter les fichiers CSV"""
    
    def __init__(self):
        self.supported_extensions = ['.csv']
        self.max_rows_preview = 1000  # Limite pour l'aperçu
    
    def extract_text(self, file_path: str) -> Optional[str]:
        """Extrait le contenu textuel d'un fichier CSV"""
        try:
            # Détecter l'encodage
            encoding = self._detect_encoding(file_path)
            
            # Lire le fichier CSV
            with open(file_path, 'r', encoding=encoding) as file:
                content = file.read()
            
            return content
            
        except Exception as e:
            logger.error(f"Erreur lors de la lecture du CSV: {e}")
            return None
    
    def _detect_encoding(self, file_path: str) -> str:
        """Détecte l'encodage du fichier CSV"""
        try:
            with open(file_path, 'rb') as file:
                raw_data = file.read(10000)  # Lire les premiers 10KB
                result = chardet.detect(raw_data)
                encoding = result['encoding']
                
                # Fallback vers des encodages courants
                if not encoding or result['confidence'] < 0.7:
                    # Tester les encodages courants
                    for test_encoding in ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']:
                        try:
                            with open(file_path, 'r', encoding=test_encoding) as test_file:
                                test_file.read(1000)
                                return test_encoding
                        except UnicodeDecodeError:
                            continue
                    
                    # Si rien ne fonctionne, utiliser utf-8 avec gestion d'erreurs
                    return 'utf-8'
                
                return encoding
                
        except Exception as e:
            logger.warning(f"Erreur lors de la détection d'encodage: {e}")
            return 'utf-8'
    
    def _detect_delimiter(self, file_path: str, encoding: str) -> str:
        """Détecte le délimiteur du fichier CSV"""
        try:
            with open(file_path, 'r', encoding=encoding) as file:
                # Lire les premières lignes pour détecter le délimiteur
                sample = file.read(1024)
                
            # Utiliser le détecteur de dialecte de Python
            sniffer = csv.Sniffer()
            dialect = sniffer.sniff(sample, delimiters=',;|\t')
            
            return dialect.delimiter
            
        except Exception as e:
            logger.warning(f"Erreur lors de la détection du délimiteur: {e}")
            # Fallback: tester les délimiteurs courants
            delimiters = [',', ';', '\t', '|']
            
            for delimiter in delimiters:
                try:
                    with open(file_path, 'r', encoding=encoding) as file:
                        reader = csv.reader(file, delimiter=delimiter)
                        first_row = next(reader)
                        second_row = next(reader)
                        
                        # Si les deux lignes ont le même nombre de colonnes > 1, c'est probablement bon
                        if len(first_row) == len(second_row) and len(first_row) > 1:
                            return delimiter
                except:
                    continue
            
            return ','  # Délimiteur par défaut
    
    def extract_structured_data(self, file_path: str) -> Dict[str, Any]:
        """Extrait les données structurées du fichier CSV"""
        try:
            # Détecter l'encodage et le délimiteur
            encoding = self._detect_encoding(file_path)
            delimiter = self._detect_delimiter(file_path, encoding)
            
            # Lire le CSV avec pandas
            df = pd.read_csv(
                file_path, 
                encoding=encoding, 
                delimiter=delimiter,
                nrows=self.max_rows_preview  # Limiter le nombre de lignes
            )
            
            # Nettoyer les données
            df = self._clean_dataframe(df)
            
            # Analyser la structure
            analysis = self._analyze_csv_structure(df)
            
            # Détecter le type de données
            data_type = self._detect_data_type(df)
            
            structured_data = {
                'data_type': data_type,
                'encoding': encoding,
                'delimiter': delimiter,
                'num_rows': len(df),
                'num_columns': len(df.columns),
                'columns': df.columns.tolist(),
                'column_types': df.dtypes.astype(str).to_dict(),
                'analysis': analysis,
                'preview_data': df.head(10).to_dict('records'),  # Aperçu des 10 premières lignes
                'sample_values': self._get_sample_values(df)
            }
            
            # Ajouter des données spécifiques selon le type détecté
            if data_type == 'clients':
                structured_data['clients_data'] = self._extract_clients_data(df)
            elif data_type == 'products':
                structured_data['products_data'] = self._extract_products_data(df)
            elif data_type == 'transactions':
                structured_data['transactions_data'] = self._extract_transactions_data(df)
            
            return structured_data
            
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction de données structurées: {e}")
            return {'error': str(e)}
    
    def _clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Nettoie le DataFrame"""
        try:
            # Supprimer les lignes complètement vides
            df = df.dropna(how='all')
            
            # Nettoyer les noms de colonnes
            df.columns = df.columns.str.strip()
            
            # Remplacer les valeurs vides par None
            df = df.where(pd.notnull(df), None)
            
            return df
            
        except Exception as e:
            logger.warning(f"Erreur lors du nettoyage: {e}")
            return df
    
    def _analyze_csv_structure(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyse la structure du CSV"""
        try:
            analysis = {}
            
            # Statistiques de base
            analysis['total_cells'] = df.size
            analysis['empty_cells'] = df.isnull().sum().sum()
            analysis['fill_rate'] = 1 - (analysis['empty_cells'] / analysis['total_cells'])
            
            # Analyse des colonnes
            column_analysis = {}
            for column in df.columns:
                col_data = df[column]
                column_analysis[column] = {
                    'non_null_count': col_data.count(),
                    'null_count': col_data.isnull().sum(),
                    'unique_count': col_data.nunique(),
                    'data_type': str(col_data.dtype),
                    'sample_values': col_data.dropna().head(3).tolist()
                }
            
            analysis['columns'] = column_analysis
            
            return analysis
            
        except Exception as e:
            logger.warning(f"Erreur lors de l'analyse: {e}")
            return {}
    
    def _detect_data_type(self, df: pd.DataFrame) -> str:
        """Détecte le type de données du CSV"""
        try:
            columns = [col.lower() for col in df.columns]
            
            # Patterns pour détecter les clients
            client_patterns = [
                'nom', 'name', 'client', 'customer', 'société', 'company',
                'email', 'mail', 'téléphone', 'phone', 'adresse', 'address'
            ]
            
            # Patterns pour détecter les produits
            product_patterns = [
                'produit', 'product', 'article', 'item', 'référence', 'ref',
                'prix', 'price', 'tarif', 'cost', 'tva', 'vat'
            ]
            
            # Patterns pour détecter les transactions
            transaction_patterns = [
                'date', 'montant', 'amount', 'débit', 'crédit', 'debit', 'credit',
                'facture', 'invoice', 'transaction', 'opération'
            ]
            
            # Compter les correspondances
            client_score = sum(1 for pattern in client_patterns 
                             if any(pattern in col for col in columns))
            
            product_score = sum(1 for pattern in product_patterns 
                              if any(pattern in col for col in columns))
            
            transaction_score = sum(1 for pattern in transaction_patterns 
                                  if any(pattern in col for col in columns))
            
            # Déterminer le type
            if client_score >= 2:
                return 'clients'
            elif product_score >= 2:
                return 'products'
            elif transaction_score >= 2:
                return 'transactions'
            else:
                return 'generic'
                
        except Exception as e:
            logger.warning(f"Erreur lors de la détection du type: {e}")
            return 'generic'
    
    def _get_sample_values(self, df: pd.DataFrame) -> Dict[str, List]:
        """Récupère des valeurs d'exemple pour chaque colonne"""
        try:
            sample_values = {}
            
            for column in df.columns:
                # Prendre 5 valeurs non-nulles uniques
                values = df[column].dropna().unique()[:5].tolist()
                sample_values[column] = values
            
            return sample_values
            
        except Exception as e:
            logger.warning(f"Erreur lors de l'extraction des valeurs d'exemple: {e}")
            return {}
    
    def _extract_clients_data(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Extrait les données clients du CSV"""
        try:
            clients = []
            
            # Mapper les colonnes communes
            column_mapping = self._map_client_columns(df.columns)
            
            for _, row in df.iterrows():
                client = {}
                
                for standard_field, csv_column in column_mapping.items():
                    if csv_column and csv_column in df.columns:
                        value = row[csv_column]
                        if pd.notna(value):
                            client[standard_field] = str(value).strip()
                
                if client:  # Ajouter seulement si on a des données
                    clients.append(client)
            
            return {
                'clients': clients,
                'total_count': len(clients),
                'column_mapping': column_mapping,
                'detected_fields': list(column_mapping.keys())
            }
            
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction des clients: {e}")
            return {'error': str(e)}
    
    def _map_client_columns(self, columns: List[str]) -> Dict[str, Optional[str]]:
        """Mappe les colonnes CSV vers les champs clients standards"""
        mapping = {
            'name': None,
            'email': None,
            'phone': None,
            'address': None,
            'city': None,
            'postal_code': None,
            'country': None,
            'company': None
        }
        
        columns_lower = [col.lower() for col in columns]
        
        # Patterns de mapping
        patterns = {
            'name': ['nom', 'name', 'client', 'customer'],
            'email': ['email', 'mail', 'e-mail'],
            'phone': ['téléphone', 'phone', 'tel', 'mobile'],
            'address': ['adresse', 'address', 'rue', 'street'],
            'city': ['ville', 'city', 'localité'],
            'postal_code': ['code postal', 'postal code', 'zip', 'cp'],
            'country': ['pays', 'country'],
            'company': ['société', 'company', 'entreprise', 'business']
        }
        
        for field, field_patterns in patterns.items():
            for pattern in field_patterns:
                for i, col in enumerate(columns_lower):
                    if pattern in col:
                        mapping[field] = columns[i]
                        break
                if mapping[field]:
                    break
        
        return mapping
    
    def _extract_products_data(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Extrait les données produits du CSV"""
        try:
            products = []
            
            # Mapper les colonnes communes
            column_mapping = self._map_product_columns(df.columns)
            
            for _, row in df.iterrows():
                product = {}
                
                for standard_field, csv_column in column_mapping.items():
                    if csv_column and csv_column in df.columns:
                        value = row[csv_column]
                        if pd.notna(value):
                            product[standard_field] = str(value).strip()
                
                if product:  # Ajouter seulement si on a des données
                    products.append(product)
            
            return {
                'products': products,
                'total_count': len(products),
                'column_mapping': column_mapping,
                'detected_fields': list(column_mapping.keys())
            }
            
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction des produits: {e}")
            return {'error': str(e)}
    
    def _map_product_columns(self, columns: List[str]) -> Dict[str, Optional[str]]:
        """Mappe les colonnes CSV vers les champs produits standards"""
        mapping = {
            'name': None,
            'reference': None,
            'description': None,
            'price': None,
            'vat_rate': None,
            'category': None,
            'unit': None
        }
        
        columns_lower = [col.lower() for col in columns]
        
        # Patterns de mapping
        patterns = {
            'name': ['nom', 'name', 'produit', 'product', 'article'],
            'reference': ['référence', 'reference', 'ref', 'sku', 'code'],
            'description': ['description', 'desc', 'détail'],
            'price': ['prix', 'price', 'tarif', 'cost', 'montant'],
            'vat_rate': ['tva', 'vat', 'taxe', 'tax'],
            'category': ['catégorie', 'category', 'type', 'famille'],
            'unit': ['unité', 'unit', 'u', 'mesure']
        }
        
        for field, field_patterns in patterns.items():
            for pattern in field_patterns:
                for i, col in enumerate(columns_lower):
                    if pattern in col:
                        mapping[field] = columns[i]
                        break
                if mapping[field]:
                    break
        
        return mapping
    
    def _extract_transactions_data(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Extrait les données de transactions du CSV"""
        try:
            transactions = []
            
            # Mapper les colonnes communes
            column_mapping = self._map_transaction_columns(df.columns)
            
            for _, row in df.iterrows():
                transaction = {}
                
                for standard_field, csv_column in column_mapping.items():
                    if csv_column and csv_column in df.columns:
                        value = row[csv_column]
                        if pd.notna(value):
                            transaction[standard_field] = str(value).strip()
                
                if transaction:  # Ajouter seulement si on a des données
                    transactions.append(transaction)
            
            return {
                'transactions': transactions,
                'total_count': len(transactions),
                'column_mapping': column_mapping,
                'detected_fields': list(column_mapping.keys())
            }
            
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction des transactions: {e}")
            return {'error': str(e)}
    
    def _map_transaction_columns(self, columns: List[str]) -> Dict[str, Optional[str]]:
        """Mappe les colonnes CSV vers les champs transactions standards"""
        mapping = {
            'date': None,
            'amount': None,
            'description': None,
            'type': None,
            'reference': None,
            'client': None
        }
        
        columns_lower = [col.lower() for col in columns]
        
        # Patterns de mapping
        patterns = {
            'date': ['date', 'jour', 'day'],
            'amount': ['montant', 'amount', 'prix', 'price', 'total'],
            'description': ['description', 'libellé', 'label', 'détail'],
            'type': ['type', 'catégorie', 'category'],
            'reference': ['référence', 'reference', 'ref', 'numéro'],
            'client': ['client', 'customer', 'nom']
        }
        
        for field, field_patterns in patterns.items():
            for pattern in field_patterns:
                for i, col in enumerate(columns_lower):
                    if pattern in col:
                        mapping[field] = columns[i]
                        break
                if mapping[field]:
                    break
        
        return mapping
    
    def is_valid_csv(self, file_path: str) -> bool:
        """Vérifie si le fichier est un CSV valide"""
        try:
            encoding = self._detect_encoding(file_path)
            delimiter = self._detect_delimiter(file_path, encoding)
            
            # Tenter de lire les premières lignes
            with open(file_path, 'r', encoding=encoding) as file:
                reader = csv.reader(file, delimiter=delimiter)
                first_row = next(reader)
                second_row = next(reader)
                
                # Vérifier qu'on a au moins 2 colonnes et 2 lignes
                return len(first_row) >= 2 and len(second_row) >= 2
                
        except Exception as e:
            logger.error(f"CSV invalide: {e}")
            return False

