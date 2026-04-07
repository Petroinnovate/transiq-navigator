"""
End-to-end integration tests for the Six Sigma analyze pipeline.

Tests the full chain: HTTP request → Pydantic validation → transiq computation
→ response serialisation → contract shape consistency.

Each test validates the LOCKED contract:
  { analysis_type, inputs, metrics, chart_data, warnings, recommendations }
"""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from transiq.api.analyze import router

# Isolated test app (no auth, no DB)
_app = FastAPI()
_app.include_router(router, prefix="/api/v2")
client = TestClient(_app)

URL = "/api/v2/six-sigma/analyze"

TOP_KEYS = {"analysis_type", "inputs", "metrics", "chart_data", "warnings", "recommendations"}


# ── Helpers ───────────────────────────────────────────────────────────────

def _ok(payload: dict) -> dict:
    """POST and assert 200, return body."""
    resp = client.post(URL, json=payload)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert set(body.keys()) == TOP_KEYS
    return body


def _fail(payload: dict, code: int = 422) -> dict:
    """POST and assert expected error status."""
    resp = client.post(URL, json=payload)
    assert resp.status_code == code, f"Expected {code}, got {resp.status_code}: {resp.text}"
    return resp.json()


# ═══════════════════════════════════════════════════════════════════════════
# 1. Contract stability — shape never changes
# ═══════════════════════════════════════════════════════════════════════════

class TestContractShape:
    PAYLOAD = {"data": [2, 4, 4, 4, 5, 5, 7, 9], "usl": 10, "lsl": 0}

    def test_top_level_keys(self):
        body = _ok(self.PAYLOAD)
        assert set(body.keys()) == TOP_KEYS

    def test_metrics_keys(self):
        body = _ok(self.PAYLOAD)
        expected = {
            "n", "mean", "std_dev", "cp", "cpk", "cpu", "cpl",
            "sigma_short_term", "sigma_long_term", "dpmo", "yield_pct",
            "fraction_defective", "sigma_level",
        }
        assert set(body["metrics"].keys()) == expected

    def test_chart_data_keys(self):
        body = _ok(self.PAYLOAD)
        expected = {"values", "cl", "ucl", "lcl", "mr_cl", "mr_ucl", "usl", "lsl"}
        assert set(body["chart_data"].keys()) == expected

    def test_warnings_are_list_of_violations(self):
        body = _ok(self.PAYLOAD)
        assert isinstance(body["warnings"], list)
        for w in body["warnings"]:
            assert {"rule", "description", "indices", "severity"} <= set(w.keys())

    def test_recommendations_are_list_of_strings(self):
        body = _ok(self.PAYLOAD)
        assert isinstance(body["recommendations"], list)
        for r in body["recommendations"]:
            assert isinstance(r, str)


# ═══════════════════════════════════════════════════════════════════════════
# 2. Metric accuracy — transiq computation is correct
# ═══════════════════════════════════════════════════════════════════════════

class TestMetricAccuracy:
    def test_mean_is_correct(self):
        body = _ok({"data": [2, 4, 6, 8, 10], "usl": 12, "lsl": 0})
        assert body["metrics"]["mean"] == pytest.approx(6.0, abs=0.001)

    def test_cp_centred_process(self):
        """σ provided → Cp = (USL-LSL)/(6σ)."""
        body = _ok({"data": [5, 5, 5], "usl": 10, "lsl": 0, "sigma": 1.0})
        # Cp = 10/6 = 1.6667
        assert body["metrics"]["cp"] == pytest.approx(1.6667, abs=0.01)

    def test_cpk_centred_equals_cp(self):
        """When mean is exactly centred, Cpk ≈ Cp."""
        body = _ok({"data": [5, 5, 5], "usl": 10, "lsl": 0, "sigma": 1.0})
        assert body["metrics"]["cpk"] == pytest.approx(body["metrics"]["cp"], abs=0.01)

    def test_cpk_shifted_less_than_cp(self):
        """Off-centre process → Cpk < Cp."""
        body = _ok({"data": [8, 8, 8], "usl": 10, "lsl": 0, "sigma": 1.0})
        assert body["metrics"]["cpk"] < body["metrics"]["cp"]

    def test_sigma_level_from_ppm(self):
        """PPM = 3.4 → ~6σ."""
        body = _ok({"data": [5, 5, 5], "usl": 10, "lsl": 0, "ppm": 3.4})
        assert body["metrics"]["sigma_level"] is not None
        assert body["metrics"]["sigma_level"] == pytest.approx(6.0, abs=0.3)

    def test_dpmo_low_for_capable_process(self):
        """Tight data → very low DPMO."""
        body = _ok({"data": [5.0, 5.01, 4.99, 5.0, 5.0, 5.01, 4.99, 5.0], "usl": 10, "lsl": 0})
        assert body["metrics"]["dpmo"] < 10

    def test_yield_high_for_capable_process(self):
        body = _ok({"data": [5.0, 5.01, 4.99, 5.0, 5.0, 5.01, 4.99, 5.0], "usl": 10, "lsl": 0})
        assert body["metrics"]["yield_pct"] > 99.99

    def test_cpu_cpl_symmetry_when_centred(self):
        body = _ok({"data": [5, 5, 5], "usl": 10, "lsl": 0, "sigma": 1.0})
        assert body["metrics"]["cpu"] == pytest.approx(body["metrics"]["cpl"], abs=0.01)

    def test_fraction_defective_consistent_with_dpmo(self):
        body = _ok({"data": [2, 4, 4, 4, 5, 5, 7, 9], "usl": 10, "lsl": 0})
        m = body["metrics"]
        # DPMO = fraction_defective * 1_000_000
        assert m["dpmo"] == pytest.approx(m["fraction_defective"] * 1_000_000, rel=0.01)


# ═══════════════════════════════════════════════════════════════════════════
# 3. Chart data — IMR limits are plausible
# ═══════════════════════════════════════════════════════════════════════════

class TestChartData:
    def test_values_echo_input(self):
        data = [1.0, 2.0, 3.0, 4.0, 5.0]
        body = _ok({"data": data, "usl": 10, "lsl": 0})
        assert body["chart_data"]["values"] == data

    def test_ucl_above_cl_above_lcl(self):
        body = _ok({"data": [2, 4, 4, 4, 5, 5, 7, 9], "usl": 10, "lsl": 0})
        cd = body["chart_data"]
        assert cd["ucl"] > cd["cl"] > cd["lcl"]

    def test_spec_limits_echo(self):
        body = _ok({"data": [1, 2, 3, 4], "usl": 20, "lsl": 5})
        assert body["chart_data"]["usl"] == 20
        assert body["chart_data"]["lsl"] == 5

    def test_mr_ucl_positive(self):
        body = _ok({"data": [1, 3, 5, 7, 2, 8], "usl": 10, "lsl": 0})
        assert body["chart_data"]["mr_ucl"] > 0


# ═══════════════════════════════════════════════════════════════════════════
# 4. Warnings and recommendations
# ═══════════════════════════════════════════════════════════════════════════

class TestWarningsAndRecs:
    def test_high_spread_triggers_not_capable_rec(self):
        body = _ok({"data": [0, 2, 4, 6, 8, 10, 0, 10], "usl": 10, "lsl": 0})
        assert any("not capable" in r.lower() for r in body["recommendations"])

    def test_marginal_cpk_recommendation(self):
        """Cpk between 1.0 and 1.33 → marginal warning."""
        # sigma chosen to get Cpk ≈ 1.1
        body = _ok({"data": [5, 5, 5], "usl": 10, "lsl": 0, "sigma": 1.5})
        # Cpk = min((10-5),(5-0))/(3*1.5) = 5/4.5 ≈ 1.11
        recs = body["recommendations"]
        assert any("marginal" in r.lower() for r in recs)

    def test_spc_violations_detected(self):
        """Data with an outlier should trigger Rule 1."""
        body = _ok({"data": [5, 5, 5, 5, 5, 5, 5, 100], "usl": 200, "lsl": 0})
        violations = body["warnings"]
        assert len(violations) > 0
        assert any("Rule 1" in v["rule"] for v in violations)

    def test_no_warnings_for_stable_process(self):
        """Constant data → no violations (but also cp=0 due to zero std)."""
        body = _ok({"data": [5, 5, 5, 5, 5, 5, 5, 5, 5, 5], "usl": 10, "lsl": 0})
        # All identical → IMR has sigma=0, so ucl=lcl=cl=5 → no out-of-control
        assert body["warnings"] == []


# ═══════════════════════════════════════════════════════════════════════════
# 5. Input echo — inputs block mirrors what was sent
# ═══════════════════════════════════════════════════════════════════════════

class TestInputEcho:
    def test_full_inputs(self):
        body = _ok({"data": [1, 2, 3], "usl": 20, "lsl": 5, "sigma": 2.0, "ppm": 100})
        inp = body["inputs"]
        assert inp["usl"] == 20
        assert inp["lsl"] == 5
        assert inp["sigma_provided"] == 2.0
        assert inp["ppm_provided"] == 100
        assert inp["n"] == 3

    def test_default_inputs(self):
        body = _ok({"data": [1, 2, 3]})
        inp = body["inputs"]
        assert inp["usl"] == 10.0
        assert inp["lsl"] == 0.0
        assert inp["sigma_provided"] is None
        assert inp["ppm_provided"] is None


# ═══════════════════════════════════════════════════════════════════════════
# 6. Validation — bad inputs rejected
# ═══════════════════════════════════════════════════════════════════════════

class TestValidation:
    def test_empty_data(self):
        _fail({"data": [], "usl": 10, "lsl": 0}, 422)

    def test_usl_below_lsl(self):
        _fail({"data": [1, 2, 3], "usl": 5, "lsl": 10}, 422)

    def test_usl_equals_lsl(self):
        _fail({"data": [1, 2, 3], "usl": 5, "lsl": 5}, 422)

    def test_null_in_data(self):
        _fail({"data": [1, None, 3], "usl": 10, "lsl": 0}, 422)

    def test_missing_data_field(self):
        _fail({"usl": 10, "lsl": 0}, 422)

    def test_negative_sigma_rejected(self):
        _fail({"data": [1, 2, 3], "sigma": -1}, 422)

    def test_negative_ppm_rejected(self):
        _fail({"data": [1, 2, 3], "ppm": -1}, 422)


# ═══════════════════════════════════════════════════════════════════════════
# 7. Edge cases
# ═══════════════════════════════════════════════════════════════════════════

class TestEdgeCases:
    def test_single_value(self):
        body = _ok({"data": [5.0], "usl": 10, "lsl": 0})
        m = body["metrics"]
        assert m["mean"] == 5.0
        assert m["cp"] == 0.0
        assert m["cpk"] == 0.0

    def test_two_values(self):
        body = _ok({"data": [4.0, 6.0], "usl": 10, "lsl": 0})
        assert body["metrics"]["n"] == 2
        assert body["metrics"]["mean"] == pytest.approx(5.0)

    def test_identical_values(self):
        body = _ok({"data": [5.0, 5.0, 5.0, 5.0], "usl": 10, "lsl": 0})
        assert body["metrics"]["std_dev"] == 0.0
        assert body["metrics"]["cp"] == 0.0

    def test_200_points(self):
        data = [5.0 + (i % 10) * 0.1 for i in range(200)]
        body = _ok({"data": data, "usl": 10, "lsl": 0})
        assert body["metrics"]["n"] == 200
        assert body["chart_data"]["cl"] > 0

    def test_very_wide_spec(self):
        body = _ok({"data": [50, 51, 49, 50], "usl": 1000, "lsl": 0, "sigma": 1.0})
        assert body["metrics"]["cp"] > 100  # extremely capable

    def test_all_at_usl(self):
        """All data at USL boundary — off-centre."""
        body = _ok({"data": [10, 10, 10], "usl": 10, "lsl": 0, "sigma": 1.0})
        assert body["metrics"]["cpk"] == pytest.approx(0.0, abs=0.01)
        assert body["metrics"]["cpl"] > body["metrics"]["cpu"]
