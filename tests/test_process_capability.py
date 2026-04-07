"""Tests for transiq.process_capability."""
import pytest
from transiq.process_capability import (
    cp, cpk, cpu, cpl, pp, ppk,
    sigma_level, sigma_with_shift,
    dpmo, dpmo_from_sigma, sigma_from_dpmo,
    yield_percent, capability_summary,
)


class TestCpCpk:
    def test_cp_equals_1_when_spread_equals_tolerance(self):
        # If USL-LSL = 6σ, then Cp = 1.0
        assert abs(cp(10.0, 4.0, 1.0) - 1.0) < 1e-10

    def test_cp_doubles_with_half_sigma(self):
        assert abs(cp(10.0, 4.0, 0.5) - 2.0) < 1e-10

    def test_cpk_centered_equals_cp(self):
        # Centered process: mean = (USL+LSL)/2
        c = cpk(10.0, 4.0, 7.0, 1.0)
        c_ref = cp(10.0, 4.0, 1.0)
        assert abs(c - c_ref) < 1e-10

    def test_cpk_shifted_less_than_cp(self):
        c_p = cp(10.0, 4.0, 1.0)
        c_pk = cpk(10.0, 4.0, 8.0, 1.0)  # shifted toward USL
        assert c_pk < c_p

    def test_cpu(self):
        assert abs(cpu(10.0, 7.0, 1.0) - 1.0) < 1e-10

    def test_cpl(self):
        assert abs(cpl(4.0, 7.0, 1.0) - 1.0) < 1e-10


class TestPpPpk:
    def test_pp_with_std(self):
        # Pp uses overall std dev (not within-subgroup)
        assert abs(pp(10.0, 4.0, 1.0) - 1.0) < 1e-10

    def test_ppk(self):
        p = ppk(10.0, 4.0, 7.0, 1.0)
        assert abs(p - 1.0) < 1e-10


class TestSigmaLevel:
    def test_sigma_from_cpk_1(self):
        # Cpk=1.0 → sigma_level = 3.0
        s = sigma_level(1.0)
        assert abs(s - 3.0) < 1e-10

    def test_sigma_from_cpk_2(self):
        # Cpk=2.0 → sigma_level = 6.0
        s = sigma_level(2.0)
        assert abs(s - 6.0) < 1e-10

    def test_sigma_with_shift(self):
        # Cpk=1.0 → base sigma=3.0 + 1.5 shift = 4.5
        s = sigma_with_shift(1.0)
        assert abs(s - 4.5) < 1e-10


class TestDPMO:
    def test_dpmo_from_fraction(self):
        # fraction_defective=0.01 → dpmo=10000
        d = dpmo(0.01)
        assert abs(d - 10000.0) < 1e-6

    def test_dpmo_from_sigma_6(self):
        d = dpmo_from_sigma(6.0)
        assert abs(d - 3.4) < 1.0  # 6σ ≈ 3.4 DPMO

    def test_sigma_from_dpmo_round_trip(self):
        d = dpmo_from_sigma(4.0)
        s = sigma_from_dpmo(d)
        assert abs(s - 4.0) < 0.1


class TestYield:
    def test_yield_from_high_sigma(self):
        # sigma=6 → yield ≈ 99.99966%
        y = yield_percent(6.0)
        assert y > 99.99

    def test_yield_from_sigma_3(self):
        # sigma=3 → yield depends on implementation (one-sided ~93.3%)
        y = yield_percent(3.0)
        assert y > 90.0 and y < 100.0


class TestCapabilitySummary:
    def test_summary_keys(self):
        data = [10.1, 10.0, 9.9, 10.2, 9.8, 10.05, 9.95, 10.1, 10.0, 9.9]
        s = capability_summary(data, 10.5, 9.5)
        assert "Cp" in s
        assert "Cpk" in s
        assert "sigma_short_term" in s
        assert "DPMO" in s
