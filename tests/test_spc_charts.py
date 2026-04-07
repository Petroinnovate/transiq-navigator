"""Tests for transiq.spc_charts."""
import pytest
from domain.transiq.spc_charts import (
    xbar_r_limits, xbar_s_limits, imr_limits,
    p_chart_limits, np_chart_limits, c_chart_limits, u_chart_limits,
    western_electric_rules, nelson_rules,
)
from domain.transiq.utils import A2_TABLE, D3_TABLE, D4_TABLE


class TestXbarRChart:
    def test_basic(self):
        subgroups = [[25, 26, 24], [27, 25, 26], [24, 25, 25]]
        result = xbar_r_limits(subgroups)
        assert "Xbar_CL" in result
        assert "Xbar_UCL" in result
        assert "Xbar_LCL" in result
        assert "R_CL" in result
        assert "R_UCL" in result
        assert result["Xbar_UCL"] > result["Xbar_CL"]
        assert result["Xbar_LCL"] < result["Xbar_CL"]

    def test_known_values(self):
        # n=5, A2=0.577, D3=0, D4=2.114
        subgroups = [[10]*5 for _ in range(5)]  # identical values
        result = xbar_r_limits(subgroups)
        assert result["R_CL"] == 0.0
        assert result["Xbar_CL"] == 10.0


class TestXbarSChart:
    def test_basic(self):
        subgroups = [[25, 26, 24], [27, 25, 26], [24, 25, 25]]
        result = xbar_s_limits(subgroups)
        assert "Xbar_UCL" in result
        assert "S_CL" in result
        assert "S_UCL" in result


class TestIMRChart:
    def test_basic(self):
        data = [10.1, 10.0, 9.9, 10.2, 9.8, 10.3, 10.0, 9.7]
        result = imr_limits(data)
        assert "I_CL" in result
        assert "I_UCL" in result
        assert "MR_CL" in result
        assert result["I_UCL"] > result["I_CL"]

    def test_constant_data(self):
        data = [5.0] * 10
        result = imr_limits(data)
        assert result["MR_CL"] == 0.0


class TestAttributeCharts:
    def test_p_chart(self):
        defectives = [3, 5, 2, 4, 6]
        sample_sizes = [100, 100, 100, 100, 100]
        result = p_chart_limits(defectives, sample_sizes)
        assert "p_bar" in result
        assert result["p_bar"] == 0.04
        # UCL is a list for p-chart (variable sample sizes)
        assert "UCL" in result

    def test_np_chart(self):
        defectives = [3, 5, 2, 4, 6]
        result = np_chart_limits(defectives, 100)
        assert "np_bar" in result
        assert result["UCL"] > result["np_bar"]

    def test_c_chart(self):
        counts = [3, 5, 2, 4, 6, 3, 4, 5]
        result = c_chart_limits(counts)
        assert "c_bar" in result
        assert result["UCL"] > result["c_bar"]

    def test_u_chart(self):
        counts = [3, 5, 2, 4, 6]
        areas = [10, 10, 10, 10, 10]
        result = u_chart_limits(counts, areas)
        assert "u_bar" in result


class TestWesternElectricRules:
    def test_rule1_beyond_3sigma(self):
        data = [10.0] * 10
        data[5] = 100.0  # way beyond UCL
        cl, ucl, lcl = 10.0, 11.5, 8.5
        violations = western_electric_rules(data, cl, ucl, lcl)
        rule1_points = [v for v in violations if "Rule 1" in str(v["rule"])]
        assert len(rule1_points) > 0

    def test_no_violations(self):
        data = [10.0] * 20
        cl, ucl, lcl = 10.0, 25.0, -5.0
        violations = western_electric_rules(data, cl, ucl, lcl)
        assert len(violations) == 0


class TestNelsonRules:
    def test_rule1(self):
        data = [10.0] * 10
        data[5] = 100.0
        cl, ucl, lcl = 10.0, 11.5, 8.5
        violations = nelson_rules(data, cl, ucl, lcl)
        rule1 = [v for v in violations if "Rule 1" in str(v["rule"])]
        assert len(rule1) > 0

    def test_consecutive_same_side(self):
        # 9 consecutive points above mean → triggers Rule 4 (8 consecutive same side)
        data = [11.0] * 9 + [9.0]
        cl, ucl, lcl = 10.0, 25.0, -5.0
        violations = nelson_rules(data, cl, ucl, lcl)
        rule4 = [v for v in violations if "Rule 4" in str(v["rule"])]
        assert len(rule4) > 0


class TestSPCFactors:
    def test_a2_factors_exist(self):
        for n in range(2, 26):
            assert n in A2_TABLE

    def test_d3_d4_factors(self):
        assert D3_TABLE[2] == 0.0
        assert abs(D4_TABLE[2] - 3.267) < 0.001
