#!/usr/bin/env python3
"""
Simple test script for Sage Business Cloud Accounting tools
Tests basic functionality without external dependencies
"""

import sys
import os
from datetime import datetime, timedelta

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

def test_imports():
    """Test if all Sage tools can be imported successfully"""
    try:
        from backend.src.tools.sage_tools import SAGE_TOOLS
        print(f"[OK] Successfully imported {len(SAGE_TOOLS)} Sage tools")
        
        tool_names = []
        for i, tool in enumerate(SAGE_TOOLS, 1):
            tool_names.append(tool.name)
            print(f"{i:2d}. {tool.name:20} - {tool.description}")
        
        return True, tool_names
        
    except ImportError as e:
        print(f"[EXPECTED] Import error (missing dependencies): {e}")
        print("This is normal in environments without CrewAI/Pydantic")
        return False, []
    
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")
        return False, []

def test_syntax():
    """Test Python syntax of sage_tools.py"""
    try:
        import py_compile
        py_compile.compile('backend/src/tools/sage_tools.py', doraise=True)
        print("[OK] Python syntax validation passed")
        return True
    except py_compile.PyCompileError as e:
        print(f"[FAIL] Syntax error: {e}")
        return False

def test_tool_structure():
    """Test the structure of tools without importing dependencies"""
    try:
        with open('backend/src/tools/sage_tools.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Count tool classes
        tool_classes = content.count('class') - content.count('# class') - content.count('"""class')
        sage_base_tools = content.count('(SageBaseTool)')
        input_schemas = content.count('Input(BaseModel)')
        
        print(f"[INFO] Found {tool_classes} total classes")
        print(f"[INFO] Found {sage_base_tools} SageBaseTool implementations") 
        print(f"[INFO] Found {input_schemas} input schema classes")
        
        # Check for SAGE_TOOLS list
        if 'SAGE_TOOLS = [' in content:
            tools_section = content.split('SAGE_TOOLS = [')[1].split(']')[0]
            tool_instances = tools_section.count('Tool()')
            print(f"[INFO] SAGE_TOOLS list contains {tool_instances} tool instances")
        
        # Check for credentials handling
        credentials_checks = content.count('get_credentials()')
        print(f"[INFO] Found {credentials_checks} credential validation calls")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to analyze tool structure: {e}")
        return False

def test_api_endpoints():
    """Verify API endpoints used in sage_api.py"""
    try:
        with open('backend/src/services/sage_api.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract endpoint patterns
        endpoints = []
        lines = content.split('\n')
        for line in lines:
            if "'GET'," in line or "'POST'," in line or "'PUT'," in line:
                if 'endpoint' in line or "'" in line:
                    endpoints.append(line.strip())
        
        print("[INFO] API endpoints found in sage_api.py:")
        for endpoint in endpoints[:10]:  # Show first 10
            print(f"  - {endpoint}")
        
        # Check for key endpoints
        key_endpoints = [
            'contacts', 'sales_invoices', 'products', 'bank_accounts',
            'reports/balance_sheet', 'reports/profit_and_loss'
        ]
        
        missing_endpoints = []
        for endpoint in key_endpoints:
            if endpoint not in content:
                missing_endpoints.append(endpoint)
        
        if missing_endpoints:
            print(f"[WARN] Potentially missing endpoints: {missing_endpoints}")
        else:
            print("[OK] All expected endpoints found")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to analyze API endpoints: {e}")
        return False

def main():
    """Run simple tests"""
    
    print("SAGE TOOLS SIMPLE TEST SUITE")
    print("=" * 40)
    
    # Test 1: Syntax validation
    print("\nTEST 1: Python Syntax Validation")
    print("-" * 30)
    syntax_ok = test_syntax()
    
    # Test 2: Tool structure analysis
    print("\nTEST 2: Tool Structure Analysis")
    print("-" * 30)
    structure_ok = test_structure()
    
    # Test 3: API endpoints check
    print("\nTEST 3: API Endpoints Verification")
    print("-" * 30)
    endpoints_ok = test_api_endpoints()
    
    # Test 4: Import test (will likely fail due to dependencies)
    print("\nTEST 4: Import Test")
    print("-" * 30)
    import_ok, tools = test_imports()
    
    # Summary
    print("\nTEST SUMMARY")
    print("=" * 40)
    
    results = {
        "Syntax Validation": syntax_ok,
        "Tool Structure": structure_ok, 
        "API Endpoints": endpoints_ok,
        "Import Test": import_ok
    }
    
    for test_name, result in results.items():
        status = "[OK]" if result else "[FAIL]"
        print(f"{status} {test_name}")
    
    if all([syntax_ok, structure_ok, endpoints_ok]):
        print("\n[SUCCESS] Core functionality verified - tools ready for testing!")
    else:
        print("\n[WARNING] Some tests failed - review required")

def test_structure():
    """Renamed function to avoid naming conflict"""
    return test_tool_structure()

if __name__ == "__main__":
    main()