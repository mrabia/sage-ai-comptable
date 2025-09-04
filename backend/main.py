from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_sqlalchemy import SQLAlchemy
import bcrypt
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['JWT_SECRET_KEY'] = 'jwt-secret-string'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sage_ai.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

CORS(app)
jwt = JWTManager(app)
db = SQLAlchemy(app)

# User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    name = db.Column(db.String(100), nullable=False)

    def set_password(self, password):
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def check_password(self, password):
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))

# Routes
@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "message": "Sage AI Backend is running"})

@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json()
    
    if User.query.filter_by(email=data['email']).first():
        return jsonify({"error": "Email already exists"}), 400
    
    user = User(email=data['email'], name=data['name'])
    user.set_password(data['password'])
    
    db.session.add(user)
    db.session.commit()
    
    access_token = create_access_token(identity=user.id)
    return jsonify({"access_token": access_token, "user": {"id": user.id, "email": user.email, "name": user.name}})

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(email=data['email']).first()
    
    if user and user.check_password(data['password']):
        access_token = create_access_token(identity=user.id)
        return jsonify({"access_token": access_token, "user": {"id": user.id, "email": user.email, "name": user.name}})
    
    return jsonify({"error": "Invalid credentials"}), 401

@app.route('/api/chat', methods=['POST'])
@jwt_required()
def chat():
    data = request.get_json()
    message = data.get('message', '')
    
    # Simple response for now
    response = f"Bonjour ! Vous avez dit: '{message}'. L'agent IA comptable est en cours de développement."
    
    return jsonify({
        "response": response,
        "suggestions": [
            "Créer un nouveau client",
            "Générer une facture",
            "Consulter le bilan",
            "Analyser des documents"
        ]
    })

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Create test user if not exists
        if not User.query.filter_by(email='test@example.com').first():
            test_user = User(email='test@example.com', name='Test User')
            test_user.set_password('password123')
            db.session.add(test_user)
            db.session.commit()
    
    app.run(host='0.0.0.0', port=5000, debug=False)
