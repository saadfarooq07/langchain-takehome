"""Middleware for multi-tenant authentication and authorization."""

import os
from typing import Optional, Dict, Any
from fastapi import HTTPException, Security, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from starlette.middleware.base import BaseHTTPMiddleware

from ..services.better_auth import BetterAuth


# Security schemes
bearer_scheme = HTTPBearer(auto_error=False)
api_key_scheme = APIKeyHeader(name="X-API-Key", auto_error=False)


class TenantContext:
    """Thread-local storage for tenant context."""
    
    def __init__(self):
        self.tenant_id: Optional[str] = None
        self.user_id: Optional[str] = None
        self.user_email: Optional[str] = None
        self.tenant_slug: Optional[str] = None
        self.role: Optional[str] = None
        self.auth_type: Optional[str] = None  # "bearer" or "api_key"


# Global tenant context (in production, use contextvars)
tenant_context = TenantContext()


async def get_auth_service() -> BetterAuth:
    """Get authentication service instance."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    return BetterAuth(database_url)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
    auth_service: BetterAuth = Depends(get_auth_service)
) -> Dict[str, Any]:
    """Get current authenticated user from bearer token."""
    token = credentials.credentials
    
    # Verify session
    session_data = await auth_service.verify_session(token)
    if not session_data:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Set tenant context
    tenant_context.tenant_id = session_data["tenant"]["id"]
    tenant_context.user_id = session_data["user"]["id"]
    tenant_context.user_email = session_data["user"]["email"]
    tenant_context.tenant_slug = session_data["tenant"]["slug"]
    tenant_context.role = session_data["tenant"]["role"]
    tenant_context.auth_type = "bearer"
    
    return session_data


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
    auth_service: BetterAuth = Depends(get_auth_service)
) -> Optional[Dict[str, Any]]:
    """Get current authenticated user if available."""
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials, auth_service)
    except HTTPException:
        return None


async def get_api_key_tenant(
    api_key: Optional[str] = Security(api_key_scheme),
    auth_service: BetterAuth = Depends(get_auth_service)
) -> Optional[Dict[str, Any]]:
    """Get tenant from API key."""
    if not api_key:
        return None
    
    # Verify API key
    tenant_data = await auth_service.verify_api_key(api_key)
    if not tenant_data:
        return None
    
    # Set tenant context
    tenant_context.tenant_id = tenant_data["tenant"]["id"]
    tenant_context.tenant_slug = tenant_data["tenant"]["slug"]
    tenant_context.auth_type = "api_key"
    tenant_context.user_id = None
    tenant_context.user_email = None
    tenant_context.role = None
    
    return tenant_data


async def require_auth(
    user_data: Optional[Dict[str, Any]] = Depends(get_current_user_optional),
    api_tenant: Optional[Dict[str, Any]] = Depends(get_api_key_tenant)
) -> Dict[str, Any]:
    """Require either user authentication or API key."""
    if user_data:
        return user_data
    
    if api_tenant:
        return api_tenant
    
    raise HTTPException(
        status_code=401,
        detail="Authentication required",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_tenant_role(required_role: str):
    """Require a specific role within the tenant."""
    async def role_checker(
        auth_data: Dict[str, Any] = Depends(require_auth)
    ) -> Dict[str, Any]:
        # API keys don't have roles
        if auth_data.get("auth_type") == "api_key":
            raise HTTPException(
                status_code=403,
                detail="API keys cannot perform this action"
            )
        
        # Check user role
        user_role = auth_data.get("tenant", {}).get("role")
        if not user_role:
            raise HTTPException(status_code=403, detail="No role assigned")
        
        # Role hierarchy: owner > admin > member > viewer
        role_hierarchy = {
            "viewer": 0,
            "member": 1,
            "admin": 2,
            "owner": 3
        }
        
        if role_hierarchy.get(user_role, -1) < role_hierarchy.get(required_role, 999):
            raise HTTPException(
                status_code=403,
                detail=f"Insufficient permissions. Required: {required_role}"
            )
        
        return auth_data
    
    return role_checker





class TenantMiddleware(BaseHTTPMiddleware):
    """Middleware to set tenant context for database queries."""
    
    async def dispatch(self, request: Request, call_next):
        """Set tenant context for the request."""
        # Clear any previous context
        tenant_context.tenant_id = None
        tenant_context.user_id = None
        tenant_context.user_email = None
        tenant_context.tenant_slug = None
        tenant_context.role = None
        tenant_context.auth_type = None
        
        # Process request
        response = await call_next(request)
        
        # Clear context after request
        tenant_context.tenant_id = None
        tenant_context.user_id = None
        tenant_context.user_email = None
        tenant_context.tenant_slug = None
        tenant_context.role = None
        tenant_context.auth_type = None
        
        return response


def get_tenant_id() -> str:
    """Get current tenant ID from context."""
    if not tenant_context.tenant_id:
        raise HTTPException(
            status_code=403,
            detail="No tenant context available"
        )
    return tenant_context.tenant_id


def get_current_user_id() -> Optional[str]:
    """Get current user ID from context."""
    return tenant_context.user_id


def get_tenant_filter() -> Dict[str, Any]:
    """Get filter dict for tenant isolation in queries."""
    tenant_id = get_tenant_id()
    return {"tenant_id": tenant_id}