"""SQLite-backed account, session, and usage storage.

The project is an experiment and runs comfortably with one backend worker, so a
small SQLite store keeps the deployment simple while still giving durable auth
and cost records in the existing Docker data volume.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator, Optional

from app.auth.security import create_session_token, hash_session_token
from app.core.config import settings


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def to_iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def from_iso(value: str) -> datetime:
    return datetime.fromisoformat(value)


class AuthStore:
    def __init__(self, database_path: str):
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.database_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def initialize(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    display_name TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'user',
                    status TEXT NOT NULL DEFAULT 'active',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    last_login_at TEXT
                );

                CREATE TABLE IF NOT EXISTS auth_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    token_hash TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    revoked_at TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_auth_sessions_token_hash
                    ON auth_sessions(token_hash);

                CREATE TABLE IF NOT EXISTS llm_usage_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    provider TEXT NOT NULL,
                    model TEXT NOT NULL,
                    endpoint TEXT NOT NULL,
                    input_tokens INTEGER NOT NULL DEFAULT 0,
                    output_tokens INTEGER NOT NULL DEFAULT 0,
                    total_tokens INTEGER NOT NULL DEFAULT 0,
                    input_cost_usd REAL NOT NULL DEFAULT 0,
                    output_cost_usd REAL NOT NULL DEFAULT 0,
                    total_cost_usd REAL NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_llm_usage_user_created
                    ON llm_usage_events(user_id, created_at);
                """
            )

    def user_count(self) -> int:
        with self.connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS count FROM users").fetchone()
            return int(row["count"])

    def create_user(
        self,
        *,
        email: str,
        display_name: str,
        password_hash: str,
        role: str = "user",
    ) -> dict[str, Any]:
        now = to_iso(utc_now())
        with self.connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO users (email, display_name, password_hash, role, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, 'active', ?, ?)
                """,
                (email.strip().lower(), display_name.strip(), password_hash, role, now, now),
            )
            return self.get_user_by_id(cur.lastrowid, conn=conn)

    def get_user_by_id(
        self,
        user_id: int,
        *,
        conn: Optional[sqlite3.Connection] = None,
    ) -> Optional[dict[str, Any]]:
        query = "SELECT * FROM users WHERE id = ?"
        if conn is not None:
            row = conn.execute(query, (user_id,)).fetchone()
            return dict(row) if row else None
        with self.connect() as owned:
            row = owned.execute(query, (user_id,)).fetchone()
            return dict(row) if row else None

    def get_user_by_email(self, email: str) -> Optional[dict[str, Any]]:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE email = ? COLLATE NOCASE",
                (email.strip().lower(),),
            ).fetchone()
            return dict(row) if row else None

    def create_session(self, user_id: int) -> tuple[str, datetime]:
        token = create_session_token()
        expires_at = utc_now() + timedelta(days=settings.AUTH_SESSION_TTL_DAYS)
        now = to_iso(utc_now())
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO auth_sessions (user_id, token_hash, created_at, expires_at)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, hash_session_token(token), now, to_iso(expires_at)),
            )
            conn.execute(
                "UPDATE users SET last_login_at = ?, updated_at = ? WHERE id = ?",
                (now, now, user_id),
            )
        return token, expires_at

    def get_user_by_session(self, token: str) -> Optional[dict[str, Any]]:
        if not token:
            return None
        now = to_iso(utc_now())
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT users.*
                FROM auth_sessions
                JOIN users ON users.id = auth_sessions.user_id
                WHERE auth_sessions.token_hash = ?
                  AND auth_sessions.revoked_at IS NULL
                  AND auth_sessions.expires_at > ?
                  AND users.status = 'active'
                """,
                (hash_session_token(token), now),
            ).fetchone()
            return dict(row) if row else None

    def revoke_session(self, token: str) -> None:
        if not token:
            return
        with self.connect() as conn:
            conn.execute(
                "UPDATE auth_sessions SET revoked_at = ? WHERE token_hash = ?",
                (to_iso(utc_now()), hash_session_token(token)),
            )

    def record_usage(
        self,
        *,
        user_id: int,
        provider: str,
        model: str,
        endpoint: str,
        input_tokens: int,
        output_tokens: int,
        input_cost_usd: float,
        output_cost_usd: float,
    ) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO llm_usage_events (
                    user_id, provider, model, endpoint,
                    input_tokens, output_tokens, total_tokens,
                    input_cost_usd, output_cost_usd, total_cost_usd,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    provider,
                    model,
                    endpoint,
                    max(0, int(input_tokens)),
                    max(0, int(output_tokens)),
                    max(0, int(input_tokens) + int(output_tokens)),
                    max(0.0, float(input_cost_usd)),
                    max(0.0, float(output_cost_usd)),
                    max(0.0, float(input_cost_usd) + float(output_cost_usd)),
                    to_iso(utc_now()),
                ),
            )

    def usage_summary(self, user_id: int) -> dict[str, Any]:
        with self.connect() as conn:
            total = self._usage_totals(conn, user_id)
            today = self._usage_totals(conn, user_id, since=self._start_of_day())
            month = self._usage_totals(conn, user_id, since=self._start_of_month())
            providers = conn.execute(
                """
                SELECT provider, model,
                       SUM(input_tokens) AS input_tokens,
                       SUM(output_tokens) AS output_tokens,
                       SUM(total_tokens) AS total_tokens,
                       SUM(total_cost_usd) AS total_cost_usd,
                       COUNT(*) AS calls
                FROM llm_usage_events
                WHERE user_id = ?
                GROUP BY provider, model
                ORDER BY total_tokens DESC
                """,
                (user_id,),
            ).fetchall()
            return {
                "today": today,
                "month": month,
                "total": total,
                "by_provider": [dict(row) for row in providers],
            }

    def _usage_totals(
        self,
        conn: sqlite3.Connection,
        user_id: int,
        *,
        since: Optional[datetime] = None,
    ) -> dict[str, Any]:
        where = "WHERE user_id = ?"
        params: list[Any] = [user_id]
        if since is not None:
            where += " AND created_at >= ?"
            params.append(to_iso(since))
        row = conn.execute(
            f"""
            SELECT COUNT(*) AS calls,
                   COALESCE(SUM(input_tokens), 0) AS input_tokens,
                   COALESCE(SUM(output_tokens), 0) AS output_tokens,
                   COALESCE(SUM(total_tokens), 0) AS total_tokens,
                   COALESCE(SUM(total_cost_usd), 0) AS total_cost_usd
            FROM llm_usage_events
            {where}
            """,
            params,
        ).fetchone()
        return dict(row)

    def _start_of_day(self) -> datetime:
        now = utc_now()
        return now.replace(hour=0, minute=0, second=0, microsecond=0)

    def _start_of_month(self) -> datetime:
        now = utc_now()
        return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


auth_store = AuthStore(settings.AUTH_DB_PATH)
