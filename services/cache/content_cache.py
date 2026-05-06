"""
Content Hash Cache — Skips reprocessing when identical content was already analyzed.

Uses SHA-256 of **normalized** document content as key. Stores dashboard results
and metadata in SQLite for persistence across restarts.

Features:
- Text normalization before hashing (collapse whitespace, strip, lowercase)
- TTL-based expiry (default 7 days)
- Hit-count tracking for observability
- Hash-only lookup for endpoint-level dedup
"""
import hashlib
import json
import re
import time
from typing import Any, Dict, Optional
from core.logging.logger import get_logger

logger = get_logger(__name__)

# Default TTL: 7 days in seconds
_DEFAULT_TTL_SECONDS = 7 * 24 * 3600


def normalize_text(text: str) -> str:
    """
    Normalize document text before hashing to avoid false cache misses.

    - Collapse all whitespace (spaces, tabs, newlines) to single space
    - Strip leading/trailing whitespace
    - Lowercase

    This ensures trivially different versions of the same content
    (e.g. different line endings, extra spaces) produce the same hash.
    """
    return re.sub(r'\s+', ' ', text).strip().lower()


def content_hash(text: str, normalize: bool = True) -> str:
    """Compute SHA-256 hex digest of (optionally normalized) document text."""
    t = normalize_text(text) if normalize else text
    return hashlib.sha256(t.encode("utf-8", errors="replace")).hexdigest()


class ContentCache:
    """
    Document-level result cache backed by SQLite.

    Caches complete processing results (dashboard, deduction, metrics, etc.)
    keyed by content hash so that re-uploads of the same file skip LLM calls
    entirely.
    """

    def __init__(self, storage=None, ttl_seconds: int = _DEFAULT_TTL_SECONDS):
        self._storage = storage
        self._ttl = ttl_seconds
        self._init_table()

    def _init_table(self):
        if not self._storage:
            return
        try:
            cur = self._storage.conn.cursor()
            cur.execute('''
                CREATE TABLE IF NOT EXISTS content_cache (
                    content_hash TEXT PRIMARY KEY,
                    result TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    expires_at REAL NOT NULL,
                    hit_count INTEGER DEFAULT 0
                )
            ''')
            # Migrate existing DBs: add expires_at if missing (must run BEFORE index on expires_at)
            try:
                cur.execute('SELECT expires_at FROM content_cache LIMIT 1')
            except Exception:
                cur.execute('ALTER TABLE content_cache ADD COLUMN expires_at REAL DEFAULT 0')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_cache_created ON content_cache(created_at)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_cache_expires ON content_cache(expires_at)')
            self._storage.conn.commit()
        except Exception as e:
            logger.warning(f"Content cache table init failed: {e}")

    def get(self, text: str) -> Optional[Dict[str, Any]]:
        """Return cached result for this content, or None (respects TTL)."""
        if not self._storage:
            return None
        h = content_hash(text)
        try:
            cur = self._storage.conn.cursor()
            cur.execute(
                'SELECT result, expires_at FROM content_cache WHERE content_hash = ?',
                (h,),
            )
            row = cur.fetchone()
            if not row:
                logger.debug(f"Content cache MISS for hash {h[:12]}…")
                return None

            # TTL check
            expires_at = row[1] if len(row) > 1 else 0
            if expires_at and time.time() > expires_at:
                logger.info(f"Content cache EXPIRED for hash {h[:12]}… (expired {time.time() - expires_at:.0f}s ago)")
                cur.execute('DELETE FROM content_cache WHERE content_hash = ?', (h,))
                self._storage.conn.commit()
                return None

            cur.execute(
                'UPDATE content_cache SET hit_count = hit_count + 1 WHERE content_hash = ?',
                (h,),
            )
            self._storage.conn.commit()
            logger.info(f"Content cache HIT for hash {h[:12]}…")
            return json.loads(row[0])
        except Exception as e:
            logger.warning(f"Content cache lookup failed: {e}")
            return None

    def put(self, text: str, result: Dict[str, Any]) -> None:
        """Store processing result keyed by content hash (with TTL)."""
        if not self._storage:
            return
        h = content_hash(text)
        now = time.time()
        expires = now + self._ttl
        try:
            cur = self._storage.conn.cursor()
            cur.execute(
                '''INSERT OR REPLACE INTO content_cache
                   (content_hash, result, created_at, expires_at, hit_count)
                   VALUES (?, ?, ?, ?, 0)''',
                (h, json.dumps(result, default=str), now, expires),
            )
            self._storage.conn.commit()
            logger.info(f"Content cache STORE for hash {h[:12]}… (TTL {self._ttl}s)")
        except Exception as e:
            logger.warning(f"Content cache store failed: {e}")

    def invalidate(self, text: str) -> bool:
        """Remove cached result for given content."""
        if not self._storage:
            return False
        h = content_hash(text)
        try:
            cur = self._storage.conn.cursor()
            cur.execute('DELETE FROM content_cache WHERE content_hash = ?', (h,))
            self._storage.conn.commit()
            return cur.rowcount > 0
        except Exception:
            return False

    def has(self, text: str) -> bool:
        """Check if content is cached (TTL-aware) without deserializing."""
        if not self._storage:
            return False
        h = content_hash(text)
        try:
            cur = self._storage.conn.cursor()
            cur.execute(
                'SELECT expires_at FROM content_cache WHERE content_hash = ?',
                (h,),
            )
            row = cur.fetchone()
            if not row:
                return False
            expires_at = row[0] if row[0] else 0
            return not (expires_at and time.time() > expires_at)
        except Exception:
            return False

    def get_hash(self, text: str) -> str:
        """Return the content hash for a given text (for endpoint dedup)."""
        return content_hash(text)

    def cleanup_expired(self) -> int:
        """Remove all expired entries. Returns count deleted."""
        if not self._storage:
            return 0
        try:
            cur = self._storage.conn.cursor()
            cur.execute(
                'DELETE FROM content_cache WHERE expires_at > 0 AND expires_at < ?',
                (time.time(),),
            )
            self._storage.conn.commit()
            deleted = cur.rowcount
            if deleted:
                logger.info(f"Content cache: cleaned up {deleted} expired entries")
            return deleted
        except Exception as e:
            logger.warning(f"Content cache cleanup failed: {e}")
            return 0

    def stats(self) -> Dict[str, Any]:
        """Return cache statistics."""
        if not self._storage:
            return {"available": False}
        try:
            cur = self._storage.conn.cursor()
            cur.execute('SELECT COUNT(*), SUM(hit_count) FROM content_cache')
            row = cur.fetchone()
            cur.execute(
                'SELECT COUNT(*) FROM content_cache WHERE expires_at > 0 AND expires_at < ?',
                (time.time(),),
            )
            expired_row = cur.fetchone()
            return {
                "available": True,
                "total_entries": row[0] if row else 0,
                "total_hits": row[1] if row and row[1] else 0,
                "expired_entries": expired_row[0] if expired_row else 0,
                "ttl_seconds": self._ttl,
            }
        except Exception as e:
            return {"available": False, "error": str(e)}
