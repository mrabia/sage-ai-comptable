import os
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Charger les variables d'environnement selon l'environnement
if os.getenv('RAILWAY_ENVIRONMENT'):
    load_dotenv('.env.production')
else:
    load_dotenv()

import sys
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory, Blueprint, jsonify
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
from src.routes.test import test_bp
from src.routes.documents import documents_bp
from src.routes.accounting_data import accounting_data_bp

# Graceful AI loading
AI_ENABLED = False
try:
    from src.routes.ai_agent import ai_agent_bp
    AI_ENABLED = True
    logger.info("AI components loaded successfully")
except ImportError as e:
    logger.warning(f"AI components failed to load: {e}")
    logger.info("Application will run without AI functionality")
    # Create a dummy blueprint for AI routes
    ai_agent_bp = Blueprint('ai_agent_disabled', __name__)
    
    @ai_agent_bp.route('/agent/chat', methods=['POST'])
    def ai_disabled():
        return {'error': 'AI functionality is temporarily unavailable', 'ai_enabled': False}, 503
        
    @ai_agent_bp.route('/agent/status', methods=['GET'])
    def ai_status():
        return {'ai_enabled': False, 'message': 'AI components not available'}, 200
except Exception as e:
    logger.error(f"Unexpected error loading AI components: {e}")
    AI_ENABLED = False

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

# Configuration de la base de données - SQLite uniquement
database_dir = os.path.join(os.path.dirname(__file__), 'database')
os.makedirs(database_dir, exist_ok=True)
sqlite_path = os.path.join(database_dir, 'app.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{sqlite_path}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

if os.getenv('RAILWAY_ENVIRONMENT'):
    logger.info("🗄️ Using SQLite database (Production on Railway)")
else:
    logger.info("🗄️ Using SQLite database (Local development)")

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
try:
    with app.app_context():
        db.create_all()
        logger.info("✅ Database tables created successfully")
except Exception as e:
    logger.error(f"❌ Database initialization error: {e}")

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
    features = [
        'Sage Business Cloud Integration',
        'Document Processing (PDF, Images, CSV, Excel)',
        'OCR and Invoice Extraction',
        'Automated Data Import'
    ]
    
    if AI_ENABLED:
        features.append('AI Agent with CrewAI')
    
    try:
        # Test database connection
        with app.app_context():
            result = db.engine.execute('SELECT 1')
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return {
        'status': 'healthy',
        'message': 'API Sage AI Comptable opérationnelle',
        'version': '1.0.0',
        'environment': 'production' if os.getenv('RAILWAY_ENVIRONMENT') else 'development',
        'ai_enabled': AI_ENABLED,
        'database_type': 'SQLite',
        'database_status': db_status,
        'features': features
    }, 200

# Simple API root endpoint
@app.route('/api', methods=['GET'])
def api_root():
    endpoints = {
        'health': '/api/health',
        'auth': '/api/auth/*',
        'users': '/api/user/*',
        'conversations': '/api/conversations/*',
        'sage': '/api/sage/*',
        'documents': '/api/documents/*',
        'accounting': '/api/accounting-data/*'
    }
    
    if AI_ENABLED:
        endpoints['ai_agent'] = '/api/ai-agent/*'
    
    return {
        'message': 'Sage AI Comptable API',
        'version': '1.0.0',
        'status': 'running',
        'ai_enabled': AI_ENABLED,
        'database_type': 'SQLite',
        'endpoints': endpoints
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
                'ai_enabled': AI_ENABLED,
                'database_type': 'SQLite',
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
                'ai_enabled': AI_ENABLED,
                'database_type': 'SQLite',
                'api_endpoint': '/api'
            })

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true' and not os.getenv('RAILWAY_ENVIRONMENT')
    
    logger.info(f"🚀 Starting Sage AI Comptable on port {port}")
    logger.info(f"🔧 Debug mode: {debug}")
    logger.info(f"🌍 Environment: {'production' if os.getenv('RAILWAY_ENVIRONMENT') else 'development'}")
    logger.info(f"🤖 AI Agent: {'✅ Available' if AI_ENABLED else '❌ Unavailable'}")
    # Test routes are always enabled in this version
    TEST_ROUTES_ENABLED = True
    logger.info(f"🧪 Test Routes: {'✅ Available' if TEST_ROUTES_ENABLED else '❌ Unavailable'}")
    logger.info(f"🗄️ Database: SQLite")
    
    app.run(host='0.0.0.0', port=port, debug=debug)