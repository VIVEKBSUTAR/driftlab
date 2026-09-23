"""
Database session management and connection utilities for DriftLab SQLite store.
"""

from contextlib import contextmanager
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session
from driftlab.store.models import Base

DEFAULT_DB_URL = "sqlite:///driftlab.db"


def get_engine(db_url: str = DEFAULT_DB_URL, echo: bool = False) -> Engine:
    """Creates a SQLAlchemy engine, with SQLite foreign key enforcement enabled."""
    connect_args = {}
    if db_url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
    
    engine = create_engine(db_url, echo=echo, connect_args=connect_args)
    
    # Enable foreign keys for SQLite
    if db_url.startswith("sqlite"):
        from sqlalchemy import event
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


def create_tables(engine: Engine) -> None:
    """Creates all database tables defined in Base metadata."""
    Base.metadata.create_all(bind=engine)


def drop_tables(engine: Engine) -> None:
    """Drops all database tables defined in Base metadata."""
    Base.metadata.drop_all(bind=engine)


def get_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Returns a configured sessionmaker bound to the given engine."""
    return sessionmaker(
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
        bind=engine,
    )


@contextmanager
def get_db(session_factory: sessionmaker[Session]) -> Generator[Session, None, None]:
    """Context manager for managing transactional session lifecycle."""
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
