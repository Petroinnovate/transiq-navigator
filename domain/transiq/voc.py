"""
Voice of Customer (VOC) and Quality Function Deployment (QFD).

Covers ASQ Handbook Chapter 5: Voice of the Customer.

Functions
---------
capture_voc         Structure customer needs with priorities
ctq_tree            Build Critical-to-Quality (CTQ) tree
qfd_matrix          House of Quality deployment matrix
kano_classify       Kano model classification of requirements
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def capture_voc(
    needs: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Structure Voice of Customer data.

    Parameters
    ----------
    needs : list of dicts with:
        - "need": customer need statement
        - "source": how it was captured ("survey" | "interview" | "complaint" | "observation")
        - "priority": 1–5 (customer importance)
        - "category": optional grouping

    Returns
    -------
    dict with categorised needs, priority distribution, summary
    """
    by_category: Dict[str, List] = {}
    by_source: Dict[str, int] = {}
    priorities = []

    for n in needs:
        cat = n.get("category", "General")
        by_category.setdefault(cat, []).append(n)
        src = n.get("source", "unknown")
        by_source[src] = by_source.get(src, 0) + 1
        priorities.append(n.get("priority", 3))

    avg_priority = sum(priorities) / len(priorities) if priorities else 0

    return {
        "needs": needs,
        "by_category": {k: len(v) for k, v in by_category.items()},
        "by_source": by_source,
        "total_needs": len(needs),
        "avg_priority": round(avg_priority, 2),
        "high_priority": [n for n in needs if n.get("priority", 0) >= 4],
    }


def ctq_tree(
    customer_need: str,
    drivers: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Build a CTQ (Critical-to-Quality) tree.

    CTQ Tree: Customer Need → Drivers → CTQ Characteristics → Specifications

    Parameters
    ----------
    customer_need : top-level customer need
    drivers : list of dicts:
        - "driver": quality driver name
        - "ctqs": list of dicts:
            - "characteristic": measurable CTQ
            - "specification": target specification
            - "unit": measurement unit
    """
    total_ctqs = sum(len(d.get("ctqs", [])) for d in drivers)

    return {
        "customer_need": customer_need,
        "drivers": drivers,
        "total_drivers": len(drivers),
        "total_ctqs": total_ctqs,
    }


def qfd_matrix(
    customer_requirements: List[Dict[str, Any]],
    technical_requirements: List[str],
    relationship_matrix: List[List[int]],
    correlation_matrix: Optional[List[List[int]]] = None,
) -> Dict[str, Any]:
    """
    Quality Function Deployment (House of Quality) matrix.

    Parameters
    ----------
    customer_requirements : list of dicts:
        - "requirement": text
        - "importance": 1–5
    technical_requirements : list of technical feature names
    relationship_matrix : 2D list [cust_req × tech_req]
        Values: 0 (none), 1 (weak), 3 (moderate), 9 (strong)
    correlation_matrix : optional 2D [tech_req × tech_req]
        Values: -1 (negative), 0 (none), 1 (positive)

    Returns
    -------
    dict with absolute/relative importance of technical requirements, priority ranking.
    """
    n_cust = len(customer_requirements)
    n_tech = len(technical_requirements)

    if len(relationship_matrix) != n_cust:
        raise ValueError("relationship_matrix rows must match customer_requirements count")

    # Compute absolute importance for each technical requirement
    abs_importance = [0.0] * n_tech
    for i in range(n_cust):
        imp = customer_requirements[i].get("importance", 3)
        for j in range(n_tech):
            if j < len(relationship_matrix[i]):
                abs_importance[j] += imp * relationship_matrix[i][j]

    total_importance = sum(abs_importance)
    rel_importance = [
        round(ai / total_importance * 100, 2) if total_importance > 0 else 0.0
        for ai in abs_importance
    ]

    # Priority ranking
    ranked = sorted(
        enumerate(technical_requirements),
        key=lambda x: abs_importance[x[0]],
        reverse=True,
    )

    return {
        "customer_requirements": customer_requirements,
        "technical_requirements": technical_requirements,
        "absolute_importance": [round(ai, 2) for ai in abs_importance],
        "relative_importance_pct": rel_importance,
        "priority_ranking": [
            {"rank": rank + 1, "technical_req": name, "abs_importance": round(abs_importance[idx], 2)}
            for rank, (idx, name) in enumerate(ranked)
        ],
        "correlation_matrix": correlation_matrix,
    }


def kano_classify(
    features: List[Dict[str, str]],
) -> Dict[str, Any]:
    """
    Kano model classification of customer requirements.

    Parameters
    ----------
    features : list of dicts:
        - "feature": name
        - "functional": response when present ("like" | "expect" | "neutral" | "tolerate" | "dislike")
        - "dysfunctional": response when absent (same scale)

    Returns
    -------
    dict with each feature classified as:
        Must-Be (M), One-Dimensional (O), Attractive (A),
        Indifferent (I), Reverse (R), Questionable (Q)
    """
    # Kano evaluation table (functional × dysfunctional)
    _KANO = {
        ("like", "like"): "Q",
        ("like", "expect"): "A",
        ("like", "neutral"): "A",
        ("like", "tolerate"): "A",
        ("like", "dislike"): "O",
        ("expect", "like"): "R",
        ("expect", "expect"): "I",
        ("expect", "neutral"): "I",
        ("expect", "tolerate"): "I",
        ("expect", "dislike"): "M",
        ("neutral", "like"): "R",
        ("neutral", "expect"): "I",
        ("neutral", "neutral"): "I",
        ("neutral", "tolerate"): "I",
        ("neutral", "dislike"): "M",
        ("tolerate", "like"): "R",
        ("tolerate", "expect"): "I",
        ("tolerate", "neutral"): "I",
        ("tolerate", "tolerate"): "I",
        ("tolerate", "dislike"): "M",
        ("dislike", "like"): "R",
        ("dislike", "expect"): "R",
        ("dislike", "neutral"): "R",
        ("dislike", "tolerate"): "R",
        ("dislike", "dislike"): "Q",
    }

    LABELS = {
        "M": "Must-Be",
        "O": "One-Dimensional",
        "A": "Attractive",
        "I": "Indifferent",
        "R": "Reverse",
        "Q": "Questionable",
    }

    results = []
    counts = {k: 0 for k in LABELS}
    for f in features:
        func = f.get("functional", "neutral").lower()
        dysfunc = f.get("dysfunctional", "neutral").lower()
        code = _KANO.get((func, dysfunc), "Q")
        counts[code] += 1
        results.append({
            "feature": f.get("feature", ""),
            "classification": LABELS[code],
            "code": code,
        })

    return {
        "features": results,
        "distribution": {LABELS[k]: v for k, v in counts.items()},
    }
