#!/usr/bin/env python3
"""Verify the demo user account."""

import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def verify_demo_user():
    """Mark demo user as verified."""
    db_url = os.getenv(
        "DATABASE_URL", "postgresql://loganalyzer:password@localhost:5432/loganalyzer"
    )
    
    conn = await asyncpg.connect(db_url)
    try:
        # Update demo user to be verified
        result = await conn.execute("""
            UPDATE users 
            SET is_verified = TRUE, verified_at = NOW()
            WHERE email = 'demo@example.com'
        """)
        
        print(f"Updated: {result}")
        
        # Check if user exists and is verified
        user = await conn.fetchrow("""
            SELECT id, email, is_verified, is_active
            FROM users
            WHERE email = 'demo@example.com'
        """)
        
        if user:
            print(f"User found: {user['email']}")
            print(f"Is verified: {user['is_verified']}")
            print(f"Is active: {user['is_active']}")
        else:
            print("Demo user not found!")
            
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(verify_demo_user())