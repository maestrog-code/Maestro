from typing import TypeVar, Generic, Type, Optional, Any
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
