#!/usr/bin/env python3
"""Comprehensive test runner for the log analyzer system."""

import asyncio
import os
import sys
import subprocess
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))


def run_command(cmd, timeout=60):
    """Run a shell command with timeout."""
    try:
        result = subprocess.run(
            cmd, 
            shell=True, 
            capture_output=True, 
            text=True,
            timeout=timeout
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"
    except Exception as e:
        return False, "", str(e)


def check_environment():
    """Check if all required environment variables are set."""
    print("Checking environment variables...")
    
    required_vars = [
        "DATABASE_URL",
        "GEMINI_API_KEY", 
        "GROQ_API_KEY",
        "TAVILY_API_KEY",
        "BETTER_AUTH_SECRET"
    ]
    
    missing = []
    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)
    
    if missing:
        print(f"✗ Missing environment variables: {missing}")
        print("Please set these in your .env file")
        return False
    
    print("✓ All required environment variables are set")
    return True


def check_dependencies():
    """Check if all required dependencies are installed."""
    print("Checking dependencies...")
    
    try:
        import langchain
        import langgraph
        import fastapi
        import asyncpg
        import psycopg
        import bcrypt
        import jwt
        print("✓ All required dependencies are installed")
        return True
    except ImportError as e:
        print(f"✗ Missing dependency: {e}")
        print("Please run: pip install -r requirements.txt")
        return False


def check_database_connection():
    """Check if database is accessible."""
    print("Checking database connection...")
    
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("✗ DATABASE_URL not set")
        return False
    
    try:
        import asyncpg
        
        async def test_connection():
            conn = await asyncpg.connect(db_url)
            await conn.close()
            return True
        
        result = asyncio.run(test_connection())
        print("✓ Database connection successful")
        return result
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return False


def test_basic_functionality():
    """Test basic functionality without memory."""
    print("Testing basic functionality...")
    
    try:
        success, stdout, stderr = run_command("python main.py --mode test", timeout=120)
        
        if success and "Analysis Result:" in stdout:
            print("✓ Basic functionality test passed")
            return True
        else:
            print(f"✗ Basic functionality test failed")
            print(f"STDOUT: {stdout}")
            print(f"STDERR: {stderr}")
            return False
            
    except Exception as e:
        print(f"✗ Basic functionality test failed: {e}")
        return False


def test_system_integration():
    """Test system integration with memory."""
    print("Testing system integration...")
    
    try:
        success, stdout, stderr = run_command("python test_system.py", timeout=180)
        
        if success and "All tests passed" in stdout:
            print("✓ System integration test passed")
            return True
        else:
            print(f"✗ System integration test failed")
            print(f"STDOUT: {stdout}")
            print(f"STDERR: {stderr}")
            return False
            
    except Exception as e:
        print(f"✗ System integration test failed: {e}")
        return False


def test_api_startup():
    """Test API server startup."""
    print("Testing API server startup...")
    
    try:
        # Start API server in background
        import threading
        import requests
        import uvicorn
        
        def run_server():
            from src.log_analyzer_agent.api.main import app
            uvicorn.run(app, host="127.0.0.1", port=8001, log_level="error")
        
        # Start server in thread
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()
        
        # Wait for server to start
        time.sleep(5)
        
        # Test health endpoint
        response = requests.get("http://127.0.0.1:8001/health", timeout=10)
        
        if response.status_code == 200:
            print("✓ API server startup test passed")
            return True
        else:
            print(f"✗ API server startup test failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"✗ API server startup test failed: {e}")
        return False


def run_all_tests():
    """Run all tests in sequence."""
    print("Log Analyzer Agent - Comprehensive Test Suite")
    print("=" * 60)
    
    tests = [
        ("Environment Check", check_environment),
        ("Dependencies Check", check_dependencies),
        ("Database Connection", check_database_connection),
        ("Basic Functionality", test_basic_functionality),
        ("System Integration", test_system_integration),
        ("API Server Startup", test_api_startup),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'-' * 20} {test_name} {'-' * 20}")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"✗ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print(f"\n{'=' * 60}")
    print("Test Summary:")
    print(f"{'=' * 60}")
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! The system is fully functional.")
        print("\nYou can now:")
        print("1. Start the API server: python main.py --mode api")
        print("2. View API docs at: http://localhost:8000/docs")
        print("3. Test with demo user: demo@example.com / demopassword123")
        return True
    else:
        print("\n❌ Some tests failed. Please check the logs above.")
        print("\nNext steps:")
        print("1. Fix any failing tests")
        print("2. Check your .env file configuration")
        print("3. Ensure database is running and accessible")
        return False


if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    success = run_all_tests()
    sys.exit(0 if success else 1)