#!/usr/bin/env python3
"""
Script d'import simplifié des données comptables
"""

import csv
import sqlite3
from datetime import datetime
from decimal import Decimal, InvalidOperation

def parse_date(date_str):
    """Parse une date au format YYYY-MM-DD"""
    if not date_str or date_str.strip() == '':
        return None
    try:
        return datetime.strptime(date_str.strip(), '%Y-%m-%d').date().isoformat()
    except ValueError:
        print(f"Erreur de format de date: {date_str}")
        return None

def parse_decimal(value_str):
    """Parse un nombre décimal"""
    if not value_str or value_str.strip() == '':
        return 0.0
    try:
        # Remplacer les virgules par des points pour les décimaux
        clean_value = value_str.strip().replace(',', '.')
        return float(clean_value)
    except (ValueError, InvalidOperation):
        print(f"Erreur de format numérique: {value_str}")
        return 0.0

def create_tables(conn):
    """Créer les tables si elles n'existent pas"""
    cursor = conn.cursor()
    
    # Table des transactions bancaires
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bank_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            compte_general VARCHAR(20) NOT NULL,
            role_tiers VARCHAR(100),
            date_ecriture DATE NOT NULL,
            numero_piece VARCHAR(50) NOT NULL,
            date_reference DATE,
            libelle TEXT NOT NULL,
            devise VARCHAR(10) NOT NULL,
            montant_tr DECIMAL(15,2) NOT NULL,
            montant_tc DECIMAL(15,2) NOT NULL,
            montant_signe_tc DECIMAL(15,2) NOT NULL,
            sens VARCHAR(10) NOT NULL,
            bq DECIMAL(15,2),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Table TVA clients
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tva_clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code_compte VARCHAR(20) NOT NULL,
            reference_piece VARCHAR(50),
            libelle_compte VARCHAR(200),
            reference_piece_2 VARCHAR(50),
            date_ecriture DATE,
            journal VARCHAR(20),
            numero_piece VARCHAR(50),
            libelle_ecriture TEXT,
            reference_piece_3 VARCHAR(50),
            lettrage VARCHAR(20),
            type_ecriture VARCHAR(10),
            debit DECIMAL(15,2) DEFAULT 0,
            credit DECIMAL(15,2) DEFAULT 0,
            solde DECIMAL(15,2) DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    print("Tables créées avec succès")

def import_bank_transactions(conn):
    """Importer les transactions bancaires"""
    print("Import des transactions bancaires...")
    
    cursor = conn.cursor()
    
    # Vider la table
    cursor.execute('DELETE FROM bank_transactions')
    
    file_path = '/home/ubuntu/upload/banque.csv'
    
    try:
        with open(file_path, 'r', encoding='iso-8859-1') as file:
            reader = csv.DictReader(file, delimiter=';')
            
            count = 0
            for row in reader:
                try:
                    cursor.execute('''
                        INSERT INTO bank_transactions 
                        (compte_general, role_tiers, date_ecriture, numero_piece, date_reference, 
                         libelle, devise, montant_tr, montant_tc, montant_signe_tc, sens, bq)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        row.get('Compte général', '').strip(),
                        row.get('Rôle tiers', '').strip() or None,
                        parse_date(row.get('Date écriture', '')),
                        row.get('N° pièce', '').strip(),
                        parse_date(row.get('Date de référence', '')),
                        row.get('Libellé', '').strip(),
                        row.get('Devise', '').strip(),
                        parse_decimal(row.get('Montant TR (MAD)', '0')),
                        parse_decimal(row.get('Montant TC', '0')),
                        parse_decimal(row.get('Montant signé TC', '0')),
                        row.get('Sens', '').strip(),
                        parse_decimal(row.get('bq', '0'))
                    ))
                    
                    count += 1
                    
                    if count % 100 == 0:
                        conn.commit()
                        print(f"Importé {count} transactions bancaires...")
                        
                except Exception as e:
                    print(f"Erreur lors de l'import de la ligne: {row}")
                    print(f"Erreur: {e}")
                    continue
            
            conn.commit()
            print(f"Import terminé: {count} transactions bancaires importées")
            
    except Exception as e:
        print(f"Erreur lors de l'ouverture du fichier: {e}")

def import_tva_clients(conn):
    """Importer les données TVA clients"""
    print("Import des données TVA clients...")
    
    cursor = conn.cursor()
    
    # Vider la table
    cursor.execute('DELETE FROM tva_clients')
    
    file_path = '/home/ubuntu/upload/déclarationtvacollectéeclientsmai2025.csv'
    
    try:
        with open(file_path, 'r', encoding='iso-8859-1') as file:
            reader = csv.DictReader(file, delimiter=';')
            
            count = 0
            for row in reader:
                try:
                    cursor.execute('''
                        INSERT INTO tva_clients 
                        (code_compte, reference_piece, libelle_compte, reference_piece_2, date_ecriture,
                         journal, numero_piece, libelle_ecriture, reference_piece_3, lettrage,
                         type_ecriture, debit, credit, solde)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        row.get('Code Compte', '').strip(),
                        row.get('Référence pièce', '').strip() or None,
                        row.get('Libellé Compte', '').strip() or None,
                        row.get('Référence pièce', '').strip() or None,  # 2ème colonne
                        parse_date(row.get('Date écriture', '')),
                        row.get('Journal', '').strip() or None,
                        row.get('Numéro de pièce', '').strip() or None,
                        row.get('Libellé écriture', '').strip() or None,
                        row.get('Référence pièce', '').strip() or None,  # 3ème colonne
                        row.get('Lettrage', '').strip() or None,
                        row.get('Type écriture', '').strip() or None,
                        parse_decimal(row.get('Débit', '0')),
                        parse_decimal(row.get('Crédit', '0')),
                        parse_decimal(row.get('Solde', '0'))
                    ))
                    
                    count += 1
                    
                    if count % 100 == 0:
                        conn.commit()
                        print(f"Importé {count} enregistrements TVA...")
                        
                except Exception as e:
                    print(f"Erreur lors de l'import de la ligne: {row}")
                    print(f"Erreur: {e}")
                    continue
            
            conn.commit()
            print(f"Import terminé: {count} enregistrements TVA importés")
            
    except Exception as e:
        print(f"Erreur lors de l'ouverture du fichier: {e}")

def main():
    """Fonction principale d'import"""
    print("Début de l'import des données comptables réelles...")
    
    # Connexion à la base de données SQLite
    db_path = '/home/ubuntu/sage-ai-comptable/backend/sage-ai-backend/sage_ai.db'
    conn = sqlite3.connect(db_path)
    
    try:
        # Créer les tables
        create_tables(conn)
        
        # Importer les données
        import_bank_transactions(conn)
        import_tva_clients(conn)
        
        # Afficher les statistiques
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM bank_transactions')
        bank_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM tva_clients')
        tva_count = cursor.fetchone()[0]
        
        print(f"\n=== IMPORT TERMINÉ ===")
        print(f"Transactions bancaires: {bank_count}")
        print(f"Enregistrements TVA: {tva_count}")
        print(f"Total: {bank_count + tva_count} enregistrements")
        
    finally:
        conn.close()

if __name__ == '__main__':
    main()

