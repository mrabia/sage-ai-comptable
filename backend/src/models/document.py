from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from src.models.user import db

class Document(db.Model):
    """Modèle pour les documents uploadés par les utilisateurs"""
    __tablename__ = 'documents'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)  # Taille en bytes
    mime_type = Column(String(100), nullable=False)
    file_type = Column(String(50), nullable=False)  # pdf, image, csv, excel
    
    # Statut du traitement
    processing_status = Column(String(50), default='pending')  # pending, processing, completed, failed
    processing_started_at = Column(DateTime)
    processing_completed_at = Column(DateTime)
    
    # Données extraites
    extracted_text = Column(Text)
    extracted_data = Column(JSON)  # Données structurées extraites
    confidence_score = Column(Integer)  # Score de confiance de l'extraction (0-100)
    
    # Métadonnées
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_deleted = Column(Boolean, default=False)
    
    # Relations
    user = relationship("User", backref="user_documents")
    
    def __repr__(self):
        return f'<Document {self.original_filename}>'
    
    def to_dict(self):
        """Convertit le document en dictionnaire pour l'API"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'filename': self.filename,
            'original_filename': self.original_filename,
            'file_size': self.file_size,
            'mime_type': self.mime_type,
            'file_type': self.file_type,
            'processing_status': self.processing_status,
            'processing_started_at': self.processing_started_at.isoformat() if self.processing_started_at else None,
            'processing_completed_at': self.processing_completed_at.isoformat() if self.processing_completed_at else None,
            'extracted_text': self.extracted_text,
            'extracted_data': self.extracted_data,
            'confidence_score': self.confidence_score,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'is_deleted': self.is_deleted
        }
    
    def set_processing_status(self, status: str):
        """Met à jour le statut de traitement"""
        self.processing_status = status
        self.updated_at = datetime.utcnow()
        
        if status == 'processing':
            self.processing_started_at = datetime.utcnow()
        elif status in ['completed', 'failed']:
            self.processing_completed_at = datetime.utcnow()
    
    def set_extracted_data(self, text: str = None, data: dict = None, confidence: int = None):
        """Met à jour les données extraites"""
        if text is not None:
            self.extracted_text = text
        if data is not None:
            self.extracted_data = data
        if confidence is not None:
            self.confidence_score = confidence
        
        self.updated_at = datetime.utcnow()
    
    @staticmethod
    def get_supported_file_types():
        """Retourne les types de fichiers supportés"""
        return {
            'pdf': {
                'mime_types': ['application/pdf'],
                'extensions': ['.pdf'],
                'description': 'Documents PDF'
            },
            'image': {
                'mime_types': ['image/jpeg', 'image/png', 'image/jpg'],
                'extensions': ['.jpg', '.jpeg', '.png'],
                'description': 'Images (JPEG, PNG)'
            },
            'csv': {
                'mime_types': ['text/csv', 'application/csv'],
                'extensions': ['.csv'],
                'description': 'Fichiers CSV'
            },
            'excel': {
                'mime_types': [
                    'application/vnd.ms-excel',
                    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                ],
                'extensions': ['.xls', '.xlsx'],
                'description': 'Fichiers Excel'
            }
        }
    
    @staticmethod
    def is_supported_file_type(mime_type: str, filename: str = None):
        """Vérifie si le type de fichier est supporté"""
        supported_types = Document.get_supported_file_types()
        
        for file_type, config in supported_types.items():
            if mime_type in config['mime_types']:
                return True, file_type
            
            # Vérification par extension si le nom de fichier est fourni
            if filename:
                file_extension = '.' + filename.lower().split('.')[-1] if '.' in filename else ''
                if file_extension in config['extensions']:
                    return True, file_type
        
        return False, None
    
    @staticmethod
    def get_max_file_size():
        """Retourne la taille maximale autorisée pour les fichiers (en bytes)"""
        return 50 * 1024 * 1024  # 50 MB

