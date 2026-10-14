from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.users.models import User
from app.modules.users.schemas import UserCreate, UserUpdate
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


async def update_user(db: AsyncSession, *, user: User, user_update: UserUpdate) -> User:
    """
    Update allowed profile fields only.
    Email, password, verification, and internal fields are NOT updated here.
    """
    if user_update.first_name is not None:
        user.first_name = user_update.first_name
    if user_update.last_name is not None:
        user.last_name = user_update.last_name
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

