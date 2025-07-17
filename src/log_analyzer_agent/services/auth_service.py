"""Authentication service for user management."""

import bcrypt
import os
import uuid
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import jwt
import asyncpg


class AuthService:
    """Simple authentication service for user management."""
    
    def __init__(self, db_url: str):
        self.db_url = db_url
        self.secret_key = os.getenv("BETTER_AUTH_SECRET", "your-secret-key-min-32-chars")
        self.algorithm = "HS256"
        self.access_token_expire_minutes = 30
    
    async def _get_db_connection(self):
        """Get database connection."""
        return await asyncpg.connect(self.db_url)
    
    async def setup_tables(self):
        """Create necessary tables for authentication."""
        conn = await self._get_db_connection()
        try:
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    email VARCHAR(255) UNIQUE NOT NULL,
                    hashed_password VARCHAR(255) NOT NULL,
                    full_name VARCHAR(255),
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            ''')
            
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS user_sessions (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    token VARCHAR(500) NOT NULL,
                    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    is_active BOOLEAN DEFAULT TRUE
                )
            ''')
            
            await conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id);
                CREATE INDEX IF NOT EXISTS idx_user_sessions_token ON user_sessions(token);
                CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
            ''')
            
        finally:
            await conn.close()
    
    def _hash_password(self, password: str) -> str:
        """Hash a password."""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def _verify_password(self, password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
    
    def _create_access_token(self, data: Dict[str, Any]) -> str:
        """Create access token."""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        to_encode.update({"exp": expire})
        
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
    
    def _verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode token."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.PyJWTError:
            return None
    
    async def create_user(
        self, 
        email: str, 
        password: str, 
        full_name: str = None
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Create a new user.
        
        Args:
            email: User email
            password: User password
            full_name: Optional full name
            
        Returns:
            Tuple of (success, message, user_data)
        """
        conn = await self._get_db_connection()
        try:
            # Check if user already exists
            existing_user = await conn.fetchrow(
                "SELECT id FROM users WHERE email = $1", email
            )
            
            if existing_user:
                return False, "User already exists", None
            
            # Hash password
            hashed_password = self._hash_password(password)
            
            # Create user
            user_id = await conn.fetchval('''
                INSERT INTO users (email, hashed_password, full_name)
                VALUES ($1, $2, $3)
                RETURNING id
            ''', email, hashed_password, full_name)
            
            # Get created user
            user = await conn.fetchrow('''
                SELECT id, email, full_name, is_active, created_at
                FROM users WHERE id = $1
            ''', user_id)
            
            user_data = {
                "id": str(user["id"]),
                "email": user["email"],
                "full_name": user["full_name"],
                "is_active": user["is_active"],
                "created_at": user["created_at"].isoformat()
            }
            
            return True, "User created successfully", user_data
            
        except Exception as e:
            return False, f"Error creating user: {str(e)}", None
        finally:
            await conn.close()
    
    async def authenticate_user(
        self, 
        email: str, 
        password: str
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Authenticate a user.
        
        Args:
            email: User email
            password: User password
            
        Returns:
            Tuple of (success, message, user_data_with_token)
        """
        conn = await self._get_db_connection()
        try:
            # Get user
            user = await conn.fetchrow('''
                SELECT id, email, hashed_password, full_name, is_active
                FROM users WHERE email = $1
            ''', email)
            
            if not user:
                return False, "Invalid credentials", None
            
            if not user["is_active"]:
                return False, "User account is disabled", None
            
            # Verify password
            if not self._verify_password(password, user["hashed_password"]):
                return False, "Invalid credentials", None
            
            # Create access token
            token_data = {
                "user_id": str(user["id"]),
                "email": user["email"]
            }
            access_token = self._create_access_token(token_data)
            
            # Store session
            expires_at = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
            await conn.execute('''
                INSERT INTO user_sessions (user_id, token, expires_at)
                VALUES ($1, $2, $3)
            ''', user["id"], access_token, expires_at)
            
            user_data = {
                "id": str(user["id"]),
                "email": user["email"],
                "full_name": user["full_name"],
                "access_token": access_token,
                "token_type": "bearer"
            }
            
            return True, "Authentication successful", user_data
            
        except Exception as e:
            return False, f"Error authenticating user: {str(e)}", None
        finally:
            await conn.close()
    
    async def verify_session(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify user session.
        
        Args:
            token: Access token
            
        Returns:
            User data if valid, None otherwise
        """
        # Verify token
        payload = self._verify_token(token)
        if not payload:
            return None
        
        conn = await self._get_db_connection()
        try:
            # Check if session exists and is active
            session = await conn.fetchrow('''
                SELECT s.id, s.user_id, s.expires_at, u.email, u.full_name, u.is_active
                FROM user_sessions s
                JOIN users u ON s.user_id = u.id
                WHERE s.token = $1 AND s.is_active = TRUE AND s.expires_at > NOW()
            ''', token)
            
            if not session:
                return None
            
            if not session["is_active"]:
                return None
            
            return {
                "id": str(session["user_id"]),
                "email": session["email"],
                "full_name": session["full_name"]
            }
            
        except Exception as e:
            print(f"Error verifying session: {e}")
            return None
        finally:
            await conn.close()
    
    async def logout_user(self, token: str) -> bool:
        """Logout user by invalidating session.
        
        Args:
            token: Access token
            
        Returns:
            True if successful, False otherwise
        """
        conn = await self._get_db_connection()
        try:
            result = await conn.execute('''
                UPDATE user_sessions 
                SET is_active = FALSE 
                WHERE token = $1
            ''', token)
            
            return result == "UPDATE 1"
            
        except Exception as e:
            print(f"Error logging out user: {e}")
            return False
        finally:
            await conn.close()
    
    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID.
        
        Args:
            user_id: User ID
            
        Returns:
            User data if found, None otherwise
        """
        conn = await self._get_db_connection()
        try:
            user = await conn.fetchrow('''
                SELECT id, email, full_name, is_active, created_at
                FROM users WHERE id = $1
            ''', uuid.UUID(user_id))
            
            if not user:
                return None
            
            return {
                "id": str(user["id"]),
                "email": user["email"],
                "full_name": user["full_name"],
                "is_active": user["is_active"],
                "created_at": user["created_at"].isoformat()
            }
            
        except Exception as e:
            print(f"Error getting user by ID: {e}")
            return None
        finally:
            await conn.close()
    
    async def cleanup_expired_sessions(self):
        """Clean up expired sessions."""
        conn = await self._get_db_connection()
        try:
            await conn.execute('''
                DELETE FROM user_sessions 
                WHERE expires_at < NOW() OR is_active = FALSE
            ''')
        except Exception as e:
            print(f"Error cleaning up expired sessions: {e}")
        finally:
            await conn.close()