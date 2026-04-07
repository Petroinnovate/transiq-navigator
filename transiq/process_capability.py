"""
Process Capability indices and sigma-level conversions.

Covers ASQ Handbook Chapter 15: Process Capability.

Cp  = (USL - LSL) / (6σ)          — potential capability (centred process)
Cpk = min(Cpu, Cpl)               — actual capability (accounts for shift)
Pp  = (USL - LSL) / (6s)          — performance (long-term σ)
Ppk = min(Ppu, Ppl)               — performance accounting for shift
DPMO = defects per million opportunities
Sigma Level = Z-bench + 1.5 shift (industry convention)
Yield = 1 - fraction nonconforming
"""
from __future__ import annotations

import math
from typing import List, Optional, Tuple

from transiq.statistics import cdf_normal, inverse_normal, mean as _mean, std_dev as _std
from transiq.utils import validate_numeric, validate_positive


# ---------------------------------------------------------------------------
# Core capability indices
# ---------------------------------------------------------------------------

def cp(usl: float, lsl: float, std_dev: float) -> float:
    """
    Process Capability Index Cp = (USL - LSL) / (6σ).

    Measures potential capability assuming process is centred.
    Cp ≥ 1.0 means specification spread covers at least ±3σ.
    """
    validate_positive(std_dev, "std_dev")
    return (usl - lsl) / (6.0 * std_dev)


def cpk(usl: float, lsl: float, mean: float, std_dev: float) -> float:
    """
    Process Capability Index Cpk = min(Cpu, Cpl).

    Cpu = (USL - μ) / (3σ)
    Cpl = (μ - LSL) / (3σ)

    Accounts for process centering.  Cpk ≤ Cp always.
    World-class: Cpk ≥ 2.0.
    """
    validate_positive(std_dev, "std_dev")
    cpu = (usl - mean) / (3.0 * std_dev)
    cpl = (mean - lsl) / (3.0 * std_dev)
    return min(cpu, cpl)


def cpu(usl: float, mean: float, std_dev: float) -> float:
    """Upper capability: Cpu = (USL - μ) / (3σ)."""
    validate_positive(std_dev, "std_dev")
    return (usl - mean) / (3.0 * std_dev)


def cpl(lsl: float, mean: float, std_dev: float) -> float:
    """Lower capability: Cpl = (μ - LSL) / (3σ)."""
    validate_positive(std_dev, "std_dev")
    return (mean - lsl) / (3.0 * std_dev)


def pp(usl: float, lsl: float, std_dev_overall: float) -> float:
    """
    Process Performance Index Pp = (USL - LSL) / (6s).

    Uses overall (long-term) standard deviation s instead of within-subgroup σ.
    """
    validate_positive(std_dev_overall, "std_dev_overall")
    return (usl - lsl) / (6.0 * std_dev_overall)


def ppk(usl: float, lsl: float, mean: float, std_dev_overall: float) -> float:
    """
    Process Performance Index Ppk = min(Ppu, Ppl).

    Uses overall (long-term) standard deviation.
    """
    validate_positive(std_dev_overall, "std_dev_overall")
    ppu = (usl - mean) / (3.0 * std_dev_overall)
    ppl = (mean - lsl) / (3.0 * std_dev_overall)
    return min(ppu, ppl)


# ---------------------------------------------------------------------------
# Sigma level & defect rate conversions
# ---------------------------------------------------------------------------

def sigma_level(cpk_value: float) -> float:
    """
    Approximate sigma level from Cpk (short-term).

    σ_level = 3 × Cpk  (bench capability)

    Industry convention adds 1.5σ shift for long-term estimate:
      σ_long_term ≈ 3 × Cpk + 1.5
    """
    return 3.0 * cpk_value


def sigma_with_shift(cpk_value: float, shift: float = 1.5) -> float:
    """
    Long-term sigma level = 3 × Cpk + shift.

    The 1.5σ shift is the industry standard (Motorola convention).
    """
    return 3.0 * cpk_value + shift


def dpmo(fraction_defective: float) -> float:
    """
    Convert fraction defective to Defects Per Million Opportunities.

    DPMO = fraction_defective × 1,000,000
    """
    if fraction_defective < 0 or fraction_defective > 1:
        raise ValueError(f"fraction_defective must be in [0, 1], got {fraction_defective}")
    return fraction_defective * 1_000_000


def dpmo_from_sigma(sigma: float) -> float:
    """
    DPMO from sigma level (accounting for 1.5σ shift).

    P(defect) = P(Z > sigma - 1.5) + P(Z < -(sigma - 1.5))
              ≈ 2 × Φ(-(sigma - 1.5))  for symmetric tails
    """
    z = sigma - 1.5
    tail = 1.0 - cdf_normal(z, 0.0, 1.0)
    return tail * 1_000_000


def sigma_from_dpmo(dpmo_value: float) -> float:
    """
    Convert DPMO to sigma level (with 1.5σ shift).

    z = Φ⁻¹(1 - DPMO/1e6)
    σ = z + 1.5
    """
    if dpmo_value <= 0 or dpmo_value >= 1_000_000:
        raise ValueError(f"DPMO must be in (0, 1000000), got {dpmo_value}")
    p = 1.0 - dpmo_value / 1_000_000
    z = inverse_normal(p)
    return z + 1.5


def yield_percent(sigma: float) -> float:
    """
    Process yield (%) from sigma level, accounting for 1.5σ shift.

    Yield = Φ(σ - 1.5) × 100
    """
    z = sigma - 1.5
    return cdf_normal(z, 0.0, 1.0) * 100.0


def fraction_defective_from_spec(
    usl: float, lsl: float, mean: float, std_dev: float
) -> float:
    """
    Total fraction defective (both tails) given process parameters.

    P(out of spec) = P(X > USL) + P(X < LSL)
    """
    validate_positive(std_dev, "std_dev")
    p_upper = 1.0 - cdf_normal(usl, mean, std_dev)
    p_lower = cdf_normal(lsl, mean, std_dev)
    return p_upper + p_lower


# ---------------------------------------------------------------------------
# Convenience: compute all capability indices from raw data
# ---------------------------------------------------------------------------

def capability_summary(
    data: List[float],
    usl: float,
    lsl: float,
    ddof: int = 1,
) -> dict:
    """
    Compute a full capability summary from raw measurement data.

    Returns dict with: mean, std_dev, Cp, Cpk, Cpu, Cpl, Pp, Ppk,
    sigma_level, DPMO, yield_pct, fraction_defective.
    """
    vals = validate_numeric(data, "data", min_len=2)
    n = len(vals)
    mu = _mean(vals)
    s = _std(vals, ddof=ddof)

    cp_val = cp(usl, lsl, s)
    cpk_val = cpk(usl, lsl, mu, s)
    sigma_short = sigma_level(cpk_val)
    sigma_long = sigma_with_shift(cpk_val)
    frac_def = fraction_defective_from_spec(usl, lsl, mu, s)

    return {
        "n": n,
        "mean": round(mu, 6),
        "std_dev": round(s, 6),
        "Cp": round(cp_val, 4),
        "Cpk": round(cpk_val, 4),
        "Cpu": round((usl - mu) / (3.0 * s), 4),
        "Cpl": round((mu - lsl) / (3.0 * s), 4),
        "sigma_short_term": round(sigma_short, 2),
        "sigma_long_term": round(sigma_long, 2),
        "DPMO": round(dpmo(frac_def), 1),
        "yield_pct": round((1.0 - frac_def) * 100, 4),
        "fraction_defective": round(frac_def, 8),
    }
