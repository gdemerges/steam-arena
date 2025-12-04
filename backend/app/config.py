from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Application
    app_name: str = "Steam Arena"
    debug: bool = False
    
    # Database
    database_url: str = "postgresql://steam_arena:steam_arena_secret@localhost:5432/steam_arena"
    
    # Redis
    redis_url: str = "redis://localhost:6379"
    
    # Steam API
    steam_api_key: str = ""
    steam_api_base_url: str = "https://api.steampowered.com"
    steam_store_api_url: str = "https://store.steampowered.com/api"
    
    # Cache settings
    cache_ttl_seconds: int = 3600  # 1 hour
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
