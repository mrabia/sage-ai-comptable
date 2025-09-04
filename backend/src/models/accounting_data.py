from src.models.user import db
from datetime import datetime
import json

class BankTransaction(db.Model):
    """Modèle pour les transactions bancaires"""
    __tablename__ = 'bank_transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    compte_general = db.Column(db.String(20), nullable=False)  # Compte général
    role_tiers = db.Column(db.String(100), nullable=True)  # Rôle tiers
    date_ecriture = db.Column(db.Date, nullable=False)  # Date écriture
    numero_piece = db.Column(db.String(50), nullable=False)  # N° pièce
    date_reference = db.Column(db.Date, nullable=True)  # Date de référence
    libelle = db.Column(db.Text, nullable=False)  # Libellé
    devise = db.Column(db.String(10), nullable=False)  # Devise
    montant_tr = db.Column(db.Numeric(15, 2), nullable=False)  # Montant TR (MAD)
    montant_tc = db.Column(db.Numeric(15, 2), nullable=False)  # Montant TC
    montant_signe_tc = db.Column(db.Numeric(15, 2), nullable=False)  # Montant signé TC
    sens = db.Column(db.String(10), nullable=False)  # Sens (Débit/Crédit)
    bq = db.Column(db.Numeric(15, 2), nullable=True)  # bq
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'compte_general': self.compte_general,
            'role_tiers': self.role_tiers,
            'date_ecriture': self.date_ecriture.isoformat() if self.date_ecriture else None,
            'numero_piece': self.numero_piece,
            'date_reference': self.date_reference.isoformat() if self.date_reference else None,
            'libelle': self.libelle,
            'devise': self.devise,
            'montant_tr': float(self.montant_tr) if self.montant_tr else 0,
            'montant_tc': float(self.montant_tc) if self.montant_tc else 0,
            'montant_signe_tc': float(self.montant_signe_tc) if self.montant_signe_tc else 0,
            'sens': self.sens,
            'bq': float(self.bq) if self.bq else 0,
            'created_at': self.created_at.isoformat()
        }

class TVAClient(db.Model):
    """Modèle pour les déclarations TVA collectée clients"""
    __tablename__ = 'tva_clients'
    
    id = db.Column(db.Integer, primary_key=True)
    code_compte = db.Column(db.String(20), nullable=False)  # Code Compte
    reference_piece = db.Column(db.String(50), nullable=True)  # Référence pièce
    libelle_compte = db.Column(db.String(200), nullable=True)  # Libellé Compte
    reference_piece_2 = db.Column(db.String(50), nullable=True)  # Référence pièce (2ème colonne)
    date_ecriture = db.Column(db.Date, nullable=True)  # Date écriture
    journal = db.Column(db.String(20), nullable=True)  # Journal
    numero_piece = db.Column(db.String(50), nullable=True)  # Numéro de pièce
    libelle_ecriture = db.Column(db.Text, nullable=True)  # Libellé écriture
    reference_piece_3 = db.Column(db.String(50), nullable=True)  # Référence pièce (3ème colonne)
    lettrage = db.Column(db.String(20), nullable=True)  # Lettrage
    type_ecriture = db.Column(db.String(10), nullable=True)  # Type écriture
    debit = db.Column(db.Numeric(15, 2), nullable=True, default=0)  # Débit
    credit = db.Column(db.Numeric(15, 2), nullable=True, default=0)  # Crédit
    solde = db.Column(db.Numeric(15, 2), nullable=True, default=0)  # Solde
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'code_compte': self.code_compte,
            'reference_piece': self.reference_piece,
            'libelle_compte': self.libelle_compte,
            'reference_piece_2': self.reference_piece_2,
            'date_ecriture': self.date_ecriture.isoformat() if self.date_ecriture else None,
            'journal': self.journal,
            'numero_piece': self.numero_piece,
            'libelle_ecriture': self.libelle_ecriture,
            'reference_piece_3': self.reference_piece_3,
            'lettrage': self.lettrage,
            'type_ecriture': self.type_ecriture,
            'debit': float(self.debit) if self.debit else 0,
            'credit': float(self.credit) if self.credit else 0,
            'solde': float(self.solde) if self.solde else 0,
            'created_at': self.created_at.isoformat()
        }

