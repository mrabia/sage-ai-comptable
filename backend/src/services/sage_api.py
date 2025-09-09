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
            'contact_type_id': 'CUSTOMER',  # Utiliser CUSTOMER selon API officielle
            'attributes': 'all'
        }
        
        return self._make_request('GET', 'contacts', credentials, business_id, params=params)
    
    def create_customer(self, credentials: Dict[str, Any], customer_data: Dict[str, Any],
                       business_id: Optional[str] = None) -> Dict[str, Any]:
        """Crée un nouveau client selon l'API officielle Sage"""
        
        # Structure officielle Sage API - doit être wrappée dans 'contact'
        contact_obj = {
            'contact_type_ids': ["CUSTOMER"],  # Array selon API officielle
            'name': customer_data.get('name', '')
        }
        
        # Ajouter les champs optionnels seulement s'ils sont fournis et non vides
        optional_fields = {
            'reference': customer_data.get('reference', ''),
            'email': customer_data.get('email', ''),
            'phone': customer_data.get('phone', ''),
            'mobile': customer_data.get('mobile', ''),
            'website': customer_data.get('website', ''),
            'notes': customer_data.get('notes', ''),
            'tax_number': customer_data.get('tax_number', '')
        }
        
        for field, value in optional_fields.items():
            if value and value.strip():
                contact_obj[field] = value
        
        # Ajouter l'adresse principale si des informations d'adresse sont fournies
        address_fields = ['address_line_1', 'address_line_2', 'city', 'region', 'postal_code']
        address_data = {field: customer_data.get(field, '') for field in address_fields}
        
        if any(address_data.values()):
            main_address = {
                'address_type_id': 'SALES',  # Default pour les clients selon la doc officielle
                'name': customer_data.get('name', ''),
                'is_main_address': True  # Requis selon API officielle
            }
            
            # Ajouter les champs d'adresse s'ils sont fournis
            for field, value in address_data.items():
                if value and value.strip():
                    main_address[field] = value
            
            # Ajouter country_group_id par défaut
            main_address['country_group_id'] = customer_data.get('country_group_id', 'FR')
            
            contact_obj['main_address'] = main_address
        
        sage_request = {'contact': contact_obj}
        
        return self._make_request('POST', 'contacts', credentials, business_id, json=sage_request)
    
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
            'contact_type_id': 'VENDOR',  # Utiliser VENDOR selon API officielle
            'attributes': 'all'
        }
        
        return self._make_request('GET', 'contacts', credentials, business_id, params=params)
    
    def create_supplier(self, credentials: Dict[str, Any], supplier_data: Dict[str, Any],
                       business_id: Optional[str] = None) -> Dict[str, Any]:
        """Crée un nouveau fournisseur selon l'API officielle Sage"""
        
        # Structure officielle Sage API pour fournisseur
        contact_obj = {
            'contact_type_ids': ["VENDOR"],  # VENDOR pour fournisseur selon API officielle
            'name': supplier_data.get('name', '')
        }
        
        # Ajouter les champs optionnels seulement s'ils sont fournis et non vides
        optional_fields = {
            'reference': supplier_data.get('reference', ''),
            'email': supplier_data.get('email', ''),
            'phone': supplier_data.get('phone', ''),
            'mobile': supplier_data.get('mobile', ''),
            'website': supplier_data.get('website', ''),
            'notes': supplier_data.get('notes', ''),
            'tax_number': supplier_data.get('tax_number', '')
        }
        
        for field, value in optional_fields.items():
            if value and value.strip():
                contact_obj[field] = value
        
        # Ajouter l'adresse principale si des informations d'adresse sont fournies
        address_fields = ['address_line_1', 'address_line_2', 'city', 'region', 'postal_code']
        address_data = {field: supplier_data.get(field, '') for field in address_fields}
        
        if any(address_data.values()):
            main_address = {
                'address_type_id': 'PURCHASING',  # Default pour les fournisseurs selon la doc officielle
                'name': supplier_data.get('name', ''),
                'is_main_address': True  # Requis selon API officielle
            }
            
            # Ajouter les champs d'adresse s'ils sont fournis
            for field, value in address_data.items():
                if value and value.strip():
                    main_address[field] = value
            
            # Ajouter country_group_id par défaut
            main_address['country_group_id'] = supplier_data.get('country_group_id', 'FR')
            
            contact_obj['main_address'] = main_address
        
        sage_request = {'contact': contact_obj}
        
        return self._make_request('POST', 'contacts', credentials, business_id, json=sage_request)
    
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
        """Crée une nouvelle facture selon l'API officielle Sage"""
        
        # Structure de base pour une facture Sage - doit être wrappée dans 'sales_invoice'
        invoice_obj = {
            'contact_id': invoice_data.get('customer_id'),
            'date': invoice_data.get('date', datetime.now().strftime('%Y-%m-%d'))
        }
        
        # Ajouter les champs optionnels seulement s'ils sont fournis
        optional_fields = {
            'due_date': invoice_data.get('due_date'),
            'reference': invoice_data.get('reference', ''),
            'notes': invoice_data.get('notes', '')
        }
        
        for field, value in optional_fields.items():
            if value:
                invoice_obj[field] = value
        
        # Ajouter les lignes de facture
        invoice_lines = []
        for item in invoice_data.get('items', []):
            line = {
                'description': item.get('description'),
                'quantity': float(item.get('quantity', 1)),
                'unit_price': float(item.get('unit_price'))
            }
            
            # Ajouter tax_rate_id si fourni
            if item.get('tax_rate_id'):
                line['tax_rate_id'] = item.get('tax_rate_id')
            
            invoice_lines.append(line)
        
        if invoice_lines:
            invoice_obj['invoice_lines'] = invoice_lines
        
        sage_request = {'sales_invoice': invoice_obj}
        
        return self._make_request('POST', 'sales_invoices', credentials, business_id, json=sage_request)
    
    def get_invoice(self, credentials: Dict[str, Any], invoice_id: str,
                   business_id: Optional[str] = None) -> Dict[str, Any]:
        """Récupère une facture spécifique"""
        return self._make_request('GET', f'sales_invoices/{invoice_id}', credentials, business_id)
    
    # ===== GESTION DES FACTURES FOURNISSEURS =====
    
    def get_purchase_invoices(self, credentials: Dict[str, Any], business_id: Optional[str] = None,
                            limit: int = 20, offset: int = 0, contact_id: Optional[str] = None,
                            status_id: Optional[str] = None, from_date: Optional[str] = None,
                            to_date: Optional[str] = None, search: Optional[str] = None) -> Dict[str, Any]:
        """Récupère la liste des factures fournisseurs selon l'API officielle Sage"""
        params = {
            '$top': limit,
            '$skip': offset,
            'attributes': 'all',
            'show_payments_allocations': True  # Include payment info for expert analysis
        }
        
        # Add optional filters based on official API documentation
        if contact_id:
            params['contact_id'] = contact_id
        if status_id:
            params['status_id'] = status_id
        if from_date:
            params['from_date'] = from_date
        if to_date:
            params['to_date'] = to_date
        if search:
            params['search'] = search
        
        return self._make_request('GET', 'purchase_invoices', credentials, business_id, params=params)
    
    def get_purchase_invoice(self, credentials: Dict[str, Any], invoice_id: str,
                           business_id: Optional[str] = None) -> Dict[str, Any]:
        """Récupère une facture fournisseur spécifique"""
        params = {
            'attributes': 'all',
            'show_payments_allocations': True
        }
        return self._make_request('GET', f'purchase_invoices/{invoice_id}', credentials, business_id, params=params)
    
    # ===== GESTION DES PAIEMENTS =====
    
    def get_contact_payments(self, credentials: Dict[str, Any], business_id: Optional[str] = None,
                           limit: int = 20, offset: int = 0, contact_id: Optional[str] = None,
                           bank_account_id: Optional[str] = None, transaction_type_id: Optional[str] = None,
                           from_date: Optional[str] = None, to_date: Optional[str] = None) -> Dict[str, Any]:
        """Récupère la liste des paiements selon l'API officielle Sage"""
        params = {
            '$top': limit,
            '$skip': offset,
            'attributes': 'all'
        }
        
        # Add optional filters based on official API documentation
        if contact_id:
            params['contact_id'] = contact_id
        if bank_account_id:
            params['bank_account_id'] = bank_account_id
        if transaction_type_id:
            params['transaction_type_id'] = transaction_type_id
        if from_date:
            params['from_date'] = from_date
        if to_date:
            params['to_date'] = to_date
        
        return self._make_request('GET', 'contact_payments', credentials, business_id, params=params)
    
    def get_contact_payment(self, credentials: Dict[str, Any], payment_id: str,
                          business_id: Optional[str] = None) -> Dict[str, Any]:
        """Récupère un paiement spécifique"""
        params = {
            'attributes': 'all'
        }
        return self._make_request('GET', f'contact_payments/{payment_id}', credentials, business_id, params=params)
    
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
        """Crée un nouveau produit/service selon l'API officielle Sage"""
        
        # Structure de base pour un produit Sage - doit être wrappée dans 'product'
        product_obj = {
            'item_code': product_data.get('code'),
            'description': product_data.get('description')
        }
        
        # Ajouter les champs optionnels seulement s'ils sont fournis
        optional_fields = {
            'sales_price': product_data.get('price'),
            'purchase_price': product_data.get('cost_price'),
            'usual_supplier_id': product_data.get('supplier_id'),
            'sales_tax_rate_id': product_data.get('tax_rate_id'),
            'purchase_tax_rate_id': product_data.get('purchase_tax_rate_id')
        }
        
        for field, value in optional_fields.items():
            if value is not None:
                if field in ['sales_price', 'purchase_price']:
                    product_obj[field] = float(value)
                else:
                    product_obj[field] = value
        
        sage_request = {'product': product_obj}
        
        return self._make_request('POST', 'products', credentials, business_id, json=sage_request)
    
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

