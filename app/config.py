from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Adzuna API credentials
    adzuna_app_id: str = ""
    adzuna_app_key: str = ""
    
    # Reed API credentials (uses basic auth with API key as username)
    reed_api_key: str = ""
    
    # Default search settings
    default_location: str = "london"
    default_max_results: int = 50
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()
