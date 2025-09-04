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

from flask import Flask, send_from_directory, jsonify
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
# Temporarily comment out ai_agent import to fix deployment
# from src.routes.ai_agent import ai_agent_bp
from src.routes.test import test_bp
from src.routes.documents import documents_bp
from src.routes.accounting_data import accounting_data_bp

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))

# Configuration with environment variables for security
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'asdf#FGSgvasgf$5$WGT')
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'jwt-secret-string')

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

# Configuration de la base de données - PostgreSQL for Railway, SQLite for local
if os.environ.get('DATABASE_URL'):
    # Railway PostgreSQL
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
    print("Using Railway PostgreSQL database")
else:
    # Local SQLite
    database_dir = os.path.join(os.path.dirname(__file__), 'database')
    os.makedirs(database_dir, exist_ok=True)
    app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(database_dir, 'app.db')}"
    print("Using local SQLite database")

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

# Temporarily comment out ai_agent blueprint to fix deployment
# app.register_blueprint(ai_agent_bp, url_prefix='/api')
print("AI Agent routes temporarily disabled due to dependency issues")

app.register_blueprint(test_bp, url_prefix='/api')
app.register_blueprint(documents_bp, url_prefix='/api')
app.register_blueprint(accounting_data_bp, url_prefix='/api')

# Création des tables de base de données
try:
    with app.app_context():
        db.create_all()
        print("Database tables created successfully")
except Exception as e:
    print(f"Database initialization error: {e}")

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
    try:
        # Test database connection
        with app.app_context():
            db.engine.execute('SELECT 1')
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return {
        'status': 'healthy',
        'message': 'API Sage AI Comptable opérationnelle',
        'version': '1.0.0',
        'environment': 'production' if os.environ.get('RAILWAY_ENVIRONMENT') else 'development',
        'database_status': db_status,
        'features': [
            'Sage Business Cloud Integration',
            'Document Processing (PDF, Images, CSV, Excel)',
            'OCR and Invoice Extraction', 
            'Automated Data Import',
            'AI Agent (temporarily disabled)'
        ]
    }, 200

# Simple API root endpoint
@app.route('/api', methods=['GET'])
def api_root():
    return {
        'message': 'Sage AI Comptable API',
        'version': '1.0.0',
        'status': 'running',
        'endpoints': {
            'health': '/api/health',
            'auth': '/api/auth/*',
            'users': '/api/user/*',
            'conversations': '/api/conversations/*',
            'sage': '/api/sage/*',
            'documents': '/api/documents/*',
            'accounting': '/api/accounting-data/*'
        }
    }

# Routes pour servir le frontend
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    static_folder_path = app.static_folder
    
    # For Railway, serve a simple message if frontend static files aren't available
    if static_folder_path is None or not os.path.exists(static_folder_path):
        if path == "" or path.startswith('api'):
            return jsonify({
                'message': 'Sage AI Comptable Backend',
                'status': 'running',
                'api_endpoint': '/api',
                'health_check': '/api/health'
            })
        else:
            return "Frontend not available. API is running at /api", 404

    if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
        return send_from_directory(static_folder_path, path)
    else:
        index_path = os.path.join(static_folder_path, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(static_folder_path, 'index.html')
        else:
            return jsonify({
                'message': 'Sage AI Comptable Backend',
                'status': 'running',
                'api_endpoint': '/api'
            })

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true' and not os.getenv('RAILWAY_ENVIRONMENT')
    
    print(f"Starting Sage AI Comptable on port {port}")
    print(f"Debug mode: {debug}")
    print(f"Environment: {'production' if os.getenv('RAILWAY_ENVIRONMENT') else 'development'}")
    
    app.run(host='0.0.0.0', port=port, debug=debug)