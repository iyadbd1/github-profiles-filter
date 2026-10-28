from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # GitHub API
    github_token: str
    github_api_base: str = "https://api.github.com"
    github_graphql_url: str = "https://api.github.com/graphql"

    # Internal API Key
    internal_api_key: str

    # Cache TTLs (seconds)
    cache_ttl_profile: int = 86400      # 24h
    cache_ttl_repos: int = 21600        # 6h
    cache_ttl_contributions: int = 3600 # 1h

    # Background sync
    sync_interval: int = 3600           # 1h

    # Database
    database_url: str = "sqlite+aiosqlite:///./data/github_cache.db"

    # Logging
    log_level: str = "INFO"

    # CORS
    cors_origins: list[str] = ["http://localhost:5173"]


@lru_cache
def get_settings() -> Settings:
    return Settings()