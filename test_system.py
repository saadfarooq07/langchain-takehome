#!/usr/bin/env python3
"""Test script to verify the system is working properly."""

import asyncio
import json
import os
import sys
import time
from typing import Dict, Any

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from log_analyzer_agent.services.auth_service import AuthService
from log_analyzer_agent.services.memory_service import MemoryService
from log_analyzer_agent.graph import create_enhanced_graph
from log_analyzer_agent.state import State


async def test_auth_service():
    """Test the authentication service."""
    print("Testing Authentication Service...")
    
    db_url = os.getenv("DATABASE_URL", "postgresql://loganalyzer:password@localhost:5432/loganalyzer")
    auth_service = AuthService(db_url)
    
    # Setup tables
    await auth_service.setup_tables()
    print("✓ Database tables set up")
    
    # Create test user
    email = "test@example.com"
    password = "testpassword123"
    
    success, message, user_data = await auth_service.create_user(
        email=email,
        password=password,
        full_name="Test User"
    )
    
    if success:
        print(f"✓ User created: {user_data['email']}")
    else:
        if "already exists" in message:
            print(f"✓ User already exists: {email}")
        else:
            print(f"✗ Failed to create user: {message}")
            return False
    
    # Test authentication
    success, message, auth_data = await auth_service.authenticate_user(
        email=email,
        password=password
    )
    
    if success:
        print(f"✓ Authentication successful")
        return auth_data
    else:
        print(f"✗ Authentication failed: {message}")
        return False


async def test_memory_service():
    """Test the memory service."""
    print("\nTesting Memory Service...")
    
    try:
        graph, store, checkpointer = await create_enhanced_graph()
        print("✓ Memory backend initialized")
        
        memory_service = MemoryService(store)
        
        # Test storing analysis result
        user_id = "test_user"
        application_name = "test_app"
        log_content = "ERROR: Database connection failed"
        
        analysis_result = {
            "issues": [
                {
                    "type": "database_error",
                    "description": "Database connection failed",
                    "severity": "high"
                }
            ],
            "suggestions": ["Check database connection settings"],
            "documentation_references": []
        }
        
        performance_metrics = {
            "response_time": 1.5,
            "memory_searches": 2,
            "similar_issues_found": 0
        }
        
        memory_id = await memory_service.store_analysis_result(
            user_id, application_name, log_content, analysis_result, performance_metrics
        )
        print(f"✓ Analysis result stored with ID: {memory_id}")
        
        # Test searching similar issues
        similar_issues = await memory_service.search_similar_issues(
            user_id, application_name, "database connection error"
        )
        print(f"✓ Found {len(similar_issues)} similar issues")
        
        # Test application context
        context_data = {
            "common_patterns": ["database_errors", "connection_timeouts"],
            "successful_solutions": ["restart database", "check network"],
            "environment_info": {"database": "PostgreSQL", "version": "14.5"}
        }
        
        context_id = await memory_service.store_application_context(
            user_id, application_name, context_data
        )
        print(f"✓ Application context stored with ID: {context_id}")
        
        # Test retrieving context
        retrieved_context = await memory_service.get_application_context(
            user_id, application_name
        )
        print(f"✓ Retrieved application context: {len(retrieved_context)} items")
        
        # Test user preferences
        preferences = {
            "analysis_style": "detailed",
            "include_commands": True,
            "severity_threshold": "medium"
        }
        
        pref_id = await memory_service.store_user_preferences(user_id, preferences)
        print(f"✓ User preferences stored with ID: {pref_id}")
        
        # Test retrieving preferences
        retrieved_prefs = await memory_service.get_user_preferences(user_id)
        print(f"✓ Retrieved user preferences: {len(retrieved_prefs)} items")
        
        # Clean up
        await store.close()
        await checkpointer.close()
        
        return True
        
    except Exception as e:
        print(f"✗ Memory service test failed: {e}")
        return False


async def test_enhanced_analysis():
    """Test the enhanced analysis with memory."""
    print("\nTesting Enhanced Analysis...")
    
    try:
        graph, store, checkpointer = await create_enhanced_graph()
        
        # Create test state
        state = State(
            log_content="""
            2023-08-15T14:25:12.345Z ERROR [app.main] Failed to connect to database: Connection refused
            2023-08-15T14:25:12.567Z INFO [app.main] Retrying database connection (attempt 1/5)
            2023-08-15T14:25:13.123Z ERROR [app.main] Retry failed: Connection refused
            2023-08-15T14:25:14.123Z FATAL [app.main] Application startup failed: Database connection error
            """,
            user_id="test_user",
            application_name="test_app",
            environment_details={
                "database": "PostgreSQL 14.5",
                "environment": "production"
            }
        )
        
        config = {
            "configurable": {
                "user_id": "test_user",
                "thread_id": state.thread_id,
                "model": "gemini:gemini-1.5-flash",
                "max_search_results": 3,
            }
        }
        
        print("Running enhanced analysis...")
        result = None
        event_count = 0
        
        async for event in graph.astream(
            state.__dict__,
            config,
            stream_mode="values"
        ):
            event_count += 1
            print(f"  Event {event_count}: {list(event.keys())}")
            
            if "analysis_result" in event and event["analysis_result"]:
                result = event["analysis_result"]
                break
        
        if result:
            print(f"✓ Analysis completed successfully")
            print(f"  - Issues found: {len(result.get('issues', []))}")
            print(f"  - Suggestions: {len(result.get('suggestions', []))}")
            print(f"  - Documentation refs: {len(result.get('documentation_references', []))}")
            
            # Pretty print the first issue
            if result.get('issues'):
                first_issue = result['issues'][0]
                print(f"  - First issue: {first_issue.get('description', 'No description')}")
        else:
            print("✗ No analysis result produced")
        
        # Clean up
        await store.close()
        await checkpointer.close()
        
        return result is not None
        
    except Exception as e:
        print(f"✗ Enhanced analysis test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    print("Log Analyzer Agent System Test")
    print("=" * 50)
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Check required environment variables
    required_vars = ["DATABASE_URL", "GEMINI_API_KEY", "GROQ_API_KEY", "TAVILY_API_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"✗ Missing required environment variables: {missing_vars}")
        print("Please set these in your .env file")
        return False
    
    print("✓ All required environment variables are set")
    
    # Run tests
    tests = [
        ("Authentication Service", test_auth_service),
        ("Memory Service", test_memory_service),
        ("Enhanced Analysis", test_enhanced_analysis),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"✗ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print(f"\n{'='*50}")
    print("Test Summary:")
    print(f"{'='*50}")
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The system is working correctly.")
        return True
    else:
        print("❌ Some tests failed. Please check the logs above.")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)