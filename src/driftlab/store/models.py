"""
Implements the SQLAlchemy and SQLite data access layer to persist derived JSONL outputs into queryable relational data.
"""

from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Task(Base):
    __tablename__ = 'tasks'
    id = None
