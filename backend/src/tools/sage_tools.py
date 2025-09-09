# Try different CrewAI import paths for compatibility
try:
    from crewai.tools import BaseTool
except ImportError:
    try:
        from crewai import BaseTool
    except ImportError:
        try:
            from crewai.tool import BaseTool
        except ImportError:
            # Fallback - create a dummy BaseTool class
            class BaseTool:
                def __init__(self, **kwargs):
                    for key, value in kwargs.items():
                        setattr(self, key, value)
from typing import Type, Dict, Any, Optional
from pydantic import BaseModel, Field
from services.sage_auth import SageOAuth2Service
from services.sage_api import SageAPIService
import json
import os

# Configuration OAuth2 Sage
SAGE_CLIENT_ID = os.getenv('SAGE_CLIENT_ID', 'your_client_id')
SAGE_CLIENT_SECRET = os.getenv('SAGE_CLIENT_SECRET', 'your_client_secret')
SAGE_REDIRECT_URI = os.getenv('SAGE_REDIRECT_URI', 'http://localhost:5000/api/sage/callback')

# Initialiser les services Sage
sage_oauth = SageOAuth2Service(SAGE_CLIENT_ID, SAGE_CLIENT_SECRET, SAGE_REDIRECT_URI)
sage_api = SageAPIService(sage_oauth)

# Variable globale pour stocker les credentials de l'utilisateur courant
_current_user_credentials = None

def set_user_credentials(credentials: Dict[str, Any]):
    """Définit les credentials de l'utilisateur courant pour tous les outils Sage"""
    global _current_user_credentials
    _current_user_credentials = credentials

def get_user_credentials() -> Optional[Dict[str, Any]]:
    """Récupère les credentials de l'utilisateur courant"""
    global _current_user_credentials
    return _current_user_credentials

class SageBaseTool(BaseTool):
    """Classe de base pour tous les outils Sage avec injection automatique des credentials"""
    
    def get_credentials(self) -> Optional[Dict[str, Any]]:
        """Récupère automatiquement les credentials de l'utilisateur connecté"""
        return get_user_credentials()

class CreateCustomerInput(BaseModel):
    """Input schema for creating a customer"""
    name: str = Field(..., description="Customer name")
    email: str = Field(..., description="Customer email address")
    phone: Optional[str] = Field(None, description="Customer phone number")
    address_line_1: Optional[str] = Field(None, description="Customer address line 1")
    city: Optional[str] = Field(None, description="Customer city")
    postal_code: Optional[str] = Field(None, description="Customer postal code")
    business_id: Optional[str] = Field(None, description="Sage business ID")

class CreateCustomerTool(SageBaseTool):
    name: str = "create_customer"
    description: str = "Crée un nouveau client dans Sage Business Cloud Accounting"
    args_schema: Type[BaseModel] = CreateCustomerInput

    def _run(self, name: str, email: str, 
             phone: Optional[str] = None, address_line_1: Optional[str] = None,
             city: Optional[str] = None, postal_code: Optional[str] = None,
             business_id: Optional[str] = None) -> str:
        try:
            # Utiliser les credentials automatiquement
            credentials = self.get_credentials()
            if not credentials:
                return "❌ Erreur: Aucune connexion Sage détectée. Veuillez vous connecter à Sage d'abord."
            
            customer_data = {
                'name': name,
                'email': email,
                'phone': phone or '',
                'address_line_1': address_line_1 or '',
                'city': city or '',
                'postal_code': postal_code or ''
            }
            
            result = sage_api.create_customer(credentials, customer_data, business_id)
            
            return f"✅ Client créé avec succès: {result.get('name', name)} (ID: {result.get('id', 'N/A')})"
            
        except Exception as e:
            return f"❌ Erreur lors de la création du client: {str(e)}"

class GetCustomersInput(BaseModel):
    """Input schema for getting customers"""
    limit: Optional[int] = Field(20, description="Number of customers to retrieve")
    business_id: Optional[str] = Field(None, description="Sage business ID")

class GetCustomersTool(SageBaseTool):
    name: str = "get_customers"
    description: str = "Récupère la liste des clients depuis Sage Business Cloud Accounting"
    args_schema: Type[BaseModel] = GetCustomersInput

    def _run(self, limit: Optional[int] = 20, 
             business_id: Optional[str] = None) -> str:
        try:
            # Utiliser les credentials automatiquement
            credentials = self.get_credentials()
            if not credentials:
                return "❌ Erreur: Aucune connexion Sage détectée. Veuillez vous connecter à Sage d'abord."
            
            result = sage_api.get_customers(credentials, business_id, limit, 0)
            
            customers = result.get('$items', [])
            if not customers:
                return "ℹ️ Aucun client trouvé dans votre compte Sage."
            
            customer_list = []
            for customer in customers:
                customer_info = f"- {customer.get('name', 'N/A')} (ID: {customer.get('id', 'N/A')}, Email: {customer.get('email', 'N/A')})"
                customer_list.append(customer_info)
            
            return f"✅ Liste des clients ({len(customers)} trouvés):\n" + "\n".join(customer_list)
            
        except Exception as e:
            return f"❌ Erreur lors de la récupération des clients: {str(e)}"

class CreateInvoiceInput(BaseModel):
    """Input schema for creating an invoice"""
    customer_id: str = Field(..., description="Customer ID")
    items: list = Field(..., description="List of invoice items with description, quantity, unit_price")
    date: Optional[str] = Field(None, description="Invoice date (YYYY-MM-DD)")
    due_date: Optional[str] = Field(None, description="Due date (YYYY-MM-DD)")
    reference: Optional[str] = Field(None, description="Invoice reference")
    business_id: Optional[str] = Field(None, description="Sage business ID")

class CreateInvoiceTool(SageBaseTool):
    name: str = "create_invoice"
    description: str = "Crée une nouvelle facture dans Sage Business Cloud Accounting"
    args_schema: Type[BaseModel] = CreateInvoiceInput

    def _run(self, customer_id: str, items: list,
             date: Optional[str] = None, due_date: Optional[str] = None,
             reference: Optional[str] = None, business_id: Optional[str] = None) -> str:
        try:
            # Utiliser les credentials automatiquement
            credentials = self.get_credentials()
            if not credentials:
                return "❌ Erreur: Aucune connexion Sage détectée. Veuillez vous connecter à Sage d'abord."
            
            # Validation des données d'entrée
            if not customer_id or not customer_id.strip():
                return "❌ Erreur: L'ID du client est requis pour créer une facture."
            
            if not items or len(items) == 0:
                return "❌ Erreur: Au moins un article est requis pour créer une facture."
            
            # Validation des articles
            for i, item in enumerate(items, 1):
                if not isinstance(item, dict):
                    return f"❌ Erreur: L'article {i} doit être un dictionnaire avec les clés: description, quantity, unit_price."
                
                required_fields = ['description', 'quantity', 'unit_price']
                for field in required_fields:
                    if field not in item or item[field] is None:
                        return f"❌ Erreur: L'article {i} doit contenir le champ '{field}'."
                
                try:
                    quantity = float(item['quantity'])
                    unit_price = float(item['unit_price'])
                    if quantity <= 0 or unit_price < 0:
                        return f"❌ Erreur: L'article {i} a des valeurs invalides (quantité > 0, prix ≥ 0)."
                except (ValueError, TypeError):
                    return f"❌ Erreur: L'article {i} contient des valeurs numériques invalides."
            
            invoice_data = {
                'customer_id': customer_id,
                'items': items,
                'date': date,
                'due_date': due_date,
                'reference': reference
            }
            
            result = sage_api.create_invoice(credentials, invoice_data, business_id)
            
            total_amount = result.get('total_amount', 'N/A')
            invoice_id = result.get('id', 'N/A')
            
            return f"✅ Facture créée avec succès: N°{result.get('displayed_as', reference or invoice_id)} - Montant: {total_amount}€"
            
        except Exception as e:
            error_msg = str(e).lower()
            if 'unauthorized' in error_msg or '401' in error_msg:
                return "❌ Erreur d'authentification: Votre session Sage a expiré. Veuillez vous reconnecter."
            elif 'not found' in error_msg or '404' in error_msg:
                return "❌ Erreur: Client non trouvé. Vérifiez que l'ID du client est correct."
            elif 'bad request' in error_msg or '400' in error_msg:
                return "❌ Erreur: Données de facture invalides. Vérifiez les informations fournies."
            else:
                return f"❌ Erreur lors de la création de la facture: {str(e)}"

class GetInvoicesInput(BaseModel):
    """Input schema for getting invoices"""
    limit: Optional[int] = Field(20, description="Number of invoices to retrieve")
    status: Optional[str] = Field(None, description="Invoice status filter")
    business_id: Optional[str] = Field(None, description="Sage business ID")

class GetInvoicesTool(SageBaseTool):
    name: str = "get_invoices"
    description: str = "Récupère la liste des factures depuis Sage Business Cloud Accounting"
    args_schema: Type[BaseModel] = GetInvoicesInput

    def _run(self, limit: Optional[int] = 20,
             status: Optional[str] = None, business_id: Optional[str] = None) -> str:
        try:
            # Utiliser les credentials automatiquement
            credentials = self.get_credentials()
            if not credentials:
                return "❌ Erreur: Aucune connexion Sage détectée. Veuillez vous connecter à Sage d'abord."
            
            result = sage_api.get_invoices(credentials, business_id, limit, 0, status)
            
            invoices = result.get('$items', [])
            if not invoices:
                return "Aucune facture trouvée."
            
            invoice_list = []
            for invoice in invoices:
                invoice_info = f"- {invoice.get('displayed_as', 'N/A')} - {invoice.get('total_amount', 'N/A')}€ - Statut: {invoice.get('status', {}).get('displayed_as', 'N/A')}"
                invoice_list.append(invoice_info)
            
            return f"Liste des factures ({len(invoices)} trouvées):\n" + "\n".join(invoice_list)
            
        except Exception as e:
            return f"Erreur lors de la récupération des factures: {str(e)}"

class GetPurchaseInvoicesInput(BaseModel):
    """Input schema for getting purchase invoices"""
    limit: Optional[int] = Field(20, description="Number of purchase invoices to retrieve")
    contact_id: Optional[str] = Field(None, description="Filter by supplier contact ID")
    status_id: Optional[str] = Field(None, description="Filter by invoice status ID")
    from_date: Optional[str] = Field(None, description="Filter from date (YYYY-MM-DD)")
    to_date: Optional[str] = Field(None, description="Filter to date (YYYY-MM-DD)")
    search: Optional[str] = Field(None, description="Search by invoice reference or contact name")
    business_id: Optional[str] = Field(None, description="Sage business ID")

class GetPurchaseInvoicesTool(SageBaseTool):
    name: str = "get_purchase_invoices"
    description: str = "Récupère la liste des factures fournisseurs depuis Sage Business Cloud Accounting"
    args_schema: Type[BaseModel] = GetPurchaseInvoicesInput

    def _run(self, limit: Optional[int] = 20, contact_id: Optional[str] = None,
             status_id: Optional[str] = None, from_date: Optional[str] = None,
             to_date: Optional[str] = None, search: Optional[str] = None,
             business_id: Optional[str] = None) -> str:
        try:
            # Utiliser les credentials automatiquement
            credentials = self.get_credentials()
            if not credentials:
                return "❌ Erreur: Aucune connexion Sage détectée. Veuillez vous connecter à Sage d'abord."
            
            result = sage_api.get_purchase_invoices(
                credentials, business_id, limit, 0, contact_id, 
                status_id, from_date, to_date, search
            )
            
            invoices = result.get('$items', [])
            if not invoices:
                return "ℹ️ Aucune facture fournisseur trouvée avec ces critères."
            
            invoice_list = []
            for invoice in invoices:
                # Extract key information for expert analysis
                supplier = invoice.get('contact', {}).get('displayed_as', 'N/A')
                ref = invoice.get('reference', invoice.get('displayed_as', 'N/A'))
                total = invoice.get('total_amount', 'N/A')
                status = invoice.get('status', {}).get('displayed_as', 'N/A')
                date = invoice.get('date', 'N/A')
                
                invoice_info = f"- {ref} | {supplier} | {total}€ | {status} | {date}"
                invoice_list.append(invoice_info)
            
            return f"✅ Factures fournisseurs ({len(invoices)} trouvées):\n" + "\n".join(invoice_list)
            
        except Exception as e:
            return f"❌ Erreur lors de la récupération des factures fournisseurs: {str(e)}"

class GetPaymentsInput(BaseModel):
    """Input schema for getting contact payments"""
    limit: Optional[int] = Field(20, description="Number of payments to retrieve")
    contact_id: Optional[str] = Field(None, description="Filter by specific contact ID")
    bank_account_id: Optional[str] = Field(None, description="Filter by bank account ID") 
    transaction_type_id: Optional[str] = Field(None, description="Filter by transaction type ID")
    from_date: Optional[str] = Field(None, description="Filter from date (YYYY-MM-DD)")
    to_date: Optional[str] = Field(None, description="Filter to date (YYYY-MM-DD)")
    business_id: Optional[str] = Field(None, description="Sage business ID")

class GetPaymentsTool(SageBaseTool):
    name: str = "get_payments"
    description: str = "Récupère la liste des paiements depuis Sage Business Cloud Accounting"
    args_schema: Type[BaseModel] = GetPaymentsInput

    def _run(self, limit: Optional[int] = 20, contact_id: Optional[str] = None,
             bank_account_id: Optional[str] = None, transaction_type_id: Optional[str] = None,
             from_date: Optional[str] = None, to_date: Optional[str] = None,
             business_id: Optional[str] = None) -> str:
        try:
            # Utiliser les credentials automatiquement
            credentials = self.get_credentials()
            if not credentials:
                return "❌ Erreur: Aucune connexion Sage détectée. Veuillez vous connecter à Sage d'abord."
            
            result = sage_api.get_contact_payments(
                credentials, business_id, limit, 0, contact_id,
                bank_account_id, transaction_type_id, from_date, to_date
            )
            
            payments = result.get('$items', [])
            if not payments:
                return "ℹ️ Aucun paiement trouvé avec ces critères."
            
            payment_list = []
            for payment in payments:
                # Extract key information for expert cash flow analysis
                contact = payment.get('contact', {}).get('displayed_as', 'N/A')
                amount = payment.get('net_amount', payment.get('total_amount', 'N/A'))
                date = payment.get('date', 'N/A')
                reference = payment.get('reference', payment.get('displayed_as', 'N/A'))
                bank_account = payment.get('bank_account', {}).get('displayed_as', 'N/A')
                payment_type = payment.get('payment_method', {}).get('displayed_as', 'N/A')
                
                payment_info = f"- {reference} | {contact} | {amount}€ | {date} | {bank_account} | {payment_type}"
                payment_list.append(payment_info)
            
            return f"✅ Paiements ({len(payments)} trouvés):\n" + "\n".join(payment_list)
            
        except Exception as e:
            return f"❌ Erreur lors de la récupération des paiements: {str(e)}"

class GetTaxReturnsInput(BaseModel):
    """Input schema for getting tax returns"""
    limit: Optional[int] = Field(20, description="Number of tax returns to retrieve")
    from_period_start_date: Optional[str] = Field(None, description="Filter from period start date (YYYY-MM-DD)")
    to_period_start_date: Optional[str] = Field(None, description="Filter to period start date (YYYY-MM-DD)")
    business_id: Optional[str] = Field(None, description="Sage business ID")

class GetTaxReturnsTool(SageBaseTool):
    name: str = "get_tax_returns"
    description: str = "Récupère les déclarations fiscales et TVA depuis Sage Business Cloud Accounting"
    args_schema: Type[BaseModel] = GetTaxReturnsInput

    def _run(self, limit: Optional[int] = 20, from_period_start_date: Optional[str] = None,
             to_period_start_date: Optional[str] = None, business_id: Optional[str] = None) -> str:
        try:
            # Utiliser les credentials automatiquement
            credentials = self.get_credentials()
            if not credentials:
                return "❌ Erreur: Aucune connexion Sage détectée. Veuillez vous connecter à Sage d'abord."
            
            result = sage_api.get_tax_returns(
                credentials, business_id, limit, 0, from_period_start_date, to_period_start_date
            )
            
            tax_returns = result.get('$items', [])
            if not tax_returns:
                return "ℹ️ Aucune déclaration fiscale trouvée avec ces critères."
            
            tax_return_list = []
            for tax_return in tax_returns:
                # Extract key information for expert tax compliance analysis
                period = tax_return.get('reporting_period', {}).get('displayed_as', 'N/A')
                status = tax_return.get('status', {}).get('displayed_as', 'N/A')
                scheme = tax_return.get('tax_scheme', {}).get('displayed_as', 'N/A')
                due_date = tax_return.get('due_date', 'N/A')
                submitted_date = tax_return.get('submitted_date', 'Non soumis')
                total_amount = tax_return.get('total_amount', 'N/A')
                
                tax_return_info = f"- {period} | {scheme} | {status} | Due: {due_date} | Submitted: {submitted_date} | {total_amount}€"
                tax_return_list.append(tax_return_info)
            
            return f"✅ Déclarations fiscales ({len(tax_returns)} trouvées):\n" + "\n".join(tax_return_list)
            
        except Exception as e:
            return f"❌ Erreur lors de la récupération des déclarations fiscales: {str(e)}"

class GetAgingAnalysisInput(BaseModel):
    """Input schema for aging analysis"""
    analysis_type: Optional[str] = Field("receivables", description="Type of aging analysis: receivables or payables")
    limit: Optional[int] = Field(50, description="Number of items to analyze")
    business_id: Optional[str] = Field(None, description="Sage business ID")

class GetAgingAnalysisTool(SageBaseTool):
    name: str = "get_aging_analysis"
    description: str = "Analyse l'âge des créances/dettes pour la gestion de trésorerie experte"
    args_schema: Type[BaseModel] = GetAgingAnalysisInput

    def _run(self, analysis_type: Optional[str] = "receivables", limit: Optional[int] = 50,
             business_id: Optional[str] = None) -> str:
        try:
            # Utiliser les credentials automatiquement
            credentials = self.get_credentials()
            if not credentials:
                return "❌ Erreur: Aucune connexion Sage détectée. Veuillez vous connecter à Sage d'abord."
            
            if analysis_type == "receivables":
                # Analyze customer receivables aging
                invoices_result = sage_api.get_invoices(credentials, business_id, limit, 0, None)
                payments_result = sage_api.get_contact_payments(credentials, business_id, limit, 0)
                
                aging_data = self._analyze_receivables_aging(invoices_result, payments_result)
                return f"✅ Analyse des créances clients:\n{aging_data}"
                
            elif analysis_type == "payables":
                # Analyze supplier payables aging  
                purchase_result = sage_api.get_purchase_invoices(credentials, business_id, limit, 0)
                payments_result = sage_api.get_contact_payments(credentials, business_id, limit, 0)
                
                aging_data = self._analyze_payables_aging(purchase_result, payments_result)
                return f"✅ Analyse des dettes fournisseurs:\n{aging_data}"
            else:
                return "❌ Type d'analyse invalide. Utilisez 'receivables' ou 'payables'."
            
        except Exception as e:
            return f"❌ Erreur lors de l'analyse aging: {str(e)}"
    
    def _analyze_receivables_aging(self, invoices_result: dict, payments_result: dict) -> str:
        """Analyze receivables aging from invoices and payments data"""
        invoices = invoices_result.get('$items', [])
        payments = payments_result.get('$items', [])
        
        if not invoices:
            return "Aucune facture trouvée pour l'analyse."
        
        # Group by aging periods: 0-30, 31-60, 61-90, 90+ days
        from datetime import datetime, timedelta
        today = datetime.now()
        aging_buckets = {"0-30": 0, "31-60": 0, "61-90": 0, "90+": 0}
        total_outstanding = 0
        
        for invoice in invoices[:20]:  # Limit for performance
            status = invoice.get('status', {}).get('displayed_as', '')
            if 'paid' not in status.lower():  # Only unpaid invoices
                due_date_str = invoice.get('due_date')
                total_amount = float(invoice.get('total_amount', 0))
                
                if due_date_str:
                    try:
                        due_date = datetime.strptime(due_date_str[:10], '%Y-%m-%d')
                        days_overdue = (today - due_date).days
                        
                        if days_overdue <= 30:
                            aging_buckets["0-30"] += total_amount
                        elif days_overdue <= 60:
                            aging_buckets["31-60"] += total_amount
                        elif days_overdue <= 90:
                            aging_buckets["61-90"] += total_amount
                        else:
                            aging_buckets["90+"] += total_amount
                        
                        total_outstanding += total_amount
                    except:
                        aging_buckets["0-30"] += total_amount  # Default bucket
                        total_outstanding += total_amount
        
        result = f"Total créances impayées: {total_outstanding:.2f}€\n"
        result += f"• 0-30 jours: {aging_buckets['0-30']:.2f}€\n"
        result += f"• 31-60 jours: {aging_buckets['31-60']:.2f}€\n"
        result += f"• 61-90 jours: {aging_buckets['61-90']:.2f}€\n"
        result += f"• 90+ jours: {aging_buckets['90+']:.2f}€ (CRITIQUE)"
        
        return result
    
    def _analyze_payables_aging(self, purchase_result: dict, payments_result: dict) -> str:
        """Analyze payables aging from purchase invoices and payments data"""
        invoices = purchase_result.get('$items', [])
        
        if not invoices:
            return "Aucune facture fournisseur trouvée pour l'analyse."
        
        # Similar analysis for payables
        from datetime import datetime
        today = datetime.now()
        aging_buckets = {"0-30": 0, "31-60": 0, "61-90": 0, "90+": 0}
        total_outstanding = 0
        
        for invoice in invoices[:20]:  # Limit for performance
            status = invoice.get('status', {}).get('displayed_as', '')
            if 'paid' not in status.lower():
                due_date_str = invoice.get('due_date')
                total_amount = float(invoice.get('total_amount', 0))
                
                if due_date_str:
                    try:
                        due_date = datetime.strptime(due_date_str[:10], '%Y-%m-%d')
                        days_overdue = (today - due_date).days
                        
                        if days_overdue <= 30:
                            aging_buckets["0-30"] += total_amount
                        elif days_overdue <= 60:
                            aging_buckets["31-60"] += total_amount
                        elif days_overdue <= 90:
                            aging_buckets["61-90"] += total_amount
                        else:
                            aging_buckets["90+"] += total_amount
                        
                        total_outstanding += total_amount
                    except:
                        aging_buckets["0-30"] += total_amount
                        total_outstanding += total_amount
        
        result = f"Total dettes impayées: {total_outstanding:.2f}€\n"
        result += f"• 0-30 jours: {aging_buckets['0-30']:.2f}€\n"
        result += f"• 31-60 jours: {aging_buckets['31-60']:.2f}€\n"
        result += f"• 61-90 jours: {aging_buckets['61-90']:.2f}€\n"
        result += f"• 90+ jours: {aging_buckets['90+']:.2f}€ (URGENT)"
        
        return result

class GetCreditNotesInput(BaseModel):
    """Input schema for getting credit notes"""
    credit_note_type: Optional[str] = Field("sales", description="Type: sales or purchase")
    limit: Optional[int] = Field(20, description="Number of credit notes to retrieve")
    contact_id: Optional[str] = Field(None, description="Filter by contact ID")
    status_id: Optional[str] = Field(None, description="Filter by status ID")
    from_date: Optional[str] = Field(None, description="Filter from date (YYYY-MM-DD)")
    to_date: Optional[str] = Field(None, description="Filter to date (YYYY-MM-DD)")
    search: Optional[str] = Field(None, description="Search by reference or contact name")
    business_id: Optional[str] = Field(None, description="Sage business ID")

class GetCreditNotesTool(SageBaseTool):
    name: str = "get_credit_notes"
    description: str = "Récupère les avoirs clients/fournisseurs pour gestion experte des retours et remboursements"
    args_schema: Type[BaseModel] = GetCreditNotesInput

    def _run(self, credit_note_type: Optional[str] = "sales", limit: Optional[int] = 20,
             contact_id: Optional[str] = None, status_id: Optional[str] = None,
             from_date: Optional[str] = None, to_date: Optional[str] = None,
             search: Optional[str] = None, business_id: Optional[str] = None) -> str:
        try:
            credentials = self.get_credentials()
            if not credentials:
                return "❌ Erreur: Aucune connexion Sage détectée. Veuillez vous connecter à Sage d'abord."
            
            if credit_note_type == "sales":
                result = sage_api.get_sales_credit_notes(
                    credentials, business_id, limit, 0, contact_id,
                    status_id, from_date, to_date, search
                )
                type_label = "clients"
            elif credit_note_type == "purchase":
                result = sage_api.get_purchase_credit_notes(
                    credentials, business_id, limit, 0, contact_id,
                    status_id, from_date, to_date, search
                )
                type_label = "fournisseurs"
            else:
                return "❌ Type invalide. Utilisez 'sales' ou 'purchase'."
            
            credit_notes = result.get('$items', [])
            if not credit_notes:
                return f"ℹ️ Aucun avoir {type_label} trouvé avec ces critères."
            
            credit_note_list = []
            for credit_note in credit_notes:
                # Extract key information for expert credit management
                contact = credit_note.get('contact', {}).get('displayed_as', 'N/A')
                ref = credit_note.get('reference', credit_note.get('displayed_as', 'N/A'))
                total = credit_note.get('total_amount', 'N/A')
                status = credit_note.get('status', {}).get('displayed_as', 'N/A')
                date = credit_note.get('date', 'N/A')
                original_invoice = credit_note.get('original_invoice_reference', 'N/A')
                
                credit_note_info = f"- {ref} | {contact} | {total}€ | {status} | {date} | Fact.orig: {original_invoice}"
                credit_note_list.append(credit_note_info)
            
            return f"✅ Avoirs {type_label} ({len(credit_notes)} trouvés):\n" + "\n".join(credit_note_list)
            
        except Exception as e:
            return f"❌ Erreur lors de la récupération des avoirs: {str(e)}"

class GetJournalEntriesInput(BaseModel):
    """Input schema for getting journal entries"""
    limit: Optional[int] = Field(20, description="Nombre d'écritures à récupérer (max 100)")
    from_date: Optional[str] = Field(None, description="Date de début (YYYY-MM-DD)")
    to_date: Optional[str] = Field(None, description="Date de fin (YYYY-MM-DD)")
    journal_code_id: Optional[str] = Field(None, description="ID du code journal spécifique")
    contact_id: Optional[str] = Field(None, description="ID du contact")
    search: Optional[str] = Field(None, description="Terme de recherche")
    business_id: Optional[str] = Field(None, description="Sage business ID")

class GetJournalEntriesTool(SageBaseTool):
    name: str = "get_journal_entries"
    description: str = "Récupère les écritures comptables pour audit et analyse experte des mouvements financiers"
    args_schema: Type[BaseModel] = GetJournalEntriesInput

    def _run(self, limit: Optional[int] = 20, from_date: Optional[str] = None,
             to_date: Optional[str] = None, journal_code_id: Optional[str] = None,
             contact_id: Optional[str] = None, search: Optional[str] = None,
             business_id: Optional[str] = None) -> str:
        try:
            credentials = self.get_credentials()
            if not credentials:
                return "❌ Erreur: Aucune connexion Sage détectée. Veuillez vous connecter à Sage d'abord."
            
            # Get journal entries
            result = sage_api.get_journal_entries(
                credentials, business_id, limit, 0, from_date, to_date,
                journal_code_id, contact_id, search
            )
            
            entries = result.get('$items', [])
            if not entries:
                return "ℹ️ Aucune écriture comptable trouvée avec ces critères."
            
            # Get journal codes for reference
            try:
                codes_result = sage_api.get_journal_codes(credentials, business_id, 50)
                journal_codes = {code.get('id'): code.get('displayed_as', 'N/A') 
                               for code in codes_result.get('$items', [])}
            except:
                journal_codes = {}
            
            # Format entries for expert analysis
            entry_list = []
            total_debit = 0
            total_credit = 0
            
            for entry in entries[:limit]:
                # Extract key journal entry data
                ref = entry.get('reference', entry.get('displayed_as', 'N/A'))
                date = entry.get('date', 'N/A')
                journal_code = journal_codes.get(entry.get('journal_code', {}).get('id'), 
                                                entry.get('journal_code', {}).get('displayed_as', 'N/A'))
                description = entry.get('description', entry.get('narrative', 'N/A'))
                
                # Calculate totals from journal lines
                lines = entry.get('journal_lines', [])
                entry_debit = sum(float(line.get('debit', 0)) for line in lines)
                entry_credit = sum(float(line.get('credit', 0)) for line in lines)
                
                total_debit += entry_debit  
                total_credit += entry_credit
                
                # Format entry info with accounting details
                entry_info = f"- {ref} | {date} | {journal_code} | Débit: {entry_debit}€ | Crédit: {entry_credit}€ | {description[:50]}..."
                entry_list.append(entry_info)
            
            # Add summary for expert analysis
            balance_check = "✅ Équilibré" if abs(total_debit - total_credit) < 0.01 else f"⚠️ Déséquilibré ({total_debit - total_credit}€)"
            summary = f"\n\n📊 RÉSUMÉ COMPTABLE:\nTotal Débit: {total_debit}€\nTotal Crédit: {total_credit}€\nStatut: {balance_check}"
            
            return f"✅ Écritures comptables ({len(entries)} trouvées):\n" + "\n".join(entry_list) + summary
            
        except Exception as e:
            return f"❌ Erreur lors de la récupération des écritures: {str(e)}"

class GetBalanceSheetInput(BaseModel):
    """Input schema for getting balance sheet"""
    from_date: Optional[str] = Field(None, description="Start date (YYYY-MM-DD)")
    to_date: Optional[str] = Field(None, description="End date (YYYY-MM-DD)")
    business_id: Optional[str] = Field(None, description="Sage business ID")

class GetBalanceSheetTool(SageBaseTool):
    name: str = "get_balance_sheet"
    description: str = "Récupère le bilan comptable depuis Sage Business Cloud Accounting"
    args_schema: Type[BaseModel] = GetBalanceSheetInput

    def _run(self, from_date: Optional[str] = None,
             to_date: Optional[str] = None, business_id: Optional[str] = None) -> str:
        try:
            # Utiliser les credentials automatiquement
            credentials = self.get_credentials()
            if not credentials:
                return "❌ Erreur: Aucune connexion Sage détectée. Veuillez vous connecter à Sage d'abord."
            
            result = sage_api.get_balance_sheet(credentials, business_id, from_date, to_date)
            
            # Extraire les informations principales du bilan
            if isinstance(result, dict):
                summary = "Bilan comptable:\n"
                
                # Actifs
                if 'assets' in result:
                    summary += "ACTIFS:\n"
                    for asset in result['assets']:
                        summary += f"- {asset.get('name', 'N/A')}: {asset.get('value', 'N/A')}€\n"
                
                # Passifs
                if 'liabilities' in result:
                    summary += "\nPASSIFS:\n"
                    for liability in result['liabilities']:
                        summary += f"- {liability.get('name', 'N/A')}: {liability.get('value', 'N/A')}€\n"
                
                return summary if summary != "Bilan comptable:\n" else f"Bilan comptable récupéré: {json.dumps(result, indent=2)}"
            
            return f"Bilan comptable récupéré: {str(result)}"
            
        except Exception as e:
            return f"Erreur lors de la récupération du bilan: {str(e)}"

class GetProfitLossInput(BaseModel):
    """Input schema for getting profit and loss"""
    from_date: Optional[str] = Field(None, description="Start date (YYYY-MM-DD)")
    to_date: Optional[str] = Field(None, description="End date (YYYY-MM-DD)")
    business_id: Optional[str] = Field(None, description="Sage business ID")

class GetProfitLossTool(SageBaseTool):
    name: str = "get_profit_loss"
    description: str = "Récupère le compte de résultat depuis Sage Business Cloud Accounting"
    args_schema: Type[BaseModel] = GetProfitLossInput

    def _run(self, from_date: Optional[str] = None,
             to_date: Optional[str] = None, business_id: Optional[str] = None) -> str:
        try:
            # Utiliser les credentials automatiquement
            credentials = self.get_credentials()
            if not credentials:
                return "❌ Erreur: Aucune connexion Sage détectée. Veuillez vous connecter à Sage d'abord."
            
            result = sage_api.get_profit_loss(credentials, business_id, from_date, to_date)
            
            # Extraire les informations principales du compte de résultat
            if isinstance(result, dict):
                summary = "Compte de résultat:\n"
                
                # Revenus
                if 'income' in result:
                    summary += "REVENUS:\n"
                    for income in result['income']:
                        summary += f"- {income.get('name', 'N/A')}: {income.get('value', 'N/A')}€\n"
                
                # Charges
                if 'expenses' in result:
                    summary += "\nCHARGES:\n"
                    for expense in result['expenses']:
                        summary += f"- {expense.get('name', 'N/A')}: {expense.get('value', 'N/A')}€\n"
                
                # Résultat net
                if 'net_profit' in result:
                    summary += f"\nRÉSULTAT NET: {result['net_profit']}€\n"
                
                return summary if summary != "Compte de résultat:\n" else f"Compte de résultat récupéré: {json.dumps(result, indent=2)}"
            
            return f"Compte de résultat récupéré: {str(result)}"
            
        except Exception as e:
            return f"Erreur lors de la récupération du compte de résultat: {str(e)}"

class SearchTransactionsInput(BaseModel):
    """Input schema for searching transactions"""
    from_date: Optional[str] = Field(None, description="Start date (YYYY-MM-DD)")
    to_date: Optional[str] = Field(None, description="End date (YYYY-MM-DD)")
    min_amount: Optional[float] = Field(None, description="Minimum amount")
    max_amount: Optional[float] = Field(None, description="Maximum amount")
    limit: Optional[int] = Field(20, description="Number of transactions to retrieve")
    business_id: Optional[str] = Field(None, description="Sage business ID")

class SearchTransactionsTool(SageBaseTool):
    name: str = "search_transactions"
    description: str = "Recherche des transactions dans Sage Business Cloud Accounting"
    args_schema: Type[BaseModel] = SearchTransactionsInput

    def _run(self, from_date: Optional[str] = None,
             to_date: Optional[str] = None, min_amount: Optional[float] = None,
             max_amount: Optional[float] = None, limit: Optional[int] = 20,
             business_id: Optional[str] = None) -> str:
        try:
            # Utiliser les credentials automatiquement
            credentials = self.get_credentials()
            if not credentials:
                return "❌ Erreur: Aucune connexion Sage détectée. Veuillez vous connecter à Sage d'abord."
            
            search_criteria = {
                'from_date': from_date,
                'to_date': to_date,
                'min_amount': min_amount,
                'max_amount': max_amount,
                'limit': limit
            }
            
            result = sage_api.search_transactions(credentials, search_criteria, business_id)
            
            transactions = result.get('$items', [])
            if not transactions:
                return "Aucune transaction trouvée avec ces critères."
            
            transaction_list = []
            for transaction in transactions:
                transaction_info = f"- {transaction.get('date', 'N/A')} - {transaction.get('displayed_as', 'N/A')} - {transaction.get('total_amount', 'N/A')}€"
                transaction_list.append(transaction_info)
            
            return f"Transactions trouvées ({len(transactions)}):\n" + "\n".join(transaction_list)
            
        except Exception as e:
            return f"Erreur lors de la recherche de transactions: {str(e)}"

class CreateSupplierInput(BaseModel):
    """Input schema for creating a supplier"""
    name: str = Field(..., description="Supplier name")
    email: str = Field(..., description="Supplier email address")
    phone: Optional[str] = Field(None, description="Supplier phone number")
    address_line_1: Optional[str] = Field(None, description="Supplier address line 1")
    city: Optional[str] = Field(None, description="Supplier city")
    postal_code: Optional[str] = Field(None, description="Supplier postal code")
    business_id: Optional[str] = Field(None, description="Sage business ID")

class CreateSupplierTool(SageBaseTool):
    name: str = "create_supplier"
    description: str = "Crée un nouveau fournisseur dans Sage Business Cloud Accounting"
    args_schema: Type[BaseModel] = CreateSupplierInput

    def _run(self, name: str, email: str, 
             phone: Optional[str] = None, address_line_1: Optional[str] = None,
             city: Optional[str] = None, postal_code: Optional[str] = None,
             business_id: Optional[str] = None) -> str:
        try:
            # Utiliser les credentials automatiquement
            credentials = self.get_credentials()
            if not credentials:
                return "❌ Erreur: Aucune connexion Sage détectée. Veuillez vous connecter à Sage d'abord."
            
            supplier_data = {
                'name': name,
                'email': email,
                'phone': phone or '',
                'address_line_1': address_line_1 or '',
                'city': city or '',
                'postal_code': postal_code or ''
            }
            
            result = sage_api.create_supplier(credentials, supplier_data, business_id)
            
            return f"✅ Fournisseur créé avec succès: {result.get('name', name)} (ID: {result.get('id', 'N/A')})"
            
        except Exception as e:
            return f"❌ Erreur lors de la création du fournisseur: {str(e)}"

class GetSuppliersInput(BaseModel):
    """Input schema for getting suppliers"""
    limit: Optional[int] = Field(20, description="Number of suppliers to retrieve")
    business_id: Optional[str] = Field(None, description="Sage business ID")

class GetSuppliersTool(SageBaseTool):
    name: str = "get_suppliers"
    description: str = "Récupère la liste des fournisseurs depuis Sage Business Cloud Accounting"
    args_schema: Type[BaseModel] = GetSuppliersInput

    def _run(self, limit: Optional[int] = 20, 
             business_id: Optional[str] = None) -> str:
        try:
            # Utiliser les credentials automatiquement
            credentials = self.get_credentials()
            if not credentials:
                return "❌ Erreur: Aucune connexion Sage détectée. Veuillez vous connecter à Sage d'abord."
            
            result = sage_api.get_suppliers(credentials, business_id, limit, 0)
            
            suppliers = result.get('$items', [])
            if not suppliers:
                return "ℹ️ Aucun fournisseur trouvé dans votre compte Sage."
            
            supplier_list = []
            for supplier in suppliers:
                supplier_info = f"- {supplier.get('name', 'N/A')} (ID: {supplier.get('id', 'N/A')}, Email: {supplier.get('email', 'N/A')})"
                supplier_list.append(supplier_info)
            
            return f"✅ Liste des fournisseurs ({len(suppliers)} trouvés):\n" + "\n".join(supplier_list)
            
        except Exception as e:
            return f"❌ Erreur lors de la récupération des fournisseurs: {str(e)}"

class CreateProductInput(BaseModel):
    """Input schema for creating a product"""
    code: str = Field(..., description="Product code")
    description: str = Field(..., description="Product description")
    price: float = Field(..., description="Sales price")
    cost_price: Optional[float] = Field(None, description="Cost price")
    supplier_id: Optional[str] = Field(None, description="Usual supplier ID")
    business_id: Optional[str] = Field(None, description="Sage business ID")

class CreateProductTool(SageBaseTool):
    name: str = "create_product"
    description: str = "Crée un nouveau produit/service dans Sage Business Cloud Accounting"
    args_schema: Type[BaseModel] = CreateProductInput

    def _run(self, code: str, description: str, price: float,
             cost_price: Optional[float] = None, supplier_id: Optional[str] = None,
             business_id: Optional[str] = None) -> str:
        try:
            # Utiliser les credentials automatiquement
            credentials = self.get_credentials()
            if not credentials:
                return "❌ Erreur: Aucune connexion Sage détectée. Veuillez vous connecter à Sage d'abord."
            
            product_data = {
                'code': code,
                'description': description,
                'price': price,
                'cost_price': cost_price or 0,
                'supplier_id': supplier_id
            }
            
            result = sage_api.create_product(credentials, product_data, business_id)
            
            return f"✅ Produit créé avec succès: {result.get('description', description)} (Code: {result.get('item_code', code)})"
            
        except Exception as e:
            return f"❌ Erreur lors de la création du produit: {str(e)}"

class GetProductsInput(BaseModel):
    """Input schema for getting products"""
    limit: Optional[int] = Field(20, description="Number of products to retrieve")
    business_id: Optional[str] = Field(None, description="Sage business ID")

class GetProductsTool(SageBaseTool):
    name: str = "get_products"
    description: str = "Récupère la liste des produits/services depuis Sage Business Cloud Accounting"
    args_schema: Type[BaseModel] = GetProductsInput

    def _run(self, limit: Optional[int] = 20, 
             business_id: Optional[str] = None) -> str:
        try:
            # Utiliser les credentials automatiquement
            credentials = self.get_credentials()
            if not credentials:
                return "❌ Erreur: Aucune connexion Sage détectée. Veuillez vous connecter à Sage d'abord."
            
            result = sage_api.get_products(credentials, business_id, limit, 0)
            
            products = result.get('$items', [])
            if not products:
                return "ℹ️ Aucun produit trouvé dans votre compte Sage."
            
            product_list = []
            for product in products:
                product_info = f"- {product.get('description', 'N/A')} (Code: {product.get('item_code', 'N/A')}, Prix: {product.get('sales_price', 'N/A')}€)"
                product_list.append(product_info)
            
            return f"✅ Liste des produits ({len(products)} trouvés):\n" + "\n".join(product_list)
            
        except Exception as e:
            return f"❌ Erreur lors de la récupération des produits: {str(e)}"

class GetBankAccountsInput(BaseModel):
    """Input schema for getting bank accounts"""
    business_id: Optional[str] = Field(None, description="Sage business ID")

class GetBankAccountsTool(SageBaseTool):
    name: str = "get_bank_accounts"
    description: str = "Récupère la liste des comptes bancaires depuis Sage Business Cloud Accounting"
    args_schema: Type[BaseModel] = GetBankAccountsInput

    def _run(self, business_id: Optional[str] = None) -> str:
        try:
            # Utiliser les credentials automatiquement
            credentials = self.get_credentials()
            if not credentials:
                return "❌ Erreur: Aucune connexion Sage détectée. Veuillez vous connecter à Sage d'abord."
            
            result = sage_api.get_bank_accounts(credentials, business_id)
            
            accounts = result.get('$items', [])
            if not accounts:
                return "ℹ️ Aucun compte bancaire trouvé dans votre compte Sage."
            
            account_list = []
            for account in accounts:
                account_info = f"- {account.get('name', 'N/A')} - {account.get('bank_account_details', {}).get('iban', 'N/A')} (Solde: {account.get('balance', 'N/A')}€)"
                account_list.append(account_info)
            
            return f"✅ Comptes bancaires ({len(accounts)} trouvés):\n" + "\n".join(account_list)
            
        except Exception as e:
            return f"❌ Erreur lors de la récupération des comptes bancaires: {str(e)}"

class SageToolkit:
    """Toolkit pour gérer les outils Sage Business Cloud Accounting"""
    
    def __init__(self, sage_base_url=None, access_token=None, client_id=None):
        """Initialize the SageToolkit with optional credentials"""
        self.sage_base_url = sage_base_url
        self.access_token = access_token
        self.client_id = client_id
        
        # Set global credentials if provided
        if access_token and client_id:
            set_user_credentials({
                'access_token': access_token,
                'client_id': client_id,
                'base_url': sage_base_url or 'https://api.accounting.sage.com/v3.1'
            })
    
    def get_tools(self):
        """Retourne la liste des outils Sage disponibles"""
        return SAGE_TOOLS

# Liste de tous les outils Sage disponibles
try:
    SAGE_TOOLS = [
        CreateCustomerTool(),
        GetCustomersTool(),
        CreateSupplierTool(),
        GetSuppliersTool(),
        CreateInvoiceTool(),
        GetInvoicesTool(),
        GetPurchaseInvoicesTool(),
        GetPaymentsTool(),
        GetTaxReturnsTool(),
        GetAgingAnalysisTool(),
        GetCreditNotesTool(),
        GetJournalEntriesTool(),
        CreateProductTool(),
        GetProductsTool(),
        GetBankAccountsTool(),
        GetBalanceSheetTool(),
        GetProfitLossTool(),
        SearchTransactionsTool()
    ]
except Exception as e:
    print(f"Warning: Could not initialize Sage tools: {e}")
    SAGE_TOOLS = []  # Empty list if tools can't be initialized

