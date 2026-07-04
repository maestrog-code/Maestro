from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies.database import get_db
from app.core.auth.schemas import LoginRequest, AuthResponse, Token
from app.modules.users.schemas import UserCreate, UserResponse
from app.core.auth.services import authenticate_user, create_refresh_token
from app.modules.users.services import create_user
from app.core.security.jwt import create_access_token
from datetime import timedelta

router = APIRouter()

@router.post("/register", response_model=AuthResponse)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    user = await create_user(db, user_in)
    access_token = create_access_token(subject=str(user.id))
    refresh_token = await create_refresh_token(db, user.id)
    return AuthResponse(
        user=user,
        token=Token(access_token=access_token, refresh_token=refresh_token)
    )

@router.post("/login", response_model=AuthResponse)
async def login(login_req: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = await authenticate_user(db, login_req)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")
    
    access_token = create_access_token(subject=str(user.id))
    refresh_token = await create_refresh_token(db, user.id)
    return AuthResponse(
        user=user,
        token=Token(access_token=access_token, refresh_token=refresh_token)
    )

@router.post("/verify-email")
async def verify_email(token: str):
    # Placeholder for email verification
    return {"message": "Email verified"}

@router.post("/password-reset")
async def password_reset(email: str):
    # Placeholder for password reset
    return {"message": "Password reset email sent"}


@router.post("/refresh")
async def refresh_token(refresh_token: str):
    # Placeholder for token rotation
    return {"message": "Token refreshed"}

@router.post("/revoke")
async def revoke_token(token: str):
    # Placeholder for token revocation/blacklisting
    return {"message": "Token revoked"}

