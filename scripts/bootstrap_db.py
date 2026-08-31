"""Development-only schema bootstrap.

Production uses Alembic migrations. This helper exists to verify the initial model graph quickly
before the first migration is frozen.
"""
from app.db.base import Base
from app.db.session import engine
import app.models  # noqa: F401

if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    print("MIRANOAH development schema created.")
