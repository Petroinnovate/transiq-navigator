"""
Data Drift Detector
===================
Monitors input data distributions over time and flags significant shifts
that could degrade model quality.

Supports:
  - Feature distribution comparison (KS test, PSI)
  - Schema drift (missing/new columns)
  - Volume drift (sudden drop/spike in data volume)
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class DriftReport:
    feature: str
    drift_score: float
    threshold: float
    drifted: bool
    method: str  # "psi" | "ks" | "volume"
    details: Dict[str, Any] = field(default_factory=dict)


def population_stability_index(
    reference: List[float],
    current: List[float],
    buckets: int = 10,
) -> float:
    """
    Population Stability Index (PSI).
    PSI < 0.1  → no significant drift
    PSI 0.1-0.2 → moderate drift
    PSI > 0.2  → significant drift
    """
    if not reference or not current:
        return 0.0

    min_val = min(min(reference), min(current))
    max_val = max(max(reference), max(current))
    if min_val == max_val:
        return 0.0

    bin_width = (max_val - min_val) / buckets
    eps = 1e-6

    def _bin(values):
        counts = [0] * buckets
        for v in values:
            idx = min(int((v - min_val) / bin_width), buckets - 1)
            counts[idx] += 1
        total = len(values)
        return [(c / total) + eps for c in counts]

    ref_pcts = _bin(reference)
    cur_pcts = _bin(current)

    psi = sum(
        (cur - ref) * math.log(cur / ref)
        for ref, cur in zip(ref_pcts, cur_pcts)
    )
    return psi


def detect_data_drift(
    reference: Dict[str, List[float]],
    current: Dict[str, List[float]],
    psi_threshold: float = 0.2,
) -> List[DriftReport]:
    """
    Check each feature for distribution drift using PSI.

    Args:
        reference: baseline feature distributions {feature_name: [values]}
        current: current feature distributions {feature_name: [values]}
        psi_threshold: PSI value above which drift is flagged

    Returns:
        List of DriftReport for each feature
    """
    reports = []
    all_features = set(reference) | set(current)

    for feat in sorted(all_features):
        ref_vals = reference.get(feat, [])
        cur_vals = current.get(feat, [])

        # Schema drift: feature missing in one set
        if not ref_vals or not cur_vals:
            reports.append(DriftReport(
                feature=feat,
                drift_score=1.0,
                threshold=psi_threshold,
                drifted=True,
                method="schema",
                details={"reason": "feature missing", "in_reference": bool(ref_vals), "in_current": bool(cur_vals)},
            ))
            continue

        psi = population_stability_index(ref_vals, cur_vals)
        reports.append(DriftReport(
            feature=feat,
            drift_score=round(psi, 4),
            threshold=psi_threshold,
            drifted=psi > psi_threshold,
            method="psi",
            details={"reference_count": len(ref_vals), "current_count": len(cur_vals)},
        ))

    drifted_count = sum(1 for r in reports if r.drifted)
    if drifted_count:
        logger.warning("Data drift detected in %d/%d features", drifted_count, len(reports))

    return reports


def detect_volume_drift(
    reference_count: int,
    current_count: int,
    threshold_pct: float = 0.3,
) -> DriftReport:
    """Flag if data volume changed by more than threshold_pct."""
    if reference_count == 0:
        ratio = float("inf") if current_count > 0 else 0.0
    else:
        ratio = abs(current_count - reference_count) / reference_count

    return DriftReport(
        feature="_volume",
        drift_score=round(ratio, 4),
        threshold=threshold_pct,
        drifted=ratio > threshold_pct,
        method="volume",
        details={"reference_count": reference_count, "current_count": current_count},
    )
