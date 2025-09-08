#!/usr/bin/env python3
"""
Direct Sage Tools Test - Tests tools by running them directly from backend
"""
import sys
import os

# Add backend src to path
backend_src = os.path.join(os.path.dirname(__file__), 'backend', 'src')
sys.path.insert(0, backend_src)

def test_sage_tools_import():
    """Test importing Sage tools directly"""
    print("=== TESTING SAGE TOOLS IMPORT ===")
    
    try:
        from tools.sage_tools import SAGE_TOOLS
        print(f"Successfully imported SAGE_TOOLS with {len(SAGE_TOOLS)} tools")
        
        # Test each tool
        for tool in SAGE_TOOLS:
            print(f"Tool: {tool.name} - {tool.description[:60]}...")
        
        return True
    except Exception as e:
        print(f"Failed to import SAGE_TOOLS: {e}")
        return False

def test_tool_conversion():
    """Test tool conversion to LangChain"""
    print("\n=== TESTING TOOL CONVERSION ===")
    
    try:
        from tools.sage_tools import SAGE_TOOLS
        from utils.tool_converter import convert_sage_tools_to_langchain
        
        langchain_tools = convert_sage_tools_to_langchain(SAGE_TOOLS)
        print(f"Successfully converted {len(langchain_tools)} tools to LangChain format")
        
        # Test each converted tool
        for tool in langchain_tools:
            print(f"+ LangChain Tool: {tool.name}")
            
            # Test Pydantic v2 compatibility
            if hasattr(tool, 'model_fields'):
                print(f"  - Pydantic v2 compatible: {list(tool.model_fields.keys())}")
            elif hasattr(tool, '__fields__'):
                print(f"  - Pydantic fields: {list(tool.__fields__.keys())}")
        
        return True
    except Exception as e:
        print(f"- Tool conversion failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_individual_tool_execution():
    """Test individual tool execution"""
    print("\n=== TESTING INDIVIDUAL TOOL EXECUTION ===")
    
    try:
        from tools.sage_tools import CreateCustomerTool
        
        tool = CreateCustomerTool()
        
        # Test with no credentials (should return proper error)
        result = tool._run(name="Test Customer", email="test@example.com")
        
        if "Aucune connexion Sage détectée" in result:
            print("+ CreateCustomerTool properly handles missing credentials")
            return True
        else:
            print(f"- Unexpected result: {result}")
            return False
            
    except Exception as e:
        print(f"- Tool execution test failed: {e}")
        return False

def test_api_services():
    """Test API services"""
    print("\n=== TESTING API SERVICES ===")
    
    try:
        from services.sage_auth import SageOAuth2Service
        from services.sage_api import SageAPIService
        
        # Test OAuth service
        oauth = SageOAuth2Service("test", "test", "test")
        print("+ SageOAuth2Service initialized")
        
        # Test API service
        api = SageAPIService(oauth)
        print("+ SageAPIService initialized")
        
        # Test PKCE generation
        verifier, challenge = oauth.generate_pkce_pair()
        print(f"+ PKCE generation works: {len(verifier)} char verifier, {len(challenge)} char challenge")
        
        return True
    except Exception as e:
        print(f"- API services test failed: {e}")
        return False

def run_all_tests():
    """Run all tests"""
    print("SAGE TOOLS DIRECT TEST SUITE")
    print("=" * 50)
    
    results = []
    
    results.append(test_sage_tools_import())
    results.append(test_tool_conversion())
    results.append(test_individual_tool_execution())
    results.append(test_api_services())
    
    passed = sum(results)
    total = len(results)
    
    print(f"\n=== TEST RESULTS ===")
    print(f"Passed: {passed}/{total}")
    print(f"Success Rate: {(passed/total*100):.1f}%")
    
    if passed == total:
        print("SUCCESS: ALL TESTS PASSED!")
    elif passed >= total * 0.75:
        print("OK Most tests passed - system is functional")
    else:
        print("WARNING  Some critical tests failed")

if __name__ == "__main__":
    run_all_tests()