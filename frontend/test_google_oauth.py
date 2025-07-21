#!/usr/bin/env python3
"""Test Google OAuth configuration."""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from parent .env file
load_dotenv(Path(__file__).parent.parent / '.env')

print("Google OAuth Configuration Test")
print("=" * 50)

# Check environment variable
google_client_id = os.getenv("GOOGLE_CLIENT_ID")
print(f"GOOGLE_CLIENT_ID: {google_client_id}")

if google_client_id:
    print("✅ GOOGLE_CLIENT_ID is set")
    print(f"   Client ID: {google_client_id[:20]}...")
else:
    print("❌ GOOGLE_CLIENT_ID is NOT set")
    print("   Please set it in your .env file")

# Check if google auth libraries are available
try:
    from google.oauth2 import id_token
    from google.auth.transport import requests
    print("\n✅ Google OAuth libraries are installed")
except ImportError as e:
    print(f"\n❌ Missing Google OAuth libraries: {e}")
    print("   Run: pip install google-auth google-auth-oauthlib google-auth-httplib2")

print("\n" + "=" * 50)
print("To fix the 401 error:")
print("1. Restart the backend server to load the GOOGLE_CLIENT_ID")
print("2. Run: pkill -f 'python.*main.py.*--api'")
print("3. Run: python main.py --use-improved --api")
print("\nOr if running in a terminal, press Ctrl+C and restart.")