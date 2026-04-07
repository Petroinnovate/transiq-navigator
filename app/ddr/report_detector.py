"""
Report Type Detector — Automatically classifies uploaded PDFs as DDR or GENERIC.

Uses keyword matching, regex patterns, and structural heuristics to detect
OPERLMTDMRREP-format Daily Drilling Reports vs generic documents.
"""
import re
from typing import Any, Dict, List, Optional

import pdfplumber
from pydantic import BaseModel, Field

from app.utils.logger import get_logger

logger = get_logger(__name__)


class DetectionResult(BaseModel):
    report_type: str = "GENERIC"  # DDR | GENERIC
    confidence: float = 0.0
    signals: List[str] = Field(default_factory=list)
    recommended_parser: str = "llm_pipeline"  # ddr_parser | llm_pipeline


# ---------------------------------------------------------------------------
# Detection signals (weighted)
# ---------------------------------------------------------------------------

# Keywords highly indicative of DDR content
DDR_KEYWORDS: List[Dict[str, Any]] = [
    {"pattern": r"OPERLMTDMRREP", "weight": 0.35, "label": "OPERLMTDMRREP format signature"},
    {"pattern": r"Daily\s+Drilling\s+Report", "weight": 0.25, "label": "DDR title"},
    {"pattern": r"Morning\s+Report", "weight": 0.15, "label": "Morning report header"},
    {"pattern": r"Rig\s+(?:Name|ID|No)", "weight": 0.10, "label": "Rig identifier"},
    {"pattern": r"(?:Measured\s+Depth|MD)\s*[:\-]", "weight": 0.08, "label": "Measured Depth field"},
    {"pattern": r"(?:True\s+Vertical\s+Depth|TVD)", "weight": 0.08, "label": "TVD field"},
    {"pattern": r"(?:Rate\s+of\s+Penetration|ROP)", "weight": 0.08, "label": "ROP field"},
    {"pattern": r"Mud\s+Weight", "weight": 0.08, "label": "Mud weight field"},
    {"pattern": r"(?:NPT|Non[- ]?Productive\s+Time)", "weight": 0.10, "label": "NPT reference"},
    {"pattern": r"(?:BHA|Bottom\s+Hole\s+Assembly)", "weight": 0.08, "label": "BHA reference"},
    {"pattern": r"Drill\s*(?:ing)?\s*(?:String|Pipe)", "weight": 0.06, "label": "Drill string"},
    {"pattern": r"(?:Pump|Standpipe)\s+Pressure", "weight": 0.06, "label": "Pump pressure"},
    {"pattern": r"(?:WOB|Weight\s+on\s+Bit)", "weight": 0.06, "label": "WOB field"},
    {"pattern": r"Formation\s+Top", "weight": 0.06, "label": "Formation top"},
    {"pattern": r"Foreman\s+(?:Remarks?|Comments?)", "weight": 0.06, "label": "Foreman remarks"},
    {"pattern": r"(?:HSE|Safety)\s+(?:Incidents?|Report)", "weight": 0.05, "label": "HSE section"},
    {"pattern": r"Personnel\s+on\s+Board|POB", "weight": 0.05, "label": "POB field"},
    {"pattern": r"Directional\s+Survey", "weight": 0.05, "label": "Directional survey"},
    {"pattern": r"Casing\s+(?:Depth|Set|Program)", "weight": 0.05, "label": "Casing data"},
    {"pattern": r"Well\s+(?:Name|ID)", "weight": 0.05, "label": "Well identifier"},
]

# Structural heuristics
STRUCTURAL_CHECKS = [
    {"check": "multi_page", "weight": 0.05, "label": "Multi-page document (≥3 pages)"},
    {"check": "tabular_density", "weight": 0.08, "label": "High table/tabular density"},
    {"check": "numeric_density", "weight": 0.06, "label": "High numeric content density"},
]

# Thresholds
DDR_CONFIDENCE_THRESHOLD = 0.40  # ≥40% confidence → classify as DDR


# ---------------------------------------------------------------------------
# Core detection
# ---------------------------------------------------------------------------

def detect_report_type(
    pdf_path: str,
    sample_pages: int = 5,
) -> DetectionResult:
    """
    Detect whether a PDF is a DDR or generic document.

    Args:
        pdf_path: Path to the uploaded PDF.
        sample_pages: Max pages to scan for classification (for speed).

    Returns:
        DetectionResult with type, confidence, signals.
    """
    signals: List[str] = []
    total_weight = 0.0

    try:
        with pdfplumber.open(pdf_path) as pdf:
            num_pages = len(pdf.pages)
            pages_to_scan = min(sample_pages, num_pages)

            # Concatenate text from sample pages
            sample_text = ""
            table_count = 0
            for i in range(pages_to_scan):
                page = pdf.pages[i]
                text = page.extract_text() or ""
                sample_text += text + "\n"
                tables = page.extract_tables() or []
                table_count += len(tables)

            # --- Keyword signals ---
            for kw in DDR_KEYWORDS:
                if re.search(kw["pattern"], sample_text, re.IGNORECASE):
                    total_weight += kw["weight"]
                    signals.append(kw["label"])

            # --- Structural signals ---
            # Multi-page check
            if num_pages >= 3:
                total_weight += 0.05
                signals.append(f"Multi-page document ({num_pages} pages)")

            # Tabular density
            if table_count >= 2:
                total_weight += 0.08
                signals.append(f"Tabular content detected ({table_count} tables in sample)")

            # Numeric density — count numbers in text
            numbers = re.findall(r"\d+\.?\d*", sample_text)
            text_words = sample_text.split()
            if text_words:
                numeric_ratio = len(numbers) / max(len(text_words), 1)
                if numeric_ratio > 0.15:
                    total_weight += 0.06
                    signals.append(f"High numeric density ({numeric_ratio:.0%})")

    except Exception as e:
        logger.error(f"Report detection failed for {pdf_path}: {e}")
        return DetectionResult(
            report_type="GENERIC",
            confidence=0.0,
            signals=[f"Detection error: {str(e)}"],
            recommended_parser="llm_pipeline",
        )

    # Clamp confidence to [0, 1]
    confidence = round(min(total_weight, 1.0), 2)
    is_ddr = confidence >= DDR_CONFIDENCE_THRESHOLD

    return DetectionResult(
        report_type="DDR" if is_ddr else "GENERIC",
        confidence=confidence,
        signals=signals,
        recommended_parser="ddr_parser" if is_ddr else "llm_pipeline",
    )


def detect_report_type_from_text(text: str) -> DetectionResult:
    """
    Lightweight detection from already-extracted text (no PDF I/O).

    Useful when text is already available from a prior extraction step.
    """
    signals: List[str] = []
    total_weight = 0.0

    for kw in DDR_KEYWORDS:
        if re.search(kw["pattern"], text, re.IGNORECASE):
            total_weight += kw["weight"]
            signals.append(kw["label"])

    confidence = round(min(total_weight, 1.0), 2)
    is_ddr = confidence >= DDR_CONFIDENCE_THRESHOLD

    return DetectionResult(
        report_type="DDR" if is_ddr else "GENERIC",
        confidence=confidence,
        signals=signals,
        recommended_parser="ddr_parser" if is_ddr else "llm_pipeline",
    )
