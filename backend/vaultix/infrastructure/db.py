import os
from typing import Any

from sqlalchemy import Connection, Engine, create_engine, text

DEFAULT_URL = "postgresql+psycopg://vaultix@127.0.0.1:56432/vaultix"


def connect_engine(url: str | None = None) -> Engine:
    return create_engine(
        url or os.getenv("DATABASE_URL", DEFAULT_URL),
        isolation_level="READ COMMITTED",
        pool_pre_ping=True,
        hide_parameters=True,
    )


def query(conn: Connection, sql: str, **parameters: Any):
    return conn.execute(text(sql), parameters)


def one(conn: Connection, sql: str, **parameters: Any) -> dict | None:
    row = query(conn, sql, **parameters).mappings().one_or_none()
    return dict(row) if row is not None else None


def many(conn: Connection, sql: str, **parameters: Any) -> list[dict]:
    return [dict(row) for row in query(conn, sql, **parameters).mappings()]
