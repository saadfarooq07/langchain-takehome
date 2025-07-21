"""Better-auth implementation for multi-tenant authentication."""

import os
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple, List
import asyncpg
import bcrypt
import jwt
from pydantic import BaseModel, Field
from enum import Enum
from google.oauth2 import id_token
from google.auth.transport import requests

from ..models.user import UserRole
from ..models.tenant import Tenant
from ..db_pool import get_db_pool
from ..models.log_analysis import LogAnalysis


class TokenType(str, Enum):
    ACCESS = "access"
    REFRESH = "refresh"
    API_KEY = "api_key"


class AuthConfig(BaseModel):
    """Authentication configuration."""
    
    secret_key: str = Field(default_factory=lambda: os.getenv("BETTER_AUTH_SECRET", ""))
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 30
    api_key_prefix: str = "lak_"  # log analyzer key
    
    # Encryption settings
    encryption_key: str = Field(default_factory=lambda: os.getenv("ENCRYPTION_KEY", ""))
    
    # Session settings
    max_sessions_per_user: int = 5
    session_cleanup_interval_minutes: int = 60


class BetterAuth:
    """Better authentication service with multi-tenant support."""
    
    def __init__(self, db_url: str, config: Optional[AuthConfig] = None):
        self.db_url = db_url
        self.config = config or AuthConfig()
        
        if not self.config.secret_key:
            raise ValueError("BETTER_AUTH_SECRET must be set")
    
    async def _get_db_pool(self):
        """Get database pool instance."""
        return await get_db_pool(self.db_url)
    
    async def setup_database(self):
        """Create all necessary tables for multi-tenant authentication."""
        pool = await self._get_db_pool()
        async with pool.acquire() as conn:
                # Create extensions
                await conn.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";")
                await conn.execute("CREATE EXTENSION IF NOT EXISTS \"pgcrypto\";")
            
                # Create tenant table
                await conn.execute("""
                CREATE TABLE IF NOT EXISTS tenants (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    name VARCHAR(255) NOT NULL,
                    slug VARCHAR(255) UNIQUE NOT NULL,
                    description TEXT,
                    settings JSONB DEFAULT '{}',
                    api_key_hash VARCHAR(255),
                    api_key_prefix VARCHAR(32),
                    is_active BOOLEAN DEFAULT TRUE NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
                    plan VARCHAR(50) DEFAULT 'free',
                    plan_expires_at TIMESTAMP WITH TIME ZONE,
                    max_users INTEGER DEFAULT 5,
                    max_monthly_logs INTEGER DEFAULT 10000,
                    max_storage_gb INTEGER DEFAULT 1
                );
                
                CREATE INDEX IF NOT EXISTS idx_tenants_slug ON tenants(slug);
                CREATE INDEX IF NOT EXISTS idx_tenants_api_key_prefix ON tenants(api_key_prefix);
                """)
            
                # Create users table
                await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    email VARCHAR(255) UNIQUE NOT NULL,
                    hashed_password VARCHAR(255) NOT NULL,
                    full_name VARCHAR(255),
                    avatar_url VARCHAR(500),
                    is_active BOOLEAN DEFAULT TRUE NOT NULL,
                    is_verified BOOLEAN DEFAULT FALSE NOT NULL,
                    verification_token VARCHAR(255),
                    verified_at TIMESTAMP WITH TIME ZONE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
                    last_login_at TIMESTAMP WITH TIME ZONE
                );
                
                CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
                """)
            
                # Create tenant_users table for many-to-many relationship
                await conn.execute("""
                CREATE TABLE IF NOT EXISTS tenant_users (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
                    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    role VARCHAR(50) DEFAULT 'member' NOT NULL,
                    custom_permissions JSONB DEFAULT '[]',
                    is_active BOOLEAN DEFAULT TRUE NOT NULL,
                    invited_by UUID REFERENCES users(id),
                    invitation_token VARCHAR(255),
                    accepted_at TIMESTAMP WITH TIME ZONE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
                    UNIQUE(tenant_id, user_id)
                );
                
                CREATE INDEX IF NOT EXISTS idx_tenant_users_tenant ON tenant_users(tenant_id);
                CREATE INDEX IF NOT EXISTS idx_tenant_users_user ON tenant_users(user_id);
                """)
            
                # Create user_sessions table with tenant context
                await conn.execute("""
                CREATE TABLE IF NOT EXISTS user_sessions (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
                    token VARCHAR(500) UNIQUE NOT NULL,
                    refresh_token VARCHAR(500) UNIQUE,
                    ip_address VARCHAR(45),
                    user_agent TEXT,
                    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    refresh_expires_at TIMESTAMP WITH TIME ZONE,
                    is_active BOOLEAN DEFAULT TRUE NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
                    last_accessed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
                );
                
                CREATE INDEX IF NOT EXISTS idx_user_sessions_user ON user_sessions(user_id);
                CREATE INDEX IF NOT EXISTS idx_user_sessions_tenant ON user_sessions(tenant_id);
                CREATE INDEX IF NOT EXISTS idx_user_sessions_token ON user_sessions(token);
                """)
            
                # Create tenant_settings table for encrypted settings
                await conn.execute("""
                CREATE TABLE IF NOT EXISTS tenant_settings (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
                    key VARCHAR(255) NOT NULL,
                    value TEXT,
                    is_encrypted BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
                    UNIQUE(tenant_id, key)
                );
                
                CREATE INDEX IF NOT EXISTS idx_tenant_settings_tenant ON tenant_settings(tenant_id);
                """)
            
                # Create log_analyses table with tenant isolation
                await conn.execute("""
                CREATE TABLE IF NOT EXISTS log_analyses (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
                    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
                    name VARCHAR(255) NOT NULL,
                    description TEXT,
                    log_source VARCHAR(255),
                    issues_found JSONB DEFAULT '[]',
                    recommendations JSONB DEFAULT '[]',
                    summary TEXT,
                    total_lines_analyzed INTEGER DEFAULT 0,
                    error_count INTEGER DEFAULT 0,
                    warning_count INTEGER DEFAULT 0,
                    analysis_duration_ms INTEGER,
                    model_used VARCHAR(100),
                    status VARCHAR(50) DEFAULT 'pending',
                    error_message TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
                    completed_at TIMESTAMP WITH TIME ZONE
                );
                
                CREATE INDEX IF NOT EXISTS idx_log_analyses_tenant_created ON log_analyses(tenant_id, created_at);
                CREATE INDEX IF NOT EXISTS idx_log_analyses_tenant_status ON log_analyses(tenant_id, status);
                """)
            
                # Create row-level security policies (commented out for now)
                # await self._setup_row_level_security(conn)
            
    
    async def _setup_row_level_security(self, conn: asyncpg.Connection):
        """Set up row-level security for tenant isolation."""
        tables = ["log_analyses", "tenant_settings", "user_sessions"]
        
        for table in tables:
                # Enable RLS
                await conn.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;")
            
                # Create policy for tenant isolation
                await conn.execute(f"""
                CREATE POLICY IF NOT EXISTS tenant_isolation_select ON {table}
                FOR SELECT USING (tenant_id = current_setting('app.current_tenant')::uuid);
                """)
            
                await conn.execute(f"""
                CREATE POLICY IF NOT EXISTS tenant_isolation_insert ON {table}
                FOR INSERT WITH CHECK (tenant_id = current_setting('app.current_tenant')::uuid);
                """)
            
                await conn.execute(f"""
                CREATE POLICY IF NOT EXISTS tenant_isolation_update ON {table}
                FOR UPDATE USING (tenant_id = current_setting('app.current_tenant')::uuid);
                """)
            
                await conn.execute(f"""
                CREATE POLICY IF NOT EXISTS tenant_isolation_delete ON {table}
                FOR DELETE USING (tenant_id = current_setting('app.current_tenant')::uuid);
                """)
    
    def _hash_password(self, password: str) -> str:
        """Hash a password using bcrypt."""
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    
    def _verify_password(self, password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))
    
    def _generate_api_key(self) -> Tuple[str, str, str]:
        """Generate an API key.
        
        Returns:
                Tuple of (full_key, key_hash, key_prefix)
        """
        # Generate random key
        raw_key = secrets.token_urlsafe(32)
        full_key = f"{self.config.api_key_prefix}{raw_key}"
        
        # Hash the key
        key_hash = hashlib.sha256(full_key.encode()).hexdigest()
        
        # Get prefix for identification (first 8 chars after prefix)
        key_prefix = full_key[:len(self.config.api_key_prefix) + 8]
        
        return full_key, key_hash, key_prefix
    
    def _create_token(self, data: Dict[str, Any], token_type: TokenType, expires_delta: Optional[timedelta] = None) -> str:
        """Create a JWT token."""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            if token_type == TokenType.ACCESS:
                expire = datetime.utcnow() + timedelta(minutes=self.config.access_token_expire_minutes)
            elif token_type == TokenType.REFRESH:
                expire = datetime.utcnow() + timedelta(days=self.config.refresh_token_expire_days)
            else:
                expire = datetime.utcnow() + timedelta(days=365)  # API keys
        
        to_encode.update({
            "exp": expire,
            "type": token_type.value,
            "iat": datetime.utcnow()
        })
        
        return jwt.encode(to_encode, self.config.secret_key, algorithm=self.config.algorithm)
    
    def _verify_token(self, token: str, expected_type: Optional[TokenType] = None) -> Optional[Dict[str, Any]]:
        """Verify and decode a JWT token."""
        try:
            payload = jwt.decode(token, self.config.secret_key, algorithms=[self.config.algorithm])
            
            # Check token type if specified
            if expected_type and payload.get("type") != expected_type.value:
                return None
                
            return payload
        except jwt.PyJWTError:
            return None
    
    async def create_tenant(
        self,
        name: str,
        slug: str,
        owner_email: str,
        owner_password: str,
        owner_name: Optional[str] = None,
        description: Optional[str] = None,
        plan: str = "free"
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Create a new tenant with an owner user.
        
        Returns:
            Tuple of (success, message, data)
        """
        try:
            pool = await self._get_db_pool()
            async with pool.acquire() as conn:
                # Start transaction
                async with conn.transaction():
                    # Check if tenant slug already exists
                    existing = await conn.fetchrow(
                        "SELECT id FROM tenants WHERE slug = $1", slug
                    )
                    if existing:
                        return False, "Tenant slug already exists", None
                    
                    # Check if user email already exists
                    existing_user = await conn.fetchrow(
                        "SELECT id FROM users WHERE email = $1", owner_email
                    )
                    if existing_user:
                        return False, "User email already exists", None
                    
                    # Generate API key for tenant
                    api_key, api_key_hash, api_key_prefix = self._generate_api_key()
                    
                    # Create tenant
                    tenant_id = await conn.fetchval("""
                        INSERT INTO tenants (name, slug, description, plan, api_key_hash, api_key_prefix)
                        VALUES ($1, $2, $3, $4, $5, $6)
                        RETURNING id
                    """, name, slug, description, plan, api_key_hash, api_key_prefix)
                    
                    # Create owner user
                    hashed_password = self._hash_password(owner_password)
                    verification_token = secrets.token_urlsafe(32)
                    
                    user_id = await conn.fetchval("""
                        INSERT INTO users (email, hashed_password, full_name, verification_token)
                        VALUES ($1, $2, $3, $4)
                        RETURNING id
                    """, owner_email, hashed_password, owner_name, verification_token)
                    
                    # Add user to tenant as owner
                    await conn.execute("""
                        INSERT INTO tenant_users (tenant_id, user_id, role, accepted_at)
                        VALUES ($1, $2, $3, NOW())
                    """, tenant_id, user_id, UserRole.OWNER.value)
                    
                    return True, "Tenant created successfully", {
                        "tenant_id": str(tenant_id),
                        "user_id": str(user_id),
                        "api_key": api_key,
                        "verification_token": verification_token
                    }
                
        except Exception as e:
                return False, f"Error creating tenant: {str(e)}", None
    
    async def authenticate_user(
        self,
        email: str,
        password: str,
        tenant_slug: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Authenticate a user, optionally within a specific tenant context."""
        try:
            pool = await self._get_db_pool()
            async with pool.acquire() as conn:
                # Get user
                user = await conn.fetchrow("""
                    SELECT id, email, hashed_password, full_name, is_active, is_verified
                    FROM users WHERE email = $1
                """, email)
                
                if not user:
                    return False, "Invalid credentials", None
                
                if not user["is_active"]:
                    return False, "User account is disabled", None
                
                if not user["is_verified"]:
                    return False, "Please verify your email first", None
                
                # Verify password
                if not self._verify_password(password, user["hashed_password"]):
                    return False, "Invalid credentials", None
                
                # Get user's tenants
                tenant_memberships = await conn.fetch("""
                SELECT t.id, t.slug, t.name, tu.role
                FROM tenant_users tu
                JOIN tenants t ON tu.tenant_id = t.id
                WHERE tu.user_id = $1 AND tu.is_active = TRUE AND t.is_active = TRUE
                ORDER BY tu.created_at
                """, user["id"])
            
                if not tenant_memberships:
                    return False, "User has no active tenant memberships", None
                
                # Select tenant
                if tenant_slug:
                    # Find specific tenant
                    selected_tenant = next(
                        (t for t in tenant_memberships if t["slug"] == tenant_slug),
                        None
                    )
                    if not selected_tenant:
                        return False, "User is not a member of this tenant", None
                else:
                    # Use first tenant
                    selected_tenant = tenant_memberships[0]
            
                # Create tokens
                token_data = {
                "user_id": str(user["id"]),
                "email": user["email"],
                "tenant_id": str(selected_tenant["id"]),
                "tenant_slug": selected_tenant["slug"],
                "role": selected_tenant["role"]
                }
            
                access_token = self._create_token(token_data, TokenType.ACCESS)
                refresh_token = self._create_token(token_data, TokenType.REFRESH)
            
                # Store session
                expires_at = datetime.utcnow() + timedelta(minutes=self.config.access_token_expire_minutes)
                refresh_expires_at = datetime.utcnow() + timedelta(days=self.config.refresh_token_expire_days)
            
                session_id = await conn.fetchval("""
                INSERT INTO user_sessions 
                (user_id, tenant_id, token, refresh_token, ip_address, user_agent, expires_at, refresh_expires_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING id
                """, user["id"], selected_tenant["id"], access_token, refresh_token, 
                ip_address, user_agent, expires_at, refresh_expires_at)
            
                # Update last login
                await conn.execute(
                "UPDATE users SET last_login_at = NOW() WHERE id = $1",
                user["id"]
                )
            
                return True, "Authentication successful", {
                "user": {
                    "id": str(user["id"]),
                    "email": user["email"],
                    "full_name": user["full_name"]
                },
                "tenant": {
                    "id": str(selected_tenant["id"]),
                    "slug": selected_tenant["slug"],
                    "name": selected_tenant["name"],
                    "role": selected_tenant["role"]
                },
                "tokens": {
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "token_type": "bearer"
                },
                "available_tenants": [
                    {
                        "id": str(t["id"]),
                        "slug": t["slug"],
                        "name": t["name"],
                        "role": t["role"]
                    }
                    for t in tenant_memberships
                ]
                }
            
        except Exception as e:
                return False, f"Error during authentication: {str(e)}", None
    
    async def authenticate_google_user(
        self,
        credential: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Authenticate user via Google OAuth."""
        try:
            # Verify the Google ID token
            google_client_id = os.getenv("GOOGLE_CLIENT_ID")
            if not google_client_id:
                return False, "Google OAuth not configured", None
            
            try:
                # Verify the token
                idinfo = id_token.verify_oauth2_token(
                    credential, 
                    requests.Request(), 
                    google_client_id
                )
                
                # Check if token is from our app
                if idinfo['aud'] != google_client_id:
                    return False, "Invalid token audience", None
                
                # Extract user info
                email = idinfo.get('email')
                email_verified = idinfo.get('email_verified', False)
                full_name = idinfo.get('name')
                google_id = idinfo.get('sub')
                
                if not email or not email_verified:
                    return False, "Email not verified", None
                
            except ValueError:
                return False, "Invalid Google token", None
            
            pool = await self._get_db_pool()
            async with pool.acquire() as conn:
                # Check if user exists
                user = await conn.fetchrow(
                    "SELECT id, email, full_name, is_active FROM users WHERE email = $1",
                    email
                )
                
                if not user:
                    # Create new user
                    user_id = await conn.fetchval("""
                        INSERT INTO users (email, full_name, google_id, is_active, email_verified)
                        VALUES ($1, $2, $3, TRUE, TRUE)
                        RETURNING id
                    """, email, full_name, google_id)
                    
                    # Create personal tenant for the user
                    tenant_slug = email.split('@')[0].lower().replace('.', '-').replace('_', '-')
                    tenant_name = f"{full_name or email.split('@')[0]}'s Workspace"
                    
                    # Ensure unique slug
                    counter = 1
                    while await conn.fetchval("SELECT 1 FROM tenants WHERE slug = $1", tenant_slug):
                        tenant_slug = f"{email.split('@')[0].lower()}-{counter}"
                        counter += 1
                    
                    tenant_id = await conn.fetchval("""
                        INSERT INTO tenants (name, slug, owner_id, plan, is_active)
                        VALUES ($1, $2, $3, 'free', TRUE)
                        RETURNING id
                    """, tenant_name, tenant_slug, user_id)
                    
                    # Add user to tenant as owner
                    await conn.execute("""
                        INSERT INTO tenant_users (tenant_id, user_id, role, is_active)
                        VALUES ($1, $2, 'owner', TRUE)
                    """, tenant_id, user_id)
                    
                    user = {
                        'id': user_id,
                        'email': email,
                        'full_name': full_name,
                        'is_active': True
                    }
                else:
                    # Update Google ID if not set
                    if not await conn.fetchval("SELECT google_id FROM users WHERE id = $1", user['id']):
                        await conn.execute(
                            "UPDATE users SET google_id = $1, email_verified = TRUE WHERE id = $2",
                            google_id, user['id']
                        )
                
                if not user["is_active"]:
                    return False, "Account is disabled", None
                
                # Get user's tenants
                tenant_memberships = await conn.fetch("""
                    SELECT t.id, t.slug, t.name, tu.role
                    FROM tenants t
                    JOIN tenant_users tu ON t.id = tu.tenant_id
                    WHERE tu.user_id = $1 AND tu.is_active = TRUE AND t.is_active = TRUE
                    ORDER BY tu.created_at
                """, user["id"])
                
                if not tenant_memberships:
                    return False, "User has no active tenant memberships", None
                
                # Use first tenant
                selected_tenant = tenant_memberships[0]
                
                # Create tokens
                token_data = {
                    "user_id": str(user["id"]),
                    "email": user["email"],
                    "tenant_id": str(selected_tenant["id"]),
                    "tenant_slug": selected_tenant["slug"],
                    "role": selected_tenant["role"]
                }
                
                access_token = self._create_token(token_data, TokenType.ACCESS)
                refresh_token = self._create_token(token_data, TokenType.REFRESH)
                
                # Store session
                expires_at = datetime.utcnow() + timedelta(minutes=self.config.access_token_expire_minutes)
                refresh_expires_at = datetime.utcnow() + timedelta(days=self.config.refresh_token_expire_days)
                
                await conn.execute("""
                    INSERT INTO user_sessions 
                    (user_id, tenant_id, token, refresh_token, ip_address, user_agent, expires_at, refresh_expires_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """, user["id"], selected_tenant["id"], access_token, refresh_token, 
                    ip_address, user_agent, expires_at, refresh_expires_at)
                
                # Update last login
                await conn.execute(
                    "UPDATE users SET last_login_at = NOW() WHERE id = $1",
                    user["id"]
                )
                
                return True, "Authentication successful", {
                    "user": {
                        "id": str(user["id"]),
                        "email": user["email"],
                        "full_name": user["full_name"]
                    },
                    "tenant": {
                        "id": str(selected_tenant["id"]),
                        "slug": selected_tenant["slug"],
                        "name": selected_tenant["name"],
                        "role": selected_tenant["role"]
                    },
                    "tokens": {
                        "access_token": access_token,
                        "refresh_token": refresh_token,
                        "token_type": "bearer"
                    },
                    "available_tenants": [
                        {
                            "id": str(t["id"]),
                            "slug": t["slug"],
                            "name": t["name"],
                            "role": t["role"]
                        }
                        for t in tenant_memberships
                    ]
                }
                
        except Exception as e:
            return False, f"Error during Google authentication: {str(e)}", None
    
    async def verify_session(
        self,
        token: str
    ) -> Optional[Dict[str, Any]]:
        """Verify a session token and return user/tenant context."""
        try:
            # Verify token
            payload = self._verify_token(token, TokenType.ACCESS)
            if not payload:
                return None
            
            pool = await self._get_db_pool()
            async with pool.acquire() as conn:
                # Check if session is active
                session = await conn.fetchrow("""
                SELECT s.id, s.tenant_id, s.expires_at,
                       u.id as user_id, u.email, u.full_name, u.is_active as user_active,
                       t.slug as tenant_slug, t.name as tenant_name, t.is_active as tenant_active,
                       tu.role
                FROM user_sessions s
                JOIN users u ON s.user_id = u.id
                JOIN tenants t ON s.tenant_id = t.id
                JOIN tenant_users tu ON tu.user_id = u.id AND tu.tenant_id = t.id
                WHERE s.token = $1 AND s.is_active = TRUE AND s.expires_at > NOW()
                """, token)
            
                if not session:
                    return None
                
                if not session["user_active"] or not session["tenant_active"]:
                    return None
            
                # Update last accessed
                await conn.execute(
                "UPDATE user_sessions SET last_accessed_at = NOW() WHERE id = $1",
                session["id"]
                )
            
                return {
                "user": {
                    "id": str(session["user_id"]),
                    "email": session["email"],
                    "full_name": session["full_name"]
                },
                "tenant": {
                    "id": str(session["tenant_id"]),
                    "slug": session["tenant_slug"],
                    "name": session["tenant_name"],
                    "role": session["role"]
                }
                }
            
        except Exception as e:
                print(f"Error verifying session: {e}")
                return None
    
    async def verify_api_key(
        self,
        api_key: str
    ) -> Optional[Dict[str, Any]]:
        """Verify a tenant API key."""
        try:
            if not api_key.startswith(self.config.api_key_prefix):
                return None
            
                # Hash the key
                key_hash = hashlib.sha256(api_key.encode()).hexdigest()
            
                pool = await self._get_db_pool()
            async with pool.acquire() as conn:
                tenant = await conn.fetchrow("""
                SELECT id, slug, name, is_active
                FROM tenants
                WHERE api_key_hash = $1 AND is_active = TRUE
                """, key_hash)
            
                if not tenant:
                    return None
            
                return {
                "tenant": {
                    "id": str(tenant["id"]),
                    "slug": tenant["slug"],
                    "name": tenant["name"]
                },
                "auth_type": "api_key"
                }
            
        except Exception as e:
                print(f"Error verifying API key: {e}")
                return None
    
    async def switch_tenant(
        self,
        user_id: str,
        new_tenant_slug: str,
        current_token: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Switch user's active tenant."""
        try:
            pool = await self._get_db_pool()
            async with pool.acquire() as conn:
                # Check user's membership in new tenant
                membership = await conn.fetchrow("""
                SELECT tu.role, t.id, t.name
                FROM tenant_users tu
                JOIN tenants t ON tu.tenant_id = t.id
                WHERE tu.user_id = $1 AND t.slug = $2 
                AND tu.is_active = TRUE AND t.is_active = TRUE
                """, user_id, new_tenant_slug)
            
                if not membership:
                    return False, "User is not a member of this tenant", None
            
                # Invalidate current session
                await conn.execute(
                "UPDATE user_sessions SET is_active = FALSE WHERE token = $1",
                current_token
                )
            
                # Get user info
                user = await conn.fetchrow(
                "SELECT email, full_name FROM users WHERE id = $1",
                user_id
                )
            
                # Create new tokens
                token_data = {
                "user_id": user_id,
                "email": user["email"],
                "tenant_id": str(membership["id"]),
                "tenant_slug": new_tenant_slug,
                "role": membership["role"]
                }
            
                access_token = self._create_token(token_data, TokenType.ACCESS)
                refresh_token = self._create_token(token_data, TokenType.REFRESH)
            
                # Store new session
                expires_at = datetime.utcnow() + timedelta(minutes=self.config.access_token_expire_minutes)
                refresh_expires_at = datetime.utcnow() + timedelta(days=self.config.refresh_token_expire_days)
            
                await conn.execute("""
                INSERT INTO user_sessions 
                (user_id, tenant_id, token, refresh_token, ip_address, user_agent, expires_at, refresh_expires_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """, user_id, membership["id"], access_token, refresh_token,
                ip_address, user_agent, expires_at, refresh_expires_at)
            
                return True, "Tenant switched successfully", {
                "tenant": {
                    "id": str(membership["id"]),
                    "slug": new_tenant_slug,
                    "name": membership["name"],
                    "role": membership["role"]
                },
                "tokens": {
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "token_type": "bearer"
                }
                }
            
        except Exception as e:
                return False, f"Error switching tenant: {str(e)}", None