"""
Six Sigma Engine — Deterministic DMAIC analytics layer.

Wraps existing SPC engine, KPI engine, and graph analytics to produce
structured Six Sigma output (CTQs, Cp/Cpk, sigma level, root causes)
WITHOUT relying on LLM text generation.

Modules:
  analyzer      - Main SixSigmaAnalyzer orchestrator
  ctq_mapper    - CTQ extraction from KPI pool
  capability    - Process capability (Cp/Cpk/DPMO) via spc_engine
  root_cause    - Deterministic root-cause analysis
  spc_wrapper   - Thin adapter around ddr.spc_engine
  insights      - Structured insight generation from sigma results
"""

from .analyzer import SixSigmaAnalyzer, run_six_sigma

__all__ = [
    "SixSigmaAnalyzer",
    "run_six_sigma",
]
