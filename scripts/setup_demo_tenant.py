#!/usr/bin/env python3
"""Setup demo tenant and associate demo user."""

import asyncio
import asyncpg
import os
import uuid
from dotenv import load_dotenv

load_dotenv()

async def setup_demo_tenant():
    """Create demo tenant and associate demo user."""
    db_url = os.getenv(
        "DATABASE_URL", "postgresql://loganalyzer:password@localhost:5432/loganalyzer"
    )
    
    conn = await asyncpg.connect(db_url)
    try:
        # Check if demo tenant exists
        tenant = await conn.fetchrow("""
            SELECT id FROM tenants WHERE slug = 'demo'
        """)
        
        if not tenant:
            # Create demo tenant
            tenant_id = await conn.fetchval("""
                INSERT INTO tenants (name, slug, description, plan)
                VALUES ('Demo Organization', 'demo', 'Demo tenant for testing', 'free')
                RETURNING id
            """)
            print(f"Created demo tenant: {tenant_id}")
        else:
            tenant_id = tenant['id']
            print(f"Demo tenant already exists: {tenant_id}")
        
        # Get demo user
        user = await conn.fetchrow("""
            SELECT id FROM users WHERE email = 'demo@example.com'
        """)
        
        if not user:
            print("Demo user not found!")
            return
        
        user_id = user['id']
        
        # Check if user is already in tenant
        membership = await conn.fetchrow("""
            SELECT id FROM tenant_users 
            WHERE tenant_id = $1 AND user_id = $2
        """, tenant_id, user_id)
        
        if not membership:
            # Add user to tenant as admin
            await conn.execute("""
                INSERT INTO tenant_users (tenant_id, user_id, role, accepted_at)
                VALUES ($1, $2, 'admin', NOW())
            """, tenant_id, user_id)
            print(f"Added demo user to demo tenant as admin")
        else:
            # Update to ensure active and admin
            await conn.execute("""
                UPDATE tenant_users 
                SET is_active = TRUE, role = 'admin', accepted_at = NOW()
                WHERE tenant_id = $1 AND user_id = $2
            """, tenant_id, user_id)
            print(f"Updated demo user membership")
        
        # Verify setup
        result = await conn.fetchrow("""
            SELECT t.name, t.slug, tu.role, tu.is_active
            FROM tenant_users tu
            JOIN tenants t ON tu.tenant_id = t.id
            WHERE tu.user_id = $1 AND t.slug = 'demo'
        """, user_id)
        
        if result:
            print(f"\nSetup complete:")
            print(f"Tenant: {result['name']} ({result['slug']})")
            print(f"User role: {result['role']}")
            print(f"Active: {result['is_active']}")
            
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(setup_demo_tenant())