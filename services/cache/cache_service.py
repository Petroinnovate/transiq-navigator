"""
Redis Cache Service — Tier 1+2 Cost Optimization
Features:
  - Redis primary with SQLite fallback (no cold starts on restart)
  - TTL-based expiry
  - Semantic result caching (hash on doc_id + query)
  - Tree structure caching (built once, reused forever)
"""

import json
import hashlib
import logging
import os
import sqlite3
from typing import Any, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", str(86400 * 7)))  # 7 days default

# SQLite fallback path
CACHE_DB_PATH = os.getenv("CACHE_DB_PATH", "cache_storage.db")


class SQLiteFallbackCache:
    """Persistent fallback cache using SQLite when Redis is unavailable."""

    def __init__(self, db_path: str = CACHE_DB_PATH):
        self.db_path = db_path
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init()

    def _init(self):
        cur = self._conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS cache (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                expires_at TEXT NOT NULL
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_cache_expires ON cache(expires_at)")
        self._conn.commit()

    def get(self, key: str) -> Optional[str]:
        cur = self._conn.cursor()
        now = datetime.now(timezone.utc).isoformat()
        cur.execute(
            "SELECT value FROM cache WHERE key = ? AND expires_at > ?",
            (key, now)
        )
        row = cur.fetchone()
        return row[0] if row else None

    def set(self, key: str, value: str, ttl: int = CACHE_TTL_SECONDS):
        from datetime import timedelta
        expires_at = (datetime.now(timezone.utc) + timedelta(seconds=ttl)).isoformat()
        cur = self._conn.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO cache (key, value, expires_at) VALUES (?, ?, ?)",
            (key, value, expires_at)
        )
        self._conn.commit()

    def delete(self, key: str):
        cur = self._conn.cursor()
        cur.execute("DELETE FROM cache WHERE key = ?", (key,))
        self._conn.commit()

    def purge_expired(self):
        """Remove all expired entries."""
        now = datetime.now(timezone.utc).isoformat()
        cur = self._conn.cursor()
        cur.execute("DELETE FROM cache WHERE expires_at <= ?", (now,))
        self._conn.commit()
        return cur.rowcount


class CacheService:
    """
    Two-tier cache:
      Tier 1 — Redis (distributed, shared across workers)
      Tier 2 — SQLite (persistent fallback, zero network overhead)
    """

    def __init__(self):
        self._redis = None
        self._sqlite = SQLiteFallbackCache()
        self._try_connect_redis()

    def _try_connect_redis(self):
        try:
            import redis as redis_lib
            client = redis_lib.from_url(REDIS_URL, socket_connect_timeout=2, decode_responses=True)
            client.ping()
            self._redis = client
            logger.info("CacheService: Redis connected at %s", REDIS_URL)
        except Exception as e:
            logger.warning("CacheService: Redis unavailable (%s). Using SQLite fallback.", e)
            self._redis = None

    # ------------------------------------------------------------------
    # Low-level get/set/delete
    # ------------------------------------------------------------------

    def _cache_get(self, key: str) -> Optional[str]:
        if self._redis:
            try:
                return self._redis.get(key)
            except Exception:
                pass
        return self._sqlite.get(key)

    def _cache_set(self, key: str, value: str, ttl: int = CACHE_TTL_SECONDS):
        if self._redis:
            try:
                self._redis.setex(key, ttl, value)
                return
            except Exception:
                pass
        self._sqlite.set(key, value, ttl)

    def _cache_delete(self, key: str):
        if self._redis:
            try:
                self._redis.delete(key)
            except Exception:
                pass
        self._sqlite.delete(key)

    # ------------------------------------------------------------------
    # Document tree caching  (used by PageIndex / outline extraction)
    # ------------------------------------------------------------------

    def get_doc_tree(self, doc_id: str) -> Optional[dict]:
        """Retrieve cached document tree."""
        raw = self._cache_get(f"tree:{doc_id}")
        if raw:
            logger.debug("Cache HIT: tree for doc_id=%s", doc_id)
            return json.loads(raw)
        return None

    def set_doc_tree(self, doc_id: str, tree: dict, ttl: int = CACHE_TTL_SECONDS):
        """Cache a document tree structure."""
        self._cache_set(f"tree:{doc_id}", json.dumps(tree), ttl)
        logger.debug("Cache SET: tree for doc_id=%s", doc_id)

    def invalidate_doc_tree(self, doc_id: str):
        self._cache_delete(f"tree:{doc_id}")

    # ------------------------------------------------------------------
    # Reasoning / retrieval result caching
    # ------------------------------------------------------------------

    @staticmethod
    def _query_key(doc_id: str, query: str) -> str:
        q_hash = hashlib.md5(query.strip().lower().encode()).hexdigest()[:16]
        return f"reasoning:{doc_id}:{q_hash}"

    def get_reasoning(self, doc_id: str, query: str) -> Optional[Any]:
        """Retrieve cached reasoning result for (doc_id, query) pair."""
        raw = self._cache_get(self._query_key(doc_id, query))
        if raw:
            logger.debug("Cache HIT: reasoning for doc_id=%s query_hash", doc_id)
            return json.loads(raw)
        return None

    def set_reasoning(self, doc_id: str, query: str, result: Any, ttl: int = CACHE_TTL_SECONDS):
        """Cache a reasoning / retrieval result."""
        self._cache_set(self._query_key(doc_id, query), json.dumps(result), ttl)
        logger.debug("Cache SET: reasoning for doc_id=%s", doc_id)

    # ------------------------------------------------------------------
    # Embedding caching  (avoid regenerating same text embeddings)
    # ------------------------------------------------------------------

    @staticmethod
    def _embedding_key(text: str) -> str:
        return f"emb:{hashlib.sha256(text.encode()).hexdigest()[:32]}"

    def get_embedding(self, text: str) -> Optional[list]:
        raw = self._cache_get(self._embedding_key(text))
        return json.loads(raw) if raw else None

    def set_embedding(self, text: str, embedding: list, ttl: int = CACHE_TTL_SECONDS):
        self._cache_set(self._embedding_key(text), json.dumps(embedding), ttl)

    # ------------------------------------------------------------------
    # Full dashboard result caching  (per file hash, saves Gemini calls)
    # ------------------------------------------------------------------

    @staticmethod
    def _dashboard_key(file_hash: str) -> str:
        return f"dashboard:{file_hash}"

    def get_dashboard(self, file_hash: str) -> Optional[dict]:
        raw = self._cache_get(self._dashboard_key(file_hash))
        if raw:
            logger.info("Cache HIT: dashboard for file_hash=%s (Gemini call SKIPPED)", file_hash)
            return json.loads(raw)
        return None

    def set_dashboard(self, file_hash: str, dashboard: dict, ttl: int = CACHE_TTL_SECONDS):
        self._cache_set(self._dashboard_key(file_hash), json.dumps(dashboard), ttl)
        logger.info("Cache SET: dashboard for file_hash=%s", file_hash)

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def purge_expired(self) -> int:
        """Purge expired SQLite entries (Redis handles TTL automatically)."""
        removed = self._sqlite.purge_expired()
        logger.info("Purged %d expired SQLite cache entries", removed)
        return removed

    def health(self) -> dict:
        return {
            "redis_connected": self._redis is not None,
            "sqlite_fallback": self.db_path if not self._redis else "standby",
        }

    @property
    def db_path(self):
        return self._sqlite.db_path


# Singleton
_cache_instance: Optional[CacheService] = None


def get_cache_service() -> CacheService:
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = CacheService()
    return _cache_instance
