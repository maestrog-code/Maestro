from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.core.database import engine

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logger import setup_logging
from app.middleware.request_logger import RequestLoggingMiddleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up Maestro API...")
    yield
    logger.info("Shutting down Maestro API...")
    await engine.dispose()


def create_app() -> FastAPI:
    setup_logging()

    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    app.add_middleware(RequestLoggingMiddleware)

    app.include_router(api_router, prefix=settings.API_V1_STR)

    return app

app = create_app()
