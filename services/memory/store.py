"""
Memory System — SQLite-backed storage engine.

Provides a thin persistence layer for episodes and learnings.
Uses a single SQLite database in the storage directory — no external
dependencies required.

Tables:
  episodes   — full conversation records
  learnings  — extracted behavioural insights
"""
from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

logger = logging.getLogger(__name__)

# ── Defaults ───────────────────────────────────────────────────────────
_DEFAULT_DB_DIR = os.path.join(".", "storage")
_DEFAULT_DB_NAME = "memory.db"
_MAX_EPISODES = 500
_MAX_LEARNINGS = 200


# ── Schema ─────────────────────────────────────────────────────────────

_SCHEMA_SQL = """\
CREATE TABLE IF NOT EXISTS episodes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts          TEXT    NOT NULL,
    session_id  TEXT,
    query       TEXT    NOT NULL,
    tools_used  TEXT,               -- JSON array
    steps       TEXT,               -- JSON array
    final_answer TEXT,
    context     TEXT,               -- JSON object
    metadata    TEXT                -- JSON object (extra fields)
);

CREATE INDEX IF NOT EXISTS idx_episodes_ts       ON episodes(ts);
CREATE INDEX IF NOT EXISTS idx_episodes_query    ON episodes(query);

CREATE TABLE IF NOT EXISTS learnings (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    ts         TEXT    NOT NULL,
    kind       TEXT    NOT NULL,    -- 'preference' | 'pattern' | 'rule'
    text       TEXT    NOT NULL,
    source     TEXT,                -- episode id(s) that produced this
    confidence REAL    DEFAULT 1.0,
    metadata   TEXT                 -- JSON object
);

CREATE INDEX IF NOT EXISTS idx_learnings_kind ON learnings(kind);
"""


# ── Connection management ──────────────────────────────────────────────

class MemoryStore:
    """Thread-safe SQLite store for the memory system."""

    def __init__(self, db_path: str | None = None) -> None:
        if db_path is None:
            db_dir = Path(_DEFAULT_DB_DIR)
            db_dir.mkdir(parents=True, exist_ok=True)
            db_path = str(db_dir / _DEFAULT_DB_NAME)

        self._db_path = db_path
        self._local = threading.local()
        self._ensure_schema()

    # ── internal -------------------------------------------------------

    def _get_conn(self) -> sqlite3.Connection:
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(self._db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn = conn
        return conn

    @contextmanager
    def _cursor(self) -> Iterator[sqlite3.Cursor]:
        conn = self._get_conn()
        cur = conn.cursor()
        try:
            yield cur
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    def _ensure_schema(self) -> None:
        conn = self._get_conn()
        conn.executescript(_SCHEMA_SQL)
        conn.commit()

    # ── Episodes -------------------------------------------------------

    def save_episode(
        self,
        query: str,
        tools_used: List[str],
        steps: List[Dict[str, Any]],
        final_answer: str,
        context: Dict[str, Any] | None = None,
        session_id: str | None = None,
        metadata: Dict[str, Any] | None = None,
    ) -> int:
        """Insert a conversation episode.  Returns the row id."""
        ts = datetime.now(timezone.utc).isoformat()
        with self._cursor() as cur:
            cur.execute(
                """INSERT INTO episodes
                   (ts, session_id, query, tools_used, steps,
                    final_answer, context, metadata)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    ts,
                    session_id,
                    query,
                    json.dumps(tools_used),
                    json.dumps(steps, default=str),
                    final_answer,
                    json.dumps(context or {}, default=str),
                    json.dumps(metadata or {}, default=str),
                ),
            )
            row_id = cur.lastrowid

        self._trim_episodes()
        return row_id

    def search_episodes(
        self,
        query: str,
        *,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Keyword search episodes (case-insensitive).

        Splits the query into words and matches episodes where the query
        or final_answer contains ANY of the keywords.  Returns newest-first.
        """
        # Split into meaningful keywords (3+ chars)
        keywords = [w for w in query.split() if len(w) >= 3]
        if not keywords:
            keywords = [query]

        # Build OR conditions for each keyword
        conditions = []
        params: list = []
        for kw in keywords:
            conditions.append("(query LIKE ? OR final_answer LIKE ?)")
            params.extend([f"%{kw}%", f"%{kw}%"])

        where = " OR ".join(conditions)
        sql = (
            f"SELECT id, ts, session_id, query, tools_used, steps,"
            f"       final_answer, context, metadata "
            f"FROM episodes WHERE {where} "
            f"ORDER BY id DESC LIMIT ?"
        )
        params.append(limit)

        with self._cursor() as cur:
            cur.execute(sql, params)
            return [self._row_to_episode(row) for row in cur.fetchall()]

    def recent_episodes(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Return the most recent episodes."""
        with self._cursor() as cur:
            cur.execute(
                """SELECT id, ts, session_id, query, tools_used, steps,
                          final_answer, context, metadata
                   FROM episodes
                   ORDER BY id DESC LIMIT ?""",
                (limit,),
            )
            return [self._row_to_episode(row) for row in cur.fetchall()]

    def episode_count(self) -> int:
        with self._cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM episodes")
            return cur.fetchone()[0]

    def _trim_episodes(self) -> None:
        """Keep only the newest _MAX_EPISODES rows."""
        with self._cursor() as cur:
            cur.execute(
                """DELETE FROM episodes WHERE id NOT IN
                   (SELECT id FROM episodes ORDER BY id DESC LIMIT ?)""",
                (_MAX_EPISODES,),
            )

    @staticmethod
    def _row_to_episode(row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "id": row["id"],
            "ts": row["ts"],
            "session_id": row["session_id"],
            "query": row["query"],
            "tools_used": json.loads(row["tools_used"] or "[]"),
            "steps": json.loads(row["steps"] or "[]"),
            "final_answer": row["final_answer"],
            "context": json.loads(row["context"] or "{}"),
            "metadata": json.loads(row["metadata"] or "{}"),
        }

    # ── Learnings -------------------------------------------------------

    def save_learning(
        self,
        kind: str,
        text: str,
        source: str | None = None,
        confidence: float = 1.0,
        metadata: Dict[str, Any] | None = None,
    ) -> int:
        """Insert a learning.  Returns the row id."""
        ts = datetime.now(timezone.utc).isoformat()
        with self._cursor() as cur:
            cur.execute(
                """INSERT INTO learnings
                   (ts, kind, text, source, confidence, metadata)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    ts,
                    kind,
                    text,
                    source,
                    confidence,
                    json.dumps(metadata or {}, default=str),
                ),
            )
            row_id = cur.lastrowid

        self._trim_learnings()
        return row_id

    def search_learnings(
        self,
        query: str,
        *,
        kind: str | None = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Keyword search learnings (splits query into words, OR match)."""
        keywords = [w for w in query.split() if len(w) >= 3]
        if not keywords:
            keywords = [query]

        kw_conditions = " OR ".join(["text LIKE ?"] * len(keywords))
        params: list = [f"%{kw}%" for kw in keywords]

        sql = f"SELECT * FROM learnings WHERE ({kw_conditions})"
        if kind:
            sql += " AND kind = ?"
            params.append(kind)
        sql += " ORDER BY confidence DESC, id DESC LIMIT ?"
        params.append(limit)

        with self._cursor() as cur:
            cur.execute(sql, params)
            return [self._row_to_learning(row) for row in cur.fetchall()]

    def all_learnings(
        self,
        kind: str | None = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Return learnings, optionally filtered by kind."""
        if kind:
            sql = "SELECT * FROM learnings WHERE kind = ? ORDER BY id DESC LIMIT ?"
            params: tuple = (kind, limit)
        else:
            sql = "SELECT * FROM learnings ORDER BY id DESC LIMIT ?"
            params = (limit,)

        with self._cursor() as cur:
            cur.execute(sql, params)
            return [self._row_to_learning(row) for row in cur.fetchall()]

    def learning_count(self) -> int:
        with self._cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM learnings")
            return cur.fetchone()[0]

    def _trim_learnings(self) -> None:
        with self._cursor() as cur:
            cur.execute(
                """DELETE FROM learnings WHERE id NOT IN
                   (SELECT id FROM learnings ORDER BY id DESC LIMIT ?)""",
                (_MAX_LEARNINGS,),
            )

    @staticmethod
    def _row_to_learning(row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "id": row["id"],
            "ts": row["ts"],
            "kind": row["kind"],
            "text": row["text"],
            "source": row["source"],
            "confidence": row["confidence"],
            "metadata": json.loads(row["metadata"] or "{}"),
        }

    # ── Maintenance ------------------------------------------------------

    def close(self) -> None:
        conn = getattr(self._local, "conn", None)
        if conn:
            conn.close()
            self._local.conn = None
