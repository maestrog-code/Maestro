import asyncio

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
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
        await asyncio.wait_for(db.execute(text("SELECT 1")), timeout=2)
    except Exception as error:
        logger.error(f"Database health check failed: {error}")
        db_status = "error"

    redis_status = "ok"
    redis_client = Redis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
    try:
        await asyncio.wait_for(redis_client.ping(), timeout=2)
    except Exception as error:
        logger.error(f"Redis health check failed: {error}")
        redis_status = "error"
    finally:
        await redis_client.aclose()

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
