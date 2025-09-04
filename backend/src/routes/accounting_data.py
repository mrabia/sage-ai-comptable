from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.models.accounting_data import BankTransaction, TVAClient
from src.models.user import db
from datetime import datetime
from sqlalchemy import func, and_, or_

accounting_data_bp = Blueprint('accounting_data', __name__)

@accounting_data_bp.route('/accounting/bank-transactions', methods=['GET'])
@jwt_required()
def get_bank_transactions():
    """Récupère les transactions bancaires avec filtres optionnels"""
    try:
        # Paramètres de pagination
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 50, type=int), 100)
        
        # Paramètres de filtrage
        compte = request.args.get('compte')
        date_debut = request.args.get('date_debut')
        date_fin = request.args.get('date_fin')
        sens = request.args.get('sens')
        search = request.args.get('search')
        
        # Construire la requête
        query = BankTransaction.query
        
        if compte:
            query = query.filter(BankTransaction.compte_general == compte)
        
        if date_debut:
            try:
                date_debut_obj = datetime.strptime(date_debut, '%Y-%m-%d').date()
                query = query.filter(BankTransaction.date_ecriture >= date_debut_obj)
            except ValueError:
                pass
        
        if date_fin:
            try:
                date_fin_obj = datetime.strptime(date_fin, '%Y-%m-%d').date()
                query = query.filter(BankTransaction.date_ecriture <= date_fin_obj)
            except ValueError:
                pass
        
        if sens:
            query = query.filter(BankTransaction.sens.ilike(f'%{sens}%'))
        
        if search:
            query = query.filter(
                or_(
                    BankTransaction.libelle.ilike(f'%{search}%'),
                    BankTransaction.numero_piece.ilike(f'%{search}%')
                )
            )
        
        # Ordonner par date décroissante
        query = query.order_by(BankTransaction.date_ecriture.desc())
        
        # Paginer
        pagination = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        transactions = [t.to_dict() for t in pagination.items]
        
        return jsonify({
            'transactions': transactions,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Erreur lors de la récupération des transactions: {str(e)}'}), 500

@accounting_data_bp.route('/accounting/bank-transactions/summary', methods=['GET'])
@jwt_required()
def get_bank_transactions_summary():
    """Récupère un résumé des transactions bancaires"""
    try:
        # Statistiques générales
        total_transactions = BankTransaction.query.count()
        
        # Sommes par sens
        debit_sum = db.session.query(func.sum(BankTransaction.montant_signe_tc))\
            .filter(BankTransaction.sens.ilike('%débit%')).scalar() or 0
        
        credit_sum = db.session.query(func.sum(BankTransaction.montant_signe_tc))\
            .filter(BankTransaction.sens.ilike('%crédit%')).scalar() or 0
        
        # Transactions par mois
        monthly_stats = db.session.query(
            func.strftime('%Y-%m', BankTransaction.date_ecriture).label('month'),
            func.count(BankTransaction.id).label('count'),
            func.sum(BankTransaction.montant_signe_tc).label('total')
        ).group_by(func.strftime('%Y-%m', BankTransaction.date_ecriture))\
         .order_by(func.strftime('%Y-%m', BankTransaction.date_ecriture).desc())\
         .limit(12).all()
        
        # Comptes les plus actifs
        top_accounts = db.session.query(
            BankTransaction.compte_general,
            func.count(BankTransaction.id).label('count'),
            func.sum(BankTransaction.montant_signe_tc).label('total')
        ).group_by(BankTransaction.compte_general)\
         .order_by(func.count(BankTransaction.id).desc())\
         .limit(10).all()
        
        return jsonify({
            'summary': {
                'total_transactions': total_transactions,
                'debit_sum': float(debit_sum),
                'credit_sum': float(credit_sum),
                'balance': float(credit_sum - debit_sum)
            },
            'monthly_stats': [
                {
                    'month': stat.month,
                    'count': stat.count,
                    'total': float(stat.total) if stat.total else 0
                }
                for stat in monthly_stats
            ],
            'top_accounts': [
                {
                    'compte': account.compte_general,
                    'count': account.count,
                    'total': float(account.total) if account.total else 0
                }
                for account in top_accounts
            ]
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Erreur lors du calcul du résumé: {str(e)}'}), 500

@accounting_data_bp.route('/accounting/tva-clients', methods=['GET'])
@jwt_required()
def get_tva_clients():
    """Récupère les données TVA clients avec filtres optionnels"""
    try:
        # Paramètres de pagination
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 50, type=int), 100)
        
        # Paramètres de filtrage
        code_compte = request.args.get('code_compte')
        journal = request.args.get('journal')
        date_debut = request.args.get('date_debut')
        date_fin = request.args.get('date_fin')
        search = request.args.get('search')
        
        # Construire la requête
        query = TVAClient.query
        
        if code_compte:
            query = query.filter(TVAClient.code_compte == code_compte)
        
        if journal:
            query = query.filter(TVAClient.journal == journal)
        
        if date_debut:
            try:
                date_debut_obj = datetime.strptime(date_debut, '%Y-%m-%d').date()
                query = query.filter(TVAClient.date_ecriture >= date_debut_obj)
            except ValueError:
                pass
        
        if date_fin:
            try:
                date_fin_obj = datetime.strptime(date_fin, '%Y-%m-%d').date()
                query = query.filter(TVAClient.date_ecriture <= date_fin_obj)
            except ValueError:
                pass
        
        if search:
            query = query.filter(
                or_(
                    TVAClient.libelle_compte.ilike(f'%{search}%'),
                    TVAClient.libelle_ecriture.ilike(f'%{search}%'),
                    TVAClient.numero_piece.ilike(f'%{search}%')
                )
            )
        
        # Ordonner par date décroissante
        query = query.order_by(TVAClient.date_ecriture.desc())
        
        # Paginer
        pagination = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        tva_records = [t.to_dict() for t in pagination.items]
        
        return jsonify({
            'tva_records': tva_records,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Erreur lors de la récupération des données TVA: {str(e)}'}), 500

@accounting_data_bp.route('/accounting/tva-clients/summary', methods=['GET'])
@jwt_required()
def get_tva_clients_summary():
    """Récupère un résumé des données TVA clients"""
    try:
        # Statistiques générales
        total_records = TVAClient.query.count()
        
        # Sommes débit/crédit
        total_debit = db.session.query(func.sum(TVAClient.debit)).scalar() or 0
        total_credit = db.session.query(func.sum(TVAClient.credit)).scalar() or 0
        total_solde = db.session.query(func.sum(TVAClient.solde)).scalar() or 0
        
        # Répartition par journal
        journal_stats = db.session.query(
            TVAClient.journal,
            func.count(TVAClient.id).label('count'),
            func.sum(TVAClient.debit).label('total_debit'),
            func.sum(TVAClient.credit).label('total_credit')
        ).filter(TVAClient.journal.isnot(None))\
         .group_by(TVAClient.journal)\
         .order_by(func.count(TVAClient.id).desc()).all()
        
        # Comptes clients principaux
        top_clients = db.session.query(
            TVAClient.code_compte,
            TVAClient.libelle_compte,
            func.count(TVAClient.id).label('count'),
            func.sum(TVAClient.solde).label('total_solde')
        ).filter(TVAClient.code_compte.like('342%'))\
         .group_by(TVAClient.code_compte, TVAClient.libelle_compte)\
         .order_by(func.sum(TVAClient.solde).desc())\
         .limit(10).all()
        
        return jsonify({
            'summary': {
                'total_records': total_records,
                'total_debit': float(total_debit),
                'total_credit': float(total_credit),
                'total_solde': float(total_solde)
            },
            'journal_stats': [
                {
                    'journal': stat.journal,
                    'count': stat.count,
                    'total_debit': float(stat.total_debit) if stat.total_debit else 0,
                    'total_credit': float(stat.total_credit) if stat.total_credit else 0
                }
                for stat in journal_stats
            ],
            'top_clients': [
                {
                    'code_compte': client.code_compte,
                    'libelle_compte': client.libelle_compte,
                    'count': client.count,
                    'total_solde': float(client.total_solde) if client.total_solde else 0
                }
                for client in top_clients
            ]
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Erreur lors du calcul du résumé TVA: {str(e)}'}), 500

