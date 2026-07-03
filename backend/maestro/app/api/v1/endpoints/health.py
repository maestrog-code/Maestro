from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from redis.asyncio import Redis

from app.schemas.health import HealthCheckResponse
from app.dependencies.database import get_db
from app.core.config import settings
from loguru import logger

router = APIRouter()

@router.get("", response_model=HealthCheckResponse)
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Check API, database, and Redis health.
    """
    db_status = "ok"
    try:
        await db.execute(text("SELECT 1"))
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = "error"
        
    redis_status = "ok"
    try:
        redis_client = Redis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
        await redis_client.ping()
        await redis_client.close()
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        redis_status = "error"

    if db_status == "error" or redis_status == "error":
        raise HTTPException(
            status_code=503, 
            detail={"status": "error", "database": db_status, "redis": redis_status}
        )

    return HealthCheckResponse(
        status="ok",
        database=db_status,
        redis=redis_status,
        version=settings.VERSION
    )
