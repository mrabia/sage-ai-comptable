import os
from dotenv import load_dotenv

# Charger les variables d'environnement selon l'environnement
if os.getenv('RAILWAY_ENVIRONMENT'):
    load_dotenv('.env.production')
else:
    load_dotenv()

import sys
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from src.models.user import db
from src.models.document import Document  # Import du modèle Document
from src.models.accounting_data import BankTransaction, TVAClient  # Import des modèles comptables
from src.routes.user import user_bp
from src.routes.auth import auth_bp
from src.routes.conversations import conversations_bp
from src.routes.sage_operations import sage_operations_bp
from src.routes.sage_auth import sage_auth_bp
from src.routes.sage_api import sage_api_bp
from src.routes.ai_agent import ai_agent_bp
from src.routes.test import test_bp
from src.routes.documents import documents_bp
from src.routes.accounting_data import accounting_data_bp

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))

# Configuration
app.config['SECRET_KEY'] = 'asdf#FGSgvasgf$5$WGT'  # TODO: Utiliser une clé secrète plus sécurisée
app.config['JWT_SECRET_KEY'] = 'jwt-secret-string'  # TODO: Utiliser une clé JWT sécurisée

# Configuration pour les uploads de fichiers
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')

# Créer le dossier uploads s'il n'existe pas
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Configuration de session pour OAuth2
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True

# Configuration CORS pour Railway
cors_origins = ["*"]
if os.getenv('RAILWAY_STATIC_URL'):
    cors_origins.append(os.getenv('RAILWAY_STATIC_URL'))
if os.getenv('CORS_ORIGINS'):
    cors_origins.extend(os.getenv('CORS_ORIGINS').split(','))

CORS(app, 
     origins=cors_origins,
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
     allow_headers=["Content-Type", "Authorization"],
     supports_credentials=True)

# Configuration JWT
jwt = JWTManager(app)

# Configuration de la base de données
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(os.path.dirname(__file__), 'database', 'app.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialisation de la base de données
db.init_app(app)

# Enregistrement des blueprints
app.register_blueprint(user_bp, url_prefix='/api')
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(conversations_bp, url_prefix='/api')
app.register_blueprint(sage_operations_bp, url_prefix='/api')
app.register_blueprint(sage_auth_bp, url_prefix='/api')
app.register_blueprint(sage_api_bp, url_prefix='/api')
app.register_blueprint(ai_agent_bp, url_prefix='/api')
app.register_blueprint(test_bp, url_prefix='/api')
app.register_blueprint(documents_bp, url_prefix='/api')
app.register_blueprint(accounting_data_bp, url_prefix='/api')

# Création des tables de base de données
with app.app_context():
    db.create_all()

# Gestionnaire d'erreur JWT
@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_payload):
    return {'error': 'Token expiré'}, 401

@jwt.invalid_token_loader
def invalid_token_callback(error):
    return {'error': 'Token invalide'}, 401

@jwt.unauthorized_loader
def missing_token_callback(error):
    return {'error': 'Token d\'autorisation requis'}, 401

# Route de santé pour vérifier que l'API fonctionne
@app.route('/api/health', methods=['GET'])
def health_check():
    return {
        'status': 'healthy',
        'message': 'API Sage AI Comptable opérationnelle',
        'version': '1.0.0',
        'features': [
            'Sage Business Cloud Integration',
            'AI Agent with CrewAI',
            'Document Processing (PDF, Images, CSV, Excel)',
            'OCR and Invoice Extraction',
            'Automated Data Import'
        ]
    }, 200

# Routes pour servir le frontend
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    static_folder_path = app.static_folder
    if static_folder_path is None:
        return "Static folder not configured", 404

    if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
        return send_from_directory(static_folder_path, path)
    else:
        index_path = os.path.join(static_folder_path, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(static_folder_path, 'index.html')
        else:
            return "index.html not found", 404

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug)
