"""
JWT Authentication utilities
"""
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, ExpiredSignatureError, jwt
from passlib.context import CryptContext

from core.config.settings import settings
from core.logging.logger import get_logger

logger = get_logger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT configuration — use dedicated JWT_SECRET; fall back to API_KEY only for backward compat
SECRET_KEY = settings.JWT_SECRET or settings.API_KEY or "your-secret-key-change-in-production"
if not settings.JWT_SECRET:
    logger.warning("JWT_SECRET not configured — falling back to API_KEY. Set a dedicated JWT_SECRET in .env for production.")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password for storage"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create JWT access token
    
    Args:
        data: Data to encode in token (usually {"sub": user_id})
        expires_delta: Token expiration time (default: 24 hours)
    
    Returns:
        JWT token string
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    return encoded_jwt


def decode_access_token(token: str) -> Optional[str]:
    """
    Decode JWT token and extract user_id
    
    Args:
        token: JWT token string
    
    Returns:
        user_id if valid, None if invalid
    
    Raises:
        Logs warning on any validation failure
    """
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"require_exp": True, "require_sub": True},
        )
        user_id: str = payload.get("sub")
        
        if user_id is None:
            logger.warning("JWT missing 'sub' claim")
            return None
        
        return user_id
    
    except ExpiredSignatureError:
        logger.warning("JWT token has expired")
        return None
    except JWTError as e:
        logger.warning(f"JWT decode error: {e}")
        return None
