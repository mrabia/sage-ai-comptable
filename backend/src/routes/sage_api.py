from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.models.user import User, SageOperation, AuditLog, db
from src.services.sage_auth import SageOAuth2Service
from src.services.sage_api import SageAPIService
import os
from datetime import datetime

sage_api_bp = Blueprint('sage_api', __name__)

# Configuration OAuth2 Sage
SAGE_CLIENT_ID = os.getenv('SAGE_CLIENT_ID', 'your_client_id')
SAGE_CLIENT_SECRET = os.getenv('SAGE_CLIENT_SECRET', 'your_client_secret')
SAGE_REDIRECT_URI = os.getenv('SAGE_REDIRECT_URI', 'http://localhost:5000/api/sage/callback')

# Initialiser les services
sage_oauth = SageOAuth2Service(SAGE_CLIENT_ID, SAGE_CLIENT_SECRET, SAGE_REDIRECT_URI)
sage_api = SageAPIService(sage_oauth)

def get_user_credentials(user_id: int):
    """Helper pour récupérer les credentials Sage de l'utilisateur"""
    user = User.query.get(user_id)
    if not user:
        raise Exception("Utilisateur non trouvé")
    
    credentials = user.get_sage_credentials()
    if not credentials:
        raise Exception("Credentials Sage non configurés")
    
    return credentials

def log_sage_operation(user_id: int, operation_type: str, operation_data: dict, 
                      sage_response: dict = None, status: str = 'success', error_message: str = None):
    """Helper pour logger les opérations Sage"""
    try:
        operation = SageOperation(
            user_id=user_id,
            operation_type=operation_type,
            status=status,
            error_message=error_message
        )
        
        operation.set_operation_data(operation_data)
        if sage_response:
            operation.set_sage_response(sage_response)
        
        db.session.add(operation)
        db.session.commit()
        
        return operation
    except Exception as e:
        print(f"Erreur lors du logging de l'opération: {e}")
        return None

# ===== GESTION DES CLIENTS =====

@sage_api_bp.route('/sage/customers', methods=['GET'])
@jwt_required()
def get_customers():
    """Récupère la liste des clients"""
    try:
        user_id = get_jwt_identity()
        credentials = get_user_credentials(user_id)
        
        # Paramètres de pagination
        limit = request.args.get('limit', 20, type=int)
        offset = request.args.get('offset', 0, type=int)
        business_id = request.args.get('business_id')
        
        # Appel API Sage
        result = sage_api.get_customers(credentials, business_id, limit, offset)
        
        # Log de l'opération
        log_sage_operation(user_id, 'get_customers', {
            'limit': limit,
            'offset': offset,
            'business_id': business_id
        }, result)
        
        return jsonify(result), 200
        
    except Exception as e:
        log_sage_operation(user_id, 'get_customers', {}, status='error', error_message=str(e))
        return jsonify({'error': str(e)}), 500

@sage_api_bp.route('/sage/customers', methods=['POST'])
@jwt_required()
def create_customer():
    """Crée un nouveau client"""
    try:
        user_id = get_jwt_identity()
        credentials = get_user_credentials(user_id)
        data = request.json
        
        if not data.get('name'):
            return jsonify({'error': 'Le nom du client est requis'}), 400
        
        business_id = data.get('business_id')
        
        # Appel API Sage
        result = sage_api.create_customer(credentials, data, business_id)
        
        # Log de l'opération
        log_sage_operation(user_id, 'create_customer', data, result)
        
        return jsonify(result), 201
        
    except Exception as e:
        log_sage_operation(user_id, 'create_customer', data, status='error', error_message=str(e))
        return jsonify({'error': str(e)}), 500

@sage_api_bp.route('/sage/customers/<customer_id>', methods=['GET'])
@jwt_required()
def get_customer(customer_id):
    """Récupère un client spécifique"""
    try:
        user_id = get_jwt_identity()
        credentials = get_user_credentials(user_id)
        business_id = request.args.get('business_id')
        
        result = sage_api.get_customer(credentials, customer_id, business_id)
        
        log_sage_operation(user_id, 'get_customer', {
            'customer_id': customer_id,
            'business_id': business_id
        }, result)
        
        return jsonify(result), 200
        
    except Exception as e:
        log_sage_operation(user_id, 'get_customer', {'customer_id': customer_id}, 
                         status='error', error_message=str(e))
        return jsonify({'error': str(e)}), 500

# ===== GESTION DES FOURNISSEURS =====

@sage_api_bp.route('/sage/suppliers', methods=['GET'])
@jwt_required()
def get_suppliers():
    """Récupère la liste des fournisseurs"""
    try:
        user_id = get_jwt_identity()
        credentials = get_user_credentials(user_id)
        
        limit = request.args.get('limit', 20, type=int)
        offset = request.args.get('offset', 0, type=int)
        business_id = request.args.get('business_id')
        
        result = sage_api.get_suppliers(credentials, business_id, limit, offset)
        
        log_sage_operation(user_id, 'get_suppliers', {
            'limit': limit,
            'offset': offset,
            'business_id': business_id
        }, result)
        
        return jsonify(result), 200
        
    except Exception as e:
        log_sage_operation(user_id, 'get_suppliers', {}, status='error', error_message=str(e))
        return jsonify({'error': str(e)}), 500

@sage_api_bp.route('/sage/suppliers', methods=['POST'])
@jwt_required()
def create_supplier():
    """Crée un nouveau fournisseur"""
    try:
        user_id = get_jwt_identity()
        credentials = get_user_credentials(user_id)
        data = request.json
        
        if not data.get('name'):
            return jsonify({'error': 'Le nom du fournisseur est requis'}), 400
        
        business_id = data.get('business_id')
        
        result = sage_api.create_supplier(credentials, data, business_id)
        
        log_sage_operation(user_id, 'create_supplier', data, result)
        
        return jsonify(result), 201
        
    except Exception as e:
        log_sage_operation(user_id, 'create_supplier', data, status='error', error_message=str(e))
        return jsonify({'error': str(e)}), 500

# ===== GESTION DES FACTURES =====

@sage_api_bp.route('/sage/invoices', methods=['GET'])
@jwt_required()
def get_invoices():
    """Récupère la liste des factures"""
    try:
        user_id = get_jwt_identity()
        credentials = get_user_credentials(user_id)
        
        limit = request.args.get('limit', 20, type=int)
        offset = request.args.get('offset', 0, type=int)
        status = request.args.get('status')
        business_id = request.args.get('business_id')
        
        result = sage_api.get_invoices(credentials, business_id, limit, offset, status)
        
        log_sage_operation(user_id, 'get_invoices', {
            'limit': limit,
            'offset': offset,
            'status': status,
            'business_id': business_id
        }, result)
        
        return jsonify(result), 200
        
    except Exception as e:
        log_sage_operation(user_id, 'get_invoices', {}, status='error', error_message=str(e))
        return jsonify({'error': str(e)}), 500

@sage_api_bp.route('/sage/invoices', methods=['POST'])
@jwt_required()
def create_invoice():
    """Crée une nouvelle facture"""
    try:
        user_id = get_jwt_identity()
        credentials = get_user_credentials(user_id)
        data = request.json
        
        if not data.get('customer_id'):
            return jsonify({'error': 'L\'ID du client est requis'}), 400
        
        if not data.get('items') or len(data['items']) == 0:
            return jsonify({'error': 'Au moins un article est requis'}), 400
        
        business_id = data.get('business_id')
        
        result = sage_api.create_invoice(credentials, data, business_id)
        
        log_sage_operation(user_id, 'create_invoice', data, result)
        
        return jsonify(result), 201
        
    except Exception as e:
        log_sage_operation(user_id, 'create_invoice', data, status='error', error_message=str(e))
        return jsonify({'error': str(e)}), 500

@sage_api_bp.route('/sage/invoices/<invoice_id>', methods=['GET'])
@jwt_required()
def get_invoice(invoice_id):
    """Récupère une facture spécifique"""
    try:
        user_id = get_jwt_identity()
        credentials = get_user_credentials(user_id)
        business_id = request.args.get('business_id')
        
        result = sage_api.get_invoice(credentials, invoice_id, business_id)
        
        log_sage_operation(user_id, 'get_invoice', {
            'invoice_id': invoice_id,
            'business_id': business_id
        }, result)
        
        return jsonify(result), 200
        
    except Exception as e:
        log_sage_operation(user_id, 'get_invoice', {'invoice_id': invoice_id}, 
                         status='error', error_message=str(e))
        return jsonify({'error': str(e)}), 500

# ===== RAPPORTS FINANCIERS =====

@sage_api_bp.route('/sage/reports/balance-sheet', methods=['GET'])
@jwt_required()
def get_balance_sheet():
    """Récupère le bilan comptable"""
    try:
        user_id = get_jwt_identity()
        credentials = get_user_credentials(user_id)
        
        from_date = request.args.get('from_date')
        to_date = request.args.get('to_date')
        business_id = request.args.get('business_id')
        
        result = sage_api.get_balance_sheet(credentials, business_id, from_date, to_date)
        
        log_sage_operation(user_id, 'get_balance_sheet', {
            'from_date': from_date,
            'to_date': to_date,
            'business_id': business_id
        }, result)
        
        return jsonify(result), 200
        
    except Exception as e:
        log_sage_operation(user_id, 'get_balance_sheet', {}, status='error', error_message=str(e))
        return jsonify({'error': str(e)}), 500

@sage_api_bp.route('/sage/reports/profit-loss', methods=['GET'])
@jwt_required()
def get_profit_loss():
    """Récupère le compte de résultat"""
    try:
        user_id = get_jwt_identity()
        credentials = get_user_credentials(user_id)
        
        from_date = request.args.get('from_date')
        to_date = request.args.get('to_date')
        business_id = request.args.get('business_id')
        
        result = sage_api.get_profit_loss(credentials, business_id, from_date, to_date)
        
        log_sage_operation(user_id, 'get_profit_loss', {
            'from_date': from_date,
            'to_date': to_date,
            'business_id': business_id
        }, result)
        
        return jsonify(result), 200
        
    except Exception as e:
        log_sage_operation(user_id, 'get_profit_loss', {}, status='error', error_message=str(e))
        return jsonify({'error': str(e)}), 500

# ===== RECHERCHE ET UTILITAIRES =====

@sage_api_bp.route('/sage/search/transactions', methods=['POST'])
@jwt_required()
def search_transactions():
    """Recherche des transactions"""
    try:
        user_id = get_jwt_identity()
        credentials = get_user_credentials(user_id)
        data = request.json
        
        business_id = data.get('business_id')
        
        result = sage_api.search_transactions(credentials, data, business_id)
        
        log_sage_operation(user_id, 'search_transactions', data, result)
        
        return jsonify(result), 200
        
    except Exception as e:
        log_sage_operation(user_id, 'search_transactions', data, status='error', error_message=str(e))
        return jsonify({'error': str(e)}), 500

@sage_api_bp.route('/sage/products', methods=['GET'])
@jwt_required()
def get_products():
    """Récupère la liste des produits/services"""
    try:
        user_id = get_jwt_identity()
        credentials = get_user_credentials(user_id)
        
        limit = request.args.get('limit', 20, type=int)
        offset = request.args.get('offset', 0, type=int)
        business_id = request.args.get('business_id')
        
        result = sage_api.get_products(credentials, business_id, limit, offset)
        
        log_sage_operation(user_id, 'get_products', {
            'limit': limit,
            'offset': offset,
            'business_id': business_id
        }, result)
        
        return jsonify(result), 200
        
    except Exception as e:
        log_sage_operation(user_id, 'get_products', {}, status='error', error_message=str(e))
        return jsonify({'error': str(e)}), 500

@sage_api_bp.route('/sage/tax-rates', methods=['GET'])
@jwt_required()
def get_tax_rates():
    """Récupère les taux de TVA"""
    try:
        user_id = get_jwt_identity()
        credentials = get_user_credentials(user_id)
        business_id = request.args.get('business_id')
        
        result = sage_api.get_tax_rates(credentials, business_id)
        
        log_sage_operation(user_id, 'get_tax_rates', {'business_id': business_id}, result)
        
        return jsonify(result), 200
        
    except Exception as e:
        log_sage_operation(user_id, 'get_tax_rates', {}, status='error', error_message=str(e))
        return jsonify({'error': str(e)}), 500

