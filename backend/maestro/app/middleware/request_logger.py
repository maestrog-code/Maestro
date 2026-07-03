import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from loguru import logger

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        response = await call_next(request)
        
        process_time = time.time() - start_time
        logger.info(
            f"{request.client.host} - \"{request.method} {request.url.path}\" "
            f"{response.status_code} {process_time:.3f}s"
        )
        
        return response
