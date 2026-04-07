"""
POST /api/v2/six-sigma/analyze — deterministic Six Sigma analysis endpoint.

Locked API contract: every response returns the same top-level shape:
  { analysis_type, inputs, metrics, chart_data, warnings, recommendations }

All math is handled by transiq/ modules (zero LLM).
"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy.orm import Session

from transiq import process_capability, spc_charts, statistics

logger = logging.getLogger("transiq.api.analyze")

router = APIRouter()


# ---------------------------------------------------------------------------
# Request model
# ---------------------------------------------------------------------------

class AnalyzeRequest(BaseModel):
    """Input payload for Six Sigma analysis."""

    data: List[float] = Field(
        ..., min_length=1, description="Process measurements"
    )
    usl: float = Field(10.0, description="Upper specification limit")
    lsl: float = Field(0.0, description="Lower specification limit")
    sigma: Optional[float] = Field(
        None, gt=0, description="Known process std dev (optional)"
    )
    ppm: Optional[float] = Field(
        None, gt=0, description="Defects per million opportunities (optional)"
    )

    @field_validator("data")
    @classmethod
    def data_must_be_finite(cls, v: List[float]) -> List[float]:
        import math

        for i, x in enumerate(v):
            if math.isnan(x) or math.isinf(x):
                raise ValueError(f"data[{i}] must be a finite number")
        return v

    @model_validator(mode="after")
    def usl_gt_lsl(self) -> "AnalyzeRequest":
        if self.usl <= self.lsl:
            raise ValueError("usl must be greater than lsl")
        return self


# ---------------------------------------------------------------------------
# Response models — locked contract
# ---------------------------------------------------------------------------

class MetricsBlock(BaseModel):
    n: int
    mean: float
    std_dev: float
    cp: float
    cpk: float
    cpu: float
    cpl: float
    sigma_short_term: float
    sigma_long_term: float
    dpmo: float
    yield_pct: float
    fraction_defective: float
    sigma_level: Optional[float] = None


class ChartDataBlock(BaseModel):
    """IMR chart control limits + raw values for plotting."""

    values: List[float]
    cl: float
    ucl: float
    lcl: float
    mr_cl: float
    mr_ucl: float
    usl: float
    lsl: float


class RuleViolation(BaseModel):
    rule: str
    description: str
    indices: List[int]
    severity: str


class AnalyzeResponse(BaseModel):
    """Stable response shape for every analysis call."""

    analysis_type: str = "process_capability"
    inputs: Dict[str, Any]
    metrics: MetricsBlock
    chart_data: ChartDataBlock
    warnings: List[RuleViolation] = []
    recommendations: List[str] = []


# ---------------------------------------------------------------------------
# Pure computation (no HTTP, no side effects)
# ---------------------------------------------------------------------------

def _compute(req: AnalyzeRequest) -> dict:
    """Run all transiq computations; return a plain dict."""

    data = req.data
    n = len(data)
    mu = statistics.mean(data)

    if req.sigma is not None:
        s = req.sigma
    elif n > 1:
        s = statistics.std_dev(data, ddof=1)
    else:
        s = 0.0

    # --- metrics ---
    if s > 0:
        cp_val = process_capability.cp(req.usl, req.lsl, s)
        cpk_val = process_capability.cpk(req.usl, req.lsl, mu, s)
        cpu_val = process_capability.cpu(req.usl, mu, s)
        cpl_val = process_capability.cpl(req.lsl, mu, s)
        sig_short = process_capability.sigma_level(cpk_val)
        sig_long = process_capability.sigma_with_shift(cpk_val)
        frac_def = process_capability.fraction_defective_from_spec(
            req.usl, req.lsl, mu, s
        )
        dpmo_val = process_capability.dpmo(frac_def)
        yield_pct = (1.0 - frac_def) * 100.0
    else:
        cp_val = cpk_val = cpu_val = cpl_val = 0.0
        sig_short = sig_long = 0.0
        frac_def = 0.0
        dpmo_val = 0.0
        yield_pct = 100.0

    sigma_level_from_ppm: float | None = None
    if req.ppm is not None and req.ppm > 0:
        sigma_level_from_ppm = process_capability.sigma_from_dpmo(req.ppm)

    metrics = MetricsBlock(
        n=n,
        mean=round(mu, 6),
        std_dev=round(s, 6),
        cp=round(cp_val, 4),
        cpk=round(cpk_val, 4),
        cpu=round(cpu_val, 4),
        cpl=round(cpl_val, 4),
        sigma_short_term=round(sig_short, 2),
        sigma_long_term=round(sig_long, 2),
        dpmo=round(dpmo_val, 1),
        yield_pct=round(yield_pct, 4),
        fraction_defective=round(frac_def, 8),
        sigma_level=round(sigma_level_from_ppm, 4)
        if sigma_level_from_ppm is not None
        else None,
    )

    # --- chart data (IMR) ---
    if n >= 2:
        imr = spc_charts.imr_limits(data)
        chart = ChartDataBlock(
            values=data,
            cl=round(imr["I_CL"], 6),
            ucl=round(imr["I_UCL"], 6),
            lcl=round(imr["I_LCL"], 6),
            mr_cl=round(imr["MR_CL"], 6),
            mr_ucl=round(imr["MR_UCL"], 6),
            usl=req.usl,
            lsl=req.lsl,
        )
    else:
        chart = ChartDataBlock(
            values=data,
            cl=mu,
            ucl=mu,
            lcl=mu,
            mr_cl=0.0,
            mr_ucl=0.0,
            usl=req.usl,
            lsl=req.lsl,
        )

    # --- rule violations (warnings) ---
    violations: list[RuleViolation] = []
    if n >= 8:
        raw = spc_charts.western_electric_rules(data, chart.cl, chart.ucl, chart.lcl)
        violations = [RuleViolation(**v) for v in raw]

    # --- recommendations ---
    recs: list[str] = []
    if cpk_val < 1.0 and s > 0:
        recs.append(
            f"Cpk={cpk_val:.2f} — process is not capable. "
            "Reduce variation or re-centre the process."
        )
    if cpk_val >= 1.0 and cpk_val < 1.33:
        recs.append(
            f"Cpk={cpk_val:.2f} — marginally capable. "
            "Target Cpk ≥ 1.33 for sustained quality."
        )
    if cp_val > 0 and cpk_val < cp_val * 0.8 and s > 0:
        recs.append(
            "Cp and Cpk diverge — process is off-centre. "
            "Adjust mean toward target."
        )
    if violations:
        recs.append(
            f"{len(violations)} SPC rule violation(s) detected — "
            "investigate assignable causes."
        )
    if dpmo_val > 66807:
        recs.append(
            f"DPMO={dpmo_val:.0f} — below 3σ. Significant quality risk."
        )

    return {
        "analysis_type": "process_capability",
        "inputs": {
            "n": n,
            "usl": req.usl,
            "lsl": req.lsl,
            "sigma_provided": req.sigma,
            "ppm_provided": req.ppm,
        },
        "metrics": metrics,
        "chart_data": chart,
        "warnings": violations,
        "recommendations": recs,
    }


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.post(
    "/six-sigma/analyze",
    response_model=AnalyzeResponse,
    summary="Deterministic Six Sigma analysis",
    description=(
        "Computes a full process capability analysis from raw data. "
        "Returns metrics, IMR chart data, SPC rule violations, and "
        "actionable recommendations. All math uses the transiq library — "
        "zero LLM calls."
    ),
)
def analyze(req: AnalyzeRequest, request: Request) -> AnalyzeResponse:
    t0 = time.perf_counter()
    try:
        result = _compute(req)
    except Exception as exc:
        logger.exception("Analysis computation failed")
        raise HTTPException(status_code=400, detail=str(exc))

    elapsed = (time.perf_counter() - t0) * 1000
    logger.info(
        "analyze n=%d usl=%.2f lsl=%.2f cpk=%.4f elapsed=%.1fms",
        len(req.data),
        req.usl,
        req.lsl,
        result["metrics"].cpk,
        elapsed,
    )

    # Persist if DB is available
    _try_persist(request, result)

    return AnalyzeResponse(**result)


# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------

def _get_db_or_none(request: Request) -> Session | None:
    """Return a DB session if the database is initialised, else None."""
    try:
        from app.db.session import SessionLocal
        if SessionLocal is None:
            return None
        return SessionLocal()
    except Exception:
        return None


def _api_key_prefix(request: Request) -> str | None:
    """First 8 chars of the X-API-Key header (for ownership, not secrets)."""
    key = request.headers.get("x-api-key") or ""
    return key[:8] if key else None


def _try_persist(request: Request, result: dict) -> None:
    """Best-effort save — never fails the request."""
    db = _get_db_or_none(request)
    if db is None:
        return
    try:
        from transiq.api.models import SavedAnalysis

        row = SavedAnalysis(
            api_key_hash=_api_key_prefix(request),
            analysis_type=result["analysis_type"],
            inputs=result["inputs"],
            metrics=result["metrics"].model_dump(),
            chart_data=result["chart_data"].model_dump(),
            warnings=[w.model_dump() for w in result["warnings"]],
            recommendations=result["recommendations"],
        )
        db.add(row)
        db.commit()
    except Exception:
        logger.debug("Persistence skipped", exc_info=True)
        db.rollback()
    finally:
        db.close()


# ---------------------------------------------------------------------------
# History endpoint
# ---------------------------------------------------------------------------

class HistoryItem(BaseModel):
    id: int
    created_at: str
    analysis_type: str
    inputs: Dict[str, Any]
    metrics: Dict[str, Any]


@router.get(
    "/six-sigma/history",
    response_model=List[HistoryItem],
    summary="Recent analysis history",
    description="Returns the last N saved analyses (most recent first).",
)
def history(limit: int = Query(20, ge=1, le=100)) -> List[HistoryItem]:
    try:
        from app.db.session import SessionLocal
        from transiq.api.models import SavedAnalysis

        if SessionLocal is None:
            return []
        db = SessionLocal()
        try:
            rows = (
                db.query(SavedAnalysis)
                .order_by(SavedAnalysis.id.desc())
                .limit(limit)
                .all()
            )
            return [
                HistoryItem(
                    id=r.id,
                    created_at=r.created_at.isoformat() if r.created_at else "",
                    analysis_type=r.analysis_type or "process_capability",
                    inputs=r.inputs or {},
                    metrics=r.metrics or {},
                )
                for r in rows
            ]
        finally:
            db.close()
    except Exception:
        logger.debug("History unavailable", exc_info=True)
        return []
