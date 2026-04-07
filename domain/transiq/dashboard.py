#!/usr/bin/env python3
"""
dashboard.py - Six Sigma TransIQ Dashboard presentation helpers.

This module is for **display / formatting** only.
All actual computations live in transiq.process_capability, transiq.statistics,
transiq.spc_charts, etc.  The API endpoint (transiq.api.analyze) calls those
modules directly and never imports from here.
"""

from domain.transiq import statistics
from domain.transiq import spc_charts
from domain.transiq import process_capability


def compute_metrics(
    data: list[float],
    usl: float = 10.0,
    lsl: float = 0.0,
    sigma: float | None = None,
    ppm: float | None = None,
) -> dict[str, float]:
    """
    Quick convenience helper — thin wrapper around transiq modules.

    Kept for backward compatibility with dashboard scripts and existing tests.
    For full analysis use :func:`transiq.api.analyze._compute` instead.
    """
    if not data:
        raise ValueError("data must not be empty")

    mu = statistics.mean(data)
    if sigma is not None:
        s = sigma
    elif len(data) > 1:
        s = statistics.std_dev(data, ddof=1)
    else:
        s = 0.0

    metrics: dict[str, float] = {"mean": mu}

    if s > 0:
        metrics["cp"] = process_capability.cp(usl, lsl, s)
        metrics["cpk"] = process_capability.cpk(usl, lsl, mu, s)
    else:
        metrics["cp"] = 0.0
        metrics["cpk"] = 0.0

    if ppm is not None and ppm > 0:
        metrics["sigma_level"] = process_capability.sigma_from_dpmo(ppm)

    return metrics


def format_capability_report(metrics: dict) -> str:
    """Format a metrics dict as a human-readable summary string."""
    lines = ["═══ Process Capability Report ═══"]
    for key in ("n", "mean", "std_dev", "Cp", "Cpk", "Cpu", "Cpl",
                "sigma_short_term", "sigma_long_term", "DPMO", "yield_pct"):
        if key in metrics:
            lines.append(f"  {key:20s}: {metrics[key]}")
    return "\n".join(lines)


def main() -> None:
    """CLI dashboard entry point."""
    data = [1, 2, 3, 4, 5]
    metrics = compute_metrics(data)
    chart = spc_charts.xbar_r_limits([[1, 2], [3, 4], [5, 6]])
    print(format_capability_report({"mean": metrics["mean"], "Cp": metrics["cp"], "Cpk": metrics["cpk"]}))
    print(f"\nX-bar R chart: CL={chart['Xbar_CL']:.4f}, "
          f"UCL={chart['Xbar_UCL']:.4f}, LCL={chart['Xbar_LCL']:.4f}")


if __name__ == "__main__":
    main()
