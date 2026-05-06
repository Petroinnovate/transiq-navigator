"""
Memory service — public API.

::

    from services.memory import Cortex, get_cortex
"""
from services.memory.cortex import Cortex              # noqa: F401
from services.memory.episodes import EpisodicMemory    # noqa: F401
from services.memory.hippocampus import Hippocampus    # noqa: F401
from services.memory.store import MemoryStore          # noqa: F401

# ── Singleton accessor ────────────────────────────────────────────────
_cortex_instance: Cortex | None = None


def get_cortex() -> Cortex:
    """Return the shared Cortex instance (created once, reused)."""
    global _cortex_instance
    if _cortex_instance is None:
        _cortex_instance = Cortex()
    return _cortex_instance
