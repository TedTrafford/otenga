import sqlalchemy
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .config import settings


def _ensure_database_exists():
    """Create BI_Otenga schema on MySQL if it doesn't exist yet."""
    url = (
        f"mysql+pymysql://{settings.BI_DB_USER}:{settings.BI_DB_PASSWORD}"
        f"@{settings.BI_DB_HOST}:{settings.BI_DB_PORT}"
    )
    try:
        tmp = create_engine(url, pool_pre_ping=True)
        with tmp.connect() as conn:
            conn.execute(text(
                f"CREATE DATABASE IF NOT EXISTS `{settings.BI_DB_NAME}` "
                f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            ))
        tmp.dispose()
    except Exception as exc:
        print(f"[database] Could not create schema '{settings.BI_DB_NAME}': {exc}")


_ensure_database_exists()

APP_DATABASE_URL = (
    f"mysql+pymysql://{settings.BI_DB_USER}:{settings.BI_DB_PASSWORD}"
    f"@{settings.BI_DB_HOST}:{settings.BI_DB_PORT}/{settings.BI_DB_NAME}"
    f"?charset=utf8mb4"
)

engine = create_engine(
    APP_DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_size=5,
    max_overflow=10,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
