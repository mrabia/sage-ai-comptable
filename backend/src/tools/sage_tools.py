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
from typing import Type, Dict, Any, Optional, List
from pydantic import BaseModel, Field
from services.sage_auth import SageOAuth2Service
from services.sage_api import SageAPIService
import json
import os
import time

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

class GetLedgerAccountsInput(BaseModel):
    """Input schema for getting ledger accounts"""
    limit: Optional[int] = Field(50, description="Nombre de comptes à récupérer (max 100)")
    account_type_id: Optional[str] = Field(None, description="ID du type de compte (assets, liabilities, equity, income, expenses)")
    search: Optional[str] = Field(None, description="Terme de recherche pour filtrer les comptes")
    show_balance: Optional[bool] = Field(True, description="Inclure les soldes des comptes")
    business_id: Optional[str] = Field(None, description="Sage business ID")

class GetLedgerAccountsTool(SageBaseTool):
    name: str = "get_ledger_accounts"
    description: str = "Récupère le plan comptable complet pour analyse experte de la structure financière"
    args_schema: Type[BaseModel] = GetLedgerAccountsInput

    def _run(self, limit: Optional[int] = 50, account_type_id: Optional[str] = None,
             search: Optional[str] = None, show_balance: Optional[bool] = True,
             business_id: Optional[str] = None) -> str:
        try:
            credentials = self.get_credentials()
            if not credentials:
                return "❌ Erreur: Aucune connexion Sage détectée. Veuillez vous connecter à Sage d'abord."
            
            # Get ledger accounts
            result = sage_api.get_ledger_accounts(
                credentials, business_id, limit, 0, account_type_id, search, show_balance
            )
            
            accounts = result.get('$items', [])
            if not accounts:
                return "ℹ️ Aucun compte trouvé avec ces critères."
            
            # Get account types for reference  
            try:
                types_result = sage_api.get_account_types(credentials, business_id, 50)
                account_types = {type_item.get('id'): type_item.get('displayed_as', 'N/A')
                               for type_item in types_result.get('$items', [])}
            except:
                account_types = {}
            
            # Group accounts by type for expert analysis
            accounts_by_type = {}
            total_assets = 0
            total_liabilities = 0
            total_equity = 0
            total_income = 0
            total_expenses = 0
            
            for account in accounts[:limit]:
                # Extract key account information
                code = account.get('ledger_account_code', account.get('nominal_code', 'N/A'))
                name = account.get('displayed_as', account.get('name', 'N/A'))
                account_type = account.get('account_type', {})
                type_name = account_types.get(account_type.get('id'), 
                                            account_type.get('displayed_as', 'N/A'))
                
                # Get balance if available
                balance = 0
                balance_info = ""
                if show_balance and 'balance' in account:
                    balance = float(account.get('balance', 0))
                    balance_info = f" | Solde: {balance}€"
                    
                    # Aggregate balances by type for financial analysis
                    type_id = account_type.get('id', '')
                    if 'asset' in type_id.lower():
                        total_assets += balance
                    elif 'liability' in type_id.lower():
                        total_liabilities += balance
                    elif 'equity' in type_id.lower():
                        total_equity += balance
                    elif 'income' in type_id.lower():
                        total_income += balance
                    elif 'expense' in type_id.lower():
                        total_expenses += balance
                
                # Group by account type
                if type_name not in accounts_by_type:
                    accounts_by_type[type_name] = []
                
                account_info = f"  - {code} | {name}{balance_info}"
                accounts_by_type[type_name].append(account_info)
            
            # Format response with expert financial structure analysis
            response_parts = [f"✅ Plan comptable ({len(accounts)} comptes):"]
            
            for type_name, type_accounts in accounts_by_type.items():
                response_parts.append(f"\n📂 {type_name}:")
                response_parts.extend(type_accounts)
            
            # Add financial summary for expert analysis if balances included
            if show_balance and any([total_assets, total_liabilities, total_equity, total_income, total_expenses]):
                response_parts.append(f"\n\n📊 RÉSUMÉ FINANCIER:")
                if total_assets: response_parts.append(f"Actifs: {total_assets}€")
                if total_liabilities: response_parts.append(f"Passifs: {total_liabilities}€")  
                if total_equity: response_parts.append(f"Capitaux propres: {total_equity}€")
                if total_income: response_parts.append(f"Produits: {total_income}€")
                if total_expenses: response_parts.append(f"Charges: {total_expenses}€")
                
                # Basic accounting equation check
                equity_balance = total_assets - total_liabilities
                equation_check = "✅ Équation respectée" if abs(equity_balance - total_equity) < 1 else f"⚠️ Écart: {equity_balance - total_equity}€"
                response_parts.append(f"Équation comptable: {equation_check}")
            
            return "\n".join(response_parts)
            
        except Exception as e:
            return f"❌ Erreur lors de la récupération du plan comptable: {str(e)}"

class GetBankReconciliationInput(BaseModel):
    """Input schema for getting bank reconciliation"""
    limit: Optional[int] = Field(20, description="Nombre de rapprochements à récupérer")
    bank_account_id: Optional[str] = Field(None, description="ID du compte bancaire spécifique")
    from_date: Optional[str] = Field(None, description="Date de début (YYYY-MM-DD)")
    to_date: Optional[str] = Field(None, description="Date de fin (YYYY-MM-DD)")
    status: Optional[str] = Field(None, description="Statut du rapprochement (reconciled/unreconciled)")
    show_transactions: Optional[bool] = Field(True, description="Inclure l'analyse des transactions non rapprochées")
    business_id: Optional[str] = Field(None, description="Sage business ID")

class GetBankReconciliationTool(SageBaseTool):
    name: str = "get_bank_reconciliation"
    description: str = "Analyse experte des rapprochements bancaires et gestion de trésorerie"
    args_schema: Type[BaseModel] = GetBankReconciliationInput

    def _run(self, limit: Optional[int] = 20, bank_account_id: Optional[str] = None,
             from_date: Optional[str] = None, to_date: Optional[str] = None,
             status: Optional[str] = None, show_transactions: Optional[bool] = True,
             business_id: Optional[str] = None) -> str:
        try:
            credentials = self.get_credentials()
            if not credentials:
                return "❌ Erreur: Aucune connexion Sage détectée. Veuillez vous connecter à Sage d'abord."
            
            # Get bank reconciliations
            recon_result = sage_api.get_bank_reconciliations(
                credentials, business_id, limit, 0, bank_account_id,
                from_date, to_date, status
            )
            
            reconciliations = recon_result.get('$items', [])
            
            # Get bank accounts for reference
            try:
                accounts_result = sage_api.get_bank_accounts(credentials, business_id)
                bank_accounts = {acc.get('id'): acc.get('displayed_as', 'N/A')
                               for acc in accounts_result.get('$items', [])}
            except:
                bank_accounts = {}
            
            response_parts = []
            
            if reconciliations:
                response_parts.append(f"✅ Rapprochements bancaires ({len(reconciliations)} trouvés):")
                
                for recon in reconciliations:
                    account_name = bank_accounts.get(recon.get('bank_account', {}).get('id'), 'N/A')
                    ref = recon.get('reference', recon.get('displayed_as', 'N/A'))
                    date = recon.get('statement_date', 'N/A')
                    status_info = recon.get('status', {}).get('displayed_as', 'N/A')
                    balance = recon.get('statement_balance', 'N/A')
                    
                    recon_info = f"- {ref} | {account_name} | {date} | {status_info} | Solde: {balance}€"
                    response_parts.append(recon_info)
            else:
                response_parts.append("ℹ️ Aucun rapprochement bancaire trouvé avec ces critères.")
            
            # Analyze unreconciled transactions if requested
            if show_transactions:
                try:
                    trans_result = sage_api.get_bank_transactions(
                        credentials, business_id, 50, 0, bank_account_id,
                        from_date, to_date, "false"  # Only unreconciled
                    )
                    
                    unreconciled_transactions = trans_result.get('$items', [])
                    
                    if unreconciled_transactions:
                        response_parts.append(f"\n⚠️ Transactions non rapprochées ({len(unreconciled_transactions)} trouvées):")
                        
                        total_unreconciled = 0
                        debit_total = 0
                        credit_total = 0
                        
                        for i, trans in enumerate(unreconciled_transactions[:20]):  # Limit for performance
                            account_name = bank_accounts.get(trans.get('bank_account', {}).get('id'), 'N/A')
                            date = trans.get('date', 'N/A')
                            amount = float(trans.get('amount', 0))
                            description = trans.get('description', trans.get('narrative', 'N/A'))[:40]
                            
                            if amount > 0:
                                credit_total += amount
                                amount_sign = "+"
                            else:
                                debit_total += abs(amount)
                                amount_sign = "-"
                            
                            total_unreconciled += amount
                            
                            trans_info = f"  - {date} | {account_name} | {amount_sign}{abs(amount)}€ | {description}..."
                            response_parts.append(trans_info)
                        
                        # Summary for expert cash flow analysis
                        response_parts.append(f"\n📊 ANALYSE TRÉSORERIE:")
                        response_parts.append(f"Total non rapproché: {total_unreconciled}€")
                        response_parts.append(f"Entrées: +{credit_total}€")
                        response_parts.append(f"Sorties: -{debit_total}€")
                        
                        # Cash flow insights
                        if total_unreconciled > 1000:
                            response_parts.append("🔴 Impact trésorerie élevé - Rapprochement prioritaire")
                        elif total_unreconciled > 100:
                            response_parts.append("🟡 Impact trésorerie modéré - Surveiller")
                        else:
                            response_parts.append("🟢 Impact trésorerie faible")
                            
                    else:
                        response_parts.append("\n✅ Toutes les transactions sont rapprochées")
                        
                except Exception as e:
                    response_parts.append(f"\n⚠️ Impossible d'analyser les transactions: {str(e)}")
            
            return "\n".join(response_parts)
            
        except Exception as e:
            return f"❌ Erreur lors de l'analyse des rapprochements bancaires: {str(e)}"

class CreatePurchaseInvoiceInput(BaseModel):
    """Input schema for creating a purchase invoice"""
    contact_id: str = Field(..., description="ID du fournisseur")
    reference: Optional[str] = Field(None, description="Référence de la facture")
    vendor_reference: Optional[str] = Field(None, description="Référence du fournisseur")
    date: str = Field(..., description="Date de la facture (YYYY-MM-DD)")
    due_date: Optional[str] = Field(None, description="Date d'échéance (YYYY-MM-DD)")
    items: List[Dict] = Field(..., description="Liste des lignes de facture [{'description': str, 'quantity': float, 'unit_price': float, 'ledger_account_id': str, 'tax_rate_id': str}]")
    notes: Optional[str] = Field(None, description="Notes sur la facture")
    currency_id: Optional[str] = Field("GBP", description="ID de la devise")
    business_id: Optional[str] = Field(None, description="Sage business ID")

class CreatePurchaseInvoiceTool(SageBaseTool):
    name: str = "create_purchase_invoice"
    description: str = "Crée une nouvelle facture fournisseur pour compléter le cycle Purchase-to-Pay"
    args_schema: Type[BaseModel] = CreatePurchaseInvoiceInput

    def _run(self, contact_id: str, date: str, items: List[Dict],
             reference: Optional[str] = None, vendor_reference: Optional[str] = None,
             due_date: Optional[str] = None, notes: Optional[str] = None,
             currency_id: Optional[str] = "GBP", business_id: Optional[str] = None) -> str:
        try:
            credentials = self.get_credentials()
            if not credentials:
                return "❌ Erreur: Aucune connexion Sage détectée. Veuillez vous connecter à Sage d'abord."
            
            # Validation des données d'entrée
            if not items or len(items) == 0:
                return "❌ Erreur: Au moins une ligne de facture est requise."
            
            # Validation des lignes de facture
            for i, item in enumerate(items):
                if not item.get('description'):
                    return f"❌ Erreur ligne {i+1}: Description requise."
                if not item.get('unit_price') and not item.get('net_amount'):
                    return f"❌ Erreur ligne {i+1}: Prix unitaire ou montant net requis."
                if not item.get('ledger_account_id'):
                    return f"❌ Erreur ligne {i+1}: Compte comptable requis."
            
            # Préparer les données de la facture
            invoice_data = {
                'contact_id': contact_id,
                'reference': reference or f'PINV-{int(time.time())}',
                'vendor_reference': vendor_reference,
                'date': date,
                'due_date': due_date or date,
                'currency_id': currency_id,
                'notes': notes,
                'items': items
            }
            
            result = sage_api.create_purchase_invoice(credentials, invoice_data, business_id)
            
            if 'error' in result or 'errors' in result:
                error_msg = result.get('error', result.get('errors', 'Erreur inconnue'))
                return f"❌ Erreur lors de la création: {error_msg}"
            
            # Extraction des informations de la facture créée
            invoice = result
            if 'purchase_invoice' in result:
                invoice = result['purchase_invoice']
            
            invoice_ref = invoice.get('reference', invoice.get('displayed_as', 'N/A'))
            invoice_id = invoice.get('id', 'N/A')
            total_amount = invoice.get('total_amount', 'N/A')
            
            # Résumé des lignes créées
            lines_summary = []
            if 'invoice_lines' in invoice:
                for line in invoice.get('invoice_lines', []):
                    desc = line.get('description', '')[:30]
                    amount = line.get('net_amount', line.get('total_amount', 'N/A'))
                    lines_summary.append(f"  - {desc}... : {amount}€")
            
            lines_text = "\n".join(lines_summary) if lines_summary else f"  - {len(items)} ligne(s) créée(s)"
            
            return f"""✅ Facture fournisseur créée avec succès!

📋 DÉTAILS:
ID: {invoice_id}
Référence: {invoice_ref}
Fournisseur: {contact_id}
Total: {total_amount}€

📝 LIGNES:
{lines_text}

🎯 Le cycle Purchase-to-Pay est maintenant complet avec cette nouvelle capacité de création!"""
            
        except Exception as e:
            return f"❌ Erreur lors de la création de la facture fournisseur: {str(e)}"

class GetFixedAssetsInput(BaseModel):
    """Input schema for getting fixed assets analysis"""
    limit: Optional[int] = Field(50, description="Nombre maximum d'actifs à analyser")
    from_date: Optional[str] = Field(None, description="Date de début pour analyser les mouvements (YYYY-MM-DD)")
    to_date: Optional[str] = Field(None, description="Date de fin pour analyser les mouvements (YYYY-MM-DD)")
    include_transactions: Optional[bool] = Field(True, description="Inclure l'analyse des mouvements sur la période")
    business_id: Optional[str] = Field(None, description="Sage business ID")

class GetFixedAssetsTool(SageBaseTool):
    name: str = "get_fixed_assets"
    description: str = "Analyse experte des immobilisations et suivi de la dépréciation"
    args_schema: Type[BaseModel] = GetFixedAssetsInput

    def _run(self, limit: Optional[int] = 50, from_date: Optional[str] = None,
             to_date: Optional[str] = None, include_transactions: Optional[bool] = True,
             business_id: Optional[str] = None) -> str:
        try:
            credentials = self.get_credentials()
            if not credentials:
                return "❌ Erreur: Aucune connexion Sage détectée. Veuillez vous connecter à Sage d'abord."
            
            # Obtenir l'analyse des immobilisations
            if include_transactions and (from_date or to_date):
                result = sage_api.get_fixed_assets_analysis(
                    credentials, business_id, limit, from_date, to_date
                )
            else:
                result = sage_api.get_fixed_assets_analysis(
                    credentials, business_id, limit
                )
            
            fixed_asset_accounts = result.get('fixed_asset_accounts', [])
            asset_transactions = result.get('asset_transactions', [])
            
            if not fixed_asset_accounts:
                return "ℹ️ Aucune immobilisation détectée dans le plan comptable."
            
            response_parts = [f"🏢 Analyse des immobilisations ({len(fixed_asset_accounts)} comptes détectés):"]
            
            # Analyse des comptes d'immobilisations
            total_gross_value = 0
            total_depreciation = 0
            total_net_value = 0
            
            assets_by_category = {}
            
            for account in fixed_asset_accounts:
                code = account.get('ledger_account_code', account.get('nominal_code', 'N/A'))
                name = account.get('displayed_as', account.get('name', 'N/A'))
                balance = float(account.get('balance', 0))
                account_type = account.get('account_type', {}).get('displayed_as', 'N/A')
                
                # Catégoriser les immobilisations
                category = "Autres immobilisations"
                if code.startswith('20') or 'incorporel' in name.lower():
                    category = "Immobilisations incorporelles"
                elif code.startswith('21') or any(word in name.lower() for word in ['terrain', 'land', 'foncier']):
                    category = "Terrains et constructions"
                elif code.startswith('22') or any(word in name.lower() for word in ['materiel', 'equipment', 'machinery', 'outillage']):
                    category = "Matériel et équipements"
                elif code.startswith('23') or any(word in name.lower() for word in ['immobilisation', 'progress', 'cours']):
                    category = "Immobilisations en cours"
                elif code.startswith('28') or any(word in name.lower() for word in ['amortissement', 'depreciation']):
                    category = "Amortissements"
                    total_depreciation += abs(balance)  # Les amortissements sont généralement négatifs
                else:
                    total_gross_value += balance
                
                if category not in assets_by_category:
                    assets_by_category[category] = []
                
                # Indicateur de dépréciation
                depreciation_info = ""
                if 'amortissement' in name.lower() or 'depreciation' in name.lower():
                    depreciation_info = " 📉"
                elif balance > 0:
                    total_gross_value += balance
                
                asset_info = f"  - {code} | {name} | {balance}€{depreciation_info}"
                assets_by_category[category].append(asset_info)
            
            # Afficher par catégorie
            for category, assets in assets_by_category.items():
                response_parts.append(f"\n📂 {category}:")
                response_parts.extend(assets)
            
            # Calcul de la valeur nette
            total_net_value = total_gross_value - total_depreciation
            
            # Résumé financier des immobilisations
            response_parts.append(f"\n\n💰 RÉSUMÉ PATRIMONIAL:")
            response_parts.append(f"Valeur brute: {total_gross_value:,.2f}€")
            if total_depreciation > 0:
                response_parts.append(f"Amortissements: -{total_depreciation:,.2f}€")
                response_parts.append(f"Valeur nette: {total_net_value:,.2f}€")
                depreciation_rate = (total_depreciation / (total_gross_value + total_depreciation)) * 100 if (total_gross_value + total_depreciation) > 0 else 0
                response_parts.append(f"Taux d'amortissement: {depreciation_rate:.1f}%")
            
            # Analyse des mouvements si demandée
            if include_transactions and asset_transactions:
                response_parts.append(f"\n\n📈 MOUVEMENTS D'IMMOBILISATIONS ({len(asset_transactions)} opérations):")
                
                acquisitions = []
                depreciations = []
                disposals = []
                
                for trans in asset_transactions[:20]:  # Limiter pour la performance
                    date = trans.get('entry_date', 'N/A')
                    account = f"{trans.get('account_code', 'N/A')} - {trans.get('account_name', 'N/A')}"
                    description = trans.get('description', '')[:40]
                    amount = trans.get('net_amount', 0)
                    
                    if amount > 0:
                        acquisitions.append(f"  + {date} | {account} | +{amount}€ | {description}...")
                    elif amount < 0:
                        if 'amortissement' in trans.get('account_name', '').lower():
                            depreciations.append(f"  📉 {date} | {account} | {amount}€ | {description}...")
                        else:
                            disposals.append(f"  - {date} | {account} | {amount}€ | {description}...")
                
                if acquisitions:
                    response_parts.append("\n🔵 Acquisitions:")
                    response_parts.extend(acquisitions[:5])
                
                if depreciations:
                    response_parts.append("\n📉 Amortissements:")
                    response_parts.extend(depreciations[:5])
                
                if disposals:
                    response_parts.append("\n🔴 Cessions/Sorties:")
                    response_parts.extend(disposals[:5])
                
                if len(asset_transactions) > 20:
                    response_parts.append(f"\n... et {len(asset_transactions) - 20} autres mouvements")
            
            # Conseils d'expert
            response_parts.append(f"\n\n🎯 ANALYSE EXPERTE:")
            if total_net_value > total_gross_value * 0.8:
                response_parts.append("✅ Actifs récents - Faible taux d'amortissement")
            elif total_net_value < total_gross_value * 0.3:
                response_parts.append("⚠️ Actifs anciens - Envisager le renouvellement")
            else:
                response_parts.append("🟡 Actifs d'âge moyen - Surveiller l'amortissement")
            
            return "\n".join(response_parts)
            
        except Exception as e:
            return f"❌ Erreur lors de l'analyse des immobilisations: {str(e)}"

class CreateJournalEntryInput(BaseModel):
    """Input schema for creating a manual journal entry"""
    entry_type: str = Field(..., description="Type d'écriture (other_payment pour les décaissements, other_receipt pour les encaissements)")
    date: str = Field(..., description="Date de l'écriture (YYYY-MM-DD)")
    total_amount: float = Field(..., description="Montant total de l'écriture")
    description: str = Field(..., description="Description de l'écriture")
    reference: Optional[str] = Field(None, description="Référence de l'écriture")
    transaction_type_id: Optional[str] = Field(None, description="ID du type de transaction")
    bank_account_id: Optional[str] = Field(None, description="ID du compte bancaire")
    contact_id: Optional[str] = Field(None, description="ID du contact (fournisseur/client)")
    tax_rate_id: Optional[str] = Field(None, description="ID du taux de TVA")
    net_amount: Optional[float] = Field(None, description="Montant HT si différent du total")
    business_id: Optional[str] = Field(None, description="Sage business ID")

class CreateJournalEntryTool(SageBaseTool):
    name: str = "create_journal_entry"
    description: str = "Crée une écriture comptable manuelle pour corrections, régularisations et ajustements"
    args_schema: Type[BaseModel] = CreateJournalEntryInput

    def _run(self, entry_type: str, date: str, total_amount: float, description: str,
             reference: Optional[str] = None, transaction_type_id: Optional[str] = None,
             bank_account_id: Optional[str] = None, contact_id: Optional[str] = None,
             tax_rate_id: Optional[str] = None, net_amount: Optional[float] = None,
             business_id: Optional[str] = None) -> str:
        try:
            credentials = self.get_credentials()
            if not credentials:
                return "❌ Erreur: Aucune connexion Sage détectée. Veuillez vous connecter à Sage d'abord."
            
            # Validation des données d'entrée
            if entry_type not in ['other_payment', 'other_receipt']:
                return "❌ Erreur: entry_type doit être 'other_payment' ou 'other_receipt'."
            
            if total_amount <= 0:
                return "❌ Erreur: Le montant doit être positif."
            
            # Auto-génération de la référence si non fournie
            if not reference:
                reference = f'{"PAY" if entry_type == "other_payment" else "REC"}-{int(time.time())}'
            
            # Récupérer les types de transactions disponibles si besoin
            if not transaction_type_id:
                try:
                    types_result = sage_api.get_transaction_types(credentials, business_id, 20)
                    transaction_types = types_result.get('$items', [])
                    
                    # Chercher un type approprié selon l'entry_type
                    for trans_type in transaction_types:
                        type_name = trans_type.get('displayed_as', '').lower()
                        if entry_type == 'other_payment' and ('payment' in type_name or 'expense' in type_name):
                            transaction_type_id = trans_type.get('id')
                            break
                        elif entry_type == 'other_receipt' and ('receipt' in type_name or 'income' in type_name):
                            transaction_type_id = trans_type.get('id')
                            break
                    
                    # Si pas trouvé, utiliser le premier disponible
                    if not transaction_type_id and transaction_types:
                        transaction_type_id = transaction_types[0].get('id')
                        
                except Exception:
                    # Si l'API transaction_types n'est pas disponible, continuer sans
                    pass
            
            # Récupérer les comptes bancaires si besoin
            if not bank_account_id:
                try:
                    banks_result = sage_api.get_bank_accounts(credentials, business_id)
                    bank_accounts = banks_result.get('$items', [])
                    if bank_accounts:
                        # Utiliser le premier compte bancaire trouvé
                        bank_account_id = bank_accounts[0].get('id')
                except Exception:
                    # Si impossible de récupérer les comptes bancaires, continuer sans
                    pass
            
            # Préparer les données de l'écriture
            journal_data = {
                'entry_type': entry_type,
                'date': date,
                'total_amount': total_amount,
                'description': description,
                'reference': reference,
                'transaction_type_id': transaction_type_id,
                'bank_account_id': bank_account_id,
                'contact_id': contact_id,
                'tax_rate_id': tax_rate_id,
                'net_amount': net_amount
            }
            
            result = sage_api.create_manual_journal_entry(credentials, journal_data, business_id)
            
            if 'error' in result:
                return f"❌ Erreur lors de la création: {result['error']}"
            
            # Extraction des informations de l'écriture créée
            entry = result
            if entry_type == 'other_payment' and 'other_payment' in result:
                entry = result['other_payment']
            elif entry_type == 'other_receipt' and 'other_receipt' in result:
                entry = result['other_receipt']
            
            entry_ref = entry.get('reference', entry.get('displayed_as', reference))
            entry_id = entry.get('id', 'N/A')
            entry_amount = entry.get('total_amount', total_amount)
            entry_status = entry.get('status', {}).get('displayed_as', 'Créé')
            
            # Déterminer le type d'écriture en français
            entry_type_fr = "Décaissement" if entry_type == "other_payment" else "Encaissement"
            icon = "💸" if entry_type == "other_payment" else "💰"
            
            return f"""{icon} Écriture comptable créée avec succès!

📋 DÉTAILS:
ID: {entry_id}
Type: {entry_type_fr}
Référence: {entry_ref}
Date: {date}
Montant: {entry_amount}€
Statut: {entry_status}

📝 DESCRIPTION:
{description}

🎯 Cette écriture manuelle permet les corrections comptables et régularisations d'expert!"""
            
        except Exception as e:
            return f"❌ Erreur lors de la création de l'écriture comptable: {str(e)}"

class GetVATReturnInput(BaseModel):
    """Input schema for getting VAT returns analysis"""
    limit: Optional[int] = Field(20, description="Nombre de déclarations à analyser")
    from_date: Optional[str] = Field(None, description="Date de début pour l'analyse (YYYY-MM-DD)")
    to_date: Optional[str] = Field(None, description="Date de fin pour l'analyse (YYYY-MM-DD)")
    include_detailed_analysis: Optional[bool] = Field(True, description="Inclure l'analyse détaillée TVA collectée/déductible")
    business_id: Optional[str] = Field(None, description="Sage business ID")

class GetVATReturnTool(SageBaseTool):
    name: str = "get_vat_return"
    description: str = "Analyse avancée des déclarations TVA avec conformité et détails fiscaux experts"
    args_schema: Type[BaseModel] = GetVATReturnInput

    def _run(self, limit: Optional[int] = 20, from_date: Optional[str] = None,
             to_date: Optional[str] = None, include_detailed_analysis: Optional[bool] = True,
             business_id: Optional[str] = None) -> str:
        try:
            credentials = self.get_credentials()
            if not credentials:
                return "❌ Erreur: Aucune connexion Sage détectée. Veuillez vous connecter à Sage d'abord."
            
            # Obtenir l'analyse avancée des déclarations TVA
            result = sage_api.get_vat_returns_analysis(
                credentials, business_id, limit, from_date, to_date
            )
            
            basic_returns = result.get('basic_returns', {})
            vat_breakdown = result.get('vat_breakdown', {})
            compliance_checks = result.get('compliance_checks', [])
            
            tax_returns = basic_returns.get('$items', [])
            
            response_parts = [f"🏛️ Analyse des déclarations TVA ({len(tax_returns)} trouvées):"]
            
            if not tax_returns:
                response_parts.append("ℹ️ Aucune déclaration TVA trouvée pour cette période.")
            else:
                # Afficher les déclarations
                total_tax_due = 0
                
                for tax_return in tax_returns:
                    ref = tax_return.get('reference', tax_return.get('displayed_as', 'N/A'))
                    period_start = tax_return.get('period_start_date', 'N/A')
                    period_end = tax_return.get('period_end_date', 'N/A')
                    status = tax_return.get('status', {}).get('displayed_as', 'N/A')
                    tax_amount = float(tax_return.get('total_tax_due', 0))
                    total_tax_due += tax_amount
                    
                    return_info = f"- {ref} | {period_start} → {period_end} | {tax_amount}€ | {status}"
                    response_parts.append(return_info)
                
                # Résumé des déclarations
                response_parts.append(f"\n💰 Total TVA due: {total_tax_due:,.2f}€")
            
            # Analyse détaillée TVA si demandée et disponible
            if include_detailed_analysis and vat_breakdown and 'error' not in vat_breakdown:
                response_parts.append(f"\n\n📊 ANALYSE DÉTAILLÉE TVA:")
                
                vat_collected = vat_breakdown.get('vat_collected', 0)
                vat_deductible = vat_breakdown.get('vat_deductible', 0)
                net_vat_due = vat_breakdown.get('net_vat_due', 0)
                sales_count = vat_breakdown.get('sales_count', 0)
                purchase_count = vat_breakdown.get('purchase_count', 0)
                
                response_parts.append(f"TVA collectée (ventes): +{vat_collected:,.2f}€ ({sales_count} factures)")
                response_parts.append(f"TVA déductible (achats): -{vat_deductible:,.2f}€ ({purchase_count} factures)")
                response_parts.append(f"TVA nette due: {net_vat_due:,.2f}€")
                
                # Ratio d'analyse
                if vat_collected > 0:
                    deduction_ratio = (vat_deductible / vat_collected) * 100
                    response_parts.append(f"Ratio de déduction: {deduction_ratio:.1f}%")
                
                # Conseils d'expert
                if net_vat_due < 0:
                    response_parts.append("💡 Crédit de TVA - Demander le remboursement")
                elif deduction_ratio > 80:
                    response_parts.append("⚠️ Ratio de déduction élevé - Vérifier la conformité")
                elif deduction_ratio < 20:
                    response_parts.append("✅ Structure TVA saine - Bon niveau de marge")
            
            elif vat_breakdown and 'error' in vat_breakdown:
                response_parts.append(f"\n⚠️ {vat_breakdown['error']}")
            
            # Vérifications de conformité
            if compliance_checks:
                response_parts.append(f"\n\n🔍 CONTRÔLES DE CONFORMITÉ:")
                
                for check in compliance_checks:
                    severity_icon = {
                        'high': '🔴',
                        'medium': '🟡',
                        'low': '🟢'
                    }.get(check.get('severity'), '🔵')
                    
                    check_message = f"{severity_icon} {check.get('message', 'Contrôle non spécifié')}"
                    response_parts.append(check_message)
            else:
                response_parts.append(f"\n\n✅ CONFORMITÉ: Aucun problème détecté")
            
            # Recommandations d'expert
            response_parts.append(f"\n\n🎯 RECOMMANDATIONS EXPERTES:")
            
            if len(tax_returns) == 0:
                response_parts.append("🔴 URGENT: Vérifier les obligations déclaratives TVA")
            elif len(tax_returns) < 4 and from_date and to_date:
                response_parts.append("🟡 Surveiller la fréquence des déclarations")
            else:
                response_parts.append("✅ Suivi déclaratif conforme")
            
            # Conseils de trésorerie
            if total_tax_due > 10000:
                response_parts.append("💸 Impact trésorerie significatif - Planifier les versements")
            elif total_tax_due > 0:
                response_parts.append("💰 Provisions recommandées pour les échéances TVA")
            
            # Période d'analyse
            if from_date or to_date:
                period_info = f"Période analysée: {from_date or 'Début'} → {to_date or 'Fin'}"
                response_parts.append(f"\n📅 {period_info}")
            
            return "\n".join(response_parts)
            
        except Exception as e:
            return f"❌ Erreur lors de l'analyse des déclarations TVA: {str(e)}"

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
        GetLedgerAccountsTool(),
        GetBankReconciliationTool(),
        CreatePurchaseInvoiceTool(),
        GetFixedAssetsTool(),
        CreateJournalEntryTool(),
        GetVATReturnTool(),
        CreateProductTool(),
        GetProductsTool(),
        GetBankAccountsTool(),
        GetBalanceSheetTool(),
        GetProfitLossTool(),
        SearchTransactionsTool()
    ]
    
    # Ajouter les outils d'analyse de fichiers
    try:
        from tools.file_analysis_tools import SAGE_FILE_TOOLS
        SAGE_TOOLS.extend(SAGE_FILE_TOOLS)
    except ImportError:
        print("Warning: File analysis tools not available")
    
except Exception as e:
    print(f"Warning: Could not initialize Sage tools: {e}")
    SAGE_TOOLS = []  # Empty list if tools can't be initialized

