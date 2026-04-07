from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON, Enum, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from .database import Base


class UserRole(str, enum.Enum):
    creator   = "creator"
    viewer    = "viewer"
    superuser = "superuser"


class UserStatus(str, enum.Enum):
    email_pending = "email_pending"  # registered, must verify email first
    pending       = "pending"        # email verified, awaiting superuser approval
    active        = "active"         # approved and able to log in
    disabled      = "disabled"       # suspended by superuser


class NotebookStatus(str, enum.Enum):
    draft            = "draft"
    published        = "published"
    pending_approval = "pending_approval"


class User(Base):
    __tablename__ = "users"

    id            = Column(Integer, primary_key=True, index=True)
    username      = Column(String(50),  unique=True, index=True, nullable=False)
    email         = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role          = Column(Enum(UserRole),   default=UserRole.viewer)
    status        = Column(Enum(UserStatus), default=UserStatus.email_pending)
    is_active     = Column(Boolean, default=True)
    avatar_color  = Column(String(20), default="#00D4FF")
    full_name     = Column(String(120), nullable=True)
    email_verified           = Column(Boolean, default=False)
    verification_token       = Column(String(100), nullable=True, index=True)
    verification_token_expires = Column(DateTime(timezone=True), nullable=True)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())
    updated_at    = Column(DateTime(timezone=True), onupdate=func.now())

    notebooks  = relationship("Notebook",  back_populates="owner")
    audit_logs = relationship("AuditLog",  back_populates="user")


class Notebook(Base):
    __tablename__ = "notebooks"

    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    owner_id    = Column(Integer, ForeignKey("users.id"), nullable=False)
    cells       = Column(JSON, default=list)
    status      = Column(Enum(NotebookStatus), default=NotebookStatus.draft)
    tags        = Column(JSON, default=list)
    thumbnail   = Column(String(500), nullable=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())
    updated_at  = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    owner      = relationship("User",      back_populates="notebooks")
    dashboards = relationship("Dashboard", back_populates="notebook")


class Dashboard(Base):
    __tablename__ = "dashboards"

    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    notebook_id = Column(Integer, ForeignKey("notebooks.id"), nullable=True)
    layout      = Column(JSON, default=list)
    widgets     = Column(JSON, default=list)
    filters     = Column(JSON, default=list)
    status      = Column(Enum(NotebookStatus), default=NotebookStatus.draft)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())
    updated_at  = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    notebook = relationship("Notebook", back_populates="dashboards")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id            = Column(Integer, primary_key=True, index=True)
    user_id       = Column(Integer, ForeignKey("users.id"), nullable=False)
    action        = Column(String(100), nullable=False)
    resource_type = Column(String(50),  nullable=True)
    resource_id   = Column(Integer,     nullable=True)
    details       = Column(JSON,        nullable=True)
    ip_address    = Column(String(50),  nullable=True)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="audit_logs")
