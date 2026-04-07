from services.cache.cache_service import get_cache_service
from services.vector_store.retrieval.hybrid_retrieval import get_hybrid_retrieval, HybridRetrieval, compress_chunks
from services.vector_store.indexing.vector_storage import get_vector_service
print("cache OK", get_cache_service)
print("hash OK", HybridRetrieval.compute_file_hash(b"test"))
print("compress OK", compress_chunks(["hello", "world"]))
print("vector OK", get_vector_service)
print("ALL IMPORTS OK")
