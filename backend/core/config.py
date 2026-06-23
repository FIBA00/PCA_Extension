import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_USERNAME: str
    DATABASE_PASSWORD: str
    DATABASE_HOSTNAME: str
    DATABASE_PORT: int
    DATABASE_NAME: str
    VERSION: str
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int
    JWT_REFRESH_TOKEN_EXPIRY_MINUTES: int
    JTI_EXPIRY_SECONDS: int = 3600
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_URL: str = "redis://localhost:6379/0"
    OLLAMA_HOST: str
    OLLAMA_MODEL: str = "phi3:mini"
    OLLAMA_TIMEOUT: int = 60

    class Config:
        # Construct absolute path to .env file in the backend root directory
        env_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"
        )
        env_file_encoding = "utf-8"
        case_sensitive = True


settings = Settings()
broker_url = settings.REDIS_URL
result_backend = settings.REDIS_URL
broker_connection_retry_on_startup = True
