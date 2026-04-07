"""
Domain Glossary for TransIQ

Defines the authoritative set of domain terms used during glossary pre-filtering.
Each entry carries aliases for matching, a short prompt_hint for LLM injection,
and an always_include flag for structural backbone terms.
"""
from dataclasses import dataclass, field
from typing import List


@dataclass
class GlossaryEntry:
    term: str
    aliases: List[str]
    prompt_hint: str
    always_include: bool = False


# ---------------------------------------------------------------------------
# Authoritative domain glossary (~25 terms)
# ---------------------------------------------------------------------------

DOMAIN_GLOSSARY: dict[str, GlossaryEntry] = {

    # ── Six Sigma backbone (always injected) ────────────────────────────────
    "DMAIC": GlossaryEntry(
        term="DMAIC",
        aliases=["dmaic", "define measure analyze improve control"],
        prompt_hint="DMAIC: Six Sigma framework — Define, Measure, Analyze, Improve, Control",
        always_include=True,
    ),
    "sigma_level": GlossaryEntry(
        term="sigma level",
        aliases=["sigma level", "sigma", "σ level", "process sigma"],
        prompt_hint="sigma level: measure of process quality (6σ = 3.4 DPMO)",
        always_include=True,
    ),
    "DPMO": GlossaryEntry(
        term="DPMO",
        aliases=["dpmo", "defects per million opportunities", "defects per million"],
        prompt_hint="DPMO: defects per million opportunities — key Six Sigma metric",
        always_include=True,
    ),
    "process_capability": GlossaryEntry(
        term="process capability",
        aliases=["process capability", "cp", "cpk", "capability index"],
        prompt_hint="process capability (Cp/Cpk): ratio of spec width to process variation",
        always_include=True,
    ),

    # ── Financial ───────────────────────────────────────────────────────────
    "OPEX": GlossaryEntry(
        term="OPEX",
        aliases=["opex", "operating expenditure", "operating expense", "operational cost"],
        prompt_hint="OPEX: operating expenditure — recurring operational costs",
        always_include=False,
    ),
    "CAPEX": GlossaryEntry(
        term="CAPEX",
        aliases=["capex", "capital expenditure", "capital expense"],
        prompt_hint="CAPEX: capital expenditure — one-time investment costs",
        always_include=False,
    ),
    "ROI": GlossaryEntry(
        term="ROI",
        aliases=["roi", "return on investment", "return on invest"],
        prompt_hint="ROI: return on investment — (gain - cost) / cost × 100%",
        always_include=False,
    ),
    "NPV": GlossaryEntry(
        term="NPV",
        aliases=["npv", "net present value"],
        prompt_hint="NPV: net present value — present value of future cash flows minus investment",
        always_include=False,
    ),
    "profit_margin": GlossaryEntry(
        term="profit margin",
        aliases=["profit margin", "margin", "net margin", "gross margin"],
        prompt_hint="profit margin: (revenue - cost) / revenue × 100%",
        always_include=False,
    ),
    "cost_variance": GlossaryEntry(
        term="cost variance",
        aliases=["cost variance", "budget variance", "variance"],
        prompt_hint="cost variance: actual cost minus budgeted cost",
        always_include=False,
    ),

    # ── Operations / Drilling ────────────────────────────────────────────────
    "NPT": GlossaryEntry(
        term="NPT",
        aliases=["npt", "non-productive time", "non productive time", "downtime"],
        prompt_hint="NPT: non-productive time — rig time not advancing the well",
        always_include=False,
    ),
    "ROP": GlossaryEntry(
        term="ROP",
        aliases=["rop", "rate of penetration"],
        prompt_hint="ROP: rate of penetration — drilling speed in ft/hr or m/hr",
        always_include=False,
    ),
    "WOB": GlossaryEntry(
        term="WOB",
        aliases=["wob", "weight on bit"],
        prompt_hint="WOB: weight on bit — downward force applied while drilling",
        always_include=False,
    ),
    "BHA": GlossaryEntry(
        term="BHA",
        aliases=["bha", "bottom hole assembly", "bottomhole assembly"],
        prompt_hint="BHA: bottom hole assembly — drill string components at the bottom",
        always_include=False,
    ),
    "BOP": GlossaryEntry(
        term="BOP",
        aliases=["bop", "blowout preventer", "blow out preventer"],
        prompt_hint="BOP: blowout preventer — safety device on wellhead",
        always_include=False,
    ),
    "measured_depth": GlossaryEntry(
        term="measured depth",
        aliases=["measured depth", "md", "m depth"],
        prompt_hint="measured depth (MD): total drilled depth along wellbore path",
        always_include=False,
    ),

    # ── Safety / HSE ─────────────────────────────────────────────────────────
    "TRIR": GlossaryEntry(
        term="TRIR",
        aliases=["trir", "total recordable incident rate", "incident rate"],
        prompt_hint="TRIR: total recordable incident rate per 200,000 man-hours",
        always_include=False,
    ),
    "LTI": GlossaryEntry(
        term="LTI",
        aliases=["lti", "lost time injury", "lost-time incident"],
        prompt_hint="LTI: lost time injury — incident causing missed work days",
        always_include=False,
    ),
    "HSE": GlossaryEntry(
        term="HSE",
        aliases=["hse", "health safety environment", "health, safety and environment"],
        prompt_hint="HSE: health, safety and environment — operational safety framework",
        always_include=False,
    ),

    # ── Units ────────────────────────────────────────────────────────────────
    "bbl": GlossaryEntry(
        term="bbl",
        aliases=["bbl", "barrel", "barrels"],
        prompt_hint="bbl: barrel — standard unit of oil volume (159 litres)",
        always_include=False,
    ),
    "mcf": GlossaryEntry(
        term="mcf",
        aliases=["mcf", "thousand cubic feet", "mscf"],
        prompt_hint="mcf: thousand cubic feet — gas volume unit",
        always_include=False,
    ),
    "psi": GlossaryEntry(
        term="psi",
        aliases=["psi", "pounds per square inch"],
        prompt_hint="psi: pounds per square inch — pressure unit",
        always_include=False,
    ),

    # ── KPI classification ────────────────────────────────────────────────────
    "defect_rate": GlossaryEntry(
        term="defect rate",
        aliases=["defect rate", "defects", "defect %", "defective"],
        prompt_hint="defect rate: proportion of non-conforming units in total output",
        always_include=False,
    ),
    "utilization": GlossaryEntry(
        term="utilization",
        aliases=["utilization", "utilisation", "asset utilization", "rig utilization"],
        prompt_hint="utilization: actual productive time / total available time × 100%",
        always_include=False,
    ),
    "throughput": GlossaryEntry(
        term="throughput",
        aliases=["throughput", "production rate", "output rate"],
        prompt_hint="throughput: units produced per unit time — core efficiency KPI",
        always_include=False,
    ),
}
