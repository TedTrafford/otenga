import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    SECRET_KEY: str = "otenga-secret-key-change-in-production-xK9mP2qR7nL5vJ8"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7

    # ── App metadata DB (BI_Otenga on MySQL) ──────────────────────────────
    BI_DB_HOST: str = os.environ.get("MPESA_DB_HOST", "139.84.243.180")
    BI_DB_PORT: int = int(os.environ.get("MPESA_DB_PORT", 3306))
    BI_DB_NAME: str = "BI_Otenga"
    BI_DB_USER: str = os.environ.get("MPESA_DB_USER", "staging")
    BI_DB_PASSWORD: str = os.environ.get("MPESA_DB_PASSWORD", "gQTnYQ8Xwh1nl0di1rbz")

    # ── Data query DB (Data_Science on MySQL) ────────────────────────────
    MPESA_DB_HOST: str = os.environ.get("MPESA_DB_HOST", "139.84.243.180")
    MPESA_DB_PORT: int = int(os.environ.get("MPESA_DB_PORT", 3306))
    MPESA_DB_NAME: str = os.environ.get("MPESA_DB_NAME", "Data_Science")
    MPESA_DB_USER: str = os.environ.get("MPESA_DB_USER", "staging")
    MPESA_DB_PASSWORD: str = os.environ.get("MPESA_DB_PASSWORD", "gQTnYQ8Xwh1nl0di1rbz")

    # ── Email / SMTP settings ─────────────────────────────────────────────
    # Leave SMTP_HOST empty to skip actual email sending and print link to console
    SMTP_HOST: str = os.environ.get("SMTP_HOST", "")
    SMTP_PORT: int = int(os.environ.get("SMTP_PORT", 587))
    SMTP_USER: str = os.environ.get("SMTP_USER", "")
    SMTP_PASSWORD: str = os.environ.get("SMTP_PASSWORD", "")
    SMTP_FROM_EMAIL: str = os.environ.get("SMTP_FROM_EMAIL", "noreply@otenga.io")
    SMTP_FROM_NAME: str = os.environ.get("SMTP_FROM_NAME", "Otenga BI Platform")

    # The base URL the frontend is served at (used to build verification links)
    APP_BASE_URL: str = os.environ.get("APP_BASE_URL", "http://localhost:5173")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
