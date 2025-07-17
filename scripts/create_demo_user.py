#!/usr/bin/env python3
"""Script to create a demo user for testing."""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from log_analyzer_agent.services.auth_service import AuthService


async def create_demo_user():
    """Create a demo user for testing."""
    load_dotenv()
    
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL environment variable is required")
        sys.exit(1)
    
    auth_service = AuthService(db_url)
    
    # Create demo user
    email = "demo@example.com"
    password = "demopassword123"
    full_name = "Demo User"
    
    print(f"Creating demo user: {email}")
    
    success, message, user_data = await auth_service.create_user(
        email=email,
        password=password,
        full_name=full_name
    )
    
    if success:
        print(f"✓ Demo user created successfully!")
        print(f"User ID: {user_data['id']}")
        print(f"Email: {user_data['email']}")
        print(f"Full Name: {user_data['full_name']}")
        print(f"Created At: {user_data['created_at']}")
        
        # Test authentication
        print("\nTesting authentication...")
        success, message, auth_data = await auth_service.authenticate_user(
            email=email,
            password=password
        )
        
        if success:
            print("✓ Authentication successful!")
            print(f"Access Token: {auth_data['access_token'][:50]}...")
        else:
            print(f"✗ Authentication failed: {message}")
    else:
        if "already exists" in message:
            print(f"Demo user already exists: {email}")
        else:
            print(f"✗ Failed to create demo user: {message}")


if __name__ == "__main__":
    asyncio.run(create_demo_user())