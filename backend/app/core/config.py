"""
SecureRotate AI - Application Configuration
Loads environment settings from root .env file.
"""

import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


# Determine project root directory (.env file location)
# config.py is at:
# backend/app/core/config.py
# parent x 4 is project root
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
ENV_FILE = BASE_DIR / ".env"


class Settings(BaseSettings):
    PROJECT_NAME: str = "SecureRotate AI"
    API_V1_STR: str = "/api/v1"

    # ================================================================
    # MySQL Configuration
    # ================================================================

    MYSQL_SERVER: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "securerotate_admin"
    MYSQL_PASSWORD: str = "YOUR_SECRET"
    SYSTEM_DB_NAME: str = "securerotate_db"

    # ================================================================
    # JWT Configuration
    # ================================================================

    JWT_SECRET_KEY: str = "YOUR_SECRET"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 120
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120

    # ================================================================
    # Vault / Secret Encryption
    # ================================================================

    VAULT_ENCRYPTION_KEY: str = "YOUR_SCRET"

    # Local / Remote Secret Provider
    SECRET_PROVIDER_TYPE: str = "LOCAL"

    # ================================================================
    # SMTP Configuration
    #
    # Kept for compatibility with the existing application.
    # Actual email delivery on Render will use Resend.
    # ================================================================

    SMTP_HOST: str | None = None
    SMTP_PORT: int = 587
    SMTP_USER: str | None = None
    SMTP_USERNAME: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_FROM: str = "alerts@securerotate.ai"
    SMTP_FROM_EMAIL: str | None = None
    SMTP_TLS: bool = True
    SMTP_USE_TLS: bool | None = None

    # ================================================================
    # Resend Configuration
    # ================================================================

    RESEND_API_KEY: str | None = None
    RESEND_FROM_EMAIL: str = "onboarding@resend.dev"

    # ================================================================
    # Optional direct database connection string override
    # ================================================================

    DATABASE_URL: str | None = None

    # ================================================================
    # CORS Configuration
    # ================================================================

    BACKEND_CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ]

    # ================================================================
    # Pydantic Settings Configuration
    # ================================================================

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE) if ENV_FILE.exists() else ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ================================================================
    # Database URL
    # ================================================================

    @property
    def get_database_url(self) -> str:
        """
        Returns a valid MySQL connection string using aiomysql.

        Priority:
        1. DATABASE_URL environment variable
        2. Individual MYSQL_* environment variables

        Never hardcodes database credentials.
        """

        if self.DATABASE_URL and self.DATABASE_URL.strip():
            url = self.DATABASE_URL.strip()

            if url.startswith("mysql://"):
                return url.replace(
                    "mysql://",
                    "mysql+aiomysql://",
                    1,
                )

            return url

        return (
            f"mysql+aiomysql://"
            f"{self.MYSQL_USER}:"
            f"{self.MYSQL_PASSWORD}@"
            f"{self.MYSQL_SERVER}:"
            f"{self.MYSQL_PORT}/"
            f"{self.SYSTEM_DB_NAME}"
        )


settings = Settings()