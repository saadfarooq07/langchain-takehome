#!/usr/bin/env python3
"""Test environment variable loading in the graph."""

import os
import sys

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Test 1: Check if .env is loaded
print("=== Testing Environment Variable Loading ===")
print(f"GEMINI_API_KEY before import: {os.getenv('GEMINI_API_KEY')}")

# Test 2: Import the graph (which should load dotenv)
try:
    from log_analyzer_agent.graph import graph
    print(f"GEMINI_API_KEY after graph import: {os.getenv('GEMINI_API_KEY')}")
    print("✓ Graph imported successfully")
except Exception as e:
    print(f"✗ Error importing graph: {e}")
    import traceback
    traceback.print_exc()

# Test 3: Try to initialize a model
try:
    from log_analyzer_agent.utils import init_model
    model = init_model()
    print("✓ Model initialized successfully")
except Exception as e:
    print(f"✗ Error initializing model: {e}")

# Test 4: Check all required env vars
print("\n=== Checking All Required Environment Variables ===")
required_vars = ['GEMINI_API_KEY', 'GROQ_API_KEY', 'TAVILY_API_KEY']
for var in required_vars:
    value = os.getenv(var)
    if value:
        print(f"✓ {var}: {'*' * 10 + value[-4:]}")
    else:
        print(f"✗ {var}: Not set")