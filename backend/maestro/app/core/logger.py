import sys
from loguru import logger
from app.core.config import settings

def setup_logging():
    logger.remove()
    
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )
    
    logger.add(
        sys.stdout,
        format=log_format,
        level="DEBUG" if settings.ENVIRONMENT == "development" else "INFO",
        colorize=True,
    )
