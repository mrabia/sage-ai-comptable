#!/usr/bin/env python3
"""
Script pour initialiser la base de données avec des données de test
"""
import sys
import os
import json
from datetime import datetime, timedelta

# Ajouter le répertoire src au path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.main import app
from src.models.user import db, User, Conversation, SageOperation, AutomationRule, AuditLog

def create_test_users():
    """Créer des utilisateurs de test"""
    users_data = [
        {
            'username': 'demo',
            'email': 'demo@test.com',
            'password': 'password123'
        },
        {
            'username': 'admin',
            'email': 'admin@sageai.com',
            'password': 'admin123'
        },
        {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'test123'
        }
    ]
    
    created_users = []
    for user_data in users_data:
        user = User(
            username=user_data['username'],
            email=user_data['email']
        )
        user.set_password(user_data['password'])
        db.session.add(user)
        created_users.append(user)
    
    db.session.commit()
    return created_users

def create_test_conversations(users):
    """Créer des conversations de test"""
    conversations_data = [
        {
            'title': 'Analyse du bilan comptable',
            'messages': [
                {
                    'role': 'user',
                    'content': 'Peux-tu analyser mon bilan comptable du mois dernier ?',
                    'timestamp': (datetime.utcnow() - timedelta(hours=2)).isoformat(),
                    'metadata': {}
                },
                {
                    'role': 'assistant',
                    'content': 'Bien sûr ! Je vais analyser votre bilan comptable. Pouvez-vous me fournir les données ou me donner accès à votre compte Sage ?',
                    'timestamp': (datetime.utcnow() - timedelta(hours=2, minutes=1)).isoformat(),
                    'metadata': {}
                }
            ]
        },
        {
            'title': 'Création de factures automatiques',
            'messages': [
                {
                    'role': 'user',
                    'content': 'Comment puis-je automatiser la création de factures récurrentes ?',
                    'timestamp': (datetime.utcnow() - timedelta(hours=1)).isoformat(),
                    'metadata': {}
                },
                {
                    'role': 'assistant',
                    'content': 'Je peux vous aider à configurer des règles d\'automatisation pour les factures récurrentes. Voici les étapes...',
                    'timestamp': (datetime.utcnow() - timedelta(hours=1, minutes=2)).isoformat(),
                    'metadata': {}
                }
            ]
        },
        {
            'title': 'Rapport financier mensuel',
            'messages': [
                {
                    'role': 'user',
                    'content': 'Génère-moi un rapport financier complet pour le mois de août',
                    'timestamp': datetime.utcnow().isoformat(),
                    'metadata': {}
                }
            ]
        }
    ]
    
    for i, conv_data in enumerate(conversations_data):
        user = users[i % len(users)]  # Distribuer les conversations entre les utilisateurs
        conversation = Conversation(
            user_id=user.id,
            title=conv_data['title'],
            messages=json.dumps(conv_data['messages'], ensure_ascii=False)
        )
        db.session.add(conversation)
    
    db.session.commit()

def create_test_sage_operations(users):
    """Créer des opérations Sage de test"""
    operations_data = [
        {
            'operation_type': 'get_balance',
            'operation_data': {'account': 'main', 'period': '2024-08'},
            'status': 'success',
            'sage_response': {'balance': 15420.50, 'currency': 'EUR'}
        },
        {
            'operation_type': 'create_invoice',
            'operation_data': {'customer': 'ABC Corp', 'amount': 1250.00, 'items': ['Consultation']},
            'status': 'success',
            'sage_response': {'invoice_id': 'INV-2024-001', 'status': 'created'}
        },
        {
            'operation_type': 'get_customers',
            'operation_data': {'limit': 50},
            'status': 'pending',
            'sage_response': None
        }
    ]
    
    for i, op_data in enumerate(operations_data):
        user = users[i % len(users)]
        operation = SageOperation(
            user_id=user.id,
            operation_type=op_data['operation_type'],
            status=op_data['status']
        )
        operation.set_operation_data(op_data['operation_data'])
        if op_data['sage_response']:
            operation.set_sage_response(op_data['sage_response'])
        
        db.session.add(operation)
    
    db.session.commit()

def create_test_automation_rules(users):
    """Créer des règles d'automatisation de test"""
    rules_data = [
        {
            'name': 'Factures récurrentes mensuelles',
            'description': 'Créer automatiquement les factures d\'abonnement chaque mois',
            'rule_config': {
                'trigger_type': 'schedule',
                'trigger_config': {'frequency': 'monthly', 'day': 1},
                'action_type': 'create_invoice',
                'action_config': {'template': 'subscription', 'customers': ['ABC Corp', 'XYZ Ltd']}
            }
        },
        {
            'name': 'Rappel de paiement automatique',
            'description': 'Envoyer un rappel 7 jours après échéance',
            'rule_config': {
                'trigger_type': 'invoice_overdue',
                'trigger_config': {'days': 7},
                'action_type': 'send_reminder',
                'action_config': {'template': 'payment_reminder'}
            }
        }
    ]
    
    for i, rule_data in enumerate(rules_data):
        user = users[i % len(users)]
        rule = AutomationRule(
            user_id=user.id,
            name=rule_data['name'],
            description=rule_data['description']
        )
        rule.set_rule_config(rule_data['rule_config'])
        
        db.session.add(rule)
    
    db.session.commit()

def create_test_audit_logs(users):
    """Créer des logs d'audit de test"""
    logs_data = [
        {
            'action': 'user_login',
            'details': {'ip': '192.168.1.100', 'user_agent': 'Mozilla/5.0'},
            'ip_address': '192.168.1.100'
        },
        {
            'action': 'sage_auth_completed',
            'details': {'country': 'CA', 'scope': 'full_access'},
            'ip_address': '192.168.1.100'
        },
        {
            'action': 'invoice_created',
            'details': {'invoice_id': 'INV-2024-001', 'amount': 1250.00},
            'ip_address': '192.168.1.100'
        }
    ]
    
    for i, log_data in enumerate(logs_data):
        user = users[i % len(users)]
        audit_log = AuditLog(
            user_id=user.id,
            action=log_data['action'],
            ip_address=log_data['ip_address'],
            user_agent=log_data.get('user_agent', 'Test Agent')
        )
        audit_log.set_details(log_data['details'])
        
        db.session.add(audit_log)
    
    db.session.commit()

def seed_database():
    """Initialiser la base de données avec des données de test"""
    with app.app_context():
        try:
            print("🗑️  Suppression des données existantes...")
            # Supprimer toutes les données existantes
            db.session.query(AuditLog).delete()
            db.session.query(AutomationRule).delete()
            db.session.query(SageOperation).delete()
            db.session.query(Conversation).delete()
            db.session.query(User).delete()
            db.session.commit()
            
            print("👥 Création des utilisateurs de test...")
            users = create_test_users()
            print(f"   ✅ {len(users)} utilisateurs créés")
            
            print("💬 Création des conversations de test...")
            create_test_conversations(users)
            print("   ✅ Conversations créées")
            
            print("🔧 Création des opérations Sage de test...")
            create_test_sage_operations(users)
            print("   ✅ Opérations Sage créées")
            
            print("⚙️  Création des règles d'automatisation de test...")
            create_test_automation_rules(users)
            print("   ✅ Règles d'automatisation créées")
            
            print("📋 Création des logs d'audit de test...")
            create_test_audit_logs(users)
            print("   ✅ Logs d'audit créés")
            
            print("\n🎉 Base de données initialisée avec succès avec des données de test !")
            print("\n📋 Utilisateurs de test créés :")
            for user in users:
                print(f"   • {user.email} (mot de passe: password123 pour demo, admin123 pour admin, test123 pour testuser)")
            
            return True
            
        except Exception as e:
            print(f"❌ Erreur lors de l'initialisation: {e}")
            db.session.rollback()
            return False

if __name__ == '__main__':
    print("🚀 Initialisation de la base de données avec des données de test...")
    if seed_database():
        print("✅ Terminé !")
    else:
        print("❌ Échec de l'initialisation")
        sys.exit(1)

