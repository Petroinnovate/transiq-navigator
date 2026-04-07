"""
v2 API endpoints
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Query, WebSocket
from fastapi.responses import JSONResponse
from typing import Optional, List, Tuple
import uuid
import os
import json
from pathlib import Path
from pydantic import BaseModel, Field

from services.workers.tasks import enqueue_document
from services.storage.local import LocalStorage
from services.vector_store.embeddings.embedding_model import EmbeddingModel
from services.vector_store.hybrid.hybrid_search import HybridSearch, ReRanker
from core.config.settings import settings
from core.config.schemas import ProcessingRequest, SearchRequest
from core.logging.logger import get_logger
from core.errors import ProcessingError, SearchError
from app.websocket.handlers import manager

logger = get_logger(__name__)
router = APIRouter()
storage = LocalStorage()

# Ensure upload directory exists
Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)


class AgentRunRequest(BaseModel):
    goal: str = Field(..., min_length=1)
    context: dict = Field(default_factory=dict)


@router.get('/health')
async def health_check():
    """
    Health check endpoint - verifies all local services are operational
    
    Returns status of:
    - API server
    - Redis (task queue)
    - Qdrant (vector DB)
    - Database (SQLite)
    - LLM provider availability
    
    Returns 200 if all critical services OK, 503 if any are down
    """
    import socket
    
    status = {
        "status": "ok",
        "services": {}
    }
    
    # 1. Check Redis
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1.0)
        redis_host = settings.REDIS_URL.split("//")[-1].split(":")[0] if "://" in settings.REDIS_URL else "localhost"
        result = sock.connect_ex((redis_host, 6379))
        sock.close()
        status["services"]["redis"] = "ok" if result == 0 else "down"
    except Exception as e:
        status["services"]["redis"] = f"error: {str(e)}"
    
    # 2. Check Qdrant
    try:
        from services.vector_store.indexing.vector_storage import VectorStorageService
        vs = VectorStorageService()
        # If initialization succeeds, Qdrant is accessible
        status["services"]["qdrant"] = "ok" if vs._client else "down"
        status["services"]["qdrant_mode"] = "docker" if vs._is_docker_mode else "local"
    except Exception as e:
        status["services"]["qdrant"] = f"error: {str(e)}"
    
    # 3. Check Database
    try:
        from services.storage.local import LocalStorage
        db = LocalStorage()
        # Simple query to verify DB is accessible
        db.conn.execute("SELECT 1").fetchone()
        status["services"]["database"] = "ok"
    except Exception as e:
        status["services"]["database"] = f"error: {str(e)}"
    
    # 4. Check LLM Provider
    try:
        from core.config.settings import settings
        llm_providers = []
        if settings.GEMINI_API_KEY:
            llm_providers.append("gemini")
        if settings.OPENAI_API_KEY:
            llm_providers.append("openai")
        if settings.ANTHROPIC_API_KEY:
            llm_providers.append("anthropic")
        
        status["services"]["llm"] = "ok" if llm_providers else "no_api_keys"
        status["services"]["llm_providers"] = llm_providers
    except Exception as e:
        status["services"]["llm"] = f"error: {str(e)}"
    
    # 5. Check Celery Workers (optional, non-blocking)
    try:
        from services.workers.processor import celery, CELERY_AVAILABLE
        if CELERY_AVAILABLE and celery:
            import asyncio
            try:
                inspect_result = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(
                        None, lambda: celery.control.inspect(timeout=2.0).active()
                    ),
                    timeout=3.0,
                )
                status["services"]["celery"] = "ok" if inspect_result else "no_workers"
                status["services"]["worker_count"] = len(inspect_result) if inspect_result else 0
            except (asyncio.TimeoutError, Exception):
                status["services"]["celery"] = "timeout"
        else:
            status["services"]["celery"] = "unavailable"
    except Exception as e:
        status["services"]["celery"] = f"error: {str(e)}"
    
    # Determine overall status
    critical_services = ["redis", "qdrant", "database", "llm"]
    down_services = [k for k in critical_services if status["services"].get(k) not in ["ok", "no_api_keys"]]
    
    if down_services:
        status["status"] = "degraded"
        status["down_services"] = down_services
        return JSONResponse(status_code=503, content=status)
    
    return status


def _enrich_kpis_with_intelligence(kpis: list) -> Tuple[list, dict]:
    """
    Run the KPI intelligence engine: score, rank, assign visibility and widget slots.
    Returns (enriched_kpis, widgets_dict).
    Falls back gracefully if kpi_engine is unavailable.
    """
    try:
        from features import process_kpis, map_kpis_to_widgets
        enriched = process_kpis(kpis)
        widgets = map_kpis_to_widgets(enriched)
        return enriched, widgets
    except Exception as exc:
        logger.warning(f"KPI intelligence engine unavailable: {exc}")
        return kpis, {}


def _build_predictive_block(kpis: list) -> dict:
    """
    Run the predictive + risk engine on every KPI that has a history array.
    Also generates pre-built what-if scenarios from PRESET_SCENARIOS.
    Falls back gracefully.
    """
    try:
        from features import forecast_kpi, enrich_kpi_with_predictions, compare_scenarios, PRESET_SCENARIOS

        forecasts = []
        enriched_for_scenarios = []

        for kpi in kpis:
            fc = forecast_kpi(kpi)
            if fc:
                enriched = enrich_kpi_with_predictions(kpi, fc)
                name = kpi.get("name") or kpi.get("title") or "KPI"
                forecasts.append({
                    "metric":         name,
                    "unit":           kpi.get("unit", ""),
                    "currentValue":   kpi.get("value"),
                    "forecastValue":  round(fc["forecast"][-1], 2) if fc.get("forecast") else None,
                    "trend":          fc.get("trend", "stable"),
                    "confidence":     min(1.0, max(0.0, 1.0 - (fc.get("modelScores", {}).get("linear", 20) / 100))),
                    "forecast":       [round(v, 2) for v in (fc.get("forecast") or [])],
                    "models":         fc.get("models", {}),
                    "riskLevel":      enriched.get("riskForecast", {}).get("riskLevel", "low"),
                    "breachPredicted": enriched.get("riskForecast", {}).get("breachPredicted", False),
                    "timeToBreach":   enriched.get("riskForecast", {}).get("timeToBreach"),
                    "financialRisk":  enriched.get("riskForecast", {}).get("financialRisk"),
                    "decision":       enriched.get("futureDecision", ""),
                    "slope":          fc.get("slope", 0),
                })
            enriched_for_scenarios.append(kpi)

        # What-if scenarios
        whatif_results = compare_scenarios(enriched_for_scenarios, PRESET_SCENARIOS)

        return {
            "forecast":         forecasts,
            "whatIfScenarios":  whatif_results,
            "forecastSteps":    5,
            "modelsUsed":       ["linear", "arima", "prophet", "xgboost", "ensemble"],
        }
    except Exception as exc:
        logger.warning(f"Predictive engine unavailable: {exc}")
        return {}


def _transform_to_dashboard_response(doc_id: str, doc: dict, dashboard_data: dict) -> dict:
    """Transform backend dashboard data to match frontend DashboardResponse schema"""
    from datetime import datetime
    
    # Extract metadata
    metadata = doc.get('metadata', {})
    file_name = metadata.get('file_name', 'Unknown')
    created_at = doc.get('created_at', datetime.now().isoformat())
    
    # Build meta info — prefer values from the pipeline result
    pipeline_meta = dashboard_data.get("meta", {})
    meta = {
        "reportId": doc_id,
        "ingestedAt": created_at,
        "sourceType": pipeline_meta.get("sourceType") or _detect_source_type(file_name),
        "confidenceOverall": pipeline_meta.get("confidenceOverall", 0.85),
        "decisionReadinessScore": pipeline_meta.get("decisionReadinessScore", 0.75),
        "pipelineVersion": pipeline_meta.get("pipelineVersion", "1.0"),
    }
    
    # Build auto-classification — prefer pipeline result
    auto_classification = dashboard_data.get("autoClassification") or {
        "reportType": _infer_report_type(dashboard_data),
        "assetScope": "Enterprise",
        "timeHorizon": "Monthly",
        "decisionLevel": "Management",
        "confidence": 0.80,
    }
    
    # Extract or build Six Sigma structure
    six_sigma_data = dashboard_data.get('sixSigma', {})

    # If the deterministic Six Sigma engine produced structured output, pass it through
    if six_sigma_data.get("methodology") == "DMAIC" and "ctq" in six_sigma_data:
        six_sigma = six_sigma_data  # structured engine output — no transform needed
    else:
        # Legacy LLM-generated sixSigma — apply transform
        six_sigma = {
            "sigmaLevel": six_sigma_data.get('sigmaLevel', '3.0σ'),
            "defectRate": six_sigma_data.get('defectRate', 'Not calculated'),
            "processCapability": six_sigma_data.get('processCapability', 'Medium'),
            "statisticalValidity": six_sigma_data.get('statisticalValidity', True),
            "dmaic": _transform_dmaic(six_sigma_data.get('dmaic', {}))
        }
    
    # Transform KPIs — apply deterministic financial scoring before sending to frontend
    raw_kpis = dashboard_data.get('kpis', [])
    try:
        from pipelines.inference.financial_engine import compute_kpi_financial_scores
        from pipelines.inference.validation import validate_kpis
        raw_kpis = validate_kpis(raw_kpis)
        raw_kpis = compute_kpi_financial_scores(raw_kpis)
    except Exception as _ie:
        logger.warning("Intelligence enrichment skipped: %s", _ie)

    kpis = _transform_kpis(raw_kpis)
    # Run AI scoring + widget mapping
    kpis, kpi_widgets = _enrich_kpis_with_intelligence(kpis)
    # Run predictive + risk + what-if engine
    predictive = _build_predictive_block(kpis)
    
    # Transform charts — use pipeline charts if present (non-empty), else transform from data
    pipeline_charts = dashboard_data.get("charts", [])
    charts = _transform_charts(pipeline_charts) if pipeline_charts else []
    
    # Transform optimization suggestions (now KPI-anchored from pipeline)
    optimizations = _transform_optimizations(dashboard_data.get('optimizationSuggestions', []))
    
    # Build insights
    insights_data = dashboard_data.get('insights', {})
    insights = {
        "alerts": _transform_alerts(insights_data.get('alerts', [])),
        "recommendations": _transform_recommendations(insights_data.get('recommendations', [])),
        "summary": insights_data.get('summary', 'Analysis complete'),
        "trends": insights_data.get('trends', []),
    }

    # ── Intelligence extensions (ESG, Drilling, Portfolio) ────────────────────
    intelligence_data = dashboard_data.get("intelligence", {})
    # Build ESG and drilling views from raw KPIs if not already present
    if not intelligence_data:
        try:
            from pipelines.inference.esg_engine import build_esg_view
            from pipelines.inference.drilling_engine import build_drilling_view
            from pipelines.inference.financial_engine import compute_portfolio_summary
            intelligence_data = {
                "esg": build_esg_view(raw_kpis),
                "drilling": build_drilling_view(raw_kpis),
                "portfolio_summary": compute_portfolio_summary(raw_kpis),
            }
        except Exception as _intel_err:
            logger.warning("Intelligence extensions skipped: %s", _intel_err)
            intelligence_data = {}

    # ── Executive views from pipeline ─────────────────────────────────────────
    ceo_view = dashboard_data.get("ceo_view", {})
    manager_view = dashboard_data.get("manager_view", {})
    boardroom_mode = dashboard_data.get("boardroom_mode", {})
    engineer_view = dashboard_data.get("engineer_view", {})
    
    # Build explainability
    explainability = dashboard_data.get("explainability") or {
        "reasoning": "TransIQ multi-stage AI pipeline (Gemini 2.0/2.5 Flash)",
        "dataSourcesUsed": [file_name],
        "assumptions": ["Data completeness verified", "Statistical methods applied"],
        "limitations": ["Limited to provided data scope"],
        "auditTrail": [
            {
                "timestamp": created_at,
                "action": "Document processed",
                "details": f"Analyzed {file_name}"
            }
        ]
    }
    
    return {
        "meta": meta,
        "autoClassification": auto_classification,
        "sixSigma": six_sigma,
        "kpis": kpis,
        "widgets": kpi_widgets,
        "predictive": predictive,
        "charts": charts,
        "optimizationSuggestions": optimizations,
        "insights": insights,
        "explainability": explainability,
        # New fields from the intelligence layer
        "intelligence": intelligence_data,
        "ceo_view": ceo_view,
        "manager_view": manager_view,
        "boardroom_mode": boardroom_mode,
        "engineer_view": engineer_view,
        "findings": dashboard_data.get("findings", []),
        "risks": dashboard_data.get("risks", []),
    }


def _detect_source_type(file_name: str) -> str:
    """Detect source type from filename"""
    ext = file_name.lower().split('.')[-1] if '.' in file_name else ''
    if ext in ['xlsx', 'xls']: return 'Excel'
    if ext == 'pdf': return 'PDF'
    if ext == 'csv': return 'CSV'
    return 'Unknown'


def _infer_report_type(dashboard_data: dict) -> list:
    """Infer report type from dashboard content"""
    types = []
    title = dashboard_data.get('title', '').lower()
    if 'operation' in title or 'production' in title:
        types.append('Operations')
    if 'quality' in title or 'sigma' in title:
        types.append('Quality')
    if 'financial' in title or 'cost' in title:
        types.append('Financial')
    return types if types else ['General']


def _transform_dmaic(dmaic_data: dict) -> dict:
    """Transform DMAIC structure to match frontend schema"""
    if not dmaic_data:
        return {
            "define": {"problemStatement": "", "goal": "", "scope": "", "stakeholders": [], "ctqCharacteristics": []},
            "measure": {"dataCollectionPlan": "", "measurementSystem": "", "baselineMetrics": [], "dataQuality": {"completeness": 0, "accuracy": 0, "reliability": "Unknown"}},
            "analyze": {"rootCauseAnalysis": [], "statisticalTests": [], "processMap": {"steps": [], "bottlenecks": []}, "variationSources": []},
            "improve": {"solutions": [], "pilotResults": [], "implementationPlan": {"phases": [], "resources": [], "timeline": "", "risks": []}},
            "control": {"controlPlan": {"metrics": [], "responsibilities": [], "frequency": ""}, "monitoring": {"tools": [], "frequency": "", "dashboards": []}, "documentation": {"procedures": [], "training": [], "auditTrail": False}, "sustainability": {"reviewSchedule": "", "continuousImprovement": [], "ownership": ""}}
        }
    
    return {
        "define": {
            "problemStatement": dmaic_data.get('define', ''),
            "goal": "Improve process performance",
            "scope": "Current analysis scope",
            "stakeholders": [],
            "ctqCharacteristics": []
        },
        "measure": {
            "dataCollectionPlan": dmaic_data.get('measure', ''),
            "measurementSystem": "Statistical analysis",
            "baselineMetrics": [],
            "dataQuality": {"completeness": 0.9, "accuracy": 0.85, "reliability": "High"}
        },
        "analyze": {
            "rootCauseAnalysis": [],
            "statisticalTests": [],
            "processMap": {"steps": [], "bottlenecks": []},
            "variationSources": []
        },
        "improve": {
            "solutions": [],
            "pilotResults": [],
            "implementationPlan": {"phases": [], "resources": [], "timeline": "", "risks": []}
        },
        "control": {
            "controlPlan": {"metrics": [], "responsibilities": [], "frequency": ""},
            "monitoring": {"tools": [], "frequency": "", "dashboards": []},
            "documentation": {"procedures": [], "training": [], "auditTrail": True},
            "sustainability": {"reviewSchedule": "", "continuousImprovement": [], "ownership": ""}
        }
    }


def _transform_kpis(kpis_data: list) -> list:
    """Transform KPIs to match frontend schema, preserving AI scoring fields."""
    transformed = []
    for kpi in kpis_data:
        transformed.append({
            "name": kpi.get('title', 'KPI'),
            "value": kpi.get('value', 0),
            "unit": kpi.get('unit', ''),
            "target": kpi.get('target'),
            "trend": _map_change_type(kpi.get('changeType') or kpi.get('trend')),
            "confidence": kpi.get('confidence', 0.85),
            "linkedCTQ": None,
            "context": kpi.get('change', ''),
            # Pass through raw fields needed by kpi_engine
            "id": kpi.get('id', ''),
            "title": kpi.get('title', 'KPI'),
            "changeType": kpi.get('changeType', 'neutral'),
            "category": kpi.get('category', ''),
            "status": kpi.get('status', ''),
            "financialImpactScore": kpi.get('financialImpactScore'),
            "riskScore": kpi.get('riskScore'),
            # Pre-computed AI fields (populated by kpi_engine after transform)
            "priorityScore": kpi.get('priorityScore'),
            "visibility": kpi.get('visibility'),
            "selectionReason": kpi.get('selectionReason'),
        })
    return transformed


def _map_change_type(change_type: str) -> str:
    """Map change type to trend"""
    if not change_type:
        return "stable"
    if change_type == "positive":
        return "up"
    if change_type == "negative":
        return "down"
    return "stable"


def _transform_charts(charts_data: list) -> list:
    """Transform charts to match frontend schema"""
    transformed = []
    for chart in charts_data:
        transformed.append({
            "chartId": chart.get('id', str(uuid.uuid4())),
            "title": chart.get('title', 'Chart'),
            "type": _map_chart_type(chart.get('type', 'BarChart')),
            "data": chart.get('data', []),
            "xAxis": chart.get('xAxis'),
            "yAxis": chart.get('yAxis'),
            "annotations": [],
            "compareMode": False
        })
    return transformed


def _map_chart_type(chart_type: str) -> str:
    """Map backend chart types to frontend types"""
    mapping = {
        'BarChart': 'bar',
        'LineChart': 'line',
        'AreaChart': 'area',
        'PieChart': 'pie',
        'ScatterChart': 'scatter',
        'SankeyChart': 'sankey',
        'HeatmapChart': 'heatmap',
        'RadarChart': 'radar',
        'RadialBarChart': 'radialbar',
        'HistogramChart': 'histogram',
        'BoxPlotChart': 'boxplot',
        'FunnelChart': 'funnel'
    }
    return mapping.get(chart_type, 'bar')


def _transform_optimizations(optimizations_data: list) -> list:
    """Transform optimization suggestions to match frontend schema"""
    transformed = []
    for opt in optimizations_data:
        transformed.append({
            "title": opt.get('title', 'Optimization'),
            "category": opt.get('category', 'general'),
            "description": opt.get('description', ''),
            "impact": opt.get('impact', 'medium'),
            "roi": opt.get('savings', {}).get('value'),
            "paybackPeriod": opt.get('savings', {}).get('timeframe'),
            "riskIfIgnored": opt.get('impact', 'Medium').capitalize(),
            "priority": opt.get('priority', 'Medium').capitalize(),
            "approvalStatus": "Pending",
            "estimatedCost": None,
            "timeline": opt.get('savings', {}).get('timeframe')
        })
    return transformed


def _transform_alerts(alerts_data: list) -> list:
    """Transform alerts to match frontend schema"""
    from datetime import datetime
    transformed = []
    for alert in alerts_data:
        transformed.append({
            "severity": alert.get('severity', 'Medium').capitalize(),
            "message": alert.get('message', ''),
            "timestamp": alert.get('timestamp', datetime.now().isoformat()),
            "category": alert.get('type', 'general'),
            "actionRequired": alert.get('action')
        })
    return transformed


def _transform_recommendations(recommendations_data: list) -> list:
    """Transform recommendations to match frontend schema"""
    transformed = []
    for rec in recommendations_data:
        transformed.append({
            "title": rec if isinstance(rec, str) else rec.get('title', 'Recommendation'),
            "description": rec if isinstance(rec, str) else rec.get('description', ''),
            "priority": "Medium",
            "estimatedImpact": "Moderate improvement expected",
            "confidence": 0.75
        })
    return transformed


def _get_fallback_dashboard_response(doc_id: str, doc: dict) -> dict:
    """Get fallback dashboard response when data is not available"""
    from datetime import datetime
    
    metadata = doc.get('metadata', {})
    file_name = metadata.get('file_name', 'Unknown')
    created_at = doc.get('created_at', datetime.now().isoformat())
    
    return {
        "meta": {
            "reportId": doc_id,
            "ingestedAt": created_at,
            "sourceType": _detect_source_type(file_name),
            "confidenceOverall": 0.0,
            "decisionReadinessScore": 0.0
        },
        "autoClassification": {
            "reportType": ["Processing"],
            "assetScope": "Unknown",
            "timeHorizon": "Unknown",
            "decisionLevel": "Unknown",
            "confidence": 0.0
        },
        "sixSigma": {
            "sigmaLevel": "N/A",
            "defectRate": "Processing...",
            "processCapability": "Low",
            "statisticalValidity": False,
            "dmaic": {
                "define": {"problemStatement": "Dashboard data not yet generated", "goal": "", "scope": "", "stakeholders": [], "ctqCharacteristics": []},
                "measure": {"dataCollectionPlan": "Please wait for processing to complete", "measurementSystem": "", "baselineMetrics": [], "dataQuality": {"completeness": 0, "accuracy": 0, "reliability": "Unknown"}},
                "analyze": {"rootCauseAnalysis": [], "statisticalTests": [], "processMap": {"steps": [], "bottlenecks": []}, "variationSources": []},
                "improve": {"solutions": [], "pilotResults": [], "implementationPlan": {"phases": [], "resources": [], "timeline": "", "risks": []}},
                "control": {"controlPlan": {"metrics": [], "responsibilities": [], "frequency": ""}, "monitoring": {"tools": [], "frequency": "", "dashboards": []}, "documentation": {"procedures": [], "training": [], "auditTrail": False}, "sustainability": {"reviewSchedule": "", "continuousImprovement": [], "ownership": ""}}
            }
        },
        "kpis": [],
        "charts": [],
        "optimizationSuggestions": [],
        "insights": {
            "alerts": [],
            "recommendations": [],
            "summary": "Document processing in progress"
        },
        "explainability": {
            "reasoning": "Processing document...",
            "dataSourcesUsed": [file_name],
            "assumptions": [],
            "limitations": ["Processing not complete"],
            "auditTrail": []
        }
    }


@router.post('/generate')
async def generate(
    file: UploadFile = File(...),
    provider: Optional[str] = Query(None, description="LLM provider override"),
    enable_deduction: bool = Query(False, description="Enable deduction engine"),
    enable_patterns: bool = Query(False, description="Enable pattern recognition")
):
    """
    Upload and process a document
    
    Args:
        file: Uploaded file
        provider: LLM provider name (optional)
        enable_deduction: Enable deduction engine
        enable_patterns: Enable pattern recognition
        
    Returns:
        Document ID and task ID
    """
    try:
        # Generate document ID
        doc_id = str(uuid.uuid4())
        
        # Save uploaded file
        file_extension = os.path.splitext(file.filename)[1] if file.filename else '.txt'
        file_path = os.path.join(settings.UPLOAD_DIR, f"{doc_id}{file_extension}")
        
        content = await file.read()
        
        # Ensure upload directory exists (handle both relative and absolute paths)
        upload_dir = os.path.dirname(file_path) or settings.UPLOAD_DIR
        os.makedirs(upload_dir, exist_ok=True)
        
        # Save uploaded file
        with open(file_path, 'wb') as f:
            f.write(content)
        
        # Use the saved file path for processing
        # The processor will handle reading the file based on its type
        text_path = file_path
        
        # Save document metadata
        storage.save_document(doc_id, {
            "file_name": file.filename,
            "file_size": len(content),
            "file_type": file_extension,
            "status": "processing"
        })
        
        # Enqueue for processing
        task_id = enqueue_document(
            doc_path=text_path,
            doc_id=doc_id,
            provider_name=provider,
            enable_deduction=enable_deduction,
            enable_patterns=enable_patterns
        )
        
        return {
            "doc_id": doc_id,
            "task_id": task_id,
            "status": "processing",
            "message": "Document uploaded and queued for processing"
        }
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"Document upload error: {e}")
        logger.error(f"Traceback: {error_trace}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to process document: {str(e)}"
        )


@router.post('/generate-batch')
async def generate_batch(
    files: List[UploadFile] = File(...),
    provider: Optional[str] = Query(None, description="LLM provider override"),
    enable_deduction: bool = Query(False, description="Enable deduction engine"),
    enable_patterns: bool = Query(False, description="Enable pattern recognition")
):
    """
    Upload and process multiple documents in parallel
    
    This endpoint accepts multiple files and processes them independently in the background.
    Each file gets its own doc_id and task_id. All files are grouped under a batch_id
    for progress tracking.
    
    Args:
        files: List of uploaded files
        provider: LLM provider name (optional)
        enable_deduction: Enable deduction engine
        enable_patterns: Enable pattern recognition
        
    Returns:
        Batch ID, list of document IDs and task IDs, total count
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    
    try:
        # Generate batch ID
        batch_id = str(uuid.uuid4())
        
        # Save batch metadata
        storage.save_batch(
            batch_id=batch_id,
            total_files=len(files),
            metadata={
                "provider": provider,
                "enable_deduction": enable_deduction,
                "enable_patterns": enable_patterns
            }
        )
        
        logger.info(f"Created batch {batch_id} with {len(files)} files")
        
        documents = []
        
        # Process each file independently
        for file in files:
            try:
                # Generate document ID
                doc_id = str(uuid.uuid4())
                
                # Save uploaded file
                file_extension = os.path.splitext(file.filename)[1] if file.filename else '.txt'
                file_path = os.path.join(settings.UPLOAD_DIR, f"{doc_id}{file_extension}")
                
                content = await file.read()
                
                # Ensure upload directory exists
                upload_dir = os.path.dirname(file_path) or settings.UPLOAD_DIR
                os.makedirs(upload_dir, exist_ok=True)
                
                # Save uploaded file
                with open(file_path, 'wb') as f:
                    f.write(content)
                
                # Save document metadata
                storage.save_document(doc_id, {
                    "file_name": file.filename,
                    "file_size": len(content),
                    "file_type": file_extension,
                    "status": "processing",
                    "batch_id": batch_id
                })
                
                # Enqueue for background processing (non-blocking)
                task_id = enqueue_document(
                    doc_path=file_path,
                    doc_id=doc_id,
                    provider_name=provider,
                    enable_deduction=enable_deduction,
                    enable_patterns=enable_patterns
                )
                
                # Link document to batch
                storage.save_batch_document(
                    batch_id=batch_id,
                    doc_id=doc_id,
                    task_id=task_id,
                    file_name=file.filename
                )
                
                documents.append({
                    "doc_id": doc_id,
                    "task_id": task_id,
                    "file_name": file.filename,
                    "status": "queued"
                })
                
                logger.info(f"Queued file {file.filename} as doc_id={doc_id}, task_id={task_id}")
                
            except Exception as file_error:
                # Isolate file-level errors - don't fail the entire batch
                logger.error(f"Failed to queue file {file.filename}: {file_error}")
                documents.append({
                    "doc_id": None,
                    "task_id": None,
                    "file_name": file.filename,
                    "status": "failed",
                    "error": str(file_error)
                })
        
        return {
            "batch_id": batch_id,
            "documents": documents,
            "total": len(files),
            "queued": len([d for d in documents if d["status"] == "queued"]),
            "failed": len([d for d in documents if d["status"] == "failed"]),
            "message": f"Batch created with {len(documents)} files"
        }
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"Batch upload error: {e}")
        logger.error(f"Traceback: {error_trace}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process batch: {str(e)}"
        )


@router.get('/batch/{batch_id}')
async def get_batch_status(batch_id: str):
    """
    Get batch processing status
    
    Returns progress, completed/failed counts, and per-document status for all files in the batch.
    Frontend can poll this endpoint to show live progress.
    
    Args:
        batch_id: Batch ID from /generate-batch response
        
    Returns:
        Batch status with per-document details
    """
    batch = storage.get_batch(batch_id)
    
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    return {
        "batch_id": batch_id,
        "status": batch["status"],
        "total_files": batch["total_files"],
        "completed_files": batch["completed_files"],
        "failed_files": batch["failed_files"],
        "progress": batch["progress"],
        "created_at": batch["created_at"],
        "updated_at": batch["updated_at"],
        "documents": [
            {
                "doc_id": doc["doc_id"],
                "task_id": doc["task_id"],
                "file_name": doc["file_name"],
                "status": doc["status"],
                "error": doc.get("error")
            }
            for doc in batch["documents"]
        ]
    }


@router.get('/task/{task_id}')
async def get_task_status(task_id: str):
    """
    Get Celery task status and progress
    
    Designed for frontend polling to show real-time progress of document processing.
    Returns detailed task info including current stage, progress %, and result.
    
    Args:
        task_id: Celery task ID from /generate or /generate-batch response
        
    Returns:
        Task status with progress details
        
    Example Response:
        {
            "task_id": "abc123...",
            "doc_id": "doc_xyz",
            "status": "processing",  // queued | processing | completed | failed
            "stage": "embedding",     // current processing stage
            "progress": 40,           // 0-100
            "error": null,
            "result": null,
            "created_at": "2026-03-24T...",
            "updated_at": "2026-03-24T..."
        }
    """
    task = storage.get_task_status(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return {
        "task_id": task["task_id"],
        "doc_id": task["doc_id"],
        "status": task["status"],
        "stage": task.get("stage"),
        "progress": task.get("progress", 0),
        "error": task.get("error"),
        "result": task.get("result"),
        "created_at": task["created_at"],
        "updated_at": task["updated_at"]
    }


@router.get('/documents/{doc_id}')
async def get_document(doc_id: str):
    """Get document information"""
    doc = storage.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    chunks = storage.get_chunks(doc_id)
    edges = storage.get_edges(doc_id)
    
    return {
        "document": doc,
        "chunks_count": len(chunks),
        "edges_count": len(edges)
    }


@router.get('/documents/{doc_id}/chunks')
async def get_chunks(doc_id: str):
    """Get document chunks"""
    chunks = storage.get_chunks(doc_id)
    if not chunks:
        raise HTTPException(status_code=404, detail="Document or chunks not found")
    
    return {"chunks": chunks, "count": len(chunks)}


@router.post('/search')
async def search(request: SearchRequest):
    """
    Search across documents
    
    Args:
        request: Search request with query and parameters
        
    Returns:
        Search results
    """
    try:
        # Get all chunks from storage
        all_docs = storage.list_documents(limit=1000)
        all_texts = []
        all_embeddings = []
        
        emb_model = EmbeddingModel()
        
        for doc in all_docs:
            chunks = storage.get_chunks(doc['id'])
            for chunk in chunks:
                all_texts.append(chunk['chunk_text'])
        
        if not all_texts:
            return {"results": [], "count": 0, "message": "No documents indexed yet"}
        
        # Generate query embedding
        query_embedding = emb_model.embed(request.query)[0]
        
        # Generate embeddings for all texts if needed
        # In production, these should be pre-computed and stored
        all_embeddings = emb_model.embed(all_texts)
        
        # Perform hybrid search
        hybrid_search = HybridSearch(all_texts, all_embeddings)
        results = hybrid_search.query(
            query=request.query,
            query_embedding=query_embedding,
            topk=request.top_k
        )
        
        # Re-rank if requested
        if request.use_hybrid:
            reranker = ReRanker()
            results = reranker.rerank(request.query, results, topk=request.top_k)
        
        return {
            "query": request.query,
            "results": results,
            "count": len(results)
        }
        
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.post('/agent/run')
async def run_agent(request: AgentRunRequest):
    """Run the lightweight GodMode-style agent against a high-level goal."""
    try:
        from agents.orchestrators.godmode_agent import GodModeAgent

        agent = GodModeAgent()
        result = agent.run(goal=request.goal, context=request.context)
        return result
    except Exception as e:
        logger.error(f"Agent run error: {e}")
        raise HTTPException(status_code=500, detail=f"Agent run failed: {str(e)}")


@router.websocket('/ws/{task_id}')
async def websocket_progress(websocket: WebSocket, task_id: str):
    """WebSocket endpoint for task progress updates"""
    await manager.connect(websocket, task_id)
    
    try:
        # Send initial connection message
        await websocket.send_json({
            "type": "connected",
            "task_id": task_id,
            "message": "Connected to progress updates"
        })
        
        # Keep connection alive
        while True:
            data = await websocket.receive_text()
            # Echo back or handle client messages
            await websocket.send_json({
                "type": "ack",
                "message": f"Received: {data}"
            })
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        manager.disconnect(websocket, task_id)


@router.get('/documents/{doc_id}/dashboard')
async def get_dashboard(doc_id: str):
    """Get dashboard data for a document"""
    doc = storage.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    chunks = storage.get_chunks(doc_id)
    edges = storage.get_edges(doc_id)
    
    # Get dashboard data from document
    dashboard_data = doc.get("dashboard_data")
    
    if dashboard_data:
        # Transform to match frontend DashboardResponse schema
        transformed_data = _transform_to_dashboard_response(doc_id, doc, dashboard_data)
        return transformed_data
    else:
        # Return basic dashboard structure if no data available
        return _get_fallback_dashboard_response(doc_id, doc)


@router.get('/dashboard/latest')
async def get_latest_dashboard():
    """Get the most recently processed dashboard"""
    try:
        # Get all documents sorted by created_at descending
        all_docs = storage.list_documents(limit=1000)
        
        # Filter for completed documents with dashboard data
        completed_docs = [
            doc for doc in all_docs 
            if doc.get('status') == 'completed' and doc.get('dashboard_data')
        ]
        
        if not completed_docs:
            raise HTTPException(
                status_code=404, 
                detail="No completed dashboards found"
            )
        
        # Get the most recent one
        latest_doc = completed_docs[0]
        doc_id = latest_doc['id']
        
        # Transform and return
        dashboard_data = latest_doc.get('dashboard_data', {})
        return _transform_to_dashboard_response(doc_id, latest_doc, dashboard_data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get latest dashboard error: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to get latest dashboard: {str(e)}"
        )


@router.get('/dashboard/{doc_id}')
async def get_dashboard_by_id(doc_id: str):
    """Get dashboard data by document ID (alias for /documents/{doc_id}/dashboard)"""
    return await get_dashboard(doc_id)


@router.get('/dashboard/status/{task_id}')
async def get_dashboard_status(task_id: str):
    """Get processing status for a task"""
    try:
        # Try to get task status from storage
        # Note: This requires task_id to doc_id mapping
        # For now, we'll check if task_id matches a doc_id
        doc = storage.get_document(task_id)
        
        if doc:
            return {
                "task_id": task_id,
                "status": doc.get('status', 'unknown'),
                "progress": 100 if doc.get('status') == 'completed' else 50,
                "message": f"Document {doc.get('status', 'processing')}",
                "doc_id": task_id,
                "has_dashboard": bool(doc.get('dashboard_data'))
            }
        else:
            # Task might still be processing
            return {
                "task_id": task_id,
                "status": "processing",
                "progress": 25,
                "message": "Document processing in progress"
            }
    except Exception as e:
        logger.error(f"Get status error: {e}")
        return {
            "task_id": task_id,
            "status": "unknown",
            "progress": 0,
            "message": str(e)
        }


@router.get('/dashboard/{doc_id}/export/pdf')
async def export_dashboard_pdf(doc_id: str):
    """Export dashboard as a formatted PDF report"""
    try:
        from fastapi.responses import Response
        from services.export_service import generate_dashboard_pdf

        doc = storage.get_document(doc_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        dashboard_data = doc.get('dashboard_data')
        if not dashboard_data:
            raise HTTPException(
                status_code=404,
                detail="Dashboard data not available for this document"
            )

        # Parse dashboard_data if it's a JSON string
        if isinstance(dashboard_data, str):
            dashboard_data = json.loads(dashboard_data)

        pdf_bytes = generate_dashboard_pdf(doc_id, dashboard_data)

        return Response(
            content=pdf_bytes,
            media_type='application/pdf',
            headers={
                'Content-Disposition': f'attachment; filename="dashboard_{doc_id[:8]}.pdf"'
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"PDF export error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to export PDF: {str(e)}"
        )


@router.get('/dashboard/{doc_id}/export/excel')
async def export_dashboard_excel(doc_id: str):
    """Export dashboard as a multi-sheet Excel workbook"""
    try:
        from fastapi.responses import Response
        from services.export_service import generate_dashboard_excel

        doc = storage.get_document(doc_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        dashboard_data = doc.get('dashboard_data')
        if not dashboard_data:
            raise HTTPException(
                status_code=404,
                detail="Dashboard data not available for this document"
            )

        # Parse dashboard_data if it's a JSON string
        if isinstance(dashboard_data, str):
            dashboard_data = json.loads(dashboard_data)

        excel_bytes = generate_dashboard_excel(doc_id, dashboard_data)

        return Response(
            content=excel_bytes,
            media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            headers={
                'Content-Disposition': f'attachment; filename="dashboard_{doc_id[:8]}.xlsx"'
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Excel export error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to export Excel: {str(e)}"
        )


# NOTE: Primary /health endpoint is defined at line 36 with full service checks.
# Removed duplicate /health here that was unreachable dead code.

