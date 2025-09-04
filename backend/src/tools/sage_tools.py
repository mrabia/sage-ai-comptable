from crewai.tools import BaseTool
from typing import Type, Dict, Any, Optional
from pydantic import BaseModel, Field
from src.services.sage_auth import SageOAuth2Service
from src.services.sage_api import SageAPIService
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
            
            return f"Facture créée avec succès: N°{result.get('displayed_as', reference or invoice_id)} - Montant: {total_amount}€"
            
        except Exception as e:
            return f"Erreur lors de la création de la facture: {str(e)}"

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

# Liste de tous les outils Sage disponibles
SAGE_TOOLS = [
    CreateCustomerTool(),
    GetCustomersTool(),
    CreateInvoiceTool(),
    GetInvoicesTool(),
    GetBalanceSheetTool(),
    GetProfitLossTool(),
    SearchTransactionsTool()
]

