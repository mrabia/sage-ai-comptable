from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import json

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    sage_credentials_encrypted = db.Column(db.Text, nullable=True)  # Credentials Sage chiffrés
    # Champs temporaires pour OAuth2
    oauth_state = db.Column(db.String(255), nullable=True)  # State temporaire OAuth
    oauth_code_verifier = db.Column(db.String(255), nullable=True)  # Code verifier temporaire
    oauth_expires_at = db.Column(db.DateTime, nullable=True)  # Expiration des données OAuth
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    
    # Relations
    conversations = db.relationship('Conversation', backref='user', lazy=True, cascade='all, delete-orphan')
    sage_operations = db.relationship('SageOperation', backref='user', lazy=True, cascade='all, delete-orphan')
    automation_rules = db.relationship('AutomationRule', backref='user', lazy=True, cascade='all, delete-orphan')
    audit_logs = db.relationship('AuditLog', backref='user', lazy=True, cascade='all, delete-orphan')

    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check if provided password matches hash"""
        return check_password_hash(self.password_hash, password)
    
    def set_sage_credentials(self, credentials_dict):
        """Store encrypted Sage credentials"""
        # TODO: Implement encryption with AES-256
        self.sage_credentials_encrypted = json.dumps(credentials_dict)
    
    def get_sage_credentials(self):
        """Retrieve and decrypt Sage credentials"""
        if not self.sage_credentials_encrypted:
            return None
        # TODO: Implement decryption
        return json.loads(self.sage_credentials_encrypted)

    def __repr__(self):
        return f'<User {self.username}>'

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }


class Conversation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=True)
    messages = db.Column(db.Text, nullable=False)  # JSON string of messages
    conversation_metadata = db.Column(db.Text, nullable=True)  # JSON string for additional data
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    def add_message(self, role, content, metadata=None):
        """Add a new message to the conversation"""
        messages = self.get_messages()
        new_message = {
            'role': role,  # 'user' or 'assistant'
            'content': content,
            'timestamp': datetime.utcnow().isoformat(),
            'metadata': metadata or {}
        }
        messages.append(new_message)
        self.messages = json.dumps(messages, ensure_ascii=False)
        self.updated_at = datetime.utcnow()
    
    def get_messages(self):
        """Get all messages in the conversation"""
        if not self.messages:
            return []
        return json.loads(self.messages)
    
    def set_metadata(self, metadata_dict):
        """Set conversation metadata"""
        self.conversation_metadata = json.dumps(metadata_dict, ensure_ascii=False)
    
    def get_metadata(self):
        """Get conversation metadata"""
        if not self.conversation_metadata:
            return {}
        return json.loads(self.conversation_metadata)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'title': self.title,
            'messages': self.get_messages(),
            'metadata': self.get_metadata(),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'is_active': self.is_active
        }


class SageOperation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    operation_type = db.Column(db.String(100), nullable=False)  # 'create_invoice', 'get_balance', etc.
    operation_data = db.Column(db.Text, nullable=False)  # JSON string of operation parameters
    sage_response = db.Column(db.Text, nullable=True)  # JSON string of Sage API response
    status = db.Column(db.String(50), default='pending')  # 'pending', 'awaiting_confirmation', 'confirmed', 'rejected', 'success', 'error'
    error_message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    def set_operation_data(self, data_dict):
        """Set operation parameters"""
        self.operation_data = json.dumps(data_dict, ensure_ascii=False)
    
    def get_operation_data(self):
        """Get operation parameters"""
        if not self.operation_data:
            return {}
        return json.loads(self.operation_data)
    
    def set_sage_response(self, response_dict):
        """Set Sage API response"""
        self.sage_response = json.dumps(response_dict, ensure_ascii=False)
        self.completed_at = datetime.utcnow()
    
    def get_sage_response(self):
        """Get Sage API response"""
        if not self.sage_response:
            return {}
        return json.loads(self.sage_response)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'operation_type': self.operation_type,
            'operation_data': self.get_operation_data(),
            'sage_response': self.get_sage_response(),
            'status': self.status,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }


class AutomationRule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    rule_config = db.Column(db.Text, nullable=False)  # JSON string of rule configuration
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_executed = db.Column(db.DateTime, nullable=True)
    execution_count = db.Column(db.Integer, default=0)
    
    def set_rule_config(self, config_dict):
        """Set rule configuration"""
        self.rule_config = json.dumps(config_dict, ensure_ascii=False)
    
    def get_rule_config(self):
        """Get rule configuration"""
        if not self.rule_config:
            return {}
        return json.loads(self.rule_config)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'description': self.description,
            'rule_config': self.get_rule_config(),
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
            'last_executed': self.last_executed.isoformat() if self.last_executed else None,
            'execution_count': self.execution_count
        }


class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    action = db.Column(db.String(200), nullable=False)
    details = db.Column(db.Text, nullable=True)  # JSON string with action details
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(500), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_details(self, details_dict):
        """Set action details"""
        self.details = json.dumps(details_dict, ensure_ascii=False)
    
    def get_details(self):
        """Get action details"""
        if not self.details:
            return {}
        return json.loads(self.details)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'action': self.action,
            'details': self.get_details(),
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'timestamp': self.timestamp.isoformat()
        }


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversation.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_from_user = db.Column(db.Boolean, nullable=False)  # True for user messages, False for AI responses
    message_metadata = db.Column(db.Text, nullable=True)  # JSON string for additional data
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relation
    conversation = db.relationship('Conversation', backref=db.backref('message_objects', lazy=True, cascade='all, delete-orphan'))
    
    def set_metadata(self, metadata_dict):
        """Set message metadata"""
        self.message_metadata = json.dumps(metadata_dict, ensure_ascii=False)
    
    def get_metadata(self):
        """Get message metadata"""
        if not self.message_metadata:
            return {}
        return json.loads(self.message_metadata)

    def to_dict(self):
        return {
            'id': self.id,
            'conversation_id': self.conversation_id,
            'content': self.content,
            'is_from_user': self.is_from_user,
            'metadata': self.get_metadata(),
            'created_at': self.created_at.isoformat()
        }

