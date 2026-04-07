"""
DDR Parser Module — Structured PDF parser for Daily Drilling Reports

Uses pdfplumber for text+layout extraction, pytesseract OCR fallback,
SHA-256 page hashing for traceability, and concurrent multi-rig parsing.
"""
import hashlib
import io
import re
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pdfplumber
from pydantic import BaseModel, Field

from app.utils.logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Pydantic output models
# ---------------------------------------------------------------------------

class PageData(BaseModel):
    page_number: int
    text: str
    bounding_boxes: List[Dict[str, float]] = Field(default_factory=list)
    page_hash: str
    extraction_method: str = "pdfplumber"  # pdfplumber | ocr


class ExtractedField(BaseModel):
    name: str
    value: Any
    raw_text: str = ""
    page_number: int = 0
    confidence: float = 1.0
    extraction_method: str = "regex"
    citation: str = ""


class DDRParseResult(BaseModel):
    report_metadata: Dict[str, Any] = Field(default_factory=dict)
    pages: List[PageData] = Field(default_factory=list)
    extracted_fields: Dict[str, Any] = Field(default_factory=dict)
    confidence_scores: Dict[str, float] = Field(default_factory=dict)
    page_hashes: List[str] = Field(default_factory=list)
    parse_time_ms: float = 0.0
    total_pages: int = 0
    ocr_pages: int = 0


# ---------------------------------------------------------------------------
# 30+ configurable regex patterns for DDR fields
# ---------------------------------------------------------------------------

DDR_FIELD_PATTERNS: Dict[str, List[Dict[str, Any]]] = {
    # ── Identification ──
    "rig_name": [
        {"pattern": r"Rig\s*(?:Name|ID|No\.?)\s*[:\-]?\s*(.+?)(?:\n|$)", "flags": re.IGNORECASE},
        {"pattern": r"(?:RIG|Rig)\s*[#:\-]?\s*(\S+)", "flags": re.IGNORECASE},
    ],
    "well_name": [
        {"pattern": r"Well\s*(?:Name|ID)\s*[:\-]?\s*(.+?)(?:\n|$)", "flags": re.IGNORECASE},
        {"pattern": r"Well\s*[#:\-]?\s*(\S+)", "flags": re.IGNORECASE},
    ],
    "report_date": [
        {"pattern": r"(?:Report|Date)\s*[:\-]?\s*(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})", "flags": re.IGNORECASE},
        {"pattern": r"(\d{4}[/\-]\d{1,2}[/\-]\d{1,2})", "flags": 0},
    ],
    "report_number": [
        {"pattern": r"Report\s*(?:No|Number|#)\s*[:\-]?\s*(\d+)", "flags": re.IGNORECASE},
    ],
    "field_name": [
        {"pattern": r"Field\s*(?:Name)?\s*[:\-]?\s*(.+?)(?:\n|$)", "flags": re.IGNORECASE},
    ],
    "operator": [
        {"pattern": r"Operator\s*[:\-]?\s*(.+?)(?:\n|$)", "flags": re.IGNORECASE},
    ],
    "contractor": [
        {"pattern": r"Contractor\s*[:\-]?\s*(.+?)(?:\n|$)", "flags": re.IGNORECASE},
    ],

    # ── Depth ──
    "depth_md": [
        {"pattern": r"(?:Measured\s*Depth|MD)\s*[:\-]?\s*([\d,]+\.?\d*)\s*(?:ft|m)?", "flags": re.IGNORECASE},
        {"pattern": r"Present\s*Depth\s*[:\-]?\s*([\d,]+\.?\d*)", "flags": re.IGNORECASE},
    ],
    "depth_tvd": [
        {"pattern": r"(?:True\s*Vertical\s*Depth|TVD)\s*[:\-]?\s*([\d,]+\.?\d*)\s*(?:ft|m)?", "flags": re.IGNORECASE},
    ],
    "hole_depth": [
        {"pattern": r"Hole\s*Depth\s*[:\-]?\s*([\d,]+\.?\d*)\s*(?:ft|m)?", "flags": re.IGNORECASE},
    ],
    "casing_depth": [
        {"pattern": r"Casing\s*(?:Depth|Set)\s*[:\-]?\s*([\d,]+\.?\d*)\s*(?:ft|m)?", "flags": re.IGNORECASE},
    ],

    # ── Drilling Parameters ──
    "rop": [
        {"pattern": r"(?:ROP|Rate\s*of\s*Penetration)\s*[:\-]?\s*([\d.]+)\s*(?:ft/hr|m/hr)?", "flags": re.IGNORECASE},
    ],
    "wob": [
        {"pattern": r"(?:WOB|Weight\s*on\s*Bit)\s*[:\-]?\s*([\d.]+)\s*(?:klbs?|kN)?", "flags": re.IGNORECASE},
    ],
    "rpm": [
        {"pattern": r"(?:RPM|Rotary\s*Speed)\s*[:\-]?\s*([\d.]+)", "flags": re.IGNORECASE},
    ],
    "torque": [
        {"pattern": r"Torque\s*[:\-]?\s*([\d,]+\.?\d*)\s*(?:ft[.\-]?lbs?|kN[.\-]?m)?", "flags": re.IGNORECASE},
    ],
    "pump_pressure": [
        {"pattern": r"(?:Pump|Standpipe)\s*Pressure\s*[:\-]?\s*([\d,]+\.?\d*)\s*(?:psi|kPa)?", "flags": re.IGNORECASE},
    ],
    "flow_rate": [
        {"pattern": r"(?:Flow\s*Rate|GPM)\s*[:\-]?\s*([\d.]+)\s*(?:gpm|lpm)?", "flags": re.IGNORECASE},
    ],
    "bit_size": [
        {"pattern": r"Bit\s*(?:Size|Diameter)\s*[:\-]?\s*([\d./]+)\s*(?:in|mm)?", "flags": re.IGNORECASE},
    ],
    "bit_type": [
        {"pattern": r"Bit\s*Type\s*[:\-]?\s*(.+?)(?:\n|$)", "flags": re.IGNORECASE},
    ],

    # ── Mud / Fluids ──
    "mud_weight": [
        {"pattern": r"(?:Mud\s*Weight|MW)\s*[:\-]?\s*([\d.]+)\s*(?:ppg|sg|lb/gal)?", "flags": re.IGNORECASE},
    ],
    "mud_type": [
        {"pattern": r"Mud\s*Type\s*[:\-]?\s*(.+?)(?:\n|$)", "flags": re.IGNORECASE},
    ],
    "mud_viscosity": [
        {"pattern": r"(?:Funnel\s*)?Viscosity\s*[:\-]?\s*([\d.]+)\s*(?:sec|cp)?", "flags": re.IGNORECASE},
    ],
    "plastic_viscosity": [
        {"pattern": r"(?:Plastic\s*Viscosity|PV)\s*[:\-]?\s*([\d.]+)", "flags": re.IGNORECASE},
    ],
    "yield_point": [
        {"pattern": r"(?:Yield\s*Point|YP)\s*[:\-]?\s*([\d.]+)", "flags": re.IGNORECASE},
    ],

    # ── NPT / HSE ──
    "npt_hours": [
        {"pattern": r"(?:NPT|Non[- ]?Productive\s*Time)\s*[:\-]?\s*([\d.]+)\s*(?:hrs?|hours?)?", "flags": re.IGNORECASE},
    ],
    "npt_description": [
        {"pattern": r"NPT\s*(?:Description|Details?|Remarks?)\s*[:\-]?\s*(.+?)(?:\n|$)", "flags": re.IGNORECASE},
    ],
    "hse_incidents": [
        {"pattern": r"(?:HSE|Safety)\s*(?:Incidents?|Events?)\s*[:\-]?\s*([\d]+|None|Zero)", "flags": re.IGNORECASE},
    ],
    "personnel_count": [
        {"pattern": r"(?:Personnel|POB|Persons?\s*on\s*Board)\s*[:\-]?\s*(\d+)", "flags": re.IGNORECASE},
    ],

    # ── Formation / Survey ──
    "formation_tops": [
        {"pattern": r"Formation\s*(?:Top|Name)\s*[:\-]?\s*(.+?)(?:\n|$)", "flags": re.IGNORECASE},
    ],
    "survey_inclination": [
        {"pattern": r"(?:Inclination|Inc)\s*[:\-]?\s*([\d.]+)\s*(?:deg|°)?", "flags": re.IGNORECASE},
    ],
    "survey_azimuth": [
        {"pattern": r"(?:Azimuth|Azi)\s*[:\-]?\s*([\d.]+)\s*(?:deg|°)?", "flags": re.IGNORECASE},
    ],

    # ── Drill String ──
    "bha_description": [
        {"pattern": r"(?:BHA|Bottom\s*Hole\s*Assembly)\s*[:\-]?\s*(.+?)(?:\n\n|$)", "flags": re.IGNORECASE | re.DOTALL},
    ],

    # ── Foreman Remarks ──
    "foreman_remarks": [
        {"pattern": r"(?:Foreman|Supervisor)\s*(?:Remarks?|Comments?|Notes?)\s*[:\-]?\s*(.+?)(?:\n\n|$)", "flags": re.IGNORECASE | re.DOTALL},
    ],
}


# ---------------------------------------------------------------------------
# OCR helpers
# ---------------------------------------------------------------------------

def _ocr_page_image(page_image) -> str:
    """Run OCR on a PIL image. Returns extracted text."""
    try:
        import pytesseract
        return pytesseract.image_to_string(page_image)
    except ImportError:
        logger.warning("pytesseract not available — OCR fallback disabled")
        return ""
    except Exception as e:
        logger.error(f"OCR failed: {e}")
        return ""


def _page_to_image(pdf_path: str, page_num: int):
    """Convert single PDF page to PIL Image using pdfplumber."""
    try:
        from PIL import Image as PILImage
        with pdfplumber.open(pdf_path) as pdf:
            page = pdf.pages[page_num]
            img = page.to_image(resolution=300)
            return img.original  # PIL Image
    except Exception as e:
        logger.error(f"Page-to-image conversion failed for page {page_num}: {e}")
        return None


# ---------------------------------------------------------------------------
# Page hash
# ---------------------------------------------------------------------------

def _page_hash(text: str) -> str:
    """SHA-256 hash of page text content for traceability."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Field extraction
# ---------------------------------------------------------------------------

def _extract_fields_from_pages(
    pages: List[PageData],
    rig_id: str = "",
    patterns: Optional[Dict] = None,
) -> Tuple[Dict[str, Any], Dict[str, float], List[ExtractedField]]:
    """
    Apply regex patterns to extracted page text.
    Returns (fields_dict, confidence_dict, detailed_extractions).
    """
    pat = patterns or DDR_FIELD_PATTERNS
    fields: Dict[str, Any] = {}
    confidence: Dict[str, float] = {}
    details: List[ExtractedField] = []

    full_text_by_page = {p.page_number: p.text for p in pages}

    for field_name, pattern_list in pat.items():
        best_match: Optional[re.Match] = None
        best_page = 0
        best_conf = 0.0
        best_raw = ""

        for pg_num, pg_text in full_text_by_page.items():
            for pat_def in pattern_list:
                m = re.search(pat_def["pattern"], pg_text, flags=pat_def.get("flags", 0))
                if m:
                    conf = 0.9 if pages[pg_num - 1].extraction_method == "pdfplumber" else 0.65
                    if conf > best_conf:
                        best_match = m
                        best_page = pg_num
                        best_conf = conf
                        best_raw = m.group(0)

        if best_match:
            value = best_match.group(1).strip()
            # Build citation: [RigID–Pg#–Section–Field]
            section = _infer_section(field_name)
            citation = f"[{rig_id or 'RIG'}–Pg{best_page}–{section}–{field_name}]"

            fields[field_name] = value
            confidence[field_name] = round(best_conf, 2)
            details.append(ExtractedField(
                name=field_name,
                value=value,
                raw_text=best_raw,
                page_number=best_page,
                confidence=best_conf,
                extraction_method="regex",
                citation=citation,
            ))

    return fields, confidence, details


def _infer_section(field_name: str) -> str:
    """Map field name to DDR section for citation."""
    section_map = {
        "rig_name": "Header", "well_name": "Header", "report_date": "Header",
        "report_number": "Header", "field_name": "Header", "operator": "Header",
        "contractor": "Header",
        "depth_md": "Depth", "depth_tvd": "Depth", "hole_depth": "Depth",
        "casing_depth": "Depth",
        "rop": "Drilling", "wob": "Drilling", "rpm": "Drilling",
        "torque": "Drilling", "pump_pressure": "Drilling", "flow_rate": "Drilling",
        "bit_size": "Drilling", "bit_type": "Drilling",
        "mud_weight": "MudData", "mud_type": "MudData", "mud_viscosity": "MudData",
        "plastic_viscosity": "MudData", "yield_point": "MudData",
        "npt_hours": "NPT", "npt_description": "NPT",
        "hse_incidents": "HSE", "personnel_count": "Personnel",
        "formation_tops": "Formation", "survey_inclination": "Survey",
        "survey_azimuth": "Survey",
        "bha_description": "DrillString",
        "foreman_remarks": "Remarks",
    }
    return section_map.get(field_name, "General")


# ---------------------------------------------------------------------------
# Core single-report parser
# ---------------------------------------------------------------------------

MIN_TEXT_CHARS = 50  # threshold for OCR fallback


def parse_ddr_pdf(
    pdf_path: str,
    rig_id: str = "",
    ocr_fallback: bool = True,
    custom_patterns: Optional[Dict] = None,
) -> DDRParseResult:
    """
    Parse a single DDR PDF file.

    Args:
        pdf_path: Path to PDF file.
        rig_id: Rig identifier for citations.
        ocr_fallback: Whether to use pytesseract on low-text pages.
        custom_patterns: Override default regex patterns.

    Returns:
        DDRParseResult with pages, fields, confidence, hashes.
    """
    start = time.time()
    pages: List[PageData] = []
    ocr_count = 0

    try:
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                pg_num = i + 1
                text = page.extract_text() or ""

                # Bounding boxes for layout preservation
                words = page.extract_words() or []
                bboxes = [
                    {"x0": w["x0"], "y0": w["top"], "x1": w["x1"], "y1": w["bottom"], "text": w["text"]}
                    for w in words[:500]  # cap for performance
                ]

                method = "pdfplumber"

                # OCR fallback for low-text pages
                if ocr_fallback and len(text.strip()) < MIN_TEXT_CHARS:
                    img = _page_to_image(pdf_path, i)
                    if img is not None:
                        ocr_text = _ocr_page_image(img)
                        if ocr_text.strip():
                            text = ocr_text
                            method = "ocr"
                            ocr_count += 1

                ph = _page_hash(text)
                pages.append(PageData(
                    page_number=pg_num,
                    text=text,
                    bounding_boxes=bboxes,
                    page_hash=ph,
                    extraction_method=method,
                ))

    except Exception as e:
        logger.error(f"Failed to open/parse PDF at {pdf_path}: {e}")
        return DDRParseResult(
            report_metadata={"error": str(e), "pdf_path": pdf_path},
            parse_time_ms=round((time.time() - start) * 1000, 1),
        )

    # Field extraction
    fields, confidence, _details = _extract_fields_from_pages(
        pages, rig_id=rig_id, patterns=custom_patterns,
    )

    # Build metadata
    metadata = {
        "pdf_path": pdf_path,
        "rig_id": rig_id or fields.get("rig_name", "UNKNOWN"),
        "well_name": fields.get("well_name", ""),
        "report_date": fields.get("report_date", ""),
        "total_pages": len(pages),
        "ocr_pages": ocr_count,
    }

    elapsed = round((time.time() - start) * 1000, 1)

    return DDRParseResult(
        report_metadata=metadata,
        pages=pages,
        extracted_fields=fields,
        confidence_scores=confidence,
        page_hashes=[p.page_hash for p in pages],
        parse_time_ms=elapsed,
        total_pages=len(pages),
        ocr_pages=ocr_count,
    )


# ---------------------------------------------------------------------------
# Multi-rig concurrent parsing
# ---------------------------------------------------------------------------

def _parse_single(args: Tuple[str, str, bool]) -> Dict[str, Any]:
    """Picklable wrapper for ProcessPoolExecutor."""
    pdf_path, rig_id, ocr = args
    try:
        result = parse_ddr_pdf(pdf_path, rig_id=rig_id, ocr_fallback=ocr)
        return result.model_dump()
    except Exception as e:
        return {"error": str(e), "pdf_path": pdf_path, "rig_id": rig_id}


def parse_multiple_ddrs(
    reports: List[Dict[str, str]],
    max_workers: int = 4,
    ocr_fallback: bool = True,
) -> List[Dict[str, Any]]:
    """
    Parse multiple DDR PDFs concurrently.

    Args:
        reports: List of dicts with keys 'pdf_path' and optional 'rig_id'.
        max_workers: Number of parallel workers.
        ocr_fallback: Enable OCR on low-text pages.

    Returns:
        List of parse results (dict form).
    """
    tasks = [
        (r["pdf_path"], r.get("rig_id", ""), ocr_fallback)
        for r in reports
    ]

    results: List[Dict[str, Any]] = []

    with ProcessPoolExecutor(max_workers=min(max_workers, len(tasks))) as executor:
        futures = {executor.submit(_parse_single, t): t for t in tasks}
        for future in as_completed(futures):
            try:
                results.append(future.result())
            except Exception as e:
                task_info = futures[future]
                logger.error(f"Worker failed for {task_info[0]}: {e}")
                results.append({"error": str(e), "pdf_path": task_info[0]})

    return results
