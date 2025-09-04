#!/usr/bin/env python3
"""
Script d'import des données comptables réelles
"""

import csv
import sys
import os
from datetime import datetime
from decimal import Decimal, InvalidOperation

# Ajouter le répertoire src au path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from models.user import db
from models.accounting_data import BankTransaction, TVAClient
from main import app

def parse_date(date_str):
    """Parse une date au format YYYY-MM-DD"""
    if not date_str or date_str.strip() == '':
        return None
    try:
        return datetime.strptime(date_str.strip(), '%Y-%m-%d').date()
    except ValueError:
        print(f"Erreur de format de date: {date_str}")
        return None

def parse_decimal(value_str):
    """Parse un nombre décimal"""
    if not value_str or value_str.strip() == '':
        return Decimal('0')
    try:
        # Remplacer les virgules par des points pour les décimaux
        clean_value = value_str.strip().replace(',', '.')
        return Decimal(clean_value)
    except (InvalidOperation, ValueError):
        print(f"Erreur de format numérique: {value_str}")
        return Decimal('0')

def import_bank_transactions():
    """Importer les transactions bancaires"""
    print("Import des transactions bancaires...")
    
    file_path = '/home/ubuntu/upload/banque.csv'
    
    try:
        with open(file_path, 'r', encoding='iso-8859-1') as file:
            # Lire le fichier avec le délimiteur point-virgule
            reader = csv.DictReader(file, delimiter=';')
            
            count = 0
            for row in reader:
                try:
                    transaction = BankTransaction(
                        compte_general=row.get('Compte général', '').strip(),
                        role_tiers=row.get('Rôle tiers', '').strip() or None,
                        date_ecriture=parse_date(row.get('Date écriture', '')),
                        numero_piece=row.get('N° pièce', '').strip(),
                        date_reference=parse_date(row.get('Date de référence', '')),
                        libelle=row.get('Libellé', '').strip(),
                        devise=row.get('Devise', '').strip(),
                        montant_tr=parse_decimal(row.get('Montant TR (MAD)', '0')),
                        montant_tc=parse_decimal(row.get('Montant TC', '0')),
                        montant_signe_tc=parse_decimal(row.get('Montant signé TC', '0')),
                        sens=row.get('Sens', '').strip(),
                        bq=parse_decimal(row.get('bq', '0'))
                    )
                    
                    db.session.add(transaction)
                    count += 1
                    
                    if count % 100 == 0:
                        db.session.commit()
                        print(f"Importé {count} transactions bancaires...")
                        
                except Exception as e:
                    print(f"Erreur lors de l'import de la ligne: {row}")
                    print(f"Erreur: {e}")
                    continue
            
            db.session.commit()
            print(f"Import terminé: {count} transactions bancaires importées")
            
    except Exception as e:
        print(f"Erreur lors de l'ouverture du fichier: {e}")
        db.session.rollback()

def import_tva_clients():
    """Importer les données TVA clients"""
    print("Import des données TVA clients...")
    
    file_path = '/home/ubuntu/upload/déclarationtvacollectéeclientsmai2025.csv'
    
    try:
        with open(file_path, 'r', encoding='iso-8859-1') as file:
            # Lire le fichier avec le délimiteur point-virgule
            reader = csv.DictReader(file, delimiter=';')
            
            count = 0
            for row in reader:
                try:
                    tva_client = TVAClient(
                        code_compte=row.get('Code Compte', '').strip(),
                        reference_piece=row.get('Référence pièce', '').strip() or None,
                        libelle_compte=row.get('Libellé Compte', '').strip() or None,
                        reference_piece_2=row.get('Référence pièce', '').strip() or None,  # 2ème colonne
                        date_ecriture=parse_date(row.get('Date écriture', '')),
                        journal=row.get('Journal', '').strip() or None,
                        numero_piece=row.get('Numéro de pièce', '').strip() or None,
                        libelle_ecriture=row.get('Libellé écriture', '').strip() or None,
                        reference_piece_3=row.get('Référence pièce', '').strip() or None,  # 3ème colonne
                        lettrage=row.get('Lettrage', '').strip() or None,
                        type_ecriture=row.get('Type écriture', '').strip() or None,
                        debit=parse_decimal(row.get('Débit', '0')),
                        credit=parse_decimal(row.get('Crédit', '0')),
                        solde=parse_decimal(row.get('Solde', '0'))
                    )
                    
                    db.session.add(tva_client)
                    count += 1
                    
                    if count % 100 == 0:
                        db.session.commit()
                        print(f"Importé {count} enregistrements TVA...")
                        
                except Exception as e:
                    print(f"Erreur lors de l'import de la ligne: {row}")
                    print(f"Erreur: {e}")
                    continue
            
            db.session.commit()
            print(f"Import terminé: {count} enregistrements TVA importés")
            
    except Exception as e:
        print(f"Erreur lors de l'ouverture du fichier: {e}")
        db.session.rollback()

def main():
    """Fonction principale d'import"""
    print("Début de l'import des données comptables réelles...")
    
    with app.app_context():
        # Créer les tables si elles n'existent pas
        db.create_all()
        
        # Vider les tables existantes
        print("Suppression des données existantes...")
        BankTransaction.query.delete()
        TVAClient.query.delete()
        db.session.commit()
        
        # Importer les données
        import_bank_transactions()
        import_tva_clients()
        
        # Afficher les statistiques
        bank_count = BankTransaction.query.count()
        tva_count = TVAClient.query.count()
        
        print(f"\n=== IMPORT TERMINÉ ===")
        print(f"Transactions bancaires: {bank_count}")
        print(f"Enregistrements TVA: {tva_count}")
        print(f"Total: {bank_count + tva_count} enregistrements")

if __name__ == '__main__':
    main()

