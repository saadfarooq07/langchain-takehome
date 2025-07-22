"""Add a test endpoint to verify auth is optional."""

test_route = '''
@router.get("/test-auth")
async def test_auth(
    current_user: Optional[UserResponse] = Depends(get_current_user_optional),
):
    """Test endpoint to verify optional auth."""
    if current_user:
        return {"authenticated": True, "user": current_user.email}
    else:
        return {"authenticated": False, "message": "No auth provided, but that's OK!"}
'''

# Add this to routes.py
import sys
sys.path.append('/home/shl0th/Documents/langchain-takehome')

from src.log_analyzer_agent.api.routes import router
from src.log_analyzer_agent.api.auth import get_current_user_optional
from src.log_analyzer_agent.api.models import UserResponse
from typing import Optional
from fastapi import Depends

# Add the test route
@router.get("/test-auth")
async def test_auth(
    current_user: Optional[UserResponse] = Depends(get_current_user_optional),
):
    """Test endpoint to verify optional auth."""
    if current_user:
        return {"authenticated": True, "user": current_user.email}
    else:
        return {"authenticated": False, "message": "No auth provided, but that's OK!"}

print("Test route added successfully!")