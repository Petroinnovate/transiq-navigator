"""
TransIQ Backend v2.0 - Main FastAPI application
Multi-tenant architecture with JWT authentication
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.api.v2 import endpoints as v2_endpoints
from app.api.v2 import auth as auth_endpoints
from app.api.v2 import impact_endpoints
from app.api.v2 import dashboard_endpoints
from app.api.v2 import intelligence_graph_endpoints
from app.api.ddr import endpoints as ddr_endpoints
from app.api.ddr import fleet_endpoints as fleet_endpoints
from app.api.ddr import rig_endpoints as rig_endpoints
from app.api.ddr import audit_endpoints as audit_endpoints
from app.api.ddr import trend_endpoints as trend_endpoints
from domain.transiq.api import analyze as sixsigma_analyze
from app.middleware.auth import APIKeyMiddleware
from services.db import init_db, close_db
from core.logging.logger import setup_logging, get_logger
from core.config.settings import settings

# Setup logging
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    logger.info("🚀 Starting TransIQ Backend v2.0...")
    settings.require_gemini_api_key()
    
    # Initialize database
    try:
        init_db()
        logger.info("✅ Database initialized")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down...")
    close_db()
    logger.info("✅ Database connections closed")


# Create FastAPI app
app = FastAPI(
    title="TransIQ Backend v2",
    description="Production-ready document processing and analytics backend with JWT authentication",
    version="2.0.0",
    lifespan=lifespan
)

# ============================================================================
# Security: CORS Configuration
# ============================================================================
# IMPORTANT: Only allow your frontend domain, never use ["*"] in production

allowed_origins = [settings.FRONTEND_URL]

# Development mode: allow localhost variations
if settings.DEBUG:
    allowed_origins.extend([
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ])
    logger.info(f"🔓 CORS enabled for: {allowed_origins} (DEBUG mode)")
else:
    logger.info(f"🔒 CORS restricted to: {allowed_origins} (PRODUCTION mode)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# ============================================================================
# Security: API Key Authentication
# ============================================================================
# Protects all /api/* endpoints (excludes /docs, /health)
# Requires X-API-Key header in requests

app.add_middleware(APIKeyMiddleware)

# Log security status at startup
valid_keys_count = sum([
    1 for k in [settings.API_KEY, settings.API_KEY_2, settings.API_KEY_3] 
    if k is not None
])

if valid_keys_count > 0:
    logger.info(f"🔐 API Key authentication enabled ({valid_keys_count} valid keys)")
    logger.info(f"⏱️  Rate limit: {settings.RATE_LIMIT_PER_MINUTE} requests/minute per key")
else:
    logger.warning("⚠️  No API keys configured - authentication disabled (INSECURE!)")
    logger.warning("⚠️  Set API_KEY in .env to enable authentication")

# ============================================================================
# Routes
# ============================================================================

# Include API routers
app.include_router(auth_endpoints.router, tags=["Authentication"])  # JWT auth endpoints (no /api prefix)
app.include_router(v2_endpoints.router, prefix="/api/v2", tags=["v2"])
app.include_router(impact_endpoints.router, tags=["Intelligence"])  # Impact analysis endpoints (already has /api/v2 prefix)
app.include_router(dashboard_endpoints.router, tags=["Dashboard"])  # Dashboard visualization endpoints (already has /api/v2 prefix)
app.include_router(intelligence_graph_endpoints.router, tags=["Graph-Intelligence"])  # Phase 5: Intelligence-weighted graph analysis
app.include_router(ddr_endpoints.router, tags=["DDR Intelligence"])  # P1: DDR parsing, SPC, citations
app.include_router(fleet_endpoints.router, tags=["Fleet Analytics"])  # P2: Fleet-wide DDR endpoints
app.include_router(rig_endpoints.router, tags=["Rig Analytics"])  # P2: Per-rig DDR endpoints
app.include_router(audit_endpoints.router, tags=["DDR Audit"])  # P2: Field-level audit trail
app.include_router(trend_endpoints.router, tags=["DDR Trends"])  # P3: Multi-report time-series trends
app.include_router(sixsigma_analyze.router, prefix="/api/v2", tags=["Six Sigma"])  # TransIQ deterministic analysis

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": "TransIQ Backend",
        "version": "2.0.0",
        "status": "operational",
        "security": {
            "authentication": "API Key (X-API-Key header)",
            "rate_limit": f"{settings.RATE_LIMIT_PER_MINUTE} requests/minute",
            "cors": "Restricted" if not settings.DEBUG else "Development mode"
        },
        "endpoints": {
            "v2": {
                "generate": "POST /api/v2/generate",
                "generate_batch": "POST /api/v2/generate-batch",
                "search": "POST /api/v2/search",
                "document": "GET /api/v2/documents/{doc_id}",
                "chunks": "GET /api/v2/documents/{doc_id}/chunks",
                "batch_status": "GET /api/v2/batch/{batch_id}",
                "task_status": "GET /api/v2/task/{task_id}",
                "websocket": "WS /api/v2/ws/{doc_id}",
                "health": "GET /api/v2/health"
            },
            "intelligence": {
                "enrich_facts": "POST /api/v2/intelligence/enrich-facts",
                "analyze_kpi_impact": "POST /api/v2/intelligence/analyze-kpi-impact",
                "dmaic_analysis": "GET /api/v2/intelligence/dmaic/{kpi_id}",
                "entity_relationships": "POST /api/v2/intelligence/entity-relationships",
                "impact_status": "GET /api/v2/intelligence/status"
            },
            "dashboard": {
                "kpi_dashboard": "GET /api/v2/intelligence/dashboard/{kpi_id}",
                "impact_network": "GET /api/v2/intelligence/impact-network/{kpi_id}",
                "dmaic_dashboard": "GET /api/v2/intelligence/dmaic/{kpi_id}",
                "batch_analysis": "POST /api/v2/intelligence/batch-analysis",
                "dashboard_status": "GET /api/v2/intelligence/dashboard-status"
            }
        },
        "documentation": {
            "swagger": "/docs",
            "redoc": "/redoc",
            "openapi": "/openapi.json"
        }
    }

# Health check (no authentication required)
@app.get("/health")
async def health():
    """Health check endpoint - No authentication required"""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "authentication": "enabled" if valid_keys_count > 0 else "disabled"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        limit_max_upload_size=36700160  # 35MB limit
    )

