#!/usr/bin/env python3
"""
Simple startup test to debug Railway deployment issues
"""

import sys
import os

print("Railway Startup Debug Test")
print("=" * 40)

# Test 1: Python version
print(f"Python version: {sys.version}")

# Test 2: Environment variables
print(f"PORT: {os.getenv('PORT', 'Not set')}")
print(f"RAILWAY_ENVIRONMENT: {os.getenv('RAILWAY_ENVIRONMENT', 'Not set')}")

# Test 3: Working directory
print(f"Working directory: {os.getcwd()}")
print(f"Python path: {sys.path}")

# Test 4: File structure
print("\nFile structure:")
for root, dirs, files in os.walk("."):
    level = root.replace(".", "").count(os.sep)
    indent = " " * 2 * level
    print(f"{indent}{os.path.basename(root)}/")
    subindent = " " * 2 * (level + 1)
    for file in files[:5]:  # Show first 5 files
        print(f"{subindent}{file}")
    if len(files) > 5:
        print(f"{subindent}... and {len(files) - 5} more files")

# Test 5: Critical imports
print("\nTesting critical imports:")
try:
    import flask
    print(f"[OK] Flask version: {flask.__version__}")
except ImportError as e:
    print(f"[FAIL] Flask import failed: {e}")

try:
    import sqlalchemy
    print(f"[OK] SQLAlchemy version: {sqlalchemy.__version__}")
except ImportError as e:
    print(f"[FAIL] SQLAlchemy import failed: {e}")

try:
    from src.models.user import db
    print("[OK] User models imported successfully")
except ImportError as e:
    print(f"[FAIL] User models import failed: {e}")

try:
    from src.routes.auth import auth_bp
    print("[OK] Auth routes imported successfully")
except ImportError as e:
    print(f"[FAIL] Auth routes import failed: {e}")

# Test 6: AI components (optional)
try:
    from src.agents.sage_agent import SageAgentManager
    print("[OK] AI Agent components available")
except ImportError as e:
    print(f"[WARN] AI components not available: {e}")

print("\nStartup test completed")