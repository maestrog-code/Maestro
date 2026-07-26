from typing import List, Union
from pydantic import AnyHttpUrl, validator
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Maestro"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"

    ENVIRONMENT: str = "development"

    # Set the real value via the BACKEND_CORS_ORIGINS env var (configured in Render's
    # dashboard per render.yaml, since it's marked `sync: false`). The default here is a
    # local-dev-only fallback — it previously contained guessed production domain names
    # that didn't match the actual deployed Vercel URL, which silently broke CORS in prod.
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = [
        "http://localhost:3000",
    ]

    # Regex for allowed origins that can't be enumerated as exact strings — e.g. Vercel
    # preview deployments, which get a fresh subdomain per branch/PR. Set via env var;
    # defaults to any *.vercel.app subdomain so previews work without extra config.
    BACKEND_CORS_ORIGIN_REGEX: str = r"https://.*\.vercel\.app"

    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    DATABASE_URL: str = "postgresql+asyncpg://maestro_user:maestro_password@localhost:5432/maestro_db"
    REDIS_URL: str = "redis://redis:6379/0"

    # JWT Settings
    SECRET_KEY: str = "change-me-in-production-use-a-long-random-string"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
