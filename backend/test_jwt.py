#!/usr/bin/env python3
"""
Script de test pour vérifier la validation JWT
"""
import sys
import os

# Ajouter le répertoire src au path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from flask_jwt_extended import decode_token
from src.main import app

def test_jwt_token(token):
    """Tester la validation d'un token JWT"""
    with app.app_context():
        try:
            # Décoder le token
            decoded = decode_token(token)
            print("Token valide!")
            print(f"User ID: {decoded['sub']}")
            print(f"Expires: {decoded['exp']}")
            return True
        except Exception as e:
            print(f"Token invalide: {e}")
            return False

if __name__ == '__main__':
    # Token de test
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJmcmVzaCI6ZmFsc2UsImlhdCI6MTc1NjQ3MDc5MywianRpIjoiNDEwN2M5NWQtNGRmNy00YjVhLTk5ODMtYjVmZmI5MTNiNDQ5IiwidHlwZSI6ImFjY2VzcyIsInN1YiI6MSwibmJmIjoxNzU2NDcwNzkzLCJjc3JmIjoiNjcxNmJhZTgtODgyMy00MjJhLTliY2UtOWYzNTZlNjY1ZTgyIiwiZXhwIjoxNzU2NTU3MTkzfQ.i_N_i8px9T4rDcG77smzoze-a4GwRk5AFG77FYbf9Ss"
    
    test_jwt_token(token)

