"""SQLite-backed case store. Jobs persist across restarts.

Schema is a pragmatic hybrid: a few queryable columns for listing, plus a
`data` column holding the full Case as JSON (the source of truth). Avoids a
normalized schema's joins and hand-rolled row<->model mapping for agent
results/conditions, at demo scale. `users`/`sessions` are separate simple
tables for the basic auth layer (see backend/auth.py).
"""

import sqlite3

from backend.config import DB_PATH
from backend.models import Case, CaseSummary


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _add_column_if_missing(conn: sqlite3.Connection, table: str, column: str, coltype: str) -> None:
    existing = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
    if column not in existing:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {coltype}")


def init_db() -> None:
    with _connect() as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                case_id     TEXT PRIMARY KEY,
                title       TEXT NOT NULL,
                change_type TEXT NOT NULL,
                status      TEXT NOT NULL,
                decision    TEXT NOT NULL,
                risk_rating TEXT,
                created_at  TEXT NOT NULL,
                data        TEXT NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs(created_at DESC)")
        # Migrate existing DBs created before created_by/decided_by existed.
        _add_column_if_missing(conn, "jobs", "created_by", "TEXT")
        _add_column_if_missing(conn, "jobs", "decided_by", "TEXT")

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                username      TEXT PRIMARY KEY,
                email         TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at    TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                token      TEXT PRIMARY KEY,
                username   TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )


def _upsert(case: Case) -> Case:
    risk_rating = case.result.risk_rating if case.result else None
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO jobs
                (case_id, title, change_type, status, decision, risk_rating, created_at,
                 created_by, decided_by, data)
            VALUES
                (:case_id, :title, :change_type, :status, :decision, :risk_rating, :created_at,
                 :created_by, :decided_by, :data)
            ON CONFLICT(case_id) DO UPDATE SET
                title=excluded.title, change_type=excluded.change_type, status=excluded.status,
                decision=excluded.decision, risk_rating=excluded.risk_rating,
                created_by=excluded.created_by, decided_by=excluded.decided_by, data=excluded.data
            """,
            {
                "case_id": case.id,
                "title": case.title,
                "change_type": case.change_type,
                "status": case.status,
                "decision": case.decision,
                "risk_rating": risk_rating,
                "created_at": case.created_at.isoformat(),
                "created_by": case.created_by,
                "decided_by": case.decided_by,
                "data": case.model_dump_json(),
            },
        )
    return case


def create_case(case: Case) -> Case:
    return _upsert(case)


def save_case(case: Case) -> Case:
    return _upsert(case)


def delete_case(case_id: str) -> bool:
    with _connect() as conn:
        cursor = conn.execute("DELETE FROM jobs WHERE case_id = ?", (case_id,))
    return cursor.rowcount > 0


def delete_all_cases() -> int:
    with _connect() as conn:
        cursor = conn.execute("DELETE FROM jobs")
    return cursor.rowcount


def get_case(case_id: str) -> Case | None:
    with _connect() as conn:
        row = conn.execute("SELECT data FROM jobs WHERE case_id = ?", (case_id,)).fetchone()
    return Case.model_validate_json(row["data"]) if row else None


def list_cases() -> list[CaseSummary]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT case_id, title, change_type, status, risk_rating, decision, created_at, "
            "created_by, decided_by FROM jobs ORDER BY created_at DESC"
        ).fetchall()
    return [CaseSummary(**dict(row)) for row in rows]


# ---- Users ----


def create_user(username: str, email: str, password_hash: str) -> None:
    from datetime import datetime, timezone

    with _connect() as conn:
        conn.execute(
            "INSERT INTO users (username, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
            (username, email, password_hash, datetime.now(timezone.utc).isoformat()),
        )


def get_user_by_username(username: str) -> dict | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    return dict(row) if row else None


def get_user_by_email(email: str) -> dict | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    return dict(row) if row else None


def update_user_password(username: str, password_hash: str) -> None:
    with _connect() as conn:
        conn.execute("UPDATE users SET password_hash = ? WHERE username = ?", (password_hash, username))


# ---- Sessions ----


def create_session(token: str, username: str) -> None:
    from datetime import datetime, timezone

    with _connect() as conn:
        conn.execute(
            "INSERT INTO sessions (token, username, created_at) VALUES (?, ?, ?)",
            (token, username, datetime.now(timezone.utc).isoformat()),
        )


def get_session_user(token: str) -> str | None:
    with _connect() as conn:
        row = conn.execute("SELECT username FROM sessions WHERE token = ?", (token,)).fetchone()
    return row["username"] if row else None


def delete_session(token: str) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
