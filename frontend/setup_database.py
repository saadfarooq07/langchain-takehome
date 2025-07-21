#!/usr/bin/env python3
"""
Database setup script for authentication tables.
Run this to initialize the database for OAuth functionality.
"""
import asyncio
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(Path(__file__).parent.parent / '.env')

# Add parent directory to path to import from src
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.log_analyzer_agent.services.better_auth import BetterAuth, AuthConfig

async def setup_db():
    try:
        db_url = os.getenv('DATABASE_URL', 'postgresql://loganalyzer:password@localhost:5432/loganalyzer')
        config = AuthConfig(
            secret_key=os.getenv('BETTER_AUTH_SECRET', 'your_secret_key_here_min_32_chars_long_for_security')
        )
        auth_service = BetterAuth(db_url, config)
        print('🔄 Initializing database tables...')
        await auth_service.setup_database()
        print('✅ Database tables created successfully!')
        
        # Test connection
        pool = await auth_service._get_db_pool()
        async with pool.acquire() as conn:
            result = await conn.fetchval("SELECT COUNT(*) FROM information_schema.tables WHERE table_name IN ('users', 'tenants', 'tenant_users', 'user_sessions')")
            print(f'✅ Found {result} auth tables in database')
        
        return True
    except Exception as e:
        print(f'❌ Error setting up database: {e}')
        return False

async def create_demo_tenant():
    """Create a demo tenant and user for testing."""
    try:
        db_url = os.getenv('DATABASE_URL', 'postgresql://loganalyzer:password@localhost:5432/loganalyzer')
        config = AuthConfig(
            secret_key=os.getenv('BETTER_AUTH_SECRET', 'your_secret_key_here_min_32_chars_long_for_security')
        )
        auth_service = BetterAuth(db_url, config)
        
        print('🔄 Creating demo tenant and user...')
        success, message, data = await auth_service.create_tenant(
            name="Demo Organization",
            slug="demo",
            owner_email="demo@example.com",
            owner_password="demopassword123",
            owner_name="Demo User",
            description="Demo tenant for testing"
        )
        
        if success:
            print(f'✅ Demo tenant created: {message}')
            print(f'   - Tenant ID: {data["tenant_id"]}')
            print(f'   - User ID: {data["user_id"]}')
            print(f'   - API Key: {data["api_key"][:20]}...')
        else:
            print(f'⚠️  Demo tenant creation: {message}')
            
        return success
    except Exception as e:
        print(f'❌ Error creating demo tenant: {e}')
        return False

if __name__ == '__main__':
    print("🚀 Setting up authentication database...")
    print(f"Database URL: {os.getenv('DATABASE_URL', 'postgresql://loganalyzer:password@localhost:5432/loganalyzer')}")
    
    # Setup database tables
    success = asyncio.run(setup_db())
    if not success:
        sys.exit(1)
    
    # Create demo tenant
    demo_success = asyncio.run(create_demo_tenant())
    
    print("\n" + "="*50)
    if success and demo_success:
        print("🎉 Setup completed successfully!")
        print("\nDemo credentials:")
        print("  Email: demo@example.com")
        print("  Password: demopassword123")
        print("  Tenant: demo")
    elif success:
        print("✅ Database setup completed!")
        print("⚠️  Demo tenant may already exist or failed to create")
    
    sys.exit(0 if success else 1)