"""
Pre-Indexed Embedding Service
==============================

Pre-computes and persists embeddings at document ingestion time so that
search queries hit the index directly with zero per-query embedding cost
for the *corpus* side.

Lifecycle:
  1. Document uploaded  → preindex_document(doc_id, chunks)
  2. Embeddings stored  → FAISS index + Qdrant payloads updated
  3. Query arrives      → only the *query* needs embedding (1 call)

Integration points:
  - Called from processors after chunking
  - Works with both FAISS (semantic.py) and Qdrant (vector_storage.py)
"""
from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)

# Batch size for embedding calls (0 = auto-detect from hardware)
_EMBED_BATCH_SIZE = int(os.getenv("EMBED_BATCH_SIZE", "0"))


class PreIndexService:
    """
    Pre-compute, persist, and manage document embeddings.

    Supports two backends:
      - FAISS  (app.search.semantic.FaissIndex)
      - Qdrant (vector_storage.VectorStorageService)

    Falls back gracefully if either backend is unavailable.
    """

    def __init__(self):
        self._embedding_model = None
        self._faiss_index = None
        self._qdrant = None
        self._init_backends()

    # ------------------------------------------------------------------
    # Backend initialization
    # ------------------------------------------------------------------

    def _init_backends(self):
        # Embedding model (singleton via EmbeddingModel wrapper)
        try:
            from services.vector_store.embeddings.embedding_model import EmbeddingModel
            self._embedding_model = EmbeddingModel()
            logger.info("PreIndexService: embedding model ready")
        except Exception as e:
            logger.warning("PreIndexService: embedding model unavailable — %s", e)

        # FAISS
        try:
            from services.vector_store.indexing.faiss_index import FaissIndex
            self._faiss_index = FaissIndex()
            logger.info("PreIndexService: FAISS backend ready (%d vectors)", self._faiss_index.index.ntotal)
        except Exception as e:
            logger.info("PreIndexService: FAISS unavailable — %s", e)

        # Qdrant
        try:
            from services.vector_store.indexing.vector_storage import VectorStorageService
            self._qdrant = VectorStorageService()
            logger.info("PreIndexService: Qdrant backend ready")
        except Exception as e:
            logger.info("PreIndexService: Qdrant unavailable — %s", e)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def preindex_document(
        self,
        doc_id: str,
        chunks: List[str],
        metadata: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Pre-compute embeddings for all chunks and store in index backends.

        Args:
            doc_id:   Unique document identifier
            chunks:   List of text chunks
            metadata: Per-chunk metadata dicts (optional)

        Returns:
            {
              "doc_id": str,
              "chunks_indexed": int,
              "backends": ["faiss", "qdrant"],
              "elapsed_ms": float,
            }
        """
        if not chunks:
            return {"doc_id": doc_id, "chunks_indexed": 0, "backends": [], "elapsed_ms": 0}

        t0 = time.time()
        embeddings = self._batch_embed(chunks)
        if embeddings is None:
            logger.warning("PreIndexService: could not embed chunks for doc %s", doc_id)
            return {"doc_id": doc_id, "chunks_indexed": 0, "backends": [], "elapsed_ms": 0}

        backends_used: List[str] = []

        # Store in FAISS
        if self._faiss_index is not None:
            try:
                chunk_ids = [f"{doc_id}__chunk_{i}" for i in range(len(chunks))]
                self._faiss_index.add(embeddings, chunk_ids=chunk_ids)
                backends_used.append("faiss")
            except Exception as e:
                logger.error("FAISS indexing failed for doc %s: %s", doc_id, e)

        # Store in Qdrant
        if self._qdrant is not None:
            try:
                payloads = []
                for i, chunk in enumerate(chunks):
                    payload = {
                        "doc_id": doc_id,
                        "chunk_index": i,
                        "text": chunk[:2000],  # payload preview
                    }
                    if metadata and i < len(metadata):
                        payload.update(metadata[i])
                    payloads.append(payload)
                self._qdrant.add_chunks(chunks, embeddings.tolist(), payloads)
                backends_used.append("qdrant")
            except Exception as e:
                logger.error("Qdrant indexing failed for doc %s: %s", doc_id, e)

        elapsed = round((time.time() - t0) * 1000, 1)
        logger.info(
            "Pre-indexed %d chunks for doc %s → %s in %.1f ms",
            len(chunks), doc_id, backends_used, elapsed,
        )
        return {
            "doc_id": doc_id,
            "chunks_indexed": len(chunks),
            "backends": backends_used,
            "elapsed_ms": elapsed,
        }

    def remove_document(self, doc_id: str) -> bool:
        """Remove all indexed embeddings for a document (cleanup on delete)."""
        try:
            if self._qdrant is not None:
                # Qdrant supports payload-filtered deletion
                from qdrant_client.models import Filter, FieldCondition, MatchValue
                self._qdrant._client.delete(
                    collection_name="transiq_chunks",
                    points_selector=Filter(
                        must=[FieldCondition(key="doc_id", match=MatchValue(value=doc_id))]
                    ),
                )
            logger.info("Removed pre-indexed embeddings for doc %s", doc_id)
            return True
        except Exception as e:
            logger.warning("Failed to remove embeddings for doc %s: %s", doc_id, e)
            return False

    def index_stats(self) -> Dict[str, Any]:
        """Return current index statistics."""
        stats: Dict[str, Any] = {}
        if self._faiss_index is not None:
            stats["faiss_total_vectors"] = self._faiss_index.index.ntotal
        if self._qdrant is not None:
            try:
                info = self._qdrant._client.get_collection("transiq_chunks")
                stats["qdrant_points"] = info.points_count
            except Exception:
                stats["qdrant_points"] = "unavailable"
        return stats

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _batch_embed(self, texts: List[str]) -> Optional[np.ndarray]:
        """Embed texts in batches with OOM auto-fallback."""
        if self._embedding_model is None:
            return None
        # Resolve batch size: env override → hardware-optimal default
        if _EMBED_BATCH_SIZE > 0:
            batch_size = _EMBED_BATCH_SIZE
        else:
            try:
                from services.vector_store.indexing.vector_storage import get_batch_size
                batch_size = get_batch_size()
            except Exception:
                batch_size = 128
        try:
            return self._embedding_model.embed_batch(texts, batch_size=batch_size)
        except RuntimeError:
            # embed_batch already retries internally; if it still fails, manual fallback
            logger.warning("PreIndex: full-batch embed failed, falling back to small batches")
            all_embeddings = []
            small_bs = 16
            for start in range(0, len(texts), small_bs):
                batch = texts[start : start + small_bs]
                embs = self._embedding_model.embed(batch)
                all_embeddings.append(np.array(embs, dtype=np.float32))
            return np.vstack(all_embeddings) if all_embeddings else None
        except Exception as e:
            logger.error("Batch embedding failed: %s", e)
            return None


# Lazy singleton
_instance: Optional[PreIndexService] = None


def get_preindex_service() -> PreIndexService:
    """Get or create the global PreIndexService singleton."""
    global _instance
    if _instance is None:
        _instance = PreIndexService()
    return _instance
