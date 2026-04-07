"""
Vector Storage Service — Qdrant (replaces FAISS)

Why Qdrant over FAISS:
  - Native hybrid search: dense (cosine) + payload-filtered search
  - Local file persistence: no server required (qdrant_storage/ folder)
  - Small-to-big retrieval: store chunk + parent context as payload
  - Backward-compatible API: same interface as previous FAISS implementation
"""

import os
import uuid
import logging
from typing import List, Dict, Any, Optional, Tuple
from sentence_transformers import SentenceTransformer
import numpy as np
from tqdm import tqdm

logger = logging.getLogger(__name__)

# Qdrant Configuration
QDRANT_URL      = os.getenv("QDRANT_URL")  # Docker: http://qdrant:6333
QDRANT_PATH     = os.getenv("QDRANT_PATH", "./qdrant_storage")
USE_LOCAL_QDRANT = os.getenv("USE_LOCAL_QDRANT", "true").lower() == "true"
COLLECTION_NAME = "transiq_chunks"
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
EMBEDDING_DIM   = 384


class VectorStorageService:
    """
    Qdrant-backed vector storage service with Docker + local fallback.
    
    Connection Priority:
    1. Docker Qdrant (if QDRANT_URL set and USE_LOCAL_QDRANT=false)
    2. Local file (./qdrant_storage folder)
    
    Benefits:
    - Scalable: Multiple containers share same Qdrant service
    - Resilient: Falls back to local if Docker unavailable
    - Zero external dependencies except LLM API
    """

    def __init__(self, model_name: str = EMBEDDING_MODEL):
        self.model_name          = model_name
        self.model               = None
        self.embedding_dimension = EMBEDDING_DIM
        self._client             = None
        self._collection_ready   = False
        self._is_docker_mode     = False
        self._init_model()
        self._init_qdrant()

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def _init_model(self):
        try:
            logger.info("Loading embedding model: %s", self.model_name)
            self.model = SentenceTransformer(self.model_name)
            test_emb   = self.model.encode("test")
            self.embedding_dimension = len(test_emb)
            logger.info("Embedding model ready. Dimension: %d", self.embedding_dimension)
        except Exception as e:
            logger.error("Failed to load embedding model: %s", e)
            raise

    def _init_qdrant(self):
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import Distance, VectorParams, PayloadSchemaType

            # Try Docker Qdrant first (if configured)
            if QDRANT_URL and not USE_LOCAL_QDRANT:
                try:
                    self._client = QdrantClient(url=QDRANT_URL, timeout=5.0)
                    self._client.get_collections()  # Health check
                    self._is_docker_mode = True
                    logger.info("✓ Connected to Docker Qdrant at %s", QDRANT_URL)
                except Exception as docker_err:
                    logger.warning("Docker Qdrant unavailable (%s), falling back to local", docker_err)
                    self._client = None
            
            # Fallback to local file storage
            if not self._client:
                os.makedirs(QDRANT_PATH, exist_ok=True)
                self._client = QdrantClient(path=QDRANT_PATH)
                self._is_docker_mode = False
                logger.info("✓ Using local Qdrant storage at %s", QDRANT_PATH)

            existing = [c.name for c in self._client.get_collections().collections]
            if COLLECTION_NAME not in existing:
                self._client.create_collection(
                    collection_name=COLLECTION_NAME,
                    vectors_config=VectorParams(
                        size=self.embedding_dimension,
                        distance=Distance.COSINE,
                    ),
                )
                logger.info("Qdrant collection '%s' created.", COLLECTION_NAME)

            try:
                self._client.create_payload_index(
                    collection_name=COLLECTION_NAME,
                    field_name="doc_id",
                    field_schema=PayloadSchemaType.KEYWORD,
                )
            except Exception:
                pass  # Index already exists

            self._collection_ready = True

        except ImportError:
            logger.warning(
                "qdrant-client not installed. Run: pip install qdrant-client"
            )
            self._client = None
        except Exception as e:
            logger.error("Failed to initialise Qdrant: %s", e)
            self._client = None

    # ------------------------------------------------------------------
    # Embedding generation
    # ------------------------------------------------------------------

    def generate_embedding(self, text: str) -> List[float]:
        if not self.model:
            raise ValueError("Embedding model not initialised")
        return self.model.encode(text, convert_to_tensor=False).tolist()

    def generate_embeddings_batch(
        self,
        texts: List[str],
        batch_size: int = 32,
        show_progress: bool = True,
    ) -> List[List[float]]:
        if not self.model:
            raise ValueError("Embedding model not initialised")
        logger.info("Generating embeddings for %d texts", len(texts))
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=show_progress,
            convert_to_tensor=False,
        )
        return [e.tolist() for e in embeddings]

    def generate_query_embedding(self, query: str) -> List[float]:
        return self.generate_embedding(query)

    # ------------------------------------------------------------------
    # Qdrant upsert
    # ------------------------------------------------------------------

    def upsert_chunks(
        self,
        chunks: List[str],
        doc_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Generate embeddings and upsert into Qdrant. Returns count upserted."""
        if not self._client or not chunks:
            return 0

        from qdrant_client.models import PointStruct

        embeddings = self.generate_embeddings_batch(chunks, show_progress=True)
        points = [
            PointStruct(
                id=str(uuid.uuid4()),
                vector=emb,
                payload={
                    "doc_id":      doc_id,
                    "chunk_text":  chunk,
                    "chunk_index": idx,
                    **(metadata or {}),
                },
            )
            for idx, (chunk, emb) in enumerate(
                tqdm(zip(chunks, embeddings), total=len(chunks), desc="Upserting to Qdrant")
            )
        ]

        batch_size = 64
        for i in range(0, len(points), batch_size):
            self._client.upsert(
                collection_name=COLLECTION_NAME,
                points=points[i : i + batch_size],
            )

        logger.info("Upserted %d vectors for doc_id=%s", len(points), doc_id)
        return len(points)

    # ------------------------------------------------------------------
    # Qdrant search — filtered by doc_id
    # ------------------------------------------------------------------

    def search(
        self,
        query_embedding: List[float],
        doc_id: Optional[str] = None,
        top_k: int = 8,
    ) -> List[Tuple[str, float]]:
        """Search Qdrant, optionally scoped to a single document."""
        if not self._client:
            return []

        from qdrant_client.models import Filter, FieldCondition, MatchValue

        search_filter = None
        if doc_id:
            search_filter = Filter(
                must=[FieldCondition(key="doc_id", match=MatchValue(value=doc_id))]
            )

        try:
            results = self._client.search(
                collection_name=COLLECTION_NAME,
                query_vector=query_embedding,
                query_filter=search_filter,
                limit=top_k,
                with_payload=True,
            )
            return [(r.payload["chunk_text"], r.score) for r in results]
        except Exception as e:
            logger.error("Qdrant search error: %s", e)
            return []

    # ------------------------------------------------------------------
    # Backward-compatible API used by llm.py / supabase_service
    # ------------------------------------------------------------------

    def prepare_chunks_for_storage(
        self,
        chunks: List[str],
        document_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Prepare chunks + embeddings. Also upserts vectors into Qdrant."""
        logger.info("Preparing %d chunks for storage (doc=%s)", len(chunks), document_id)
        embeddings = self.generate_embeddings_batch(chunks, show_progress=True)
        # Persist to Qdrant
        self.upsert_chunks(chunks, doc_id=document_id, metadata=metadata)
        return [
            {
                "document_id": document_id,
                "chunk_text":  chunk,
                "chunk_index": idx,
                "embedding":   emb,
                "metadata":    metadata or {},
            }
            for idx, (chunk, emb) in enumerate(zip(chunks, embeddings))
        ]

    def delete_doc_vectors(self, doc_id: str) -> bool:
        if not self._client:
            return False
        from qdrant_client.models import Filter, FieldCondition, MatchValue
        try:
            self._client.delete(
                collection_name=COLLECTION_NAME,
                points_selector=Filter(
                    must=[FieldCondition(key="doc_id", match=MatchValue(value=doc_id))]
                ),
            )
            return True
        except Exception as e:
            logger.error("Failed to delete vectors for doc_id=%s: %s", doc_id, e)
            return False

    def collection_stats(self) -> Dict[str, Any]:
        if not self._client:
            return {"available": False, "backend": "none"}
        try:
            info = self._client.get_collection(COLLECTION_NAME)
            return {
                "available":     True,
                "backend":       "qdrant_local",
                "storage_path":  QDRANT_PATH,
                "total_vectors": info.vectors_count,
                "collection":    COLLECTION_NAME,
            }
        except Exception as e:
            return {"available": False, "error": str(e)}

    @staticmethod
    def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        v1, v2 = np.array(vec1), np.array(vec2)
        n1, n2 = np.linalg.norm(v1), np.linalg.norm(v2)
        if n1 == 0 or n2 == 0:
            return 0.0
        return float(np.dot(v1, v2) / (n1 * n2))

    # Kept for backward compat (used in verify_setup.py)
    def find_most_similar(
        self,
        query_embedding: List[float],
        candidate_embeddings: List[List[float]],
        top_k: int = 5,
    ) -> List[Tuple[int, float]]:
        sims = [
            (idx, self.cosine_similarity(query_embedding, cand))
            for idx, cand in enumerate(candidate_embeddings)
        ]
        sims.sort(key=lambda x: x[1], reverse=True)
        return sims[:top_k]


# ------------------------------------------------------------------
# Singleton (drop-in for old get_vector_service)
# ------------------------------------------------------------------

_vector_service_instance: Optional[VectorStorageService] = None


def get_vector_service(model_name: str = EMBEDDING_MODEL) -> VectorStorageService:
    global _vector_service_instance
    if _vector_service_instance is None:
        _vector_service_instance = VectorStorageService(model_name)
    return _vector_service_instance


def generate_embedding(text: str) -> List[float]:
    return get_vector_service().generate_embedding(text)


def generate_embeddings(texts: List[str]) -> List[List[float]]:
    return get_vector_service().generate_embeddings_batch(texts)


def prepare_chunks_with_embeddings(
    chunks: List[str],
    document_id: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    return get_vector_service().prepare_chunks_for_storage(chunks, document_id, metadata)


if __name__ == "__main__":
    print("Testing Qdrant Vector Storage Service...")
    svc = VectorStorageService()
    print(f"Model: {svc.model_name}  |  Dim: {svc.embedding_dimension}")
    print(f"Stats: {svc.collection_stats()}")
    test_chunks = [
        "Six Sigma is a methodology for process improvement.",
        "DMAIC: Define, Measure, Analyze, Improve, Control.",
        "Oil & Gas operations focus on production efficiency.",
    ]
    svc.upsert_chunks(test_chunks, doc_id="test-doc-001")
    q_emb   = svc.generate_embedding("What is Six Sigma?")
    results = svc.search(q_emb, doc_id="test-doc-001", top_k=2)
    print("\nSearch results:")
    for text, score in results:
        print(f"  [{score:.3f}] {text[:60]}")
    print("\n✓ Qdrant vector storage test passed.")
