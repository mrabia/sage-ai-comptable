#!/usr/bin/env python3
"""
Script d'initialisation de la base de données
"""
import sys
import os

# Ajouter le répertoire src au path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.main import app
from src.models.user import db

def init_database():
    """Initialise la base de données avec toutes les tables"""
    with app.app_context():
        try:
            # Supprimer toutes les tables existantes
            db.drop_all()
            print("Tables existantes supprimées")
            
            # Créer toutes les tables
            db.create_all()
            print("Toutes les tables ont été créées avec succès:")
            
            # Lister les tables créées
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            for table in tables:
                print(f"  - {table}")
                
        except Exception as e:
            print(f"Erreur lors de l'initialisation de la base de données: {e}")
            return False
    
    return True

if __name__ == '__main__':
    print("Initialisation de la base de données...")
    if init_database():
        print("Base de données initialisée avec succès!")
    else:
        print("Échec de l'initialisation de la base de données")
        sys.exit(1)

