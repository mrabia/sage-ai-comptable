"""
Routes pour la gestion des fichiers attachés
Upload, traitement, et analyse des fichiers
"""

from flask import Blueprint, jsonify, request, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.exceptions import RequestEntityTooLarge
from src.models.user import User, FileAttachment, db
from src.services.file_processor import file_processor
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

file_upload_bp = Blueprint('file_upload', __name__)

@file_upload_bp.route('/upload', methods=['POST'])
@jwt_required()
def upload_file():
    """Upload et traitement d'un fichier"""
    try:
        user_id = int(get_jwt_identity())
        
        # Vérifier qu'un fichier est présent
        if 'file' not in request.files:
            return jsonify({'error': 'Aucun fichier fourni'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'Nom de fichier vide'}), 400
        
        # Paramètres optionnels
        conversation_id = request.form.get('conversation_id', type=int)
        
        # Vérifier l'utilisateur
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'Utilisateur non trouvé'}), 404
        
        # Traiter et sauvegarder le fichier
        try:
            file_path, analysis = file_processor.save_uploaded_file(file, user_id, conversation_id)
        except ValueError as e:
            return jsonify({'error': str(e)}), 400
        
        # Créer l'enregistrement en base
        file_attachment = FileAttachment(
            user_id=user_id,
            conversation_id=conversation_id,
            filename=os.path.basename(file_path),
            original_filename=file.filename,
            file_path=file_path,
            file_size=analysis.get('file_size', 0),
            file_type=analysis.get('mime_type', 'application/octet-stream'),
            file_extension=analysis.get('file_extension', ''),
            is_processed='error' not in analysis,
            processing_error=analysis.get('error')
        )
        
        # Sauvegarder l'analyse si elle a réussi
        if 'error' not in analysis:
            file_attachment.set_analysis_metadata(analysis)
            # Extraire le contenu traité pour la recherche
            if analysis.get('type') == 'text':
                file_attachment.processed_content = analysis.get('text_sample', '')
            elif analysis.get('type') == 'pdf':
                file_attachment.processed_content = analysis.get('text_sample', '')
            elif analysis.get('type') == 'image' and analysis.get('extracted_text'):
                file_attachment.processed_content = analysis.get('extracted_text', '')
        
        db.session.add(file_attachment)
        db.session.commit()
        
        response_data = {
            'file_id': file_attachment.id,
            'filename': file_attachment.original_filename,
            'file_size': file_attachment.file_size,
            'file_type': file_attachment.file_type,
            'is_processed': file_attachment.is_processed,
            'upload_timestamp': file_attachment.upload_timestamp.isoformat()
        }
        
        # Ajouter un résumé de l'analyse
        if file_attachment.is_processed:
            response_data['analysis_summary'] = {
                'type': analysis.get('type'),
                'potential_financial_data': analysis.get('potential_financial_data', False),
                'has_tables': analysis.get('has_tables', analysis.get('tables_count', 0) > 0),
                'has_text': analysis.get('has_text', len(analysis.get('text_sample', '')) > 0)
            }
        else:
            response_data['processing_error'] = file_attachment.processing_error
        
        return jsonify(response_data), 201
        
    except RequestEntityTooLarge:
        return jsonify({'error': 'Fichier trop volumineux'}), 413
    except Exception as e:
        logger.error(f"Erreur lors de l'upload: {str(e)}")
        return jsonify({'error': f'Erreur interne: {str(e)}'}), 500

@file_upload_bp.route('/files', methods=['GET'])
@jwt_required()
def list_files():
    """Lister les fichiers de l'utilisateur"""
    try:
        user_id = int(get_jwt_identity())
        conversation_id = request.args.get('conversation_id', type=int)
        
        query = FileAttachment.query.filter_by(user_id=user_id)
        
        if conversation_id:
            query = query.filter_by(conversation_id=conversation_id)
        
        files = query.order_by(FileAttachment.upload_timestamp.desc()).all()
        
        return jsonify({
            'files': [file_attachment.to_dict() for file_attachment in files],
            'count': len(files)
        })
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des fichiers: {str(e)}")
        return jsonify({'error': f'Erreur interne: {str(e)}'}), 500

@file_upload_bp.route('/files/<int:file_id>', methods=['GET'])
@jwt_required()
def get_file_details(file_id):
    """Obtenir les détails complets d'un fichier"""
    try:
        user_id = int(get_jwt_identity())
        
        file_attachment = FileAttachment.query.filter_by(
            id=file_id, 
            user_id=user_id
        ).first()
        
        if not file_attachment:
            return jsonify({'error': 'Fichier non trouvé'}), 404
        
        file_details = file_attachment.to_dict()
        
        # Ajouter le contenu traité si disponible
        if file_attachment.processed_content:
            file_details['processed_content'] = file_attachment.processed_content
        
        return jsonify(file_details)
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération du fichier: {str(e)}")
        return jsonify({'error': f'Erreur interne: {str(e)}'}), 500

@file_upload_bp.route('/files/<int:file_id>/download', methods=['GET'])
@jwt_required()
def download_file(file_id):
    """Télécharger un fichier"""
    try:
        user_id = int(get_jwt_identity())
        
        file_attachment = FileAttachment.query.filter_by(
            id=file_id, 
            user_id=user_id
        ).first()
        
        if not file_attachment:
            return jsonify({'error': 'Fichier non trouvé'}), 404
        
        if not os.path.exists(file_attachment.file_path):
            return jsonify({'error': 'Fichier physique non trouvé'}), 404
        
        return send_file(
            file_attachment.file_path,
            as_attachment=True,
            download_name=file_attachment.original_filename
        )
        
    except Exception as e:
        logger.error(f"Erreur lors du téléchargement: {str(e)}")
        return jsonify({'error': f'Erreur interne: {str(e)}'}), 500

@file_upload_bp.route('/files/<int:file_id>', methods=['DELETE'])
@jwt_required()
def delete_file(file_id):
    """Supprimer un fichier"""
    try:
        user_id = int(get_jwt_identity())
        
        file_attachment = FileAttachment.query.filter_by(
            id=file_id, 
            user_id=user_id
        ).first()
        
        if not file_attachment:
            return jsonify({'error': 'Fichier non trouvé'}), 404
        
        # Supprimer le fichier physique
        if os.path.exists(file_attachment.file_path):
            try:
                os.remove(file_attachment.file_path)
            except OSError as e:
                logger.warning(f"Impossible de supprimer le fichier physique: {str(e)}")
        
        # Supprimer l'enregistrement en base
        db.session.delete(file_attachment)
        db.session.commit()
        
        return jsonify({'message': 'Fichier supprimé avec succès'})
        
    except Exception as e:
        logger.error(f"Erreur lors de la suppression: {str(e)}")
        return jsonify({'error': f'Erreur interne: {str(e)}'}), 500

@file_upload_bp.route('/files/<int:file_id>/reprocess', methods=['POST'])
@jwt_required()
def reprocess_file(file_id):
    """Retraiter un fichier"""
    try:
        user_id = int(get_jwt_identity())
        
        file_attachment = FileAttachment.query.filter_by(
            id=file_id, 
            user_id=user_id
        ).first()
        
        if not file_attachment:
            return jsonify({'error': 'Fichier non trouvé'}), 404
        
        if not os.path.exists(file_attachment.file_path):
            return jsonify({'error': 'Fichier physique non trouvé'}), 404
        
        # Retraiter le fichier
        analysis = file_processor.process_file(file_attachment.file_path)
        
        # Mettre à jour l'enregistrement
        file_attachment.is_processed = 'error' not in analysis
        file_attachment.processing_error = analysis.get('error')
        
        if file_attachment.is_processed:
            file_attachment.set_analysis_metadata(analysis)
            # Mettre à jour le contenu traité
            if analysis.get('type') == 'text':
                file_attachment.processed_content = analysis.get('text_sample', '')
            elif analysis.get('type') == 'pdf':
                file_attachment.processed_content = analysis.get('text_sample', '')
            elif analysis.get('type') == 'image' and analysis.get('extracted_text'):
                file_attachment.processed_content = analysis.get('extracted_text', '')
        
        db.session.commit()
        
        return jsonify({
            'message': 'Fichier retraité avec succès',
            'is_processed': file_attachment.is_processed,
            'analysis_summary': {
                'type': analysis.get('type'),
                'potential_financial_data': analysis.get('potential_financial_data', False),
                'has_tables': analysis.get('has_tables', analysis.get('tables_count', 0) > 0),
                'has_text': analysis.get('has_text', len(analysis.get('text_sample', '')) > 0)
            } if file_attachment.is_processed else None
        })
        
    except Exception as e:
        logger.error(f"Erreur lors du retraitement: {str(e)}")
        return jsonify({'error': f'Erreur interne: {str(e)}'}), 500

@file_upload_bp.route('/supported-formats', methods=['GET'])
def get_supported_formats():
    """Obtenir la liste des formats supportés"""
    return jsonify({
        'supported_extensions': list(file_processor.allowed_extensions),
        'max_file_size': file_processor.max_file_size,
        'max_file_size_mb': round(file_processor.max_file_size / (1024 * 1024), 1),
        'categories': {
            'spreadsheets': ['.xlsx', '.xls', '.csv'],
            'documents': ['.pdf', '.docx', '.doc', '.txt'],
            'images': ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff'],
            'data': ['.json', '.xml']
        },
        'features': {
            'excel_analysis': True,
            'csv_analysis': True,
            'pdf_text_extraction': True,
            'image_ocr': True,
            'word_processing': True,
            'financial_data_detection': True,
            'table_extraction': True
        }
    })