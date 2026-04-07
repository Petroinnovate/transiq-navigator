"""
Confusion Matrix Analysis Module — Oil & Gas / Industrial Domain
Supports binary and multi-class classification, imbalanced datasets,
threshold optimization, and domain-aware business interpretation.
"""

from __future__ import annotations

import io
import json
import logging
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Domain interpretation helpers
# ---------------------------------------------------------------------------

_DOMAIN_CONTEXT = {
    "oil_gas": {
        "FN_msg": "Missed failure → downtime / safety risk",
        "FP_msg": "False alarm → unnecessary maintenance cost",
        "FN_severity": "HIGH",
        "FP_severity": "MEDIUM",
    },
    "manufacturing": {
        "FN_msg": "Missed defect → quality escape risk",
        "FP_msg": "False rejection → production waste",
        "FN_severity": "HIGH",
        "FP_severity": "MEDIUM",
    },
    "general": {
        "FN_msg": "Missed critical event → operational risk",
        "FP_msg": "Over-prediction → resource waste",
        "FN_severity": "HIGH",
        "FP_severity": "LOW",
    },
}


def _domain(use_case: str) -> Dict[str, str]:
    return _DOMAIN_CONTEXT.get(use_case, _DOMAIN_CONTEXT["general"])


# ---------------------------------------------------------------------------
# Core analysis function
# ---------------------------------------------------------------------------

def generate_confusion_matrix_report(
    y_true: List[Any],
    y_pred: List[Any],
    y_prob: Optional[List[float]] = None,
    labels: Optional[List[str]] = None,
    normalize: bool = False,
    use_case: str = "oil_gas",
) -> Dict[str, Any]:
    """
    Generate a full confusion matrix analysis report.

    Parameters
    ----------
    y_true   : Ground-truth labels
    y_pred   : Model-predicted labels
    y_prob   : Prediction probabilities (binary only, for threshold tuning)
    labels   : Human-readable class names
    normalize: Return normalized matrix (proportions) in addition to counts
    use_case : Domain context for business interpretation

    Returns
    -------
    Structured JSON-ready dict
    """
    y_true = list(y_true)
    y_pred = list(y_pred)

    unique_classes = sorted(set(y_true) | set(y_pred))
    if labels is None:
        labels = [str(c) for c in unique_classes]

    n_classes = len(unique_classes)
    is_binary = n_classes == 2

    # -----------------------------------------------------------------------
    # 1. Confusion matrix (counts + optional normalised)
    # -----------------------------------------------------------------------
    cm_raw = confusion_matrix(y_true, y_pred, labels=unique_classes)
    cm_list = cm_raw.tolist()

    cm_norm = None
    if normalize:
        row_sums = cm_raw.sum(axis=1, keepdims=True)
        row_sums[row_sums == 0] = 1  # avoid divide-by-zero
        cm_norm = (cm_raw / row_sums).round(4).tolist()

    # -----------------------------------------------------------------------
    # 2. Per-class + aggregate metrics
    # -----------------------------------------------------------------------
    acc = round(accuracy_score(y_true, y_pred), 4)

    avg = "binary" if is_binary else "macro"

    precision_macro = round(precision_score(y_true, y_pred, average="macro", zero_division=0), 4)
    recall_macro    = round(recall_score(y_true, y_pred, average="macro", zero_division=0), 4)
    f1_macro        = round(f1_score(y_true, y_pred, average="macro", zero_division=0), 4)

    precision_weighted = round(precision_score(y_true, y_pred, average="weighted", zero_division=0), 4)
    recall_weighted    = round(recall_score(y_true, y_pred, average="weighted", zero_division=0), 4)
    f1_weighted        = round(f1_score(y_true, y_pred, average="weighted", zero_division=0), 4)

    report = classification_report(
        y_true, y_pred,
        labels=unique_classes,
        target_names=labels,
        output_dict=True,
        zero_division=0,
    )

    per_class_metrics = []
    for cls_name in labels:
        r = report.get(cls_name, {})
        per_class_metrics.append({
            "class": cls_name,
            "precision": round(r.get("precision", 0), 4),
            "recall":    round(r.get("recall", 0), 4),
            "f1_score":  round(r.get("f1-score", 0), 4),
            "support":   int(r.get("support", 0)),
        })

    # -----------------------------------------------------------------------
    # 3. Error analysis — top confused pairs
    # -----------------------------------------------------------------------
    top_errors: List[Dict[str, Any]] = []
    for i in range(n_classes):
        for j in range(n_classes):
            if i != j and cm_raw[i, j] > 0:
                top_errors.append({
                    "actual":    labels[i],
                    "predicted": labels[j],
                    "count":     int(cm_raw[i, j]),
                    "pct_of_actual": round(cm_raw[i, j] / max(cm_raw[i].sum(), 1), 4),
                })
    top_errors.sort(key=lambda x: x["count"], reverse=True)
    top_errors = top_errors[:5]

    # -----------------------------------------------------------------------
    # 4. Binary-specific: FP / FN counts + domain risk flags
    # -----------------------------------------------------------------------
    risk_flags: List[Dict[str, str]] = []
    fp_count = fn_count = 0

    if is_binary:
        # Assume positive class is index 1
        tn, fp, fn, tp = cm_raw.ravel()
        fp_count = int(fp)
        fn_count = int(fn)
        total    = len(y_true)
        ctx      = _domain(use_case)

        fn_rate = round(fn / max(total, 1), 4)
        fp_rate = round(fp / max(total, 1), 4)

        if fn_rate > 0.10:
            risk_flags.append({
                "type":     "FALSE_NEGATIVE",
                "severity": ctx["FN_severity"],
                "message":  f"Model misses {fn} cases ({fn_rate*100:.1f}%) — {ctx['FN_msg']}",
            })
        if fp_rate > 0.15:
            risk_flags.append({
                "type":     "FALSE_POSITIVE",
                "severity": ctx["FP_severity"],
                "message":  f"Model raises {fp} false alarms ({fp_rate*100:.1f}%) — {ctx['FP_msg']}",
            })
    else:
        # Multi-class: flag classes with low recall
        ctx = _domain(use_case)
        for pc in per_class_metrics:
            if pc["recall"] < 0.70 and pc["support"] > 0:
                risk_flags.append({
                    "type":     "LOW_RECALL",
                    "severity": "HIGH",
                    "message":  (
                        f"Class '{pc['class']}' recall = {pc['recall']*100:.1f}% — "
                        f"{ctx['FN_msg']}"
                    ),
                })

    # -----------------------------------------------------------------------
    # 5. Business insights
    # -----------------------------------------------------------------------
    insights: List[str] = []

    if acc >= 0.95:
        insights.append(f"Excellent accuracy ({acc*100:.1f}%) — model is highly reliable.")
    elif acc >= 0.85:
        insights.append(f"Good accuracy ({acc*100:.1f}%) — acceptable for most operational use cases.")
    else:
        insights.append(f"Accuracy ({acc*100:.1f}%) is below threshold — review training data.")

    if f1_weighted < 0.70:
        insights.append("Weighted F1 < 0.70 — consider class-imbalance handling (SMOTE / class weights).")
    if len(top_errors) > 0:
        worst = top_errors[0]
        insights.append(
            f"Highest confusion: {worst['actual']} → {worst['predicted']} "
            f"({worst['count']} cases, {worst['pct_of_actual']*100:.1f}% of true '{worst['actual']}')."
        )

    # Imbalance check
    class_counts = pd.Series(y_true).value_counts()
    imbalance_ratio = class_counts.max() / max(class_counts.min(), 1)
    if imbalance_ratio > 5:
        insights.append(
            f"Dataset is imbalanced (ratio {imbalance_ratio:.1f}:1). "
            "Use weighted metrics or resampling techniques."
        )

    # -----------------------------------------------------------------------
    # 6. Threshold optimisation (binary + probabilities)
    # -----------------------------------------------------------------------
    threshold_analysis: Optional[Dict[str, Any]] = None
    pr_curve: Optional[Dict[str, List[float]]] = None

    if is_binary and y_prob is not None:
        try:
            precision_arr, recall_arr, thresholds_arr = precision_recall_curve(
                y_true, y_prob, pos_label=unique_classes[1]
            )
            # F1 at each threshold
            f1_arr = (
                2 * precision_arr[:-1] * recall_arr[:-1]
                / np.maximum(precision_arr[:-1] + recall_arr[:-1], 1e-9)
            )
            best_idx       = int(np.argmax(f1_arr))
            optimal_thresh = round(float(thresholds_arr[best_idx]), 4)
            best_f1        = round(float(f1_arr[best_idx]), 4)
            best_precision = round(float(precision_arr[best_idx]), 4)
            best_recall    = round(float(recall_arr[best_idx]), 4)

            threshold_analysis = {
                "optimal_threshold": optimal_thresh,
                "best_f1":          best_f1,
                "best_precision":   best_precision,
                "best_recall":      best_recall,
                "note": (
                    f"Use threshold {optimal_thresh} instead of default 0.5 "
                    f"to maximise F1 → {best_f1:.3f}"
                ),
            }

            # Downsample curve to ≤50 points for frontend
            step = max(1, len(thresholds_arr) // 50)
            pr_curve = {
                "precision":  [round(float(v), 4) for v in precision_arr[::step]],
                "recall":     [round(float(v), 4) for v in recall_arr[::step]],
                "thresholds": [round(float(v), 4) for v in thresholds_arr[::step]],
            }

            insights.append(
                f"Optimal decision threshold = {optimal_thresh} (F1={best_f1:.3f}). "
                f"Default 0.5 may not be optimal for this dataset."
            )
        except Exception as e:
            logger.warning("Threshold analysis failed: %s", e)

    # -----------------------------------------------------------------------
    # 7. Assemble final report
    # -----------------------------------------------------------------------
    return {
        "confusion_matrix":       cm_list,
        "confusion_matrix_norm":  cm_norm,
        "labels":                 labels,
        "n_classes":              n_classes,
        "total_samples":          len(y_true),
        "metrics": {
            "accuracy":           acc,
            "precision_macro":    precision_macro,
            "recall_macro":       recall_macro,
            "f1_macro":           f1_macro,
            "precision_weighted": precision_weighted,
            "recall_weighted":    recall_weighted,
            "f1_weighted":        f1_weighted,
        },
        "per_class_metrics":      per_class_metrics,
        "top_errors":             top_errors,
        "risk_flags":             risk_flags,
        "insights":               insights,
        "threshold_analysis":     threshold_analysis,
        "pr_curve":               pr_curve,
        "domain":                 use_case,
    }


# ---------------------------------------------------------------------------
# CSV parser helper
# ---------------------------------------------------------------------------

def parse_csv_for_labels(
    content: bytes,
    actual_col: str = "actual",
    predicted_col: str = "predicted",
    prob_col: Optional[str] = "probability",
) -> Dict[str, Any]:
    """Parse a CSV file and extract y_true, y_pred, y_prob arrays."""
    df = pd.read_csv(io.BytesIO(content))
    df.columns = [c.strip().lower() for c in df.columns]

    # Try common column name variants
    for variant in [actual_col, "actual", "y_true", "true", "label", "target"]:
        if variant in df.columns:
            actual_col = variant
            break
    else:
        raise ValueError(
            f"Could not find actual/y_true column. Found columns: {list(df.columns)}"
        )

    for variant in [predicted_col, "predicted", "y_pred", "pred", "prediction"]:
        if variant in df.columns:
            predicted_col = variant
            break
    else:
        raise ValueError(
            f"Could not find predicted column. Found columns: {list(df.columns)}"
        )

    y_true = df[actual_col].tolist()
    y_pred = df[predicted_col].tolist()
    y_prob = None

    for variant in [prob_col, "probability", "prob", "score", "confidence"]:
        if variant and variant in df.columns:
            y_prob = df[variant].tolist()
            break

    return {"y_true": y_true, "y_pred": y_pred, "y_prob": y_prob}
