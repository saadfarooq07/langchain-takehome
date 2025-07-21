#!/usr/bin/env python3
"""Create a simple demo user that works with the frontend."""

import asyncio
import asyncpg
import os
import bcrypt
from dotenv import load_dotenv

load_dotenv()

async def create_simple_demo_user():
    """Create demo user and associate with default tenant."""
    db_url = os.getenv(
        "DATABASE_URL", "postgresql://loganalyzer:password@localhost:5432/loganalyzer"
    )
    
    conn = await asyncpg.connect(db_url)
    try:
        # First, ensure demo tenant exists and is default
        tenant = await conn.fetchrow("""
            SELECT id FROM tenants WHERE slug = 'demo'
        """)
        
        if not tenant:
            print("Demo tenant not found!")
            return
            
        tenant_id = tenant['id']
        
        # Create or update demo2 user (simpler for testing)
        email = "demo2@example.com"
        password = "demo123"
        hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        
        # Check if user exists
        existing_user = await conn.fetchrow("""
            SELECT id FROM users WHERE email = $1
        """, email)
        
        if existing_user:
            # Update user
            await conn.execute("""
                UPDATE users 
                SET hashed_password = $1, is_verified = TRUE, is_active = TRUE, verified_at = NOW()
                WHERE email = $2
            """, hashed_password, email)
            user_id = existing_user['id']
            print(f"Updated existing user: {email}")
        else:
            # Create user
            user_id = await conn.fetchval("""
                INSERT INTO users (email, hashed_password, full_name, is_verified, verified_at, is_active)
                VALUES ($1, $2, $3, TRUE, NOW(), TRUE)
                RETURNING id
            """, email, hashed_password, "Demo User 2")
            print(f"Created new user: {email}")
        
        # Ensure user is in demo tenant
        membership = await conn.fetchrow("""
            SELECT id FROM tenant_users 
            WHERE tenant_id = $1 AND user_id = $2
        """, tenant_id, user_id)
        
        if not membership:
            await conn.execute("""
                INSERT INTO tenant_users (tenant_id, user_id, role, accepted_at, is_active)
                VALUES ($1, $2, 'admin', NOW(), TRUE)
            """, tenant_id, user_id)
            print(f"Added user to demo tenant")
        else:
            await conn.execute("""
                UPDATE tenant_users 
                SET is_active = TRUE, role = 'admin', accepted_at = NOW()
                WHERE tenant_id = $1 AND user_id = $2
            """, tenant_id, user_id)
            print(f"Updated user membership")
        
        print(f"\n✅ Demo user ready:")
        print(f"Email: {email}")
        print(f"Password: {password}")
        print(f"Tenant: demo")
        
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(create_simple_demo_user())