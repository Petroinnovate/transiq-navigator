import os
import time
import uuid
from typing import Dict, Any, Optional
from pipelines.processing.chunking.adaptive import AdaptiveChunker
from core.logging.logger import get_logger

logger = get_logger(__name__)


class ChunkingPipeline:

    def __init__(self, strategy: str = 'adaptive', max_embed_chunks: int = 400, enable_metrics: bool = False):
        self.strategy = strategy
        self.max_embed_chunks = max_embed_chunks
        self.enable_metrics = enable_metrics

    def process(
        self,
        text: str,
        doc_id: str,
        doc_path: str = '',
        storage=None,
        enable_caching: bool = False,
    ) -> Dict[str, Any]:
        metrics = {}
        t0 = time.time()

        # --- Chunk ---
        t1 = time.time()
        chunker = AdaptiveChunker()
        chunks_with_meta = chunker.chunk_with_metadata(text)
        chunk_texts = [c['text'] for c in chunks_with_meta]
        if self.enable_metrics:
            metrics['chunking_time_ms'] = int((time.time() - t1) * 1000)
            metrics['total_chunks'] = len(chunk_texts)

        logger.info(f"Chunked document {doc_id}: {len(chunk_texts)} chunks")

        # Cap chunks for embedding
        embed_texts = chunk_texts[:self.max_embed_chunks]

        # --- Embed + Index (Qdrant) ---
        embedding_count = 0
        t2 = time.time()
        try:
            from services.vector_store.vector_storage import VectorStorageService
            vs = VectorStorageService()
            embedding_count = vs.upsert_chunks(embed_texts, doc_id)
            logger.info(f"Indexed {embedding_count} embeddings for {doc_id}")
        except Exception as e:
            logger.warning(f"Vector indexing skipped: {e}")
            embedding_count = 0
        if self.enable_metrics:
            metrics['embedding_time_ms'] = int((time.time() - t2) * 1000)

        # --- Save chunks to SQLite ---
        t3 = time.time()
        if storage:
            for idx, cm in enumerate(chunks_with_meta):
                chunk_id = f"{doc_id}-c-{idx}"
                storage.save_chunk(chunk_id, doc_id, cm['text'], cm.get('metadata', {}))
        if self.enable_metrics:
            metrics['storage_time_ms'] = int((time.time() - t3) * 1000)

        if self.enable_metrics:
            metrics['total_time_ms'] = int((time.time() - t0) * 1000)
            metrics['avg_chunk_size'] = (
                int(sum(len(c) for c in chunk_texts) / len(chunk_texts))
                if chunk_texts else 0
            )

        return {
            'chunks_data': chunks_with_meta,
            'chunks_count': len(chunk_texts),
            'embeddings_count': embedding_count,
            'metrics': metrics,
        }
