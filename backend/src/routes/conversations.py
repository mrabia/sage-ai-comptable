from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.models.user import User, Conversation, AuditLog, db

conversations_bp = Blueprint('conversations', __name__)

@conversations_bp.route('/conversations', methods=['GET'])
@jwt_required()
def get_conversations():
    """Récupérer toutes les conversations de l'utilisateur"""
    try:
        user_id = get_jwt_identity()
        
        conversations = Conversation.query.filter_by(
            user_id=user_id, 
            is_active=True
        ).order_by(Conversation.updated_at.desc()).all()
        
        return jsonify([conv.to_dict() for conv in conversations]), 200
        
    except Exception as e:
        return jsonify({'error': f'Erreur lors de la récupération des conversations: {str(e)}'}), 500

@conversations_bp.route('/conversations', methods=['POST'])
@jwt_required()
def create_conversation():
    """Créer une nouvelle conversation"""
    try:
        user_id = get_jwt_identity()
        data = request.json
        
        conversation = Conversation(
            user_id=user_id,
            title=data.get('title', 'Nouvelle conversation'),
            messages='[]'  # Conversation vide au départ
        )
        
        if data.get('metadata'):
            conversation.set_metadata(data['metadata'])
        
        db.session.add(conversation)
        db.session.commit()
        
        # Log de création de conversation
        audit_log = AuditLog(
            user_id=user_id,
            action='conversation_created',
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        audit_log.set_details({
            'conversation_id': conversation.id,
            'title': conversation.title
        })
        db.session.add(audit_log)
        db.session.commit()
        
        return jsonify(conversation.to_dict()), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erreur lors de la création de la conversation: {str(e)}'}), 500

@conversations_bp.route('/conversations/<int:conversation_id>', methods=['GET'])
@jwt_required()
def get_conversation(conversation_id):
    """Récupérer une conversation spécifique avec ses messages"""
    try:
        user_id = get_jwt_identity()
        
        # Import Message here to avoid circular imports
        from src.models.user import Message
        
        conversation = Conversation.query.filter_by(
            id=conversation_id,
            user_id=user_id,
            is_active=True
        ).first()
        
        if not conversation:
            return jsonify({'error': 'Conversation non trouvée'}), 404
        
        # Get messages ordered by creation time
        messages = Message.query.filter_by(
            conversation_id=conversation_id
        ).order_by(Message.created_at.asc()).all()
        
        # Build response with messages
        conversation_dict = {
            'id': conversation.id,
            'user_id': conversation.user_id,
            'title': conversation.title,
            'messages': [msg.to_dict() for msg in messages],
            'metadata': conversation.get_metadata(),
            'created_at': conversation.created_at.isoformat(),
            'updated_at': conversation.updated_at.isoformat(),
            'is_active': conversation.is_active
        }
        
        return jsonify(conversation_dict), 200
        
    except Exception as e:
        return jsonify({'error': f'Erreur lors de la récupération de la conversation: {str(e)}'}), 500

@conversations_bp.route('/conversations/<int:conversation_id>/messages', methods=['POST'])
@jwt_required()
def add_message(conversation_id):
    """Ajouter un message à une conversation"""
    try:
        user_id = get_jwt_identity()
        data = request.json
        
        if not data.get('role') or not data.get('content'):
            return jsonify({'error': 'Role et content sont requis'}), 400
        
        conversation = Conversation.query.filter_by(
            id=conversation_id,
            user_id=user_id,
            is_active=True
        ).first()
        
        if not conversation:
            return jsonify({'error': 'Conversation non trouvée'}), 404
        
        # Ajouter le message
        conversation.add_message(
            role=data['role'],
            content=data['content'],
            metadata=data.get('metadata')
        )
        
        db.session.commit()
        
        return jsonify(conversation.to_dict()), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erreur lors de l\'ajout du message: {str(e)}'}), 500

@conversations_bp.route('/conversations/<int:conversation_id>', methods=['PUT'])
@jwt_required()
def update_conversation(conversation_id):
    """Mettre à jour une conversation (titre, métadonnées)"""
    try:
        user_id = get_jwt_identity()
        data = request.json
        
        conversation = Conversation.query.filter_by(
            id=conversation_id,
            user_id=user_id,
            is_active=True
        ).first()
        
        if not conversation:
            return jsonify({'error': 'Conversation non trouvée'}), 404
        
        # Mettre à jour les champs autorisés
        if 'title' in data:
            conversation.title = data['title']
        
        if 'metadata' in data:
            conversation.set_metadata(data['metadata'])
        
        db.session.commit()
        
        return jsonify(conversation.to_dict()), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erreur lors de la mise à jour: {str(e)}'}), 500

@conversations_bp.route('/conversations/<int:conversation_id>', methods=['DELETE'])
@jwt_required()
def delete_conversation(conversation_id):
    """Supprimer une conversation (soft delete)"""
    try:
        user_id = get_jwt_identity()
        
        conversation = Conversation.query.filter_by(
            id=conversation_id,
            user_id=user_id,
            is_active=True
        ).first()
        
        if not conversation:
            return jsonify({'error': 'Conversation non trouvée'}), 404
        
        # Soft delete
        conversation.is_active = False
        
        # Log de suppression
        audit_log = AuditLog(
            user_id=user_id,
            action='conversation_deleted',
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        audit_log.set_details({
            'conversation_id': conversation.id,
            'title': conversation.title
        })
        db.session.add(audit_log)
        db.session.commit()
        
        return jsonify({'message': 'Conversation supprimée avec succès'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erreur lors de la suppression: {str(e)}'}), 500

@conversations_bp.route('/conversations/<int:conversation_id>/messages', methods=['GET'])
@jwt_required()
def get_conversation_messages(conversation_id):
    """Récupérer tous les messages d'une conversation"""
    try:
        user_id = get_jwt_identity()
        
        conversation = Conversation.query.filter_by(
            id=conversation_id,
            user_id=user_id,
            is_active=True
        ).first()
        
        if not conversation:
            return jsonify({'error': 'Conversation non trouvée'}), 404
        
        messages = conversation.get_messages()
        
        return jsonify({
            'conversation_id': conversation.id,
            'title': conversation.title,
            'messages': messages,
            'total_messages': len(messages)
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Erreur lors de la récupération des messages: {str(e)}'}), 500

@conversations_bp.route('/conversations/search', methods=['GET'])
@jwt_required()
def search_conversations():
    """Rechercher dans les conversations"""
    try:
        user_id = get_jwt_identity()
        query = request.args.get('q', '').strip()
        
        if not query:
            return jsonify({'error': 'Paramètre de recherche requis'}), 400
        
        # Recherche dans les titres et les messages
        conversations = Conversation.query.filter_by(
            user_id=user_id,
            is_active=True
        ).filter(
            db.or_(
                Conversation.title.contains(query),
                Conversation.messages.contains(query)
            )
        ).order_by(Conversation.updated_at.desc()).all()
        
        return jsonify({
            'query': query,
            'results': [conv.to_dict() for conv in conversations],
            'total_results': len(conversations)
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Erreur lors de la recherche: {str(e)}'}), 500

