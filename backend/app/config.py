import os
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_ROOT_DIR = _BACKEND_DIR.parent


class Settings(BaseSettings):
    SECRET_KEY: str = "otenga-secret-key-change-in-production-xK9mP2qR7nL5vJ8"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7

    # ── App metadata DB (BI_Otenga — dashboards, users, notebooks) ───────────
    BI_DB_HOST: str = ""
    BI_DB_PORT: int = 3306
    BI_DB_NAME: str = "BI_Otenga"
    BI_DB_USER: str = ""
    BI_DB_PASSWORD: str = ""

    # ── Data query DB (Data_Science — dashboard widget SQL) ──────────────────
    MPESA_DB_HOST: str = ""
    MPESA_DB_PORT: int = 3306
    MPESA_DB_NAME: str = "Data_Science"
    MPESA_DB_USER: str = ""
    MPESA_DB_PASSWORD: str = ""

    # ── Email / SMTP settings ─────────────────────────────────────────────
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "noreply@otenga.io"
    SMTP_FROM_NAME: str = "Otenga BI Platform"

    APP_BASE_URL: str = "http://localhost:5173"

    # ── Laravel SSO integration ───────────────────────────────────────────
    LARAVEL_JWT_SECRET: str = ""
    LARAVEL_APP_URL: str = ""

    DASHBOARD_REFRESH_ON_STARTUP: bool = False
    DASHBOARD_REFRESH_WORKERS: int = 8

    @model_validator(mode="after")
    def _apply_db_defaults(self):
        """Fall back to MPESA_DB_* for any unset BI metadata connection fields."""
        legacy_host = self.MPESA_DB_HOST or os.environ.get("MPESA_DB_HOST", "65.20.86.247")
        legacy_port = self.MPESA_DB_PORT or int(os.environ.get("MPESA_DB_PORT", 3306))
        legacy_user = self.MPESA_DB_USER or os.environ.get("MPESA_DB_USER", "production")
        legacy_password = self.MPESA_DB_PASSWORD or os.environ.get("MPESA_DB_PASSWORD", "")

        if not self.BI_DB_HOST:
            self.BI_DB_HOST = legacy_host
        if not self.BI_DB_PORT:
            self.BI_DB_PORT = legacy_port
        if not self.BI_DB_USER:
            self.BI_DB_USER = legacy_user
        if not self.BI_DB_PASSWORD:
            self.BI_DB_PASSWORD = legacy_password

        if not self.MPESA_DB_HOST:
            self.MPESA_DB_HOST = legacy_host
        if not self.MPESA_DB_PORT:
            self.MPESA_DB_PORT = legacy_port
        if not self.MPESA_DB_USER:
            self.MPESA_DB_USER = legacy_user
        if not self.MPESA_DB_PASSWORD:
            self.MPESA_DB_PASSWORD = legacy_password

        return self

    class Config:
        # Fixed paths — not cwd-dependent (matches Veriscore BI platform).
        env_file = (
            str(_BACKEND_DIR / ".env"),
            str(_ROOT_DIR / ".env"),
        )
        env_file_encoding = "utf-8"


settings = Settings()
