"""
Migration pour ajouter la table des fichiers attachés
Exécuter avec: python migrations/add_file_attachments.py
"""

from src.models.user import db, FileAttachment
from src.main import app

def upgrade():
    """Ajouter la table file_attachments"""
    with app.app_context():
        try:
            # Créer la table FileAttachment
            db.create_all()
            print("✅ Table file_attachments créée avec succès")
            
            # Vérifier que la table existe
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            
            if 'file_attachments' in tables:
                print("✅ Vérification: table file_attachments présente")
                
                # Afficher les colonnes
                columns = inspector.get_columns('file_attachments')
                print("📋 Colonnes de la table:")
                for column in columns:
                    print(f"  - {column['name']}: {column['type']}")
            else:
                print("❌ Erreur: table file_attachments non trouvée")
                
        except Exception as e:
            print(f"❌ Erreur lors de la migration: {str(e)}")

def downgrade():
    """Supprimer la table file_attachments"""
    with app.app_context():
        try:
            FileAttachment.__table__.drop(db.engine)
            print("✅ Table file_attachments supprimée")
        except Exception as e:
            print(f"❌ Erreur lors du rollback: {str(e)}")

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'downgrade':
        downgrade()
    else:
        upgrade()