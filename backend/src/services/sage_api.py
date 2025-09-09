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
    
    # ===== GESTION FISCALE ET TVA =====
    
    def get_tax_returns(self, credentials: Dict[str, Any], business_id: Optional[str] = None,
                       limit: int = 20, offset: int = 0, from_period_start_date: Optional[str] = None,
                       to_period_start_date: Optional[str] = None) -> Dict[str, Any]:
        """Récupère les déclarations fiscales selon l'API officielle Sage"""
        params = {
            '$top': limit,
            '$skip': offset,
            'attributes': 'all'
        }
        
        # Add optional filters based on official API documentation
        if from_period_start_date:
            params['from_period_start_date'] = from_period_start_date
        if to_period_start_date:
            params['to_period_start_date'] = to_period_start_date
        
        return self._make_request('GET', 'tax_returns', credentials, business_id, params=params)
    
    def get_tax_return(self, credentials: Dict[str, Any], tax_return_id: str,
                      business_id: Optional[str] = None) -> Dict[str, Any]:
        """Récupère une déclaration fiscale spécifique"""
        params = {
            'attributes': 'all'
        }
        return self._make_request('GET', f'tax_returns/{tax_return_id}', credentials, business_id, params=params)
    
    # ===== GESTION DES AVOIRS =====
    
    def get_sales_credit_notes(self, credentials: Dict[str, Any], business_id: Optional[str] = None,
                              limit: int = 20, offset: int = 0, contact_id: Optional[str] = None,
                              status_id: Optional[str] = None, from_date: Optional[str] = None,
                              to_date: Optional[str] = None, search: Optional[str] = None) -> Dict[str, Any]:
        """Récupère les avoirs clients selon l'API officielle Sage"""
        params = {
            '$top': limit,
            '$skip': offset,
            'attributes': 'all',
            'show_payments_allocations': True
        }
        
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
            
        return self._make_request('GET', 'sales_credit_notes', credentials, business_id, params=params)
    
    def get_purchase_credit_notes(self, credentials: Dict[str, Any], business_id: Optional[str] = None,
                                 limit: int = 20, offset: int = 0, contact_id: Optional[str] = None,
                                 status_id: Optional[str] = None, from_date: Optional[str] = None,
                                 to_date: Optional[str] = None, search: Optional[str] = None) -> Dict[str, Any]:
        """Récupère les avoirs fournisseurs selon l'API officielle Sage"""
        params = {
            '$top': limit,
            '$skip': offset,
            'attributes': 'all',
            'show_payments_allocations': True
        }
        
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
            
        return self._make_request('GET', 'purchase_credit_notes', credentials, business_id, params=params)
    
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
    
    # ===== JOURNAL ENTRIES - Expert Accounting Analysis =====
    
    def get_journal_entries(self, credentials: Dict[str, Any], business_id: Optional[str] = None,
                           limit: int = 20, offset: int = 0, from_date: Optional[str] = None,
                           to_date: Optional[str] = None, journal_code_id: Optional[str] = None,
                           contact_id: Optional[str] = None, search: Optional[str] = None) -> Dict[str, Any]:
        """Récupère les écritures comptables pour analyse experte des mouvements"""
        params = {
            '$top': limit,
            '$skip': offset,
            'attributes': 'all'
        }
        
        if from_date:
            params['from_date'] = from_date
        if to_date:
            params['to_date'] = to_date  
        if journal_code_id:
            params['journal_code_id'] = journal_code_id
        if contact_id:
            params['contact_id'] = contact_id
        if search:
            params['search'] = search
            
        return self._make_request('GET', 'journal_entries', credentials, business_id, params=params)
    
    def get_journal_codes(self, credentials: Dict[str, Any], business_id: Optional[str] = None,
                         limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        """Récupère les codes journaux disponibles"""
        params = {
            '$top': limit,
            '$skip': offset,
            'attributes': 'all'
        }
        return self._make_request('GET', 'journal_codes', credentials, business_id, params=params)
    
    # ===== LEDGER ACCOUNTS - Chart of Accounts Management =====
    
    def get_ledger_accounts(self, credentials: Dict[str, Any], business_id: Optional[str] = None,
                           limit: int = 50, offset: int = 0, account_type_id: Optional[str] = None,
                           search: Optional[str] = None, show_balance: bool = True) -> Dict[str, Any]:
        """Récupère le plan comptable avec analyse experte des comptes"""
        params = {
            '$top': limit,
            '$skip': offset,
            'attributes': 'all'
        }
        
        if account_type_id:
            params['account_type_id'] = account_type_id
        if search:
            params['search'] = search
        if show_balance:
            params['show_balance'] = 'true'
            
        return self._make_request('GET', 'ledger_accounts', credentials, business_id, params=params)
    
    def get_account_types(self, credentials: Dict[str, Any], business_id: Optional[str] = None,
                         limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        """Récupère les types de comptes disponibles"""
        params = {
            '$top': limit,
            '$skip': offset,
            'attributes': 'all'
        }
        return self._make_request('GET', 'account_types', credentials, business_id, params=params)
    
    # ===== BANK RECONCILIATION - Cash Management =====
    
    def get_bank_reconciliations(self, credentials: Dict[str, Any], business_id: Optional[str] = None,
                                limit: int = 20, offset: int = 0, bank_account_id: Optional[str] = None,
                                from_date: Optional[str] = None, to_date: Optional[str] = None,
                                status: Optional[str] = None) -> Dict[str, Any]:
        """Récupère les rapprochements bancaires pour analyse des flux de trésorerie"""
        params = {
            '$top': limit,
            '$skip': offset,
            'attributes': 'all'
        }
        
        if bank_account_id:
            params['bank_account_id'] = bank_account_id
        if from_date:
            params['from_date'] = from_date
        if to_date:
            params['to_date'] = to_date
        if status:
            params['status'] = status
            
        return self._make_request('GET', 'bank_reconciliations', credentials, business_id, params=params)
    
    def get_bank_transactions(self, credentials: Dict[str, Any], business_id: Optional[str] = None,
                             limit: int = 50, offset: int = 0, bank_account_id: Optional[str] = None,
                             from_date: Optional[str] = None, to_date: Optional[str] = None,
                             reconciled: Optional[str] = None) -> Dict[str, Any]:
        """Récupère les transactions bancaires pour analyse de rapprochement"""
        params = {
            '$top': limit,
            '$skip': offset,
            'attributes': 'all'
        }
        
        if bank_account_id:
            params['bank_account_id'] = bank_account_id
        if from_date:
            params['from_date'] = from_date
        if to_date:
            params['to_date'] = to_date
        if reconciled is not None:
            params['reconciled'] = reconciled
            
        return self._make_request('GET', 'bank_transactions', credentials, business_id, params=params)
    
    # ===== CREATE PURCHASE INVOICE - Complete P2P Cycle =====
    
    def create_purchase_invoice(self, credentials: Dict[str, Any], invoice_data: Dict[str, Any], 
                               business_id: Optional[str] = None) -> Dict[str, Any]:
        """Crée une nouvelle facture fournisseur selon l'API officielle Sage"""
        # Construire l'objet facture selon le schéma officiel Sage
        purchase_invoice = {
            "contact_id": invoice_data['contact_id'],
            "reference": invoice_data.get('reference', ''),
            "date": invoice_data['date'],
            "due_date": invoice_data.get('due_date', invoice_data['date']),
            "currency_id": invoice_data.get('currency_id', 'GBP'),  # Default to GBP
            "exchange_rate": invoice_data.get('exchange_rate', 1.0)
        }
        
        # Champs optionnels pour factures fournisseurs
        optional_fields = {
            'vendor_reference': invoice_data.get('vendor_reference'),
            'notes': invoice_data.get('notes'),
            'tax_address_region_id': invoice_data.get('tax_address_region_id'),
            'tax_calculation_method': invoice_data.get('tax_calculation_method', 'compound')
        }
        
        for field, value in optional_fields.items():
            if value is not None:
                purchase_invoice[field] = value
        
        # Traitement des lignes de facture
        if 'items' in invoice_data and invoice_data['items']:
            purchase_invoice['invoice_lines'] = []
            
            for item in invoice_data['items']:
                line = {
                    "ledger_account_id": item.get('ledger_account_id'),
                    "description": item.get('description', ''),
                    "quantity": float(item.get('quantity', 1)),
                    "unit_price": float(item.get('unit_price', 0)),
                    "net_amount": float(item.get('net_amount', 0)),
                    "tax_rate_id": item.get('tax_rate_id')
                }
                
                # Calcul automatique du montant net si non fourni
                if not line['net_amount'] and line['quantity'] and line['unit_price']:
                    line['net_amount'] = line['quantity'] * line['unit_price']
                
                # Champs optionnels pour les lignes
                if item.get('trade_of_asset'):
                    line['trade_of_asset'] = item['trade_of_asset']
                if item.get('eu_goods_services_type_id'):
                    line['eu_goods_services_type_id'] = item['eu_goods_services_type_id']
                
                purchase_invoice['invoice_lines'].append(line)
        
        sage_request = {'purchase_invoice': purchase_invoice}
        
        return self._make_request('POST', 'purchase_invoices', credentials, business_id, json=sage_request)
    
    # ===== FIXED ASSETS ANALYSIS - Asset Management =====
    
    def get_fixed_assets_analysis(self, credentials: Dict[str, Any], business_id: Optional[str] = None,
                                 limit: int = 50, from_date: Optional[str] = None,
                                 to_date: Optional[str] = None) -> Dict[str, Any]:
        """Analyse les immobilisations via les comptes comptables et transactions"""
        # Récupérer les comptes d'actifs immobilisés (comptes 2xxx en France)
        accounts_result = self.get_ledger_accounts(
            credentials, business_id, limit=100, show_balance=True
        )
        
        # Filtrer les comptes d'immobilisations
        fixed_asset_accounts = []
        for account in accounts_result.get('$items', []):
            account_code = account.get('ledger_account_code', account.get('nominal_code', ''))
            account_type = account.get('account_type', {}).get('displayed_as', '').lower()
            
            # Identifier les comptes d'immobilisations
            if (account_code and (
                account_code.startswith('2') or  # Comptes classe 2 (France)
                'asset' in account_type or
                'fixed' in account_type or
                'plant' in account_type or
                'equipment' in account_type or
                'machinery' in account_type or
                'building' in account_type or
                'land' in account_type
            )):
                fixed_asset_accounts.append(account)
        
        # Analyser les transactions sur ces comptes si demandé
        asset_transactions = []
        if from_date or to_date:
            try:
                # Récupérer les écritures sur la période
                journal_result = self.get_journal_entries(
                    credentials, business_id, limit=200, from_date=from_date, to_date=to_date
                )
                
                for entry in journal_result.get('$items', []):
                    for line in entry.get('journal_lines', []):
                        line_account_id = line.get('ledger_account', {}).get('id')
                        # Vérifier si cette ligne concerne un compte d'immobilisation
                        for asset_account in fixed_asset_accounts:
                            if asset_account.get('id') == line_account_id:
                                asset_transactions.append({
                                    'entry_date': entry.get('date'),
                                    'entry_ref': entry.get('reference', entry.get('displayed_as')),
                                    'account_code': asset_account.get('ledger_account_code'),
                                    'account_name': asset_account.get('displayed_as'),
                                    'description': line.get('description', entry.get('description', '')),
                                    'debit': line.get('debit', 0),
                                    'credit': line.get('credit', 0),
                                    'net_amount': float(line.get('debit', 0)) - float(line.get('credit', 0))
                                })
                                break
            except Exception as e:
                # Si l'analyse des transactions échoue, continuer avec les comptes seulement
                pass
        
        return {
            'fixed_asset_accounts': fixed_asset_accounts,
            'asset_transactions': asset_transactions,
            'analysis_period': {
                'from_date': from_date,
                'to_date': to_date
            }
        }
    
    # ===== CREATE JOURNAL ENTRY - Manual Accounting Entries =====
    
    def create_manual_journal_entry(self, credentials: Dict[str, Any], journal_data: Dict[str, Any], 
                                   business_id: Optional[str] = None) -> Dict[str, Any]:
        """Crée une écriture comptable manuelle via les services Sage"""
        # Dans Sage, les écritures manuelles peuvent être créées via plusieurs méthodes:
        # 1. Via des "Other Payments" ou "Other Receipts" 
        # 2. Via des "Journal" entries si disponible
        # 3. Via des "Quick Entries"
        
        # Construire l'écriture selon le schéma Sage
        entry_type = journal_data.get('entry_type', 'other_payment')  # other_payment, other_receipt, journal
        
        if entry_type == 'other_payment':
            # Utiliser l'API Other Payments pour les écritures manuelles
            other_payment = {
                "transaction_type_id": journal_data.get('transaction_type_id'),
                "reference": journal_data.get('reference', ''),
                "total_amount": float(journal_data.get('total_amount', 0)),
                "date": journal_data['date'],
                "contact_id": journal_data.get('contact_id'),
                "bank_account_id": journal_data.get('bank_account_id'),
                "description": journal_data.get('description', journal_data.get('narrative', ''))
            }
            
            # Champs optionnels
            if journal_data.get('tax_rate_id'):
                other_payment['tax_rate_id'] = journal_data['tax_rate_id']
            if journal_data.get('net_amount'):
                other_payment['net_amount'] = float(journal_data['net_amount'])
                
            sage_request = {'other_payment': other_payment}
            return self._make_request('POST', 'other_payments', credentials, business_id, json=sage_request)
            
        elif entry_type == 'other_receipt':
            # Utiliser l'API Other Receipts pour les écritures manuelles
            other_receipt = {
                "transaction_type_id": journal_data.get('transaction_type_id'),
                "reference": journal_data.get('reference', ''),
                "total_amount": float(journal_data.get('total_amount', 0)),
                "date": journal_data['date'],
                "contact_id": journal_data.get('contact_id'),
                "bank_account_id": journal_data.get('bank_account_id'),
                "description": journal_data.get('description', journal_data.get('narrative', ''))
            }
            
            # Champs optionnels
            if journal_data.get('tax_rate_id'):
                other_receipt['tax_rate_id'] = journal_data['tax_rate_id']
            if journal_data.get('net_amount'):
                other_receipt['net_amount'] = float(journal_data['net_amount'])
                
            sage_request = {'other_receipt': other_receipt}
            return self._make_request('POST', 'other_receipts', credentials, business_id, json=sage_request)
            
        else:
            # Fallback - essayer les quick entries ou journals si disponible
            return {
                'error': 'Type d\'écriture non supporté. Utilisez "other_payment" ou "other_receipt".'
            }
            
    def get_transaction_types(self, credentials: Dict[str, Any], business_id: Optional[str] = None,
                             limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        """Récupère les types de transactions disponibles pour les écritures manuelles"""
        params = {
            '$top': limit,
            '$skip': offset,
            'attributes': 'all'
        }
        return self._make_request('GET', 'transaction_types', credentials, business_id, params=params)

