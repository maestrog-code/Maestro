import os
from pathlib import Path

BASE_DIR = Path("/Users/cuthbertrwebilumi/Desktop/Maestro/backend/maestro/app")

files = {}

# ----------------- AUTH MODELS -----------------
files["core/auth/models.py"] = """from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, ForeignKey, DateTime, JSON
import uuid
from datetime import datetime

from app.models.base import TimestampedModel

class RefreshToken(TimestampedModel):
    __tablename__ = "refresh_tokens"

    token: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    user = relationship("User", back_populates="refresh_tokens")


class AuditLog(TimestampedModel):
    __tablename__ = "audit_logs"

    action: Mapped[str] = mapped_column(String, index=True, nullable=False)
    entity_type: Mapped[str] = mapped_column(String, index=True, nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    details: Mapped[dict | list] = mapped_column(JSON, nullable=True)
    
    user = relationship("User", back_populates="audit_logs")
"""

# ----------------- SECURITY: PASSWORD & JWT -----------------
files["core/security/password.py"] = """from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)
"""

files["core/security/jwt.py"] = """from datetime import datetime, timedelta
from typing import Any
from jose import jwt
from app.core.config import settings

def create_access_token(subject: str | Any, expires_delta: timedelta = None) -> str:
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt
"""

# ----------------- SCHEMAS -----------------
files["modules/users/schemas.py"] = """from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional
import uuid
from datetime import datetime

class UserBase(BaseModel):
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: bool = True

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    password: Optional[str] = None

class UserResponse(UserBase):
    id: uuid.UUID
    is_verified: bool
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
"""

files["core/auth/schemas.py"] = """from pydantic import BaseModel
from app.modules.users.schemas import UserResponse

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    refresh_token: str

class LoginRequest(BaseModel):
    email: str
    password: str

class AuthResponse(BaseModel):
    user: UserResponse
    token: Token
"""

# ----------------- REPOSITORIES -----------------
files["shared/utils/repository.py"] = """from typing import TypeVar, Generic, Type, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.base import Base
import uuid

ModelType = TypeVar("ModelType", bound=Base)

class BaseRepository(Generic[ModelType]):
    def __init__(self, model: Type[ModelType]):
        self.model = model
    
    async def get(self, db: AsyncSession, id: uuid.UUID) -> Optional[ModelType]:
        query = select(self.model).filter(self.model.id == id, self.model.is_deleted == False)
        result = await db.execute(query)
        return result.scalar_one_or_none()
"""

files["modules/users/repositories.py"] = """from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.shared.utils.repository import BaseRepository
from app.modules.users.models import User

class UserRepository(BaseRepository[User]):
    def __init__(self):
        super().__init__(User)
        
    async def get_by_email(self, db: AsyncSession, email: str) -> Optional[User]:
        query = select(self.model).filter(self.model.email == email, self.model.is_deleted == False)
        result = await db.execute(query)
        return result.scalar_one_or_none()

user_repository = UserRepository()
"""

files["core/auth/repositories.py"] = """from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.shared.utils.repository import BaseRepository
from app.core.auth.models import RefreshToken
import uuid

class RefreshTokenRepository(BaseRepository[RefreshToken]):
    def __init__(self):
        super().__init__(RefreshToken)
        
    async def get_by_token(self, db: AsyncSession, token: str) -> Optional[RefreshToken]:
        query = select(self.model).filter(self.model.token == token)
        result = await db.execute(query)
        return result.scalar_one_or_none()

refresh_token_repository = RefreshTokenRepository()
"""

# ----------------- SERVICES -----------------
files["modules/users/services.py"] = """from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.users.models import User
from app.modules.users.schemas import UserCreate
from app.modules.users.repositories import user_repository
from app.core.security.password import get_password_hash
from fastapi import HTTPException, status

async def create_user(db: AsyncSession, user_in: UserCreate) -> User:
    user = await user_repository.get_by_email(db, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The user with this username already exists in the system.",
        )
    
    db_obj = User(
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        first_name=user_in.first_name,
        last_name=user_in.last_name,
    )
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj
"""

files["core/auth/services.py"] = """from sqlalchemy.ext.asyncio import AsyncSession
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
"""

# ----------------- ROUTERS -----------------
files["core/auth/router.py"] = """from fastapi import APIRouter, Depends, HTTPException, status
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
"""

# ----------------- DEPENDENCIES -----------------
files["dependencies/auth.py"] = """from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.dependencies.database import get_db
from app.modules.users.repositories import user_repository
from app.modules.users.models import User
import uuid

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

async def get_current_user(
    db: AsyncSession = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    user = await user_repository.get(db, id=uuid.UUID(user_id))
    if user is None:
        raise credentials_exception
    return user
"""

# Write all files
for file_path, content in files.items():
    full_path = BASE_DIR / file_path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    with open(full_path, "w") as f:
        f.write(content)

print("Files generated successfully!")
