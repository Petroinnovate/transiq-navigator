"""
Authentication dependencies for FastAPI
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional

from services.db.session import get_db
from services.db.models import User
from core.security.jwt import decode_access_token
from core.logging.logger import get_logger

logger = get_logger(__name__)

# OAuth2 schemes
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)
http_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    bearer: Optional[HTTPAuthorizationCredentials] = Depends(http_bearer),
    db: Session = Depends(get_db)
) -> User:
    """
    Get current authenticated user from JWT token
    
    Supports both:
    - Authorization: Bearer <token> (HTTP Bearer)
    - OAuth2 password flow
    
    Raises:
        HTTPException: 401 if authentication fails
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Try to get token from either source
    if bearer and bearer.credentials:
        token = bearer.credentials
    
    if not token:
        raise credentials_exception
    
    # Decode token
    user_id = decode_access_token(token)
    if user_id is None:
        raise credentials_exception
    
    # Get user from database
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    
    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current active user
    (Convenience dependency that's more explicit)
    """
    return current_user


async def get_current_admin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current user (must be admin)
    
    Raises:
        HTTPException: 403 if user is not admin
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    
    return current_user


def get_optional_user(
    token: Optional[str] = Depends(oauth2_scheme),
    bearer: Optional[HTTPAuthorizationCredentials] = Depends(http_bearer),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Get current user if authenticated, None otherwise
    (For endpoints that work both authenticated and unauthenticated)
    """
    try:
        # Try to get token
        if bearer and bearer.credentials:
            token = bearer.credentials
        
        if not token:
            return None
        
        # Decode token
        user_id = decode_access_token(token)
        if user_id is None:
            return None
        
        # Get user
        user = db.query(User).filter(User.id == user_id, User.is_active == 1).first()
        return user
    
    except Exception as e:
        logger.debug(f"Optional auth failed: {e}")
        return None
