from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from datetime import datetime, timedelta
from src.models.user import User, AuditLog, db

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    """Inscription d'un nouvel utilisateur"""
    try:
        data = request.json
        
        # Validation des données
        if not data.get('username') or not data.get('email') or not data.get('password'):
            return jsonify({'error': 'Username, email et password sont requis'}), 400
        
        # Vérifier si l'utilisateur existe déjà
        if User.query.filter_by(username=data['username']).first():
            return jsonify({'error': 'Ce nom d\'utilisateur existe déjà'}), 400
        
        if User.query.filter_by(email=data['email']).first():
            return jsonify({'error': 'Cette adresse email existe déjà'}), 400
        
        # Créer le nouvel utilisateur
        user = User(
            username=data['username'],
            email=data['email']
        )
        user.set_password(data['password'])
        
        db.session.add(user)
        db.session.commit()
        
        # Log de l'inscription
        audit_log = AuditLog(
            user_id=user.id,
            action='user_registration',
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        audit_log.set_details({
            'username': user.username,
            'email': user.email
        })
        db.session.add(audit_log)
        db.session.commit()
        
        return jsonify({
            'message': 'Utilisateur créé avec succès',
            'user': user.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erreur lors de l\'inscription: {str(e)}'}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    """Connexion utilisateur"""
    try:
        data = request.json
        
        # Accepter soit email soit username
        identifier = data.get('email') or data.get('username')
        password = data.get('password')
        
        if not identifier or not password:
            return jsonify({'error': 'Email/Username et password sont requis'}), 400
        
        # Trouver l'utilisateur par email ou username
        user = User.query.filter(
            (User.email == identifier) | (User.username == identifier)
        ).first()
        
        if not user or not user.check_password(password):
            # Log de tentative de connexion échouée
            if user:
                audit_log = AuditLog(
                    user_id=user.id,
                    action='failed_login_attempt',
                    ip_address=request.remote_addr,
                    user_agent=request.headers.get('User-Agent')
                )
                db.session.add(audit_log)
                db.session.commit()
            
            return jsonify({'error': 'Identifiants invalides'}), 401
        
        if not user.is_active:
            return jsonify({'error': 'Compte désactivé'}), 401
        
        # Créer le token JWT
        access_token = create_access_token(
            identity=str(user.id),  # Convertir en string
            expires_delta=timedelta(hours=24)
        )
        
        # Mettre à jour la dernière connexion
        user.last_login = datetime.utcnow()
        
        # Log de connexion réussie
        audit_log = AuditLog(
            user_id=user.id,
            action='successful_login',
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        db.session.add(audit_log)
        db.session.commit()
        
        return jsonify({
            'access_token': access_token,
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Erreur lors de la connexion: {str(e)}'}), 500

@auth_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """Récupérer le profil de l'utilisateur connecté"""
    try:
        user_id = int(get_jwt_identity())  # Convertir en int
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'Utilisateur non trouvé'}), 404
        
        return jsonify(user.to_dict()), 200
        
    except Exception as e:
        return jsonify({'error': f'Erreur lors de la récupération du profil: {str(e)}'}), 500

@auth_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    """Mettre à jour le profil de l'utilisateur connecté"""
    try:
        user_id = int(get_jwt_identity())  # Convertir en int
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'Utilisateur non trouvé'}), 404
        
        data = request.json
        
        # Mettre à jour les champs autorisés
        if 'email' in data:
            # Vérifier que l'email n'est pas déjà utilisé
            existing_user = User.query.filter_by(email=data['email']).first()
            if existing_user and existing_user.id != user.id:
                return jsonify({'error': 'Cette adresse email est déjà utilisée'}), 400
            user.email = data['email']
        
        if 'username' in data:
            # Vérifier que le username n'est pas déjà utilisé
            existing_user = User.query.filter_by(username=data['username']).first()
            if existing_user and existing_user.id != user.id:
                return jsonify({'error': 'Ce nom d\'utilisateur est déjà utilisé'}), 400
            user.username = data['username']
        
        # Log de modification du profil
        audit_log = AuditLog(
            user_id=user.id,
            action='profile_update',
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        audit_log.set_details({
            'updated_fields': list(data.keys())
        })
        db.session.add(audit_log)
        db.session.commit()
        
        return jsonify(user.to_dict()), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erreur lors de la mise à jour: {str(e)}'}), 500

@auth_bp.route('/change-password', methods=['POST'])
@jwt_required()
def change_password():
    """Changer le mot de passe de l'utilisateur connecté"""
    try:
        user_id = int(get_jwt_identity())  # Convertir en int
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'Utilisateur non trouvé'}), 404
        
        data = request.json
        
        if not data.get('current_password') or not data.get('new_password'):
            return jsonify({'error': 'Mot de passe actuel et nouveau mot de passe requis'}), 400
        
        # Vérifier le mot de passe actuel
        if not user.check_password(data['current_password']):
            return jsonify({'error': 'Mot de passe actuel incorrect'}), 400
        
        # Mettre à jour le mot de passe
        user.set_password(data['new_password'])
        
        # Log de changement de mot de passe
        audit_log = AuditLog(
            user_id=user.id,
            action='password_change',
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        db.session.add(audit_log)
        db.session.commit()
        
        return jsonify({'message': 'Mot de passe modifié avec succès'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erreur lors du changement de mot de passe: {str(e)}'}), 500

@auth_bp.route('/sage-credentials', methods=['POST'])
@jwt_required()
def save_sage_credentials():
    """Sauvegarder les credentials Sage de l'utilisateur"""
    try:
        user_id = int(get_jwt_identity())  # Convertir en int
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'Utilisateur non trouvé'}), 404
        
        data = request.json
        
        if not data.get('client_id') or not data.get('client_secret'):
            return jsonify({'error': 'Client ID et Client Secret Sage requis'}), 400
        
        # Sauvegarder les credentials (TODO: chiffrement)
        user.set_sage_credentials({
            'client_id': data['client_id'],
            'client_secret': data['client_secret'],
            'access_token': data.get('access_token'),
            'refresh_token': data.get('refresh_token'),
            'expires_at': data.get('expires_at')
        })
        
        # Log de sauvegarde des credentials
        audit_log = AuditLog(
            user_id=user.id,
            action='sage_credentials_saved',
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        db.session.add(audit_log)
        db.session.commit()
        
        return jsonify({'message': 'Credentials Sage sauvegardés avec succès'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erreur lors de la sauvegarde: {str(e)}'}), 500

@auth_bp.route('/sage-credentials', methods=['GET'])
@jwt_required()
def get_sage_credentials():
    """Récupérer les credentials Sage de l'utilisateur"""
    try:
        user_id = int(get_jwt_identity())  # Convertir en int
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'Utilisateur non trouvé'}), 404
        
        credentials = user.get_sage_credentials()
        
        if not credentials:
            return jsonify({'has_credentials': False}), 200
        
        # Ne pas retourner les secrets, juste confirmer leur existence
        return jsonify({
            'has_credentials': True,
            'client_id': credentials.get('client_id', '').replace(credentials.get('client_id', '')[4:-4], '*' * 8) if credentials.get('client_id') else None,
            'has_access_token': bool(credentials.get('access_token')),
            'expires_at': credentials.get('expires_at')
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Erreur lors de la récupération: {str(e)}'}), 500

