#!/usr/bin/env python3
"""Fix database schema for Google OAuth support."""

import asyncio
import os
from pathlib import Path
import sys

# Add parent directory to path to import our modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.log_analyzer_agent.db_pool import get_db_pool


async def fix_schema():
    """Add missing columns for Google OAuth support."""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("❌ DATABASE_URL environment variable is required")
        return False
    
    try:
        pool = await get_db_pool(db_url)
        async with pool.acquire() as conn:
            print("🔧 Adding missing columns for Google OAuth support...")
            
            # Add google_id column to users table
            await conn.execute("""
                ALTER TABLE users 
                ADD COLUMN IF NOT EXISTS google_id VARCHAR(255) UNIQUE
            """)
            print("✅ Added google_id column to users table")
            
            # Add email_verified column to users table
            await conn.execute("""
                ALTER TABLE users 
                ADD COLUMN IF NOT EXISTS email_verified BOOLEAN DEFAULT FALSE
            """)
            print("✅ Added email_verified column to users table")
            
            # Make hashed_password nullable for OAuth users
            await conn.execute("""
                ALTER TABLE users 
                ALTER COLUMN hashed_password DROP NOT NULL
            """)
            print("✅ Made hashed_password nullable for OAuth users")
            
            # Add owner_id column to tenants table
            await conn.execute("""
                ALTER TABLE tenants 
                ADD COLUMN IF NOT EXISTS owner_id UUID REFERENCES users(id)
            """)
            print("✅ Added owner_id column to tenants table")
            
            # Create index on google_id for faster lookups
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_users_google_id ON users(google_id)
            """)
            print("✅ Created index on google_id")
            
            print("\n✨ Schema updates completed successfully!")
            return True
            
    except Exception as e:
        print(f"❌ Error updating schema: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main function."""
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    success = await fix_schema()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())