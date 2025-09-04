from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.models.user import User, SageOperation, AuditLog, db
from datetime import datetime, timedelta

sage_operations_bp = Blueprint('sage_operations', __name__)

@sage_operations_bp.route('/sage-operations', methods=['GET'])
@jwt_required()
def get_sage_operations():
    """Récupérer toutes les opérations Sage de l'utilisateur"""
    try:
        user_id = get_jwt_identity()
        
        # Paramètres de pagination
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        operation_type = request.args.get('type')
        status = request.args.get('status')
        
        query = SageOperation.query.filter_by(user_id=user_id)
        
        # Filtres optionnels
        if operation_type:
            query = query.filter_by(operation_type=operation_type)
        if status:
            query = query.filter_by(status=status)
        
        operations = query.order_by(SageOperation.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'operations': [op.to_dict() for op in operations.items],
            'total': operations.total,
            'page': page,
            'per_page': per_page,
            'pages': operations.pages
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Erreur lors de la récupération des opérations: {str(e)}'}), 500

@sage_operations_bp.route('/sage-operations', methods=['POST'])
@jwt_required()
def create_sage_operation():
    """Créer une nouvelle opération Sage"""
    try:
        user_id = get_jwt_identity()
        data = request.json
        
        if not data.get('operation_type'):
            return jsonify({'error': 'Type d\'opération requis'}), 400
        
        # Vérifier que l'utilisateur a des credentials Sage
        user = User.query.get(user_id)
        if not user or not user.get_sage_credentials():
            return jsonify({'error': 'Credentials Sage non configurés'}), 400
        
        operation = SageOperation(
            user_id=user_id,
            operation_type=data['operation_type'],
            status='pending'
        )
        
        operation.set_operation_data(data.get('operation_data', {}))
        
        db.session.add(operation)
        db.session.commit()
        
        # Log de création d'opération
        audit_log = AuditLog(
            user_id=user_id,
            action='sage_operation_created',
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        audit_log.set_details({
            'operation_id': operation.id,
            'operation_type': operation.operation_type
        })
        db.session.add(audit_log)
        db.session.commit()
        
        return jsonify(operation.to_dict()), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erreur lors de la création de l\'opération: {str(e)}'}), 500

@sage_operations_bp.route('/sage-operations/<int:operation_id>', methods=['GET'])
@jwt_required()
def get_sage_operation(operation_id):
    """Récupérer une opération Sage spécifique"""
    try:
        user_id = get_jwt_identity()
        
        operation = SageOperation.query.filter_by(
            id=operation_id,
            user_id=user_id
        ).first()
        
        if not operation:
            return jsonify({'error': 'Opération non trouvée'}), 404
        
        return jsonify(operation.to_dict()), 200
        
    except Exception as e:
        return jsonify({'error': f'Erreur lors de la récupération de l\'opération: {str(e)}'}), 500

@sage_operations_bp.route('/sage-operations/<int:operation_id>/status', methods=['PUT'])
@jwt_required()
def update_operation_status(operation_id):
    """Mettre à jour le statut d'une opération"""
    try:
        user_id = get_jwt_identity()
        data = request.json
        
        if not data.get('status'):
            return jsonify({'error': 'Statut requis'}), 400
        
        operation = SageOperation.query.filter_by(
            id=operation_id,
            user_id=user_id
        ).first()
        
        if not operation:
            return jsonify({'error': 'Opération non trouvée'}), 404
        
        old_status = operation.status
        operation.status = data['status']
        
        if data.get('sage_response'):
            operation.set_sage_response(data['sage_response'])
        
        if data.get('error_message'):
            operation.error_message = data['error_message']
        
        if data['status'] in ['success', 'error']:
            operation.completed_at = datetime.utcnow()
        
        # Log de mise à jour du statut
        audit_log = AuditLog(
            user_id=user_id,
            action='sage_operation_status_updated',
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        audit_log.set_details({
            'operation_id': operation.id,
            'old_status': old_status,
            'new_status': operation.status
        })
        db.session.add(audit_log)
        db.session.commit()
        
        return jsonify(operation.to_dict()), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erreur lors de la mise à jour: {str(e)}'}), 500

@sage_operations_bp.route('/sage-operations/types', methods=['GET'])
@jwt_required()
def get_operation_types():
    """Récupérer les types d'opérations Sage disponibles"""
    try:
        operation_types = [
            {
                'type': 'create_customer',
                'name': 'Créer un client',
                'description': 'Créer un nouveau client dans Sage',
                'required_fields': ['name', 'email']
            },
            {
                'type': 'create_supplier',
                'name': 'Créer un fournisseur',
                'description': 'Créer un nouveau fournisseur dans Sage',
                'required_fields': ['name', 'email']
            },
            {
                'type': 'create_invoice',
                'name': 'Créer une facture',
                'description': 'Créer une nouvelle facture',
                'required_fields': ['customer_id', 'items']
            },
            {
                'type': 'get_balance_sheet',
                'name': 'Bilan comptable',
                'description': 'Récupérer le bilan comptable',
                'required_fields': []
            },
            {
                'type': 'get_profit_loss',
                'name': 'Compte de résultat',
                'description': 'Récupérer le compte de résultat',
                'required_fields': []
            },
            {
                'type': 'search_transactions',
                'name': 'Rechercher des transactions',
                'description': 'Rechercher des transactions comptables',
                'required_fields': ['search_criteria']
            },
            {
                'type': 'get_customers',
                'name': 'Liste des clients',
                'description': 'Récupérer la liste des clients',
                'required_fields': []
            },
            {
                'type': 'get_suppliers',
                'name': 'Liste des fournisseurs',
                'description': 'Récupérer la liste des fournisseurs',
                'required_fields': []
            },
            {
                'type': 'get_invoices',
                'name': 'Liste des factures',
                'description': 'Récupérer la liste des factures',
                'required_fields': []
            },
            {
                'type': 'bank_reconciliation',
                'name': 'Rapprochement bancaire',
                'description': 'Effectuer un rapprochement bancaire',
                'required_fields': ['bank_account_id', 'transactions']
            }
        ]
        
        return jsonify(operation_types), 200
        
    except Exception as e:
        return jsonify({'error': f'Erreur lors de la récupération des types: {str(e)}'}), 500

@sage_operations_bp.route('/sage-operations/stats', methods=['GET'])
@jwt_required()
def get_operation_stats():
    """Récupérer les statistiques des opérations Sage"""
    try:
        user_id = get_jwt_identity()
        
        # Statistiques générales
        total_operations = SageOperation.query.filter_by(user_id=user_id).count()
        successful_operations = SageOperation.query.filter_by(user_id=user_id, status='success').count()
        failed_operations = SageOperation.query.filter_by(user_id=user_id, status='error').count()
        pending_operations = SageOperation.query.filter_by(user_id=user_id, status='pending').count()
        
        # Opérations par type
        operations_by_type = db.session.query(
            SageOperation.operation_type,
            db.func.count(SageOperation.id).label('count')
        ).filter_by(user_id=user_id).group_by(SageOperation.operation_type).all()
        
        # Opérations récentes (7 derniers jours)
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        recent_operations = SageOperation.query.filter(
            SageOperation.user_id == user_id,
            SageOperation.created_at >= seven_days_ago
        ).count()
        
        return jsonify({
            'total_operations': total_operations,
            'successful_operations': successful_operations,
            'failed_operations': failed_operations,
            'pending_operations': pending_operations,
            'success_rate': (successful_operations / total_operations * 100) if total_operations > 0 else 0,
            'operations_by_type': [
                {'type': op_type, 'count': count} 
                for op_type, count in operations_by_type
            ],
            'recent_operations_7_days': recent_operations
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Erreur lors de la récupération des statistiques: {str(e)}'}), 500

