from typing import TypeVar, Generic, Type, Optional, List, Any, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import InstrumentedAttribute
from app.models.base import Base, TimestampedModel
import uuid

ModelType = TypeVar("ModelType", bound=TimestampedModel)


class BaseRepository(Generic[ModelType]):
    """
    Generic async CRUD repository.
    All queries automatically filter out soft-deleted records.
    """

    def __init__(self, model: Type[ModelType]):
        self.model = model

    async def get(self, db: AsyncSession, id: uuid.UUID) -> Optional[ModelType]:
        """Get a single record by UUID. Returns None if not found or soft-deleted."""
        query = select(self.model).where(
            self.model.id == id,
            self.model.is_deleted == False,  # noqa: E712
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_multi(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 20,
        filters: Optional[List[Any]] = None,
    ) -> List[ModelType]:
        """Get a paginated list of records. Accepts optional extra SQLAlchemy filter clauses."""
        query = select(self.model).where(self.model.is_deleted == False)  # noqa: E712
        if filters:
            query = query.where(*filters)
        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def create(self, db: AsyncSession, *, obj_in: Dict[str, Any]) -> ModelType:
        """Create a new record from a plain dict."""
        db_obj = self.model(**obj_in)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: ModelType,
        obj_in: Dict[str, Any],
    ) -> ModelType:
        """Update an existing record with fields from a plain dict."""
        for field, value in obj_in.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def soft_delete(self, db: AsyncSession, *, id: uuid.UUID) -> Optional[ModelType]:
        """Mark a record as deleted without removing it from the database."""
        from datetime import datetime
        db_obj = await self.get(db, id)
        if not db_obj:
            return None
        db_obj.is_deleted = True
        db_obj.deleted_at = datetime.utcnow()
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def hard_delete(self, db: AsyncSession, *, id: uuid.UUID) -> Optional[ModelType]:
        """
        Permanently remove a record from the database.
        Use only for non-business records (e.g. test cleanup, sessions).
        Business data must use soft_delete instead.
        """
        db_obj = await self.get(db, id)
        if not db_obj:
            return None
        await db.delete(db_obj)
        await db.commit()
        return db_obj

