#!/usr/bin/env python3
"""
Startup test for LLM configuration (Expert recommended)
Tests ChatOpenAI instantiation to catch proxy errors early
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_llm_startup():
    """Expert recommended: Test LLM instantiation at startup"""
    try:
        from langchain_openai import ChatOpenAI
        import httpx
        
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("⚠️ OPENAI_API_KEY not set - skipping LLM test")
            return False
        
        # Expert solution: proxy via httpx client
        proxy = os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY")
        http_client = httpx.Client(proxies=proxy, timeout=30.0) if proxy else None
        
        llm_config = {
            "model": "gpt-4o-mini",
            "api_key": api_key,
            "base_url": os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1"),
            "temperature": 0.1,
            "max_tokens": 50
        }
        
        if http_client:
            llm_config["http_client"] = http_client
            print(f"🌐 Using proxy: {proxy}")
        
        # Instantiate LLM
        llm = ChatOpenAI(**llm_config)
        
        # Quick test invoke
        response = llm.invoke("ping")
        
        print("✅ LLM startup test PASSED - No proxy errors")
        print(f"✅ Response: {response.content[:50]}...")
        return True
        
    except Exception as e:
        print(f"❌ LLM startup test FAILED: {e}")
        return False

if __name__ == "__main__":
    success = test_llm_startup()
    sys.exit(0 if success else 1)