from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.models.user import User, SageOperation, db
from datetime import datetime, timedelta

sage_operations_bp = Blueprint('sage_operations', __name__)

@sage_operations_bp.route('/sage/operations/pending', methods=['GET'])
@jwt_required()
def get_pending_operations():
    """Récupère les opérations en attente de confirmation"""
    try:
        user_id = int(get_jwt_identity())
        
        # Nettoyer les opérations expirées (plus de 5 minutes)
        expired_time = datetime.utcnow() - timedelta(minutes=5)
        expired_ops = SageOperation.query.filter(
            SageOperation.user_id == user_id,
            SageOperation.status == 'awaiting_confirmation',
            SageOperation.created_at < expired_time
        ).all()
        
        for op in expired_ops:
            op.status = 'expired'
        db.session.commit()
        
        # Récupérer les opérations en attente
        pending_ops = SageOperation.query.filter_by(
            user_id=user_id,
            status='awaiting_confirmation'
        ).order_by(SageOperation.created_at.desc()).all()
        
        return jsonify({
            'pending_operations': [op.to_dict() for op in pending_ops]
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Erreur lors de la récupération: {str(e)}'}), 500

@sage_operations_bp.route('/sage/operations/<int:operation_id>/confirm', methods=['POST'])
@jwt_required()
def confirm_operation(operation_id):
    """Confirme une opération en attente"""
    try:
        user_id = int(get_jwt_identity())
        data = request.json or {}
        confirmed = data.get('confirmed', False)
        
        # Récupérer l'opération
        operation = SageOperation.query.filter_by(
            id=operation_id,
            user_id=user_id,
            status='awaiting_confirmation'
        ).first()
        
        if not operation:
            return jsonify({'error': 'Opération non trouvée ou expirée'}), 404
        
        # Vérifier l'expiration (5 minutes)
        if operation.created_at < datetime.utcnow() - timedelta(minutes=5):
            operation.status = 'expired'
            db.session.commit()
            return jsonify({'error': 'Opération expirée'}), 400
        
        if confirmed:
            operation.status = 'confirmed'
            message = 'Opération confirmée. Exécution en cours...'
            
            # TODO: Implémenter l'exécution réelle selon le type d'opération
            # Pour l'instant, on simule
            operation.status = 'success'
            operation.set_sage_response({'message': 'Simulated execution', 'success': True})
            
        else:
            operation.status = 'rejected'
            message = 'Opération annulée avec succès.'
        
        db.session.commit()
        
        return jsonify({
            'message': message,
            'operation': operation.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Erreur lors de la confirmation: {str(e)}'}), 500

@sage_operations_bp.route('/sage/operations/history', methods=['GET'])
@jwt_required()
def get_operations_history():
    """Récupère l'historique des opérations"""
    try:
        user_id = int(get_jwt_identity())
        
        operations = SageOperation.query.filter_by(
            user_id=user_id
        ).order_by(SageOperation.created_at.desc()).limit(50).all()
        
        return jsonify({
            'operations': [op.to_dict() for op in operations]
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Erreur lors de la récupération: {str(e)}'}), 500