"""
ESG Engine — Environmental, Social & Governance Scoring
========================================================

Auto-classifies KPIs into ESG pillars and computes 0-100 scores per pillar.
All calculations are deterministic — no LLM calls.

Key functions:
  classify_kpi_esg(kpi)           → adds 'esg_pillars' list to kpi
  compute_esg_scores(kpis)        → returns ESG scorecard dict
  compute_carbon_cost(kpis)       → estimates carbon cost in $
  build_esg_view(kpis)            → full ESG dashboard view
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Keyword classifiers (case-insensitive regex)
# ---------------------------------------------------------------------------

_ENV_KEYWORDS = re.compile(
    r"\b(co2|carbon|emission|ghg|methane|flare|spill|effluent|waste|energy|fuel|"
    r"power|water|consumption|renewabl|solar|wind|biodiversity|pollution|air|noise)\b",
    re.IGNORECASE,
)

_SOCIAL_KEYWORDS = re.compile(
    r"\b(trir|ltir|fatality|injury|incident|near.?miss|safety|health|training|"
    r"workforce|employee|community|diversity|inclusion|wellbeing|contractor|"
    r"consultation|grievance|human.?rights|labour|labor)\b",
    re.IGNORECASE,
)

_GOV_KEYWORDS = re.compile(
    r"\b(compliance|audit|regulatory|reporting|disclosure|transparency|board|"
    r"governance|policy|procedure|risk.?management|anti.?corruption|bribery|"
    r"iso|api|osha|epa|sec|code.?of.?conduct)\b",
    re.IGNORECASE,
)

# Risk direction keywords
_NEGATIVE_KEYWORDS = re.compile(
    r"\b(increase|high|above|exceed|breach|deteriorat|decline|spike|incident|fail)\b",
    re.IGNORECASE,
)
_POSITIVE_KEYWORDS = re.compile(
    r"\b(decreas|reduc|improv|below|target|achiev|comply|meet)\b",
    re.IGNORECASE,
)

# Carbon price (USD per tonne CO2e) — update as market changes
_CARBON_PRICE_PER_TONNE = 25.0

# CO2 identifiers in KPI title/unit
_CO2_UNIT_PATTERN = re.compile(r"\b(co2|ghg|carbon|tonne|ton|mtco2)\b", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Individual KPI ESG classification
# ---------------------------------------------------------------------------

def classify_kpi_esg(kpi: Dict[str, Any]) -> Dict[str, Any]:
    """
    Add 'esg_pillars' and 'esg_primary_pillar' fields to a KPI dict.
    Returns the modified copy.
    """
    k = dict(kpi)
    text = " ".join([
        str(k.get("title") or ""),
        str(k.get("description") or ""),
        str(k.get("category") or ""),
        str(k.get("unit") or ""),
    ])

    pillars: List[str] = []
    if _ENV_KEYWORDS.search(text):
        pillars.append("environmental")
    if _SOCIAL_KEYWORDS.search(text):
        pillars.append("social")
    if _GOV_KEYWORDS.search(text):
        pillars.append("governance")

    k["esg_pillars"] = pillars
    k["esg_primary_pillar"] = pillars[0] if pillars else None
    k["esg_relevant"] = len(pillars) > 0
    return k


# ---------------------------------------------------------------------------
# ESG score computation
# ---------------------------------------------------------------------------

def _kpi_esg_signal(kpi: Dict[str, Any]) -> float:
    """
    Return a -1 (bad) to +1 (good) performance signal for ESG scoring.
    Negative trend = worse ESG performance.
    """
    trend = (kpi.get("trend") or "").lower()
    ct = (kpi.get("changeType") or "").lower()
    desc = str(kpi.get("description") or "")

    if trend in ("improving", "up") or ct == "positive":
        return 1.0
    if trend in ("deteriorating", "down") or ct == "negative":
        return -1.0
    if _POSITIVE_KEYWORDS.search(desc):
        return 0.5
    if _NEGATIVE_KEYWORDS.search(desc):
        return -0.5
    return 0.0


def compute_esg_scores(kpis: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Compute ESG pillar scores (0-100) from classified KPIs.

    Score interpretation:
      80-100: Strong ESG performance
      60-79:  Adequate
      40-59:  Needs improvement
      0-39:   Poor / at-risk
    """
    pillar_signals: Dict[str, List[float]] = {
        "environmental": [],
        "social": [],
        "governance": [],
    }

    classified = [classify_kpi_esg(k) for k in kpis]

    for kpi in classified:
        signal = _kpi_esg_signal(kpi)
        for pillar in (kpi.get("esg_pillars") or []):
            if pillar in pillar_signals:
                pillar_signals[pillar].append(signal)

    def _score(signals: List[float]) -> Optional[float]:
        if not signals:
            return None
        avg = sum(signals) / len(signals)  # range -1 to 1
        return round((avg + 1) / 2 * 100, 1)  # map to 0-100

    e = _score(pillar_signals["environmental"])
    s = _score(pillar_signals["social"])
    g = _score(pillar_signals["governance"])

    valid_scores = [x for x in [e, s, g] if x is not None]
    overall = round(sum(valid_scores) / len(valid_scores), 1) if valid_scores else None

    return {
        "environmental_score": e,
        "social_score": s,
        "governance_score": g,
        "overall_esg_score": overall,
        "kpis_classified": len([k for k in classified if k.get("esg_relevant")]),
        "total_kpis": len(kpis),
    }


# ---------------------------------------------------------------------------
# Carbon cost estimation
# ---------------------------------------------------------------------------

def compute_carbon_cost(kpis: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Estimate carbon cost from CO2/GHG-related KPIs.
    Looks for KPIs where unit or title suggests CO2 tonnes.
    """
    carbon_kpis: List[Dict] = []
    total_co2_tonnes = 0.0

    for kpi in kpis:
        unit = str(kpi.get("unit") or "")
        title = str(kpi.get("title") or "")
        combined = f"{title} {unit}"

        if _CO2_UNIT_PATTERN.search(combined):
            value = kpi.get("value")
            try:
                v = float(value)
                total_co2_tonnes += v
                carbon_kpis.append({
                    "title": title,
                    "value": v,
                    "unit": unit,
                    "carbon_cost_usd": round(v * _CARBON_PRICE_PER_TONNE, 2),
                })
            except (TypeError, ValueError):
                pass

    total_cost = round(total_co2_tonnes * _CARBON_PRICE_PER_TONNE, 2)

    return {
        "total_co2_tonnes_identified": round(total_co2_tonnes, 2),
        "carbon_cost_usd": total_cost,
        "carbon_price_per_tonne": _CARBON_PRICE_PER_TONNE,
        "contributing_kpis": carbon_kpis,
    }


# ---------------------------------------------------------------------------
# Full ESG view builder
# ---------------------------------------------------------------------------

def build_esg_view(kpis: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Build full ESG dashboard view from KPIs.
    Returns a self-contained ESG section ready for the frontend.
    """
    classified_kpis = [classify_kpi_esg(k) for k in kpis]
    scores = compute_esg_scores(kpis)
    carbon = compute_carbon_cost(kpis)

    env_kpis = [k for k in classified_kpis if "environmental" in (k.get("esg_pillars") or [])]
    social_kpis = [k for k in classified_kpis if "social" in (k.get("esg_pillars") or [])]
    gov_kpis = [k for k in classified_kpis if "governance" in (k.get("esg_pillars") or [])]

    def _summarize(kpi_list: List[Dict]) -> List[Dict]:
        return [
            {
                "id": k.get("id"),
                "title": k.get("title"),
                "value": k.get("value"),
                "unit": k.get("unit"),
                "trend": k.get("trend"),
                "changeType": k.get("changeType"),
            }
            for k in kpi_list[:10]
        ]

    esg_score = scores.get("overall_esg_score")
    if esg_score is None:
        rating = "Not Assessed"
    elif esg_score >= 80:
        rating = "Strong"
    elif esg_score >= 60:
        rating = "Adequate"
    elif esg_score >= 40:
        rating = "Needs Improvement"
    else:
        rating = "At Risk"

    return {
        "scores": scores,
        "rating": rating,
        "carbon": carbon,
        "environmental_kpis": _summarize(env_kpis),
        "social_kpis": _summarize(social_kpis),
        "governance_kpis": _summarize(gov_kpis),
        "all_classified_kpis": classified_kpis,
    }
