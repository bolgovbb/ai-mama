from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://aimama:aimama_secret@127.0.0.1:5432/aimama"
    redis_url: str = "redis://127.0.0.1:6379/0"
    secret_key: str = "public-beta-secret-2026"
    site_url: str = "http://5.129.205.143"
    anthropic_api_key: str = ""

    class Config:
        env_file = ".env"

settings = Settings()
