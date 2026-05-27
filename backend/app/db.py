"""Postgres storage for rule sets.

Rule sets are stored as JSON in a single table. All queries are
parameterized; no user content is interpolated into SQL. The schema
supports versioning: each save creates a new row (version) and a
separate pointer table records the active version per rule set name.
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import psycopg
from psycopg.rows import DictRow, dict_row

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://clientflow:clientflow@localhost:5432/clientflow",
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS rule_set_version (
    id          BIGSERIAL PRIMARY KEY,
    name        TEXT NOT NULL,
    version     INTEGER NOT NULL,
    body        JSONB NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (name, version)
);

CREATE TABLE IF NOT EXISTS rule_set_active (
    name        TEXT PRIMARY KEY,
    version     INTEGER NOT NULL
);
"""


@contextmanager
def connect() -> Iterator[psycopg.Connection[DictRow]]:
    conn = psycopg.connect(DATABASE_URL, row_factory=dict_row)
    try:
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    with connect() as conn:
        conn.execute(SCHEMA)
        conn.commit()


def next_version(conn: psycopg.Connection[DictRow], name: str) -> int:
    row = conn.execute(
        "SELECT COALESCE(MAX(version), 0) AS v FROM rule_set_version WHERE name = %s",
        (name,),
    ).fetchone()
    assert row is not None
    return int(row["v"]) + 1


def save_version(name: str, body: dict[str, Any]) -> int:
    """Store a new version of a rule set. Returns the new version number."""
    with connect() as conn:
        version = next_version(conn, name)
        conn.execute(
            "INSERT INTO rule_set_version (name, version, body) VALUES (%s, %s, %s)",
            (name, version, json.dumps(body)),
        )
        conn.commit()
        return version


def activate_version(name: str, version: int) -> None:
    """Point the active pointer at a version atomically."""
    with connect() as conn:
        exists = conn.execute(
            "SELECT 1 FROM rule_set_version WHERE name = %s AND version = %s",
            (name, version),
        ).fetchone()
        if exists is None:
            raise KeyError(f"version {version} of {name} does not exist")
        conn.execute(
            """
            INSERT INTO rule_set_active (name, version) VALUES (%s, %s)
            ON CONFLICT (name) DO UPDATE SET version = EXCLUDED.version
            """,
            (name, version),
        )
        conn.commit()


def get_version(name: str, version: int) -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute(
            "SELECT body FROM rule_set_version WHERE name = %s AND version = %s",
            (name, version),
        ).fetchone()
        return row["body"] if row else None


def get_active(name: str) -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT v.body
            FROM rule_set_active a
            JOIN rule_set_version v ON v.name = a.name AND v.version = a.version
            WHERE a.name = %s
            """,
            (name,),
        ).fetchone()
        return row["body"] if row else None


def active_version_number(name: str) -> int | None:
    with connect() as conn:
        row = conn.execute(
            "SELECT version FROM rule_set_active WHERE name = %s",
            (name,),
        ).fetchone()
        return int(row["version"]) if row else None


def list_versions(name: str) -> list[int]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT version FROM rule_set_version WHERE name = %s ORDER BY version",
            (name,),
        ).fetchall()
        return [int(r["version"]) for r in rows]
