import os
import uuid
import magic
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
from src.models.user import User, db
from src.models.document import Document
from src.services.document_processor import DocumentProcessor

documents_bp = Blueprint('documents', __name__)

# Configuration des uploads
UPLOAD_FOLDER = 'src/uploads'
TEMP_FOLDER = 'src/uploads/temp'
MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50 MB

def allowed_file(filename, mime_type):
    """Vérifie si le fichier est autorisé"""
    is_supported, file_type = Document.is_supported_file_type(mime_type, filename)
    return is_supported, file_type

def generate_unique_filename(original_filename):
    """Génère un nom de fichier unique"""
    file_extension = os.path.splitext(original_filename)[1].lower()
    unique_id = str(uuid.uuid4())
    return f"{unique_id}{file_extension}"

@documents_bp.route('/documents/upload', methods=['POST'])
@jwt_required()
def upload_document():
    """Upload d'un document avec validation et sécurité"""
    try:
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'Utilisateur non trouvé'}), 404
        
        # Vérifier qu'un fichier a été envoyé
        if 'file' not in request.files:
            return jsonify({'error': 'Aucun fichier fourni'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'Nom de fichier vide'}), 400
        
        # Vérifier la taille du fichier
        if len(file.read()) > MAX_CONTENT_LENGTH:
            return jsonify({'error': f'Fichier trop volumineux (max {MAX_CONTENT_LENGTH // (1024*1024)} MB)'}), 400
        
        # Remettre le pointeur au début du fichier
        file.seek(0)
        
        # Détecter le type MIME réel du fichier
        file_content = file.read()
        file.seek(0)
        
        mime_type = magic.from_buffer(file_content, mime=True)
        
        # Vérifier si le type de fichier est supporté
        is_supported, file_type = allowed_file(file.filename, mime_type)
        
        if not is_supported:
            supported_types = Document.get_supported_file_types()
            return jsonify({
                'error': 'Type de fichier non supporté',
                'supported_types': {k: v['description'] for k, v in supported_types.items()}
            }), 400
        
        # Générer un nom de fichier sécurisé et unique
        original_filename = secure_filename(file.filename)
        unique_filename = generate_unique_filename(original_filename)
        
        # Créer le répertoire utilisateur s'il n'existe pas
        user_upload_dir = os.path.join(UPLOAD_FOLDER, str(user_id))
        os.makedirs(user_upload_dir, exist_ok=True)
        
        # Chemin complet du fichier
        file_path = os.path.join(user_upload_dir, unique_filename)
        
        # Sauvegarder le fichier
        file.save(file_path)
        
        # Créer l'enregistrement en base de données
        document = Document(
            user_id=user_id,
            filename=unique_filename,
            original_filename=original_filename,
            file_path=file_path,
            file_size=len(file_content),
            mime_type=mime_type,
            file_type=file_type,
            processing_status='pending'
        )
        
        db.session.add(document)
        db.session.commit()
        
        # Démarrer le traitement asynchrone du document
        try:
            processor = DocumentProcessor()
            processor.process_document_async(document.id)
        except Exception as e:
            print(f"Erreur lors du démarrage du traitement: {e}")
            # Le document est sauvegardé, on peut traiter plus tard
        
        return jsonify({
            'success': True,
            'message': 'Fichier uploadé avec succès',
            'document': document.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erreur lors de l\'upload: {str(e)}'}), 500

@documents_bp.route('/documents', methods=['GET'])
@jwt_required()
def get_user_documents():
    """Récupère la liste des documents de l'utilisateur"""
    try:
        user_id = int(get_jwt_identity())
        
        # Paramètres de pagination
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        file_type = request.args.get('file_type')
        status = request.args.get('status')
        
        # Construire la requête
        query = Document.query.filter_by(user_id=user_id, is_deleted=False)
        
        if file_type:
            query = query.filter_by(file_type=file_type)
        
        if status:
            query = query.filter_by(processing_status=status)
        
        # Ordonner par date de création (plus récent en premier)
        query = query.order_by(Document.created_at.desc())
        
        # Paginer
        documents = query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        return jsonify({
            'documents': [doc.to_dict() for doc in documents.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': documents.total,
                'pages': documents.pages,
                'has_next': documents.has_next,
                'has_prev': documents.has_prev
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Erreur lors de la récupération: {str(e)}'}), 500

@documents_bp.route('/documents/<int:document_id>', methods=['GET'])
@jwt_required()
def get_document(document_id):
    """Récupère les détails d'un document spécifique"""
    try:
        user_id = int(get_jwt_identity())
        
        document = Document.query.filter_by(
            id=document_id, 
            user_id=user_id, 
            is_deleted=False
        ).first()
        
        if not document:
            return jsonify({'error': 'Document non trouvé'}), 404
        
        return jsonify({
            'document': document.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Erreur lors de la récupération: {str(e)}'}), 500

@documents_bp.route('/documents/<int:document_id>/download', methods=['GET'])
@jwt_required()
def download_document(document_id):
    """Télécharge un document"""
    try:
        user_id = int(get_jwt_identity())
        
        document = Document.query.filter_by(
            id=document_id, 
            user_id=user_id, 
            is_deleted=False
        ).first()
        
        if not document:
            return jsonify({'error': 'Document non trouvé'}), 404
        
        if not os.path.exists(document.file_path):
            return jsonify({'error': 'Fichier physique non trouvé'}), 404
        
        return send_file(
            document.file_path,
            as_attachment=True,
            download_name=document.original_filename,
            mimetype=document.mime_type
        )
        
    except Exception as e:
        return jsonify({'error': f'Erreur lors du téléchargement: {str(e)}'}), 500

@documents_bp.route('/documents/<int:document_id>', methods=['DELETE'])
@jwt_required()
def delete_document(document_id):
    """Supprime un document (soft delete)"""
    try:
        user_id = int(get_jwt_identity())
        
        document = Document.query.filter_by(
            id=document_id, 
            user_id=user_id, 
            is_deleted=False
        ).first()
        
        if not document:
            return jsonify({'error': 'Document non trouvé'}), 404
        
        # Soft delete
        document.is_deleted = True
        document.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Document supprimé avec succès'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erreur lors de la suppression: {str(e)}'}), 500

@documents_bp.route('/documents/<int:document_id>/reprocess', methods=['POST'])
@jwt_required()
def reprocess_document(document_id):
    """Relance le traitement d'un document"""
    try:
        user_id = int(get_jwt_identity())
        
        document = Document.query.filter_by(
            id=document_id, 
            user_id=user_id, 
            is_deleted=False
        ).first()
        
        if not document:
            return jsonify({'error': 'Document non trouvé'}), 404
        
        if not os.path.exists(document.file_path):
            return jsonify({'error': 'Fichier physique non trouvé'}), 404
        
        # Réinitialiser le statut de traitement
        document.set_processing_status('pending')
        document.extracted_text = None
        document.extracted_data = None
        document.confidence_score = None
        
        db.session.commit()
        
        # Relancer le traitement
        processor = DocumentProcessor()
        processor.process_document_async(document.id)
        
        return jsonify({
            'success': True,
            'message': 'Traitement relancé avec succès',
            'document': document.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erreur lors du retraitement: {str(e)}'}), 500

@documents_bp.route('/documents/supported-types', methods=['GET'])
def get_supported_types():
    """Retourne les types de fichiers supportés"""
    try:
        supported_types = Document.get_supported_file_types()
        max_size_mb = Document.get_max_file_size() // (1024 * 1024)
        
        return jsonify({
            'supported_types': supported_types,
            'max_file_size_mb': max_size_mb,
            'max_file_size_bytes': Document.get_max_file_size()
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Erreur: {str(e)}'}), 500

@documents_bp.route('/documents/stats', methods=['GET'])
@jwt_required()
def get_document_stats():
    """Retourne les statistiques des documents de l'utilisateur"""
    try:
        user_id = int(get_jwt_identity())
        
        # Compter les documents par type
        stats = {}
        
        total_docs = Document.query.filter_by(user_id=user_id, is_deleted=False).count()
        stats['total'] = total_docs
        
        # Par type de fichier
        file_types = ['pdf', 'image', 'csv', 'excel']
        for file_type in file_types:
            count = Document.query.filter_by(
                user_id=user_id, 
                file_type=file_type, 
                is_deleted=False
            ).count()
            stats[file_type] = count
        
        # Par statut de traitement
        statuses = ['pending', 'processing', 'completed', 'failed']
        for status in statuses:
            count = Document.query.filter_by(
                user_id=user_id, 
                processing_status=status, 
                is_deleted=False
            ).count()
            stats[f'status_{status}'] = count
        
        # Taille totale des fichiers
        total_size = db.session.query(db.func.sum(Document.file_size)).filter_by(
            user_id=user_id, 
            is_deleted=False
        ).scalar() or 0
        
        stats['total_size_bytes'] = total_size
        stats['total_size_mb'] = round(total_size / (1024 * 1024), 2)
        
        return jsonify({'stats': stats}), 200
        
    except Exception as e:
        return jsonify({'error': f'Erreur lors du calcul des statistiques: {str(e)}'}), 500

