#!/usr/bin/env python3
"""
example_analysis.py — Demonstrates TransIQ capability analysis on sample data.

Shows how to compute process capability (Cp/Cpk), sigma level, and DPMO
using the transiq library based on the ASQ Green Belt Handbook.
"""
from transiq.process_capability import cp, cpk, sigma_level, dpmo_from_sigma
from transiq.statistics import mean, std_dev, cdf_normal

# --- Sample process data ---
data = [7.2, 7.5, 7.8, 7.1, 7.6, 7.4, 7.3, 7.7, 7.5, 7.2,
        7.6, 7.3, 7.8, 7.4, 7.5, 7.1, 7.6, 7.7, 7.3, 7.5]
USL, LSL = 8.5, 6.5

# --- Descriptive stats ---
mu = mean(data)
sigma = std_dev(data, ddof=1)
print(f"Mean    = {mu:.4f}")
print(f"Std Dev = {sigma:.4f}")
print(f"n       = {len(data)}")
print()

# --- Capability ---
Cp = cp(USL, LSL, sigma)
Cpk = cpk(USL, LSL, mu, sigma)
sig = sigma_level(Cpk)
d = dpmo_from_sigma(sig)

print(f"Cp      = {Cp:.4f}")
print(f"Cpk     = {Cpk:.4f}")
print(f"Sigma   = {sig:.2f}")
print(f"DPMO    = {d:.1f}")
print()

# --- Interpretation ---
if Cpk >= 2.0:
    print("World Class — exceeds 6σ benchmarks")
elif Cpk >= 1.33:
    print("Capable — meets typical industry requirements")
elif Cpk >= 1.0:
    print("Marginal — just meets minimum specification")
else:
    print("Not Capable — process improvement needed")
