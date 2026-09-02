import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

# Get root directory of project
BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    # Model configuration to support loading from .env file
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # 1. Databases
    DATABASE_URL: str = "postgresql+asyncpg://user:pass@localhost:5432/devmind"
    MONGODB_URL: str = "mongodb://localhost:27017/devmind"
    REDIS_URL: str = "redis://localhost:6379/0"
    CHROMADB_PATH: str = "./chroma_db"

    # 2. AI & LLM Inference
    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL: str = "openai/gpt-oss-20b"
    HUGGINGFACE_API_KEY: Optional[str] = None

    # 3. Third-party APIs
    GITHUB_TOKEN: Optional[str] = None

    # 4. Storage & Infrastructure
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_S3_BUCKET: str = "devmind-storage"
    AWS_EC2_REGION: str = "ap-south-1"

    # 5. Security & Authentication
    JWT_SECRET: str = "default_secret_key_change_me_in_production"


# Global settings instance
settings = Settings()
