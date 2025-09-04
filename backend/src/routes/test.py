from flask import Blueprint, jsonify, request
from src.agents.sage_agent import SageAgentManager

test_bp = Blueprint('test', __name__)

# Initialiser le gestionnaire d'agent
agent_manager = SageAgentManager()

@test_bp.route('/test/agent', methods=['POST'])
def test_agent():
    """Endpoint de test pour l'agent IA sans authentification"""
    try:
        data = request.json
        
        if not data or not data.get('message'):
            return jsonify({'error': 'Message requis'}), 400
        
        user_message = data.get('message')
        
        # Test simple avec l'agent support qui ne nécessite pas de credentials Sage
        try:
            # Utiliser l'agent support pour répondre
            response = agent_manager.process_user_message(
                user_message=user_message,
                credentials=None,  # Pas de credentials pour le test
                business_id=None
            )
            
            return jsonify({
                'response': response.get('response', 'Réponse de test de l\'agent IA'),
                'agent_used': response.get('agent_used', 'support'),
                'status': 'success'
            }), 200
            
        except Exception as e:
            # Si l'agent ne fonctionne pas, retourner une réponse de test
            return jsonify({
                'response': f'Bonjour ! Je suis votre assistant comptable IA. Mes capacités incluent :\n\n• Gestion des clients et fournisseurs\n• Création et suivi des factures\n• Analyses financières (bilan, compte de résultat)\n• Calcul des KPIs\n• Recherche de transactions\n• Support et aide technique\n\nPour utiliser toutes mes fonctionnalités, veuillez connecter votre compte Sage Business Cloud Accounting.\n\nErreur technique: {str(e)}',
                'agent_used': 'fallback',
                'status': 'fallback'
            }), 200
            
    except Exception as e:
        return jsonify({'error': f'Erreur lors du test: {str(e)}'}), 500

