from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
import uuid
import secrets
from datetime import datetime, timedelta
from app.core.auth.models import RefreshToken
from app.modules.users.repositories import user_repository
from app.core.auth.schemas import LoginRequest, Token
from app.core.security.password import verify_password
from app.core.security.jwt import create_access_token

async def authenticate_user(db: AsyncSession, login_req: LoginRequest):
    user = await user_repository.get_by_email(db, email=login_req.email)
    if not user:
        return None
    if not verify_password(login_req.password, user.hashed_password):
        return None
    return user

async def create_refresh_token(db: AsyncSession, user_id: uuid.UUID) -> str:
    token_str = secrets.token_urlsafe(32)
    db_token = RefreshToken(
        token=token_str,
        user_id=user_id,
        expires_at=datetime.utcnow() + timedelta(days=7)
    )
    db.add(db_token)
    await db.commit()
    return token_str
