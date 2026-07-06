from typing import Optional
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
