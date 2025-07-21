"""Authentication routes for multi-tenant support."""

from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, EmailStr, Field

from ..services.better_auth import BetterAuth
from .middleware import get_auth_service, get_current_user, require_tenant_role


auth_router = APIRouter()


class TenantCreateRequest(BaseModel):
    """Request model for creating a tenant."""
    name: str = Field(..., min_length=3, max_length=255)
    slug: str = Field(..., min_length=3, max_length=50, pattern="^[a-z0-9-]+$")
    owner_email: EmailStr
    owner_password: str = Field(..., min_length=8)
    owner_name: Optional[str] = None
    description: Optional[str] = None


class LoginRequest(BaseModel):
    """Request model for user login."""
    email: EmailStr
    password: str
    tenant_slug: Optional[str] = None


class SwitchTenantRequest(BaseModel):
    """Request model for switching tenant."""
    tenant_slug: str


class RefreshTokenRequest(BaseModel):
    """Request model for refreshing tokens."""
    refresh_token: str


class GoogleAuthRequest(BaseModel):
    """Request model for Google OAuth authentication."""
    credential: str


@auth_router.post("/tenants")
async def create_tenant(
    request: TenantCreateRequest,
    auth_service: BetterAuth = Depends(get_auth_service)
):
    """Create a new tenant with an owner user.
    
    This endpoint is public to allow new organizations to sign up.
    In production, you might want to add rate limiting or require admin approval.
    """
    success, message, data = await auth_service.create_tenant(
        name=request.name,
        slug=request.slug,
        owner_email=request.owner_email,
        owner_password=request.owner_password,
        owner_name=request.owner_name,
        description=request.description
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    # Don't return sensitive data
    return {
        "message": message,
        "tenant_id": data["tenant_id"],
        "tenant_slug": request.slug,
        "verification_required": True
    }


@auth_router.post("/login")
async def login(
    request: LoginRequest,
    req: Request,
    auth_service: BetterAuth = Depends(get_auth_service)
):
    """Authenticate user and return access tokens."""
    # Get client info
    ip_address = req.client.host if req.client else None
    user_agent = req.headers.get("user-agent")
    
    success, message, data = await auth_service.authenticate_user(
        email=request.email,
        password=request.password,
        tenant_slug=request.tenant_slug,
        ip_address=ip_address,
        user_agent=user_agent
    )
    
    if not success:
        raise HTTPException(status_code=401, detail=message)
    
    return {
        "user": data["user"],
        "tenant": data["tenant"],
        "tokens": data["tokens"],
        "available_tenants": data["available_tenants"]
    }


@auth_router.post("/google")
async def google_auth(
    request: GoogleAuthRequest,
    req: Request,
    auth_service: BetterAuth = Depends(get_auth_service)
):
    """Authenticate user via Google OAuth and return access tokens."""
    # Get client info
    ip_address = req.client.host if req.client else None
    user_agent = req.headers.get("user-agent")
    
    success, message, data = await auth_service.authenticate_google_user(
        credential=request.credential,
        ip_address=ip_address,
        user_agent=user_agent
    )
    
    if not success:
        raise HTTPException(status_code=401, detail=message)
    
    return {
        "user": data["user"],
        "tenant": data["tenant"],
        "tokens": data["tokens"],
        "available_tenants": data["available_tenants"]
    }


@auth_router.get("/me")
async def get_current_user_info(
    current_user = Depends(get_current_user)
):
    """Get current authenticated user information."""
    return current_user


@auth_router.post("/switch-tenant")
async def switch_tenant(
    request: SwitchTenantRequest,
    req: Request,
    current_user = Depends(get_current_user),
    auth_service: BetterAuth = Depends(get_auth_service)
):
    """Switch to a different tenant."""
    # Get client info
    ip_address = req.client.host if req.client else None
    user_agent = req.headers.get("user-agent")
    
    # Get current token from authorization header
    auth_header = req.headers.get("authorization", "")
    current_token = auth_header.replace("Bearer ", "") if auth_header.startswith("Bearer ") else ""
    
    success, message, data = await auth_service.switch_tenant(
        user_id=current_user["user"]["id"],
        new_tenant_slug=request.tenant_slug,
        current_token=current_token,
        ip_address=ip_address,
        user_agent=user_agent
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return {
        "message": message,
        "tenant": data["tenant"],
        "tokens": data["tokens"]
    }


@auth_router.post("/logout")
async def logout(
    req: Request,
    current_user = Depends(get_current_user),
    auth_service: BetterAuth = Depends(get_auth_service)
):
    """Logout current user session."""
    # Get current token from authorization header
    auth_header = req.headers.get("authorization", "")
    current_token = auth_header.replace("Bearer ", "") if auth_header.startswith("Bearer ") else ""
    
    if current_token:
        pool = await auth_service._get_db_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE user_sessions SET is_active = FALSE WHERE token = $1",
                current_token
            )
    
    return {"message": "Logged out successfully"}


@auth_router.get("/tenants/{tenant_slug}")
async def get_tenant_info(
    tenant_slug: str,
    current_user = Depends(get_current_user),
    auth_service: BetterAuth = Depends(get_auth_service)
):
    """Get information about a tenant (requires membership)."""
    conn = await auth_service._get_db_connection()
    try:
        # Check if user is member of this tenant
        tenant = await conn.fetchrow("""
            SELECT t.id, t.name, t.slug, t.description, t.plan, 
                   t.max_users, t.max_monthly_logs, t.max_storage_gb,
                   tu.role
            FROM tenants t
            JOIN tenant_users tu ON t.id = tu.tenant_id
            WHERE t.slug = $1 AND tu.user_id = $2::uuid
            AND t.is_active = TRUE AND tu.is_active = TRUE
        """, tenant_slug, current_user["user"]["id"])
        
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found or access denied")
        
        return {
            "id": str(tenant["id"]),
            "name": tenant["name"],
            "slug": tenant["slug"],
            "description": tenant["description"],
            "plan": tenant["plan"],
            "limits": {
                "max_users": tenant["max_users"],
                "max_monthly_logs": tenant["max_monthly_logs"],
                "max_storage_gb": tenant["max_storage_gb"]
            },
            "user_role": tenant["role"]
        }
        
    finally:
        await conn.close()


@auth_router.get("/tenants/{tenant_slug}/users")
async def get_tenant_users(
    tenant_slug: str,
    auth_data: Dict[str, Any] = Depends(require_tenant_role("admin")),
    auth_service: BetterAuth = Depends(get_auth_service)
):
    """Get all users in a tenant (requires admin role)."""
    conn = await auth_service._get_db_connection()
    try:
        # Get tenant ID
        tenant = await conn.fetchrow(
            "SELECT id FROM tenants WHERE slug = $1 AND is_active = TRUE",
            tenant_slug
        )
        
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")
        
        # Get users
        users = await conn.fetch("""
            SELECT u.id, u.email, u.full_name, u.is_active, u.last_login_at,
                   tu.role, tu.created_at as joined_at
            FROM users u
            JOIN tenant_users tu ON u.id = tu.user_id
            WHERE tu.tenant_id = $1 AND tu.is_active = TRUE
            ORDER BY tu.created_at DESC
        """, tenant["id"])
        
        return {
            "users": [
                {
                    "id": str(user["id"]),
                    "email": user["email"],
                    "full_name": user["full_name"],
                    "is_active": user["is_active"],
                    "role": user["role"],
                    "joined_at": user["joined_at"].isoformat() if user["joined_at"] else None,
                    "last_login_at": user["last_login_at"].isoformat() if user["last_login_at"] else None
                }
                for user in users
            ]
        }
        
    finally:
        await conn.close()