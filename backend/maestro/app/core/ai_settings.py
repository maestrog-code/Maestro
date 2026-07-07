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


ai_settings = AISettings()
