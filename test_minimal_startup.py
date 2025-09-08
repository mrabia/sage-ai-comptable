#!/usr/bin/env python3
"""
Minimal startup test for Railway deployment
Tests if the app can start without AI components
"""

import os
import sys

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

print("Testing minimal app startup...")

try:
    # Set minimal environment
    os.environ['PYTHONPATH'] = os.path.join(os.path.dirname(__file__), 'backend')
    
    # Test Flask imports first
    print("1. Testing Flask imports...")
    from flask import Flask
    print("   SUCCESS Flask imported successfully")
    
    # Test database models
    print("2. Testing database models...")
    from src.models.user import db, User
    print("   SUCCESS Database models imported successfully")
    
    # Test basic routes (non-AI)
    print("3. Testing basic routes...")
    from src.routes.auth import auth_bp
    from src.routes.user import user_bp
    print("   SUCCESS Basic routes imported successfully")
    
    # Test AI components gracefully
    print("4. Testing AI components (should gracefully fail)...")
    try:
        from src.routes.ai_agent import ai_agent_bp
        print("   SUCCESS AI routes loaded (unexpected but okay)")
    except ImportError as e:
        print(f"   WARNING AI routes failed to load (expected): {e}")
    
    # Try to create basic Flask app
    print("5. Testing Flask app creation...")
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'test_key'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    
    # Register basic blueprints
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(user_bp, url_prefix='/api')
    
    print("   SUCCESS Flask app created successfully")
    
    # Test basic health endpoint
    print("6. Testing health endpoint simulation...")
    with app.test_client() as client:
        # Create a simple health check endpoint
        @app.route('/api/health')
        def health():
            return {'status': 'healthy', 'ai_enabled': False}
        
        response = client.get('/api/health')
        if response.status_code == 200:
            print("   SUCCESS Health endpoint working")
        else:
            print(f"   ERROR Health endpoint failed: {response.status_code}")
    
    print("\nMinimal startup test PASSED!")
    print("The app should be able to start without AI components")
    
except Exception as e:
    print(f"\nERROR Minimal startup test FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)