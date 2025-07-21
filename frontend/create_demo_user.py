#!/usr/bin/env python3
"""
Create demo user script using synchronous approach.
"""
import os
import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(Path(__file__).parent.parent / '.env')

# Add parent directory to path to import from src
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.log_analyzer_agent.services.better_auth import BetterAuth, AuthConfig

async def create_demo_user_simple():
    """Create a demo user with a simplified approach."""
    try:
        db_url = os.getenv('DATABASE_URL', 'postgresql://loganalyzer:password@localhost:5432/loganalyzer')
        config = AuthConfig(
            secret_key=os.getenv('BETTER_AUTH_SECRET', 'your_secret_key_here_min_32_chars_long_for_security')
        )
        auth_service = BetterAuth(db_url, config)
        
        print('🔄 Creating demo user...')
        success, message, data = await auth_service.create_tenant(
            name="Demo Organization",
            slug="demo",
            owner_email="demo@example.com",
            owner_password="demopassword123",
            owner_name="Demo User",
            description="Demo tenant for testing"
        )
        
        if success:
            print(f'✅ {message}')
            print(f'   - API Key: {data["api_key"][:20]}...')
        else:
            print(f'ℹ️  {message} (may already exist)')
            
        # Try creating a second demo user
        success2, message2, data2 = await auth_service.create_tenant(
            name="Test Company",
            slug="test",
            owner_email="test@example.com",
            owner_password="testpassword123",
            owner_name="Test User",
            description="Test tenant for authentication"
        )
        
        if success2:
            print(f'✅ {message2}')
            print(f'   - API Key: {data2["api_key"][:20]}...')
        else:
            print(f'ℹ️  {message2} (may already exist)')
        
        return True
    except Exception as e:
        print(f'❌ Error: {e}')
        return False

if __name__ == '__main__':
    print("🚀 Creating demo users...")
    success = asyncio.run(create_demo_user_simple())
    
    print("\n" + "="*50)
    if success:
        print("✅ Demo users setup completed!")
        print("\nDemo credentials:")
        print("  1. Email: demo@example.com")
        print("     Password: demopassword123")
        print("     Tenant: demo")
        print("")
        print("  2. Email: test@example.com")
        print("     Password: testpassword123")
        print("     Tenant: test")
        print("\nYou can now test the login flow!")
    else:
        print("❌ Failed to create demo users")