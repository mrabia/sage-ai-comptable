from typing import Dict, Any, List, Optional
import json
from datetime import datetime
from .sage_auth import SageOAuth2Service

class SageAPIService:
    """Service pour effectuer les opérations comptables via l'API Sage"""
    
    def __init__(self, oauth_service: SageOAuth2Service):
        self.oauth_service = oauth_service
    
    def _make_request(self, method: str, endpoint: str, credentials: Dict[str, Any],
                     business_id: Optional[str] = None, **kwargs):
        """Helper pour effectuer des requêtes API"""
        try:
            response = self.oauth_service.make_authenticated_request(
                method, endpoint, credentials, business_id, **kwargs
            )
            
            if response.status_code in [200, 201]:
                return response.json()
            else:
                raise Exception(f"Erreur API Sage: {response.status_code} - {response.text}")
        
        except Exception as e:
            raise Exception(f"Erreur lors de la requête Sage API: {str(e)}")
    
    # ===== GESTION DES CLIENTS =====
    
    def get_customers(self, credentials: Dict[str, Any], business_id: Optional[str] = None,
                     limit: int = 20, offset: int = 0) -> Dict[str, Any]:
        """Récupère la liste des clients"""
        params = {
            '$top': limit,
            '$skip': offset,
            'attributes': 'all'
        }
        
        return self._make_request('GET', 'contacts', credentials, business_id, params=params)
    
    def create_customer(self, credentials: Dict[str, Any], customer_data: Dict[str, Any],
                       business_id: Optional[str] = None) -> Dict[str, Any]:
        """Crée un nouveau client"""
        # Structure de base pour un client Sage
        sage_customer = {
            'contact_type_id': '1',  # 1 = Customer
            'name': customer_data.get('name'),
            'email': customer_data.get('email'),
            'telephone': customer_data.get('phone', ''),
            'mobile': customer_data.get('mobile', ''),
            'website': customer_data.get('website', ''),
            'notes': customer_data.get('notes', ''),
            'main_address': {
                'address_line_1': customer_data.get('address_line_1', ''),
                'address_line_2': customer_data.get('address_line_2', ''),
                'city': customer_data.get('city', ''),
                'postal_code': customer_data.get('postal_code', ''),
                'country_id': customer_data.get('country_id', 'FR')  # France par défaut
            }
        }
        
        return self._make_request('POST', 'contacts', credentials, business_id, json=sage_customer)
    
    def update_customer(self, credentials: Dict[str, Any], customer_id: str, 
                       customer_data: Dict[str, Any], business_id: Optional[str] = None) -> Dict[str, Any]:
        """Met à jour un client existant"""
        return self._make_request('PUT', f'contacts/{customer_id}', credentials, 
                                business_id, json=customer_data)
    
    def get_customer(self, credentials: Dict[str, Any], customer_id: str,
                    business_id: Optional[str] = None) -> Dict[str, Any]:
        """Récupère un client spécifique"""
        return self._make_request('GET', f'contacts/{customer_id}', credentials, business_id)
    
    # ===== GESTION DES FOURNISSEURS =====
    
    def get_suppliers(self, credentials: Dict[str, Any], business_id: Optional[str] = None,
                     limit: int = 20, offset: int = 0) -> Dict[str, Any]:
        """Récupère la liste des fournisseurs"""
        params = {
            '$top': limit,
            '$skip': offset,
            '$filter': 'contact_type_id eq 2',  # 2 = Supplier
            'attributes': 'all'
        }
        
        return self._make_request('GET', 'contacts', credentials, business_id, params=params)
    
    def create_supplier(self, credentials: Dict[str, Any], supplier_data: Dict[str, Any],
                       business_id: Optional[str] = None) -> Dict[str, Any]:
        """Crée un nouveau fournisseur"""
        sage_supplier = {
            'contact_type_id': '2',  # 2 = Supplier
            'name': supplier_data.get('name'),
            'email': supplier_data.get('email'),
            'telephone': supplier_data.get('phone', ''),
            'mobile': supplier_data.get('mobile', ''),
            'website': supplier_data.get('website', ''),
            'notes': supplier_data.get('notes', ''),
            'main_address': {
                'address_line_1': supplier_data.get('address_line_1', ''),
                'address_line_2': supplier_data.get('address_line_2', ''),
                'city': supplier_data.get('city', ''),
                'postal_code': supplier_data.get('postal_code', ''),
                'country_id': supplier_data.get('country_id', 'FR')
            }
        }
        
        return self._make_request('POST', 'contacts', credentials, business_id, json=sage_supplier)
    
    # ===== GESTION DES FACTURES =====
    
    def get_invoices(self, credentials: Dict[str, Any], business_id: Optional[str] = None,
                    limit: int = 20, offset: int = 0, status: Optional[str] = None) -> Dict[str, Any]:
        """Récupère la liste des factures"""
        params = {
            '$top': limit,
            '$skip': offset,
            'attributes': 'all'
        }
        
        if status:
            params['$filter'] = f'status_id eq {status}'
        
        return self._make_request('GET', 'sales_invoices', credentials, business_id, params=params)
    
    def create_invoice(self, credentials: Dict[str, Any], invoice_data: Dict[str, Any],
                      business_id: Optional[str] = None) -> Dict[str, Any]:
        """Crée une nouvelle facture"""
        # Structure de base pour une facture Sage
        sage_invoice = {
            'contact_id': invoice_data.get('customer_id'),
            'date': invoice_data.get('date', datetime.now().strftime('%Y-%m-%d')),
            'due_date': invoice_data.get('due_date'),
            'reference': invoice_data.get('reference', ''),
            'notes': invoice_data.get('notes', ''),
            'invoice_lines': []
        }
        
        # Ajouter les lignes de facture
        for item in invoice_data.get('items', []):
            line = {
                'description': item.get('description'),
                'quantity': item.get('quantity', 1),
                'unit_price': item.get('unit_price'),
                'tax_rate_id': item.get('tax_rate_id', '1')  # TVA par défaut
            }
            sage_invoice['invoice_lines'].append(line)
        
        return self._make_request('POST', 'sales_invoices', credentials, business_id, json=sage_invoice)
    
    def get_invoice(self, credentials: Dict[str, Any], invoice_id: str,
                   business_id: Optional[str] = None) -> Dict[str, Any]:
        """Récupère une facture spécifique"""
        return self._make_request('GET', f'sales_invoices/{invoice_id}', credentials, business_id)
    
    # ===== RAPPORTS FINANCIERS =====
    
    def get_balance_sheet(self, credentials: Dict[str, Any], business_id: Optional[str] = None,
                         from_date: Optional[str] = None, to_date: Optional[str] = None) -> Dict[str, Any]:
        """Récupère le bilan comptable"""
        params = {}
        if from_date:
            params['from_date'] = from_date
        if to_date:
            params['to_date'] = to_date
        
        return self._make_request('GET', 'reports/balance_sheet', credentials, business_id, params=params)
    
    def get_profit_loss(self, credentials: Dict[str, Any], business_id: Optional[str] = None,
                       from_date: Optional[str] = None, to_date: Optional[str] = None) -> Dict[str, Any]:
        """Récupère le compte de résultat"""
        params = {}
        if from_date:
            params['from_date'] = from_date
        if to_date:
            params['to_date'] = to_date
        
        return self._make_request('GET', 'reports/profit_and_loss', credentials, business_id, params=params)
    
    def get_aged_debtors(self, credentials: Dict[str, Any], business_id: Optional[str] = None) -> Dict[str, Any]:
        """Récupère le rapport des créances clients"""
        return self._make_request('GET', 'reports/aged_debtors', credentials, business_id)
    
    def get_aged_creditors(self, credentials: Dict[str, Any], business_id: Optional[str] = None) -> Dict[str, Any]:
        """Récupère le rapport des dettes fournisseurs"""
        return self._make_request('GET', 'reports/aged_creditors', credentials, business_id)
    
    # ===== TRANSACTIONS ET COMPTES =====
    
    def get_bank_accounts(self, credentials: Dict[str, Any], business_id: Optional[str] = None) -> Dict[str, Any]:
        """Récupère la liste des comptes bancaires"""
        return self._make_request('GET', 'bank_accounts', credentials, business_id)
    
    def get_bank_transactions(self, credentials: Dict[str, Any], bank_account_id: str,
                             business_id: Optional[str] = None, limit: int = 50) -> Dict[str, Any]:
        """Récupère les transactions d'un compte bancaire"""
        params = {
            '$top': limit,
            'attributes': 'all'
        }
        
        return self._make_request('GET', f'bank_accounts/{bank_account_id}/bank_transactions', 
                                credentials, business_id, params=params)
    
    def search_transactions(self, credentials: Dict[str, Any], search_criteria: Dict[str, Any],
                           business_id: Optional[str] = None) -> Dict[str, Any]:
        """Recherche des transactions selon des critères"""
        params = {
            '$top': search_criteria.get('limit', 50),
            '$skip': search_criteria.get('offset', 0)
        }
        
        # Construire les filtres
        filters = []
        if search_criteria.get('from_date'):
            filters.append(f"date ge '{search_criteria['from_date']}'")
        if search_criteria.get('to_date'):
            filters.append(f"date le '{search_criteria['to_date']}'")
        if search_criteria.get('min_amount'):
            filters.append(f"total_amount ge {search_criteria['min_amount']}")
        if search_criteria.get('max_amount'):
            filters.append(f"total_amount le {search_criteria['max_amount']}")
        
        if filters:
            params['$filter'] = ' and '.join(filters)
        
        return self._make_request('GET', 'sales_invoices', credentials, business_id, params=params)
    
    # ===== PRODUITS ET SERVICES =====
    
    def get_products(self, credentials: Dict[str, Any], business_id: Optional[str] = None,
                    limit: int = 20, offset: int = 0) -> Dict[str, Any]:
        """Récupère la liste des produits/services"""
        params = {
            '$top': limit,
            '$skip': offset,
            'attributes': 'all'
        }
        
        return self._make_request('GET', 'products', credentials, business_id, params=params)
    
    def create_product(self, credentials: Dict[str, Any], product_data: Dict[str, Any],
                      business_id: Optional[str] = None) -> Dict[str, Any]:
        """Crée un nouveau produit/service"""
        sage_product = {
            'item_code': product_data.get('code'),
            'description': product_data.get('description'),
            'sales_price': product_data.get('price'),
            'purchase_price': product_data.get('cost_price', 0),
            'usual_supplier_id': product_data.get('supplier_id'),
            'sales_tax_rate_id': product_data.get('tax_rate_id', '1'),
            'purchase_tax_rate_id': product_data.get('purchase_tax_rate_id', '1')
        }
        
        return self._make_request('POST', 'products', credentials, business_id, json=sage_product)
    
    # ===== UTILITAIRES =====
    
    def get_tax_rates(self, credentials: Dict[str, Any], business_id: Optional[str] = None) -> Dict[str, Any]:
        """Récupère les taux de TVA disponibles"""
        return self._make_request('GET', 'tax_rates', credentials, business_id)
    
    def get_chart_of_accounts(self, credentials: Dict[str, Any], business_id: Optional[str] = None) -> Dict[str, Any]:
        """Récupère le plan comptable"""
        return self._make_request('GET', 'ledger_accounts', credentials, business_id)
    
    def get_business_info(self, credentials: Dict[str, Any], business_id: str) -> Dict[str, Any]:
        """Récupère les informations d'un business"""
        return self._make_request('GET', f'businesses/{business_id}', credentials, business_id)

