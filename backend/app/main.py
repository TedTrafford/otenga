from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session
from .database import engine, Base
from .routers import auth_router, notebooks, execution, dashboards, users
from .models import User, UserRole, UserStatus
from .auth import get_password_hash

# ── Create / verify tables ─────────────────────────────────────────────────────
try:
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created / verified")
except Exception as exc:
    print(f"⚠️  Could not create tables: {exc}")

app = FastAPI(
    title="Otenga BI Platform",
    description="A collaborative Business Intelligence platform with Python-native query execution.",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://bi.aleza.co.ke",
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router, prefix="/api/v1/auth",       tags=["Authentication"])
app.include_router(notebooks.router,   prefix="/api/v1/notebooks",  tags=["Notebooks"])
app.include_router(execution.router,   prefix="/api/v1/execute",    tags=["Execution"])
app.include_router(dashboards.router,  prefix="/api/v1/dashboards", tags=["Dashboards"])
app.include_router(users.router,       prefix="/api/v1/users",      tags=["Users"])


# ── Column migrations ──────────────────────────────────────────────────────────
_COLUMN_MIGRATIONS = [
    # (column_name, ALTER TABLE SQL)
    ("status",
     "ALTER TABLE users ADD COLUMN status ENUM('email_pending','pending','active','disabled') "
     "NOT NULL DEFAULT 'active'"),
    ("full_name",
     "ALTER TABLE users ADD COLUMN full_name VARCHAR(120) NULL"),
    ("email_verified",
     "ALTER TABLE users ADD COLUMN email_verified TINYINT(1) NOT NULL DEFAULT 0"),
    ("verification_token",
     "ALTER TABLE users ADD COLUMN verification_token VARCHAR(100) NULL"),
    ("verification_token_expires",
     "ALTER TABLE users ADD COLUMN verification_token_expires DATETIME NULL"),
]


def _run_column_migrations():
    """Add any columns that don't yet exist in the users table."""
    try:
        from .config import settings
        with engine.connect() as conn:
            existing = {
                row[0] for row in conn.execute(
                    text(
                        "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
                        "WHERE TABLE_SCHEMA = :schema AND TABLE_NAME = 'users'"
                    ),
                    {"schema": settings.BI_DB_NAME},
                )
            }
            for col, sql in _COLUMN_MIGRATIONS:
                if col not in existing:
                    conn.execute(text(sql))
                    conn.commit()
                    print(f"✅ Migration: added column users.{col}")
    except Exception as exc:
        print(f"⚠️  Migration warning: {exc}")


# ── Startup ────────────────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    _run_column_migrations()
    _seed_default_users()


def _seed_default_users():
    """Seed admin / creator / viewer accounts on first run."""
    db: Session = None
    from .database import SessionLocal
    db = SessionLocal()
    try:
        if db.query(User).count() == 0:
            defaults = [
                User(
                    username="admin", email="admin@otenga.io",
                    password_hash=get_password_hash("admin123"),
                    role=UserRole.superuser, status=UserStatus.active,
                    email_verified=True, avatar_color="#7C3AED",
                ),
                User(
                    username="creator", email="creator@otenga.io",
                    password_hash=get_password_hash("creator123"),
                    role=UserRole.creator, status=UserStatus.active,
                    email_verified=True, avatar_color="#00D4FF",
                ),
                User(
                    username="viewer", email="viewer@otenga.io",
                    password_hash=get_password_hash("viewer123"),
                    role=UserRole.viewer, status=UserStatus.active,
                    email_verified=True, avatar_color="#06FFA5",
                ),
            ]
            db.add_all(defaults)
            db.commit()
            print("✅ Default users seeded: admin/admin123, creator/creator123, viewer/viewer123")
    except Exception as exc:
        print(f"⚠️  Seeding skipped: {exc}")
    finally:
        if db:
            db.close()


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "Otenga BI Platform", "version": "1.0.0"}
