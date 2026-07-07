from pydantic_settings import BaseSettings, SettingsConfigDict


class AISettings(BaseSettings):
    """
    AI-specific configuration for MAESTRO's AI Executive Engine.
    Values can be overridden by environment variables with the `AI_` prefix.
    """
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", env_prefix="AI_"
    )

    # Provider & Model Settings
    DEFAULT_PROVIDER: str = "google"
    GOOGLE_MODEL: str = "gemini-2.5-pro"

    # Execution Limits
    MAX_TOOL_CALLS: int = 8
    MAX_CONTEXT_TOKENS: int = 32000
    
    # Model Generation Defaults
    DEFAULT_TEMPERATURE: float = 0.2
    STREAMING: bool = True
    
    # Memory Ranking & Vector Config
    EMBEDDING_DIMENSIONS: int = 768
    MEMORY_SIMILARITY_WEIGHT: float = 0.4
    MEMORY_IMPORTANCE_WEIGHT: float = 0.2
    MEMORY_CONFIDENCE_WEIGHT: float = 0.2
    MEMORY_RECENCY_WEIGHT: float = 0.1
    MEMORY_ACCESS_WEIGHT: float = 0.1
    MEMORY_RETRIEVAL_LIMIT: int = 10

    # Sprint 005 — Embeddings
    EMBEDDING_MODEL: str = "text-embedding-004"
    EMBEDDING_DIMENSIONS: int = 768
    EMBEDDING_BATCH_SIZE: int = 10  # chunks per API call to avoid rate limits

    # Sprint 005 — Knowledge / RAG
    VECTOR_SEARCH_TOP_K: int = 5
    CHUNK_SIZE_TOKENS: int = 512
    CHUNK_OVERLAP_TOKENS: int = 80
    KNOWLEDGE_MAX_CONTEXT_CHARS: int = 8000  # max chars injected into system prompt


ai_settings = AISettings()
