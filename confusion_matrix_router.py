"""
FastAPI router for Confusion Matrix Analysis.
Endpoints:
  POST /api/v2/confusion-matrix        — JSON payload (y_true, y_pred, y_prob)
  POST /api/v2/confusion-matrix/upload — CSV file upload
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel, field_validator

from confusion_matrix_service import generate_confusion_matrix_report, parse_csv_for_labels

router = APIRouter(prefix="/api/v2/confusion-matrix", tags=["confusion-matrix"])


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class ConfusionMatrixRequest(BaseModel):
    y_true:   List[Any]
    y_pred:   List[Any]
    y_prob:   Optional[List[float]] = None
    labels:   Optional[List[str]]   = None
    normalize: bool                 = False
    use_case: str                   = "oil_gas"

    @field_validator("y_true", "y_pred")
    @classmethod
    def must_not_be_empty(cls, v):
        if not v:
            raise ValueError("y_true and y_pred must not be empty")
        return v

    @field_validator("y_pred")
    @classmethod
    def same_length(cls, v, info):
        y_true = info.data.get("y_true", [])
        if y_true and len(v) != len(y_true):
            raise ValueError("y_true and y_pred must have the same length")
        return v


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("")
async def analyze_confusion_matrix(body: ConfusionMatrixRequest) -> Dict[str, Any]:
    """
    Compute confusion matrix, classification metrics, risk flags, and insights.

    Body example:
    ```json
    {
      "y_true": [0,1,1,0,1,0,1],
      "y_pred": [0,1,0,0,1,1,1],
      "use_case": "oil_gas"
    }
    ```
    """
    try:
        result = generate_confusion_matrix_report(
            y_true    = body.y_true,
            y_pred    = body.y_pred,
            y_prob    = body.y_prob,
            labels    = body.labels,
            normalize = body.normalize,
            use_case  = body.use_case,
        )
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.post("/upload")
async def analyze_from_csv(
    file: UploadFile = File(...),
    actual_col:    str  = Query("actual"),
    predicted_col: str  = Query("predicted"),
    prob_col:      str  = Query(""),          # empty = auto-detect
    normalize:     bool = Query(False),
    use_case:      str  = Query("oil_gas"),
) -> Dict[str, Any]:
    """
    Upload a CSV file with actual/predicted columns and receive full analysis.

    CSV must have columns like: actual, predicted (and optionally: probability)
    Column name variants are auto-detected.
    """
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are accepted")

    content = await file.read()
    if len(content) > 50 * 1024 * 1024:  # 50 MB limit
        raise HTTPException(status_code=413, detail="File too large (max 50 MB)")

    prob_col_clean = prob_col.strip() if prob_col and prob_col.strip() else None

    try:
        parsed = parse_csv_for_labels(
            content,
            actual_col=actual_col,
            predicted_col=predicted_col,
            prob_col=prob_col_clean,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    try:
        result = generate_confusion_matrix_report(
            y_true    = parsed["y_true"],
            y_pred    = parsed["y_pred"],
            y_prob    = parsed.get("y_prob"),
            normalize = normalize,
            use_case  = use_case,
        )
        return {"status": "success", "filename": file.filename, "data": result}
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))
