from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings


def normalize_database_url(database_url: str) -> str:
    """
    Railway などが発行する PostgreSQL URL を
    SQLAlchemy + psycopg v3 用に正規化する。

    Railway:
        postgresql://user:password@host:port/db

    SQLAlchemy + psycopg v3:
        postgresql+psycopg://user:password@host:port/db
    """

    if database_url.startswith("postgresql://"):
        return database_url.replace(
            "postgresql://",
            "postgresql+psycopg://",
            1,
        )

    if database_url.startswith("postgres://"):
        return database_url.replace(
            "postgres://",
            "postgresql+psycopg://",
            1,
        )

    return database_url


DATABASE_URL = normalize_database_url(settings.database_url)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()
