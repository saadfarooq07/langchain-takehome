#!/usr/bin/env python3
"""Set up the authentication database with multi-tenant support."""

import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.log_analyzer_agent.services.better_auth import BetterAuth, AuthConfig


async def main():
    """Set up the authentication database."""
    # Load environment variables
    load_dotenv()
    
    # Get database URL
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL not found in environment variables")
        return 1
    
    # Check required environment variables
    if not os.getenv("BETTER_AUTH_SECRET"):
        print("❌ BETTER_AUTH_SECRET not found in environment variables")
        print("💡 Generate one with: openssl rand -base64 32")
        return 1
    
    print("🔧 Setting up authentication database...")
    print(f"📊 Database: {database_url}")
    
    try:
        # Initialize auth service
        auth = BetterAuth(database_url)
        
        # Set up database
        await auth.setup_database()
        print("✅ Database tables created successfully")
        
        # Create a demo tenant if requested
        if "--demo" in sys.argv:
            print("\n📦 Creating demo tenant...")
            success, message, data = await auth.create_tenant(
                name="Demo Organization",
                slug="demo",
                owner_email="admin@demo.local",
                owner_password="demo123456",
                owner_name="Demo Admin",
                description="Demo tenant for testing",
                plan="free"
            )
            
            if success:
                print("✅ Demo tenant created successfully")
                print(f"📧 Admin email: admin@demo.local")
                print(f"🔑 Admin password: demo123456")
                print(f"🔐 API Key: {data['api_key']}")
                print(f"🏢 Tenant ID: {data['tenant_id']}")
                print("\n⚠️  Please change the password after first login!")
            else:
                print(f"❌ Failed to create demo tenant: {message}")
        
        print("\n✅ Setup completed successfully!")
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))