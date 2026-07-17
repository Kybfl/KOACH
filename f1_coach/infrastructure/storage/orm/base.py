"""Shared SQLAlchemy declarative base.

Both the F1 25 and FSAE ORM table modules import Base from here rather
than defining their own — all ORM models must share a single Base so
that Base.metadata.create_all() (called once in database.py) creates
every table, F1 25 and FSAE alike, in the same SQLite file.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass