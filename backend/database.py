"""
AutoRun v3 - Database Models

SQLAlchemy models for User, UserSession, Service.
Database lives at /var/lib/autorun/autorun.db (production)
or ./autorun.db (development fallback).
"""

import os
import secrets
from datetime import datetime, timezone, timedelta
from pathlib import Path

import bcrypt
from sqlalchemy import (
    create_engine, Column, Integer, String, Boolean,
    DateTime, Text, JSON, ForeignKey, event
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, Session

# ---------------------------------------------------------------------------
# Engine + Session
# ---------------------------------------------------------------------------

DB_DIR = Path(os.environ.get("AUTORUN_DB_DIR", "/var/lib/autorun"))
DB_PATH = DB_DIR / "autorun.db"

if not DB_DIR.exists():
    DB_PATH = Path("autorun.db")

engine = create_engine(
    f"sqlite:///{DB_PATH}",
    connect_args={"check_same_thread": False},
    echo=False,
)

@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    password_hash = Column(String(128), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_login = Column(DateTime, nullable=True)

    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")

    def set_password(self, password: str) -> None:
        self.password_hash = bcrypt.hashpw(
            password.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")

    def check_password(self, password: str) -> bool:
        return bcrypt.checkpw(
            password.encode("utf-8"),
            self.password_hash.encode("utf-8")
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "username": self.username,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
        }


class UserSession(Base):
    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token = Column(String(64), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime, nullable=False)

    user = relationship("User", back_populates="sessions")

    @classmethod
    def create(cls, user_id: int, days: int = 30) -> "UserSession":
        return cls(
            user_id=user_id,
            token=secrets.token_urlsafe(48),
            expires_at=datetime.now(timezone.utc) + timedelta(days=days),
        )

    @property
    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) > self.expires_at.replace(tzinfo=timezone.utc)


class Service(Base):
    __tablename__ = "services"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(64), unique=True, nullable=False, index=True)
    description = Column(Text, default="")
    folder = Column(Text, nullable=False)
    entrypoint = Column(String(128), default="run.py")
    port = Column(Integer, nullable=True)
    web_interface = Column(Boolean, default=False)
    url = Column(String(128), nullable=True)
    auto_restart = Column(String(16), default="always")
    enabled = Column(Boolean, default=True)
    environment = Column(JSON, default=dict)
    depends_on = Column(JSON, default=list)
    github_url = Column(Text, nullable=True)
    auto_update = Column(Boolean, default=False)
    last_commit_sha = Column(String(40), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime,
                        default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    @property
    def service_filename(self) -> str:
        return f"autorun-{self.name}.service"

    @property
    def service_path(self) -> Path:
        return Path(f"/etc/systemd/system/{self.service_filename}")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "folder": self.folder,
            "entrypoint": self.entrypoint,
            "port": self.port,
            "web_interface": self.web_interface,
            "url": self.url,
            "auto_restart": self.auto_restart,
            "enabled": self.enabled,
            "environment": self.environment or {},
            "depends_on": self.depends_on or [],
            "github_url": self.github_url,
            "auto_update": self.auto_update,
            "last_commit_sha": self.last_commit_sha,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Setting(Base):
    __tablename__ = "settings"

    key   = Column(String(64), primary_key=True)
    value = Column(Text, nullable=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def next_available_port(db, start: int = 5001) -> int:
    from sqlalchemy import func
    max_port = db.query(func.max(Service.port)).filter(Service.port.isnot(None)).scalar()
    if max_port is None:
        return start
    next_port = max_port + 1
    if next_port <= 5999:
        return next_port
    used = {row[0] for row in db.query(Service.port).filter(Service.port.isnot(None)).all()}
    for port in range(start, 6000):
        if port not in used:
            return port
    raise RuntimeError("No available ports in range 5001-5999")


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def create_first_user(username: str, password: str) -> User:
    db = SessionLocal()
    try:
        existing = db.query(User).first()
        if existing:
            raise ValueError("Users already exist. Use the dashboard to manage users.")
        user = User(username=username)
        user.set_password(password)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    finally:
        db.close()
