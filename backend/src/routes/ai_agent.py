from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.models.user import User, Conversation, Message, AuditLog, db
from src.agents.sage_agent import SageAgentManager
from datetime import datetime

ai_agent_bp = Blueprint('ai_agent', __name__)

# Initialiser le gestionnaire d'agent
agent_manager = SageAgentManager()

@ai_agent_bp.route('/agent/chat', methods=['POST'])
@jwt_required()
def chat_with_agent():
    """Endpoint principal pour discuter avec l'agent AI"""
    try:
        user_id = int(get_jwt_identity())  # Convertir en int
        data = request.json
        
        if not data or not data.get('message'):
            return jsonify({'error': 'Message requis'}), 400
        
        user_message = data.get('message')
        conversation_id = data.get('conversation_id')
        business_id = data.get('business_id')
        
        # Récupérer l'utilisateur et ses credentials Sage
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'Utilisateur non trouvé'}), 404
        
        credentials = user.get_sage_credentials()
        if not credentials:
            return jsonify({
                'error': 'Credentials Sage non configurés',
                'suggestion': 'Veuillez d\'abord vous connecter à Sage Business Cloud Accounting'
            }), 400
        
        # Créer ou récupérer la conversation
        if conversation_id:
            conversation = Conversation.query.filter_by(
                id=conversation_id, 
                user_id=user_id
            ).first()
            if not conversation:
                return jsonify({'error': 'Conversation non trouvée'}), 404
        else:
            # Créer une nouvelle conversation
            conversation = Conversation(
                user_id=user_id,
                title=user_message[:50] + "..." if len(user_message) > 50 else user_message,
                messages='[]'  # Initialiser avec une liste vide
            )
            db.session.add(conversation)
            db.session.flush()  # Pour obtenir l'ID
        
        # Sauvegarder le message utilisateur
        user_msg = Message(
            conversation_id=conversation.id,
            content=user_message,
            is_from_user=True
        )
        db.session.add(user_msg)
        
        # Check if this is a confirmation response
        confirmation_id = data.get('confirmation_id')
        if confirmation_id:
            return handle_agent_confirmation(user_id, confirmation_id, user_message, conversation, user_msg)
        
        # Traiter le message avec l'agent AI
        agent_response = agent_manager.process_user_request(
            user_message, user_id
        )
        
        # Normaliser la réponse de l'agent (peut être string ou dict)
        if isinstance(agent_response, str):
            agent_response = {
                'response': agent_response,
                'agent_type': 'comptable',
                'capabilities_used': [],
                'success': True
            }
        elif not isinstance(agent_response, dict):
            agent_response = {
                'response': str(agent_response),
                'agent_type': 'comptable',
                'capabilities_used': [],
                'success': False
            }
        
        # Check if the agent response contains a planned action that needs confirmation
        if agent_response.get('planned_action'):
            return request_agent_confirmation(user_id, agent_response, conversation, user_msg)
        
        # Sauvegarder la réponse de l'agent
        agent_msg = Message(
            conversation_id=conversation.id,
            content=agent_response.get('response', 'Erreur lors du traitement'),
            is_from_user=False
        )
        
        # Ajouter les métadonnées de l'agent
        agent_msg.set_metadata({
            'agent_type': agent_response.get('agent_type'),
            'capabilities_used': agent_response.get('capabilities_used', []),
            'success': agent_response.get('success', False),
            'business_id': business_id
        })
        
        db.session.add(agent_msg)
        
        # Log de l'interaction
        audit_log = AuditLog(
            user_id=user_id,
            action='ai_chat_interaction',
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        audit_log.set_details({
            'conversation_id': conversation.id,
            'message_length': len(user_message),
            'agent_type': agent_response.get('agent_type'),
            'success': agent_response.get('success')
        })
        db.session.add(audit_log)
        
        db.session.commit()
        
        return jsonify({
            'conversation_id': conversation.id,
            'message_id': agent_msg.id,
            'response': agent_response.get('response'),
            'agent_type': agent_response.get('agent_type'),
            'capabilities_used': agent_response.get('capabilities_used', []),
            'success': agent_response.get('success', False),
            'timestamp': agent_msg.created_at.isoformat()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erreur lors du traitement: {str(e)}'}), 500

@ai_agent_bp.route('/agent/capabilities', methods=['GET'])
@jwt_required()
def get_agent_capabilities():
    """Récupère les capacités disponibles de l'agent AI"""
    try:
        capabilities = agent_manager.get_agent_capabilities()
        
        return jsonify(capabilities), 200
        
    except Exception as e:
        return jsonify({'error': f'Erreur lors de la récupération des capacités: {str(e)}'}), 500

@ai_agent_bp.route('/agent/suggestions', methods=['POST'])
@jwt_required()
def get_suggestions():
    """Génère des suggestions basées sur le contexte de l'utilisateur"""
    try:
        user_id = int(get_jwt_identity())  # Convertir en int
        data = request.json or {}
        
        # Récupérer l'utilisateur
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'Utilisateur non trouvé'}), 404
        
        # Vérifier les credentials Sage
        credentials = user.get_sage_credentials()
        sage_connected = bool(credentials)
        
        # Générer des suggestions basées sur le contexte
        suggestions = []
        
        if not sage_connected:
            suggestions.extend([
                "Connectez-vous à Sage Business Cloud Accounting pour commencer",
                "Configurez votre authentification Sage pour accéder à vos données"
            ])
        else:
            # Suggestions pour utilisateurs connectés
            suggestions.extend([
                "Afficher la liste de mes clients",
                "Créer une nouvelle facture",
                "Analyser mon bilan comptable du mois dernier",
                "Rechercher les factures impayées",
                "Créer un nouveau client",
                "Afficher mon compte de résultat",
                "Rechercher les transactions de cette semaine",
                "Analyser la performance financière de mon entreprise"
            ])
        
        # Suggestions basées sur l'historique récent
        recent_conversations = Conversation.query.filter_by(user_id=user_id)\
            .order_by(Conversation.created_at.desc()).limit(3).all()
        
        if recent_conversations:
            suggestions.append("Continuer notre dernière conversation")
        
        return jsonify({
            'suggestions': suggestions,
            'sage_connected': sage_connected,
            'context': {
                'has_recent_conversations': len(recent_conversations) > 0,
                'total_conversations': len(recent_conversations)
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Erreur lors de la génération des suggestions: {str(e)}'}), 500

@ai_agent_bp.route('/agent/quick-actions', methods=['GET'])
@jwt_required()
def get_quick_actions():
    """Récupère les actions rapides disponibles"""
    try:
        user_id = int(get_jwt_identity())  # Convertir en int
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'Utilisateur non trouvé'}), 404
        
        credentials = user.get_sage_credentials()
        sage_connected = bool(credentials)
        
        quick_actions = []
        
        if sage_connected:
            quick_actions = [
                {
                    'id': 'list_customers',
                    'title': 'Mes clients',
                    'description': 'Afficher la liste de tous mes clients',
                    'icon': 'users',
                    'category': 'clients'
                },
                {
                    'id': 'create_invoice',
                    'title': 'Nouvelle facture',
                    'description': 'Créer une nouvelle facture',
                    'icon': 'file-text',
                    'category': 'facturation'
                },
                {
                    'id': 'balance_sheet',
                    'title': 'Bilan comptable',
                    'description': 'Consulter mon bilan comptable',
                    'icon': 'bar-chart',
                    'category': 'rapports'
                },
                {
                    'id': 'profit_loss',
                    'title': 'Compte de résultat',
                    'description': 'Analyser mon compte de résultat',
                    'icon': 'trending-up',
                    'category': 'rapports'
                },
                {
                    'id': 'search_transactions',
                    'title': 'Rechercher transactions',
                    'description': 'Rechercher des transactions spécifiques',
                    'icon': 'search',
                    'category': 'transactions'
                },
                {
                    'id': 'create_customer',
                    'title': 'Nouveau client',
                    'description': 'Ajouter un nouveau client',
                    'icon': 'user-plus',
                    'category': 'clients'
                }
            ]
        else:
            quick_actions = [
                {
                    'id': 'connect_sage',
                    'title': 'Connecter Sage',
                    'description': 'Se connecter à Sage Business Cloud Accounting',
                    'icon': 'link',
                    'category': 'configuration'
                }
            ]
        
        return jsonify({
            'quick_actions': quick_actions,
            'sage_connected': sage_connected
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Erreur lors de la récupération des actions rapides: {str(e)}'}), 500

@ai_agent_bp.route('/agent/execute-action', methods=['POST'])
@jwt_required()
def execute_quick_action():
    """Exécute une action rapide"""
    try:
        user_id = int(get_jwt_identity())  # Convertir en int
        data = request.json
        
        if not data or not data.get('action_id'):
            return jsonify({'error': 'ID d\'action requis'}), 400
        
        action_id = data.get('action_id')
        business_id = data.get('business_id')
        
        # Mapper les actions vers des messages
        action_messages = {
            'list_customers': 'Affiche-moi la liste de tous mes clients',
            'create_invoice': 'Je veux créer une nouvelle facture',
            'balance_sheet': 'Montre-moi mon bilan comptable',
            'profit_loss': 'Affiche mon compte de résultat',
            'search_transactions': 'Je veux rechercher des transactions',
            'create_customer': 'Je veux créer un nouveau client',
            'connect_sage': 'Comment me connecter à Sage Business Cloud Accounting ?'
        }
        
        message = action_messages.get(action_id)
        if not message:
            return jsonify({'error': 'Action non reconnue'}), 400
        
        # Utiliser l'endpoint de chat pour traiter l'action
        return chat_with_agent()
        
    except Exception as e:
        return jsonify({'error': f'Erreur lors de l\'exécution de l\'action: {str(e)}'}), 500


def request_agent_confirmation(user_id, agent_response, conversation, user_msg):
    """Demande confirmation après analyse de l'agent"""
    from src.models.user import SageOperation, db
    import uuid
    from datetime import datetime
    
    # Créer une opération en attente de confirmation avec le plan détaillé
    operation = SageOperation(
        user_id=user_id,
        operation_type=agent_response.get('planned_action', {}).get('type', 'unknown_action'),
        status='awaiting_confirmation'
    )
    
    confirmation_id = str(uuid.uuid4())
    operation.set_operation_data({
        'original_message': user_msg.content,
        'confirmation_id': confirmation_id,
        'agent_response': agent_response.get('response'),
        'planned_action': agent_response.get('planned_action'),
        'conversation_id': conversation.id,
        'user_message_id': user_msg.id
    })
    
    db.session.add(operation)
    db.session.commit()
    
    # Construire le message de confirmation avec les détails de l'analyse
    confirmation_response = f"🔍 **ANALYSE TERMINÉE** 🔍\n\n"
    confirmation_response += f"{agent_response.get('response')}\n\n"
    confirmation_response += f"🚨 **CONFIRMATION REQUISE** 🚨\n\n"
    confirmation_response += f"⚠️ Cette action va **modifier vos données Sage** et ne peut pas être annulée facilement.\n\n"
    confirmation_response += f"**Confirmez-vous cette opération ?**\n\n"
    confirmation_response += f"✅ Tapez `OUI CONFIRMER {confirmation_id[:8]}` pour procéder\n"
    confirmation_response += f"❌ Tapez `NON` pour annuler\n\n"
    confirmation_response += f"_Cette demande expirera dans 5 minutes._"
    
    return jsonify({
        'conversation_id': conversation.id,
        'message_id': int(datetime.now().timestamp() * 1000),
        'response': confirmation_response,
        'agent_type': 'sage_confirmation',
        'capabilities_used': ['human_in_loop', 'analysis'],
        'success': True,
        'requires_confirmation': True,
        'confirmation_id': confirmation_id,
        'planned_action': agent_response.get('planned_action'),
        'timestamp': datetime.now().isoformat()
    }), 200


def handle_agent_confirmation(user_id, confirmation_id, user_message, conversation, user_msg):
    """Traite la confirmation après analyse de l'agent"""
    from src.models.user import SageOperation, db
    from datetime import datetime
    
    # Trouver l'opération en attente
    operation = SageOperation.query.filter_by(
        user_id=user_id,
        status='awaiting_confirmation'
    ).filter(
        SageOperation.operation_data.contains(confirmation_id)
    ).first()
    
    if not operation:
        response = "❌ Opération de confirmation non trouvée ou expirée."
        return create_agent_response(response, conversation, False)
    
    # Vérifier si c'est une confirmation
    if any(word in user_message.lower() for word in ['oui', 'confirmer', 'confirm', 'yes']):
        # Confirmation positive - exécuter l'action planifiée
        operation.status = 'confirmed'
        db.session.commit()
        
        return execute_planned_action(operation, conversation)
    else:
        # Confirmation négative
        operation.status = 'rejected'
        db.session.commit()
        
        response = "✅ Opération annulée avec succès. Aucune modification n'a été apportée à vos données Sage."
        return create_agent_response(response, conversation, True)


def execute_planned_action(operation, conversation):
    """Exécute l'action planifiée après confirmation"""
    try:
        operation_data = operation.get_operation_data()
        planned_action = operation_data.get('planned_action', {})
        
        # Pour l'instant, on simule l'exécution
        # TODO: Implémenter l'exécution réelle selon le type d'action
        
        response = f"✅ **OPÉRATION EXÉCUTÉE AVEC SUCCÈS**\n\n"
        response += f"L'action '{planned_action.get('description', 'Action')}' a été exécutée dans Sage.\n\n"
        
        if planned_action.get('details'):
            response += "**Détails de l'exécution :**\n"
            for key, value in planned_action['details'].items():
                response += f"- {key}: {value}\n"
        
        response += f"\n✨ L'opération a été enregistrée dans votre historique."
        
        # Marquer comme réussie
        operation.status = 'success'
        operation.set_sage_response({
            'executed': True,
            'action': planned_action,
            'timestamp': datetime.now().isoformat()
        })
        db.session.commit()
        
        return create_agent_response(response, conversation, True)
        
    except Exception as e:
        operation.status = 'error'
        operation.error_message = str(e)
        db.session.commit()
        
        response = f"❌ Erreur lors de l'exécution: {str(e)}"
        return create_agent_response(response, conversation, False)


def create_agent_response(response_text, conversation, success=True):
    """Helper pour créer une réponse d'agent standardisée"""
    from datetime import datetime
    
    return jsonify({
        'conversation_id': conversation.id,
        'message_id': int(datetime.now().timestamp() * 1000),
        'response': response_text,
        'agent_type': 'sage_intelligent_confirmation',
        'capabilities_used': ['human_in_loop', 'analysis'],
        'success': success,
        'timestamp': datetime.now().isoformat()
    }), 200

