#!/usr/bin/env python3
"""
example_spc.py — Demonstrates SPC control chart analysis with TransIQ.

Computes X-bar R chart limits and runs Nelson rule checks on subgroup data.
Uses the transiq library based on the ASQ Green Belt Handbook.
"""
from transiq.spc_charts import xbar_r_limits, imr_limits, nelson_rules

# --- Subgroup data (5 samples per subgroup, 8 subgroups) ---
subgroups = [
    [25.0, 26.1, 24.8, 25.5, 25.2],
    [25.3, 25.7, 24.9, 25.1, 25.4],
    [26.0, 25.8, 25.5, 25.9, 25.7],
    [24.5, 25.0, 24.8, 24.7, 25.1],
    [25.2, 25.4, 25.1, 25.3, 25.0],
    [25.6, 25.8, 25.5, 25.7, 25.9],
    [25.0, 25.2, 25.1, 24.9, 25.3],
    [25.4, 25.3, 25.5, 25.2, 25.6],
]

# --- X-bar R chart ---
result = xbar_r_limits(subgroups)
print("=== X-bar R Chart ===")
print(f"X-bar CL  = {result['Xbar_CL']:.4f}")
print(f"X-bar UCL = {result['Xbar_UCL']:.4f}")
print(f"X-bar LCL = {result['Xbar_LCL']:.4f}")
print(f"R-bar CL  = {result['R_CL']:.4f}")
print(f"R-bar UCL = {result['R_UCL']:.4f}")
print(f"R-bar LCL = {result['R_LCL']:.4f}")
print(f"σ̂ (estimated) = {result['sigma_hat']:.4f}")
print()

# --- Individual measurements with I-MR chart ---
individuals = [25.1, 25.3, 25.0, 25.4, 25.2, 25.6, 25.1, 25.3,
               25.5, 25.2, 25.4, 25.0, 25.3, 25.1, 25.5]
imr = imr_limits(individuals)
print("=== I-MR Chart ===")
print(f"I CL  = {imr['I_CL']:.4f}")
print(f"I UCL = {imr['I_UCL']:.4f}")
print(f"I LCL = {imr['I_LCL']:.4f}")
print(f"MR CL = {imr['MR_CL']:.4f}")
print()

# --- Nelson rule checks ---
violations = nelson_rules(
    individuals,
    cl=imr['I_CL'],
    ucl=imr['I_UCL'],
    lcl=imr['I_LCL'],
)
if violations:
    print("=== Nelson Rule Violations ===")
    for v in violations:
        print(f"  {v['rule']}: {v['description']} at indices {v['indices']}")
else:
    print("No Nelson rule violations detected — process appears in control.")
