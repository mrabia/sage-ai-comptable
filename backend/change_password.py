import sys
sys.path.insert(0, '.')
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import bcrypt

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sage_ai.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    name = db.Column(db.String(100), nullable=False)

    def set_password(self, password):
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

with app.app_context():
    user = User.query.filter_by(email='test@example.com').first()
    if user:
        user.set_password('Sageuser2025')
        db.session.commit()
        print("Mot de passe changé avec succès pour test@example.com")
    else:
        print("Utilisateur test@example.com non trouvé")
