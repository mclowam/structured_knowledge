import os
from os import getenv
import aioboto3


class Config:
    DB_HOST: str = getenv("DB_HOST", "localhost")
    DB_PORT: str = getenv("DB_PORT", "5434")
    DB_NAME: str = getenv("DB_NAME", "library_db")
    DB_USER: str = getenv("DB_USER", "admin")
    DB_PASSWORD: str = getenv("DB_PASSWORD", "admin")

    SECRET_KEY: str = getenv("SECRET_KEY")
    ALGORITHM: str = "HS256"

    MINIO_ENDPOINT: str = os.getenv("MINIO_ENDPOINT", "http://localhost:9100")
    MINIO_ACCESS_KEY: str = os.getenv("MINIO_ACCESS_KEY", "admin")
    MINIO_SECRET_KEY: str = os.getenv("MINIO_SECRET_KEY", "password123")
    MINIO_BUCKET: str = os.getenv("MINIO_BUCKET", "library-documents")

    PUBLIC_BASE_URL: str = ""
    LOCAL_BASE_URL: str = "http://localhost:8001"

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

settings = Config()
session_minio = aioboto3.Session()
