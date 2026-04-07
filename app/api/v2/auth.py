"""
Authentication API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, Field
from typing import Optional

from app.db.session import get_db
from app.db.models import User
from app.auth import verify_password, get_password_hash, create_access_token, get_current_user
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


# Pydantic schemas
class UserRegister(BaseModel):
    """User registration request"""
    email: EmailStr
    password: str = Field(..., min_length=8, description="Password (min 8 characters)")


class UserLogin(BaseModel):
    """User login request"""
    email: EmailStr
    password: str


class Token(BaseModel):
    """JWT token response"""
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str


class UserResponse(BaseModel):
    """User info response"""
    id: str
    email: str
    is_active: bool
    is_admin: bool
    created_at: str
    
    class Config:
        from_attributes = True


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserRegister,
    db: Session = Depends(get_db)
):
    """
    Register a new user
    
    - **email**: Valid email address (must be unique)
    - **password**: Minimum 8 characters
    
    Returns JWT access token
    """
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Hash password
    hashed_password = get_password_hash(user_data.password)
    
    # Create user
    new_user = User(
        email=user_data.email,
        hashed_password=hashed_password,
        is_active=1,
        is_admin=0
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    logger.info(f"New user registered: {new_user.email} (ID: {new_user.id})")
    
    # Generate JWT token
    access_token = create_access_token(data={"sub": new_user.id})
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        user_id=new_user.id,
        email=new_user.email
    )


@router.post("/login", response_model=Token)
async def login(
    user_data: UserLogin,
    db: Session = Depends(get_db)
):
    """
    Login with email and password
    
    Returns JWT access token
    """
    # Find user by email
    user = db.query(User).filter(User.email == user_data.email).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Verify password
    if not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
    
    logger.info(f"User logged in: {user.email} (ID: {user.id})")
    
    # Generate JWT token
    access_token = create_access_token(data={"sub": user.id})
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        user_id=user.id,
        email=user.email
    )


@router.post("/login/oauth2", response_model=Token)
async def login_oauth2(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    OAuth2 compatible login endpoint
    (For Swagger UI authentication)
    """
    # Find user by email (username field in OAuth2 form)
    user = db.query(User).filter(User.email == form_data.username).first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
    
    access_token = create_access_token(data={"sub": user.id})
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        user_id=user.id,
        email=user.email
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    Get current logged-in user info
    
    Requires: Authorization header with JWT token
    """
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        is_active=bool(current_user.is_active),
        is_admin=bool(current_user.is_admin),
        created_at=str(current_user.created_at)
    )


@router.post("/logout")
async def logout():
    """
    Logout (client should delete token)
    
    Note: JWT tokens are stateless, so logout is handled client-side
    by deleting the token. This endpoint exists for client convenience.
    """
    return {"message": "Logged out successfully. Please delete your access token."}
