"""
TransIQ — Six Sigma Toolkit
============================

A comprehensive Python implementation of Six Sigma methodologies based on the
*ASQ Certified Six Sigma Green Belt Handbook* (Second Edition, 2015).

Modules
-------
statistics          Descriptive stats, distributions (normal, Poisson, binomial)
process_capability  Cp, Cpk, Pp, Ppk, sigma level, yield, DPMO
spc_charts          Control charts (X̄-R, X̄-S, p, np, c, u) and run rules
hypothesis          z-test, t-test, paired-t, chi², F-test, one-way ANOVA
regression          Linear regression, Pearson r, R², residual analysis
doe                 Full/fractional factorial design, ANOVA, main effects
msa                 Measurement System Analysis — Gauge R&R (ANOVA method)
lean_tools          OEE, Takt time, cycle time, waste identification, Kaizen
fmea                FMEA Risk Priority Number (RPN) calculation and ranking
project             Project charter, SIPOC, stakeholder analysis
voc                 Voice of Customer capture, CTQ tree, QFD (House of Quality)
control_plan        Control plan templates, reaction plans
utils               Shared constants, SPC factors, combinatorics, helpers
"""

__version__ = "0.1.0"
__author__ = "TransIQ Team"

from transiq.process_capability import cp, cpk, pp, ppk, sigma_level, dpmo, yield_percent
from transiq.statistics import mean, variance, std_dev, cdf_normal, pdf_normal
from transiq.spc_charts import xbar_r_limits, xbar_s_limits, p_chart_limits, c_chart_limits
from transiq.hypothesis import z_test, t_test_one_sample, anova_oneway
from transiq.regression import linear_regression, pearson_r
from transiq.doe import full_factorial_design
from transiq.msa import gage_rr_anova
from transiq.lean_tools import calculate_oee
from transiq.fmea import compute_rpn

__all__ = [
    # process_capability
    "cp", "cpk", "pp", "ppk", "sigma_level", "dpmo", "yield_percent",
    # statistics
    "mean", "variance", "std_dev", "cdf_normal", "pdf_normal",
    # spc_charts
    "xbar_r_limits", "xbar_s_limits", "p_chart_limits", "c_chart_limits",
    # hypothesis
    "z_test", "t_test_one_sample", "anova_oneway",
    # regression
    "linear_regression", "pearson_r",
    # doe
    "full_factorial_design",
    # msa
    "gage_rr_anova",
    # lean
    "calculate_oee",
    # fmea
    "compute_rpn",
]
