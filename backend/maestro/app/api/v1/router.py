from fastapi import APIRouter
from app.api.v1.endpoints import health
from app.core.auth.router import router as auth_router
from app.modules.users.router import router as users_router
from app.modules.organizations.router import router as organizations_router
from app.modules.ai_conversations.router import router as ai_conversations_router
from app.modules.knowledge.router import router as knowledge_router
from app.modules.memory.router import router as memory_router
from app.modules.business.router import router as business_router

api_router = APIRouter()
api_router.include_router(health.router, prefix="/health", tags=["Health"])
api_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users_router, prefix="/users", tags=["Users"])
api_router.include_router(organizations_router, prefix="/organizations", tags=["Organizations"])
api_router.include_router(ai_conversations_router)
api_router.include_router(knowledge_router)
api_router.include_router(memory_router)
api_router.include_router(business_router)

