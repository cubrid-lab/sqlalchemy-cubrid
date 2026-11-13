"""Shared helpers for the offline compiler test modules (``test/test_compiler*.py``).

One ``metadata`` and ``users`` table are shared so every module compiles against
the same objects.
"""

from __future__ import annotations

from sqlalchemy import Column, Integer, MetaData, String, Table

from sqlalchemy_cubrid.dialect import CubridDialect


def _compile(stmt, dialect=None):
    """Compile a statement using the CUBRID dialect and return SQL string."""
    if dialect is None:
        dialect = CubridDialect()
    return stmt.compile(dialect=dialect, compile_kwargs={"literal_binds": True}).string


def _norm(sql: str) -> str:
    return " ".join(sql.split())


metadata = MetaData()


users = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String(100)),
    Column("email", String(200)),
)
