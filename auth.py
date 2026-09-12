import os
from typing import Optional, Dict, Any

from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL: str = os.getenv("SUPABASE_URL", "https://your-project.supabase.co")
SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "your-anon-key")

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Security scheme for FastAPI Swagger UI
security = HTTPBearer(auto_error=False)


class UserSignUp(BaseModel):
    email: str = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class UserLogin(BaseModel):
    email: str = Field(..., description="User email address")
    password: str = Field(..., description="User password")


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Dict[str, Any]:
    """
    FastAPI dependency that extracts the Bearer token from the Authorization header,
    verifies it via Supabase Auth, and returns the authenticated user object.
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    try:
        # Verify JWT access token with Supabase Auth
        response = supabase.auth.get_user(token)
        if not response or not response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        user_data = response.user
        return {
            "id": getattr(user_data, "id", None),
            "email": getattr(user_data, "email", None),
            "created_at": getattr(user_data, "created_at", None),
            "role": getattr(user_data, "role", "authenticated"),
            "user_metadata": getattr(user_data, "user_metadata", {}),
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {str(exc)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
