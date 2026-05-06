"""Quick health check — verifies all backend modules import & initialize."""
import os
import sys

# Ensure Backend root is on sys.path (same as running from Backend/)
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

print("Python:", sys.version)
print()

checks = []

def check(name, fn):
    try:
        result = fn()
        tag = "[OK]"
        msg = result if result else ""
        checks.append((name, True, msg))
        print(f"  {tag} {name} {msg}")
    except Exception as e:
        checks.append((name, False, str(e)))
        print(f"  [FAIL] {name}: {e}")

# Core imports
check("FastAPI app", lambda: (
    __import__("app.main", fromlist=["app"]),
    "imports ok"
)[1])

check("AsyncPipelineOrchestrator", lambda: (
    __import__("pipelines.processing.async_orchestrator", fromlist=["AsyncPipelineOrchestrator"]),
    "imports ok"
)[1])

check("DashboardGenerator", lambda: (
    __import__("pipelines.processing.dashboard", fromlist=["DashboardGenerator"]),
    "imports ok"
)[1])

check("DeductionEngine", lambda: (
    __import__("pipelines.processing.deduction", fromlist=["DeductionEngine"]),
    "imports ok"
)[1])

# Storage
def check_storage():
    from services.storage.local import LocalStorage
    s = LocalStorage()
    return "SQLite OK"
check("LocalStorage", check_storage)

# LLM
def check_llm():
    from services.llm.factory import LLMFactory
    p = LLMFactory.get_provider()
    info = p.get_model_info()
    return f"{info.get('provider', '?')}/{info.get('model', '?')}"
check("LLM Provider", check_llm)

# Embeddings
def check_embed():
    from services.vector_store.embeddings.embedding_model import EmbeddingModel
    em = EmbeddingModel()
    return f"{em.model_name} dim={em.dimension}"
check("Embedding Model", check_embed)

# File reader
check("File Reader", lambda: (
    __import__("services.file_reader", fromlist=["read_file_content"]),
    "imports ok"
)[1])

# Celery
def check_celery():
    from services.workers.processor import celery, CELERY_AVAILABLE
    return f"available={CELERY_AVAILABLE}"
check("Celery", check_celery)

# Routes
def check_routes():
    from app.api.v2.endpoints import router
    routes = [getattr(r, 'path', '') for r in router.routes]
    critical = [
        '/documents/upload',
        '/documents/{doc_id}/dashboard',
        '/documents/{doc_id}/dashboard/stream',
        '/health',
    ]
    missing = [c for c in critical if not any(c in r for r in routes)]
    if missing:
        return f"{len(routes)} routes, MISSING: {missing}"
    return f"{len(routes)} routes, all critical present"
check("V2 API Routes", check_routes)

# Cache
def check_cache():
    from services.storage.local import LocalStorage
    from services.cache.content_cache import ContentCache
    c = ContentCache(LocalStorage())
    return "init ok"
check("Content Cache", check_cache)

# SSE Streaming
def check_sse():
    from app.api.v2.endpoints import stream_dashboard
    import inspect
    assert inspect.iscoroutinefunction(stream_dashboard)
    return "async endpoint ok"
check("SSE Streaming", check_sse)

# Settings
def check_settings():
    from core.config.settings import settings
    return f"concurrency={settings.WORKER_CONCURRENCY}, pool={settings.WORKER_POOL}"
check("Worker Config", check_settings)

print()
passed = sum(1 for _, ok, _ in checks if ok)
failed = sum(1 for _, ok, _ in checks if not ok)
print(f"=== {passed}/{len(checks)} checks passed, {failed} failed ===")
if failed:
    print("ISSUES FOUND - fix before testing")
else:
    print("ALL SYSTEMS GO - ready for real-world test")
