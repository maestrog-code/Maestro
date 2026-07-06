from typing import Optional
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
