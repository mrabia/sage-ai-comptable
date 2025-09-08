from flask import Blueprint, jsonify, request, redirect, session
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.models.user import User, AuditLog, db
from src.services.sage_auth import SageOAuth2Service
import os
from urllib.parse import parse_qs, urlparse

sage_auth_bp = Blueprint('sage_auth', __name__)

# Configuration OAuth2 Sage (à mettre dans les variables d'environnement)
SAGE_CLIENT_ID = os.getenv('SAGE_CLIENT_ID', 'your_sage_client_id')
SAGE_CLIENT_SECRET = os.getenv('SAGE_CLIENT_SECRET', 'your_sage_client_secret')
SAGE_REDIRECT_URI = os.getenv('SAGE_REDIRECT_URI', 'http://localhost:5000/api/sage/callback')

# Initialiser le service OAuth2
sage_oauth = SageOAuth2Service(SAGE_CLIENT_ID, SAGE_CLIENT_SECRET, SAGE_REDIRECT_URI)

@sage_auth_bp.route('/sage/auth/start', methods=['POST'])
@jwt_required()
def start_sage_auth():
    """Démarre le processus d'authentification OAuth2 avec Sage"""
    try:
        user_id = get_jwt_identity()
        data = request.json or {}
        
        # Paramètres optionnels
        scope = data.get('scope', 'full_access')
        country = data.get('country')  # 'gb', 'fr', 'ie', etc.
        
        # Générer l'URL d'autorisation
        auth_url, state, code_verifier = sage_oauth.get_authorization_url(
            scope=scope,
            country=country
        )
        
        # Stocker temporairement le state et code_verifier dans la base de données
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'Utilisateur non trouvé'}), 404
        
        # Stocker les données OAuth temporaires avec expiration (10 minutes)
        from datetime import datetime, timedelta
        user.oauth_state = state
        user.oauth_code_verifier = code_verifier
        user.oauth_expires_at = datetime.utcnow() + timedelta(minutes=10)
        db.session.commit()
        
        # Log de début d'authentification
        audit_log = AuditLog(
            user_id=user_id,
            action='sage_auth_started',
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        audit_log.set_details({
            'scope': scope,
            'country': country
        })
        db.session.add(audit_log)
        db.session.commit()
        
        return jsonify({
            'authorization_url': auth_url,
            'state': state
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Erreur lors du démarrage de l\'authentification: {str(e)}'}), 500

@sage_auth_bp.route('/sage/callback', methods=['GET'])
def sage_callback():
    """Callback OAuth2 de Sage"""
    try:
        # Récupérer les paramètres du callback
        code = request.args.get('code')
        state = request.args.get('state')
        country = request.args.get('country')
        error = request.args.get('error')
        
        if error:
            return jsonify({'error': f'Erreur d\'autorisation Sage: {error}'}), 400
        
        if not code or not state:
            return jsonify({'error': 'Paramètres manquants dans le callback'}), 400
        
        # Trouver l'utilisateur correspondant au state
        from datetime import datetime
        user = User.query.filter(
            User.oauth_state == state,
            User.oauth_expires_at > datetime.utcnow()
        ).first()
        
        if not user:
            return jsonify({'error': 'Session invalide ou expirée'}), 400
        
        user_id = user.id
        code_verifier = user.oauth_code_verifier
        
        # Échanger le code contre un token d'accès
        token_data = sage_oauth.exchange_code_for_token(code, code_verifier)
        
        # Sauvegarder les credentials Sage
        user.set_sage_credentials({
            'access_token': token_data.get('access_token'),
            'refresh_token': token_data.get('refresh_token'),
            'expires_at': token_data.get('expires_at'),
            'token_type': token_data.get('token_type', 'Bearer'),
            'scope': token_data.get('scope'),
            'country': country
        })
        
        # Nettoyer les données OAuth temporaires
        user.oauth_state = None
        user.oauth_code_verifier = None
        user.oauth_expires_at = None
        
        # Log de succès d'authentification
        audit_log = AuditLog(
            user_id=int(user_id),
            action='sage_auth_completed',
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        audit_log.set_details({
            'country': country,
            'scope': token_data.get('scope')
        })
        db.session.add(audit_log)
        db.session.commit()
        
        # Rediriger vers le frontend avec un message de succès
        frontend_url = os.getenv('FRONTEND_URL', 'https://sage-ai-comptable-production.up.railway.app')
        return redirect(f"{frontend_url}?sage_auth=success")
        
    except Exception as e:
        return jsonify({'error': f'Erreur lors du callback Sage: {str(e)}'}), 500

@sage_auth_bp.route('/sage/status', methods=['GET'])
@jwt_required()
def sage_auth_status():
    """Vérifie le statut de l'authentification Sage"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'Utilisateur non trouvé'}), 404
        
        credentials = user.get_sage_credentials()
        
        if not credentials:
            return jsonify({
                'authenticated': False,
                'message': 'Aucune authentification Sage configurée'
            }), 200
        
        # Tester la connexion
        is_valid = sage_oauth.test_connection(credentials)
        
        if is_valid:
            # Récupérer les businesses de l'utilisateur
            try:
                businesses = sage_oauth.get_user_businesses(credentials)
                return jsonify({
                    'authenticated': True,
                    'country': credentials.get('country'),
                    'scope': credentials.get('scope'),
                    'businesses': businesses,
                    'expires_at': credentials.get('expires_at')
                }), 200
            except Exception as e:
                return jsonify({
                    'authenticated': False,
                    'error': f'Erreur lors de la récupération des businesses: {str(e)}'
                }), 400
        else:
            # Token invalide - nettoyer les credentials pour forcer une nouvelle authentification
            user.sage_credentials_encrypted = None
            db.session.commit()
            
            return jsonify({
                'authenticated': False,
                'message': 'Token Sage expiré ou invalide - veuillez vous reconnecter',
                'require_reconnect': True
            }), 200
        
    except Exception as e:
        return jsonify({'error': f'Erreur lors de la vérification du statut: {str(e)}'}), 500

@sage_auth_bp.route('/sage/disconnect', methods=['POST'])
@jwt_required()
def disconnect_sage():
    """Déconnecte l'utilisateur de Sage"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'Utilisateur non trouvé'}), 404
        
        # Supprimer les credentials Sage
        user.sage_credentials_encrypted = None
        
        # Log de déconnexion
        audit_log = AuditLog(
            user_id=user_id,
            action='sage_disconnected',
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        db.session.add(audit_log)
        db.session.commit()
        
        return jsonify({'message': 'Déconnexion de Sage réussie'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erreur lors de la déconnexion: {str(e)}'}), 500

@sage_auth_bp.route('/sage/refresh-token', methods=['POST'])
@jwt_required()
def refresh_sage_token():
    """Rafraîchit manuellement le token Sage"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'Utilisateur non trouvé'}), 404
        
        credentials = user.get_sage_credentials()
        if not credentials or not credentials.get('refresh_token'):
            return jsonify({'error': 'Aucun refresh token disponible'}), 400
        
        # Rafraîchir le token
        new_token_data = sage_oauth.refresh_access_token(credentials['refresh_token'])
        
        # Mettre à jour les credentials
        credentials.update({
            'access_token': new_token_data.get('access_token'),
            'refresh_token': new_token_data.get('refresh_token', credentials['refresh_token']),
            'expires_at': new_token_data.get('expires_at')
        })
        
        user.set_sage_credentials(credentials)
        
        # Log de rafraîchissement
        audit_log = AuditLog(
            user_id=user_id,
            action='sage_token_refreshed',
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        db.session.add(audit_log)
        db.session.commit()
        
        return jsonify({
            'message': 'Token rafraîchi avec succès',
            'expires_at': new_token_data.get('expires_at')
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erreur lors du rafraîchissement: {str(e)}'}), 500

