"""
Prediction Logger
=================
Structured logging for every prediction/inference call.
Feeds into drift detection and audit trail.

Usage:
    from pipelines.monitoring.prediction_logger import get_prediction_logger

    pred_logger = get_prediction_logger()
    pred_logger.log(doc_id="abc", prediction={...}, confidence=0.87, latency_ms=450)
"""
from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_ROOT = Path(__file__).resolve().parent.parent.parent  # Backend/
DEFAULT_LOG_DIR = _ROOT / "storage_runtime" / "logs" / "predictions"


@dataclass
class PredictionRecord:
    timestamp: str
    doc_id: str
    model_name: str = ""
    model_version: str = ""
    prediction: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    latency_ms: float = 0.0
    input_hash: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class PredictionLogger:
    """
    Append-only structured prediction logger.
    Writes JSONL (one JSON record per line) for easy streaming analysis.
    """

    def __init__(self, log_dir: Optional[Path] = None, max_buffer: int = 50):
        self.log_dir = log_dir or DEFAULT_LOG_DIR
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._buffer: List[Dict[str, Any]] = []
        self._max_buffer = max_buffer

    def log(
        self,
        doc_id: str,
        prediction: Dict[str, Any],
        confidence: float = 0.0,
        latency_ms: float = 0.0,
        model_name: str = "",
        model_version: str = "",
        input_hash: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Log a single prediction."""
        record = PredictionRecord(
            timestamp=datetime.now(timezone.utc).isoformat(),
            doc_id=doc_id,
            model_name=model_name,
            model_version=model_version,
            prediction=prediction,
            confidence=confidence,
            latency_ms=latency_ms,
            input_hash=input_hash,
            metadata=metadata or {},
        )
        self._buffer.append(asdict(record))

        if len(self._buffer) >= self._max_buffer:
            self.flush()

    def flush(self):
        """Write buffered records to disk."""
        if not self._buffer:
            return
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        log_file = self.log_dir / f"predictions_{today}.jsonl"
        with open(log_file, "a", encoding="utf-8") as f:
            for record in self._buffer:
                f.write(json.dumps(record, default=str) + "\n")
        logger.debug("Flushed %d prediction records to %s", len(self._buffer), log_file.name)
        self._buffer.clear()

    def get_recent(self, n: int = 100) -> List[Dict[str, Any]]:
        """Read the most recent n prediction records from today's log."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        log_file = self.log_dir / f"predictions_{today}.jsonl"
        if not log_file.exists():
            return list(self._buffer[-n:])
        lines = log_file.read_text(encoding="utf-8").strip().split("\n")
        records = [json.loads(line) for line in lines[-n:] if line]
        return records

    def __del__(self):
        try:
            self.flush()
        except Exception:
            pass


# Singleton
_logger: Optional[PredictionLogger] = None


def get_prediction_logger() -> PredictionLogger:
    global _logger
    if _logger is None:
        _logger = PredictionLogger()
    return _logger
