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

    # Memory Weights
    MEMORY_SIMILARITY_WEIGHT: float = 0.4
    MEMORY_IMPORTANCE_WEIGHT: float = 0.2
    MEMORY_CONFIDENCE_WEIGHT: float = 0.2
    MEMORY_RECENCY_WEIGHT: float = 0.1
    MEMORY_ACCESS_WEIGHT: float = 0.1
    MEMORY_RETRIEVAL_LIMIT: int = 10

    # Memory Thresholds (Sprint 006.5)
    MEMORY_MERGE_THRESHOLD: float = 0.90
    MEMORY_CONFLICT_THRESHOLD: float = 0.82
    MEMORY_RETRIEVAL_THRESHOLD: float = 0.60
    MEMORY_ARCHIVE_THRESHOLD: float = 0.10  # Importance below this triggers archival
    MEMORY_UNCERTAIN_CONFIDENCE_PENALTY: float = 0.80  # Multiplier on confidence for UNCERTAIN resolution
    MEMORY_RECENCY_WINDOW_DAYS: int = 30   # Days over which recency score decays to 0
    MEMORY_SEARCH_POOL_SIZE: int = 30
    MEMORY_MAX_ACCESS_NORMALIZATION: int = 10  # Access count at which access_freq score reaches 1.0

    # Memory Decay Rate (lambda for exponential decay: e^(-lambda * days))
    # A lambda of 0.01 means memory importance decays by ~1% per day if untouched
    MEMORY_DECAY_RATE: float = 0.01

    # Sprint 005 — Embeddings
    EMBEDDING_MODEL: str = "text-embedding-004"
    EMBEDDING_BATCH_SIZE: int = 10  # chunks per API call to avoid rate limits

    # Sprint 005 — Knowledge / RAG
    VECTOR_SEARCH_TOP_K: int = 5
    CHUNK_SIZE_TOKENS: int = 512
    CHUNK_OVERLAP_TOKENS: int = 80
    KNOWLEDGE_MAX_CONTEXT_CHARS: int = 8000  # max chars injected into system prompt

    # Sprint 007 — Orchestration
    DELEGATION_MAX_CHARS: int = 4000

ai_settings = AISettings()
