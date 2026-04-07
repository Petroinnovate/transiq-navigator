"""Tests for POST /api/v2/six-sigma/analyze — locked contract."""
import pytest
from fastapi.testclient import TestClient
from transiq.api.analyze import router
from fastapi import FastAPI

app = FastAPI()
app.include_router(router, prefix="/api/v2")
client = TestClient(app)

URL = "/api/v2/six-sigma/analyze"

# ── Stable response shape ────────────────────────────────────────────────

TOP_KEYS = {"analysis_type", "inputs", "metrics", "chart_data", "warnings", "recommendations"}
METRIC_KEYS = {
    "n", "mean", "std_dev", "cp", "cpk", "cpu", "cpl",
    "sigma_short_term", "sigma_long_term", "dpmo", "yield_pct",
    "fraction_defective", "sigma_level",
}
CHART_KEYS = {"values", "cl", "ucl", "lcl", "mr_cl", "mr_ucl", "usl", "lsl"}


def _post(payload: dict) -> dict:
    resp = client.post(URL, json=payload)
    return {"status": resp.status_code, "body": resp.json()}


# ── Contract shape tests ─────────────────────────────────────────────────

def test_response_has_all_top_level_keys():
    r = _post({"data": [2, 4, 4, 4, 5, 5, 7, 9], "usl": 10, "lsl": 0})
    assert r["status"] == 200
    assert set(r["body"].keys()) == TOP_KEYS


def test_metrics_block_keys():
    r = _post({"data": [2, 4, 4, 4, 5, 5, 7, 9], "usl": 10, "lsl": 0})
    assert set(r["body"]["metrics"].keys()) == METRIC_KEYS


def test_chart_data_keys():
    r = _post({"data": [2, 4, 4, 4, 5, 5, 7, 9], "usl": 10, "lsl": 0})
    assert set(r["body"]["chart_data"].keys()) == CHART_KEYS


def test_analysis_type_is_process_capability():
    r = _post({"data": [5, 5, 5], "usl": 10, "lsl": 0})
    assert r["body"]["analysis_type"] == "process_capability"


# ── Metric correctness ───────────────────────────────────────────────────

def test_basic_analysis():
    r = _post({"data": [2, 4, 4, 4, 5, 5, 7, 9], "usl": 10, "lsl": 0})
    assert r["status"] == 200
    m = r["body"]["metrics"]
    assert m["mean"] == pytest.approx(5.0, abs=0.01)
    assert m["n"] == 8
    assert m["std_dev"] > 0
    assert m["sigma_level"] is None  # no ppm provided


def test_with_ppm():
    r = _post({"data": [5, 5, 5], "usl": 10, "lsl": 0, "ppm": 3.4})
    m = r["body"]["metrics"]
    assert m["sigma_level"] is not None
    assert m["sigma_level"] > 0


def test_with_known_sigma():
    r = _post({"data": [5, 5, 5], "usl": 10, "lsl": 0, "sigma": 1.5})
    m = r["body"]["metrics"]
    # cp = (10-0)/(6*1.5) = 1.111...
    assert m["cp"] == pytest.approx(1.1111, abs=0.01)


def test_defaults():
    r = _post({"data": [3, 4, 5, 6, 7]})
    assert r["status"] == 200
    m = r["body"]["metrics"]
    assert m["mean"] == pytest.approx(5.0, abs=0.01)


def test_capable_process():
    """Tight data around centre → high Cpk, high yield, low DPMO."""
    r = _post({"data": [4.9, 5.0, 5.1, 5.0, 4.95, 5.05, 5.0, 5.02], "usl": 10, "lsl": 0})
    m = r["body"]["metrics"]
    assert m["cpk"] > 2.0
    assert m["yield_pct"] > 99.99
    assert m["dpmo"] < 10


# ── Chart / warnings / recommendations ───────────────────────────────────

def test_chart_values_echo_input():
    data = [1.0, 2.0, 3.0, 4.0, 5.0]
    r = _post({"data": data, "usl": 10, "lsl": 0})
    assert r["body"]["chart_data"]["values"] == data
    assert r["body"]["chart_data"]["usl"] == 10.0
    assert r["body"]["chart_data"]["lsl"] == 0.0


def test_warnings_list_present():
    r = _post({"data": [2, 4, 4, 4, 5, 5, 7, 9], "usl": 10, "lsl": 0})
    assert isinstance(r["body"]["warnings"], list)
    # this dataset triggers rule violations
    assert len(r["body"]["warnings"]) > 0
    first = r["body"]["warnings"][0]
    assert "rule" in first and "indices" in first and "severity" in first


def test_recommendations_for_low_cpk():
    """Data with high spread → low Cpk → recommendation generated."""
    r = _post({"data": [0, 2, 4, 6, 8, 10, 0, 10], "usl": 10, "lsl": 0})
    recs = r["body"]["recommendations"]
    assert any("not capable" in rec.lower() or "cpk" in rec.lower() for rec in recs)


def test_inputs_echo():
    r = _post({"data": [1, 2, 3], "usl": 20, "lsl": 5, "sigma": 2.0, "ppm": 100})
    inp = r["body"]["inputs"]
    assert inp["usl"] == 20
    assert inp["lsl"] == 5
    assert inp["sigma_provided"] == 2.0
    assert inp["ppm_provided"] == 100


# ── Validation / error cases ─────────────────────────────────────────────

def test_empty_data_rejected():
    r = _post({"data": [], "usl": 10, "lsl": 0})
    assert r["status"] == 422


def test_usl_must_exceed_lsl():
    r = _post({"data": [1, 2, 3], "usl": 5, "lsl": 10})
    assert r["status"] == 422


def test_null_in_data_rejected():
    r = _post({"data": [1, None, 3], "usl": 10, "lsl": 0})
    assert r["status"] == 422


# ── Edge cases ───────────────────────────────────────────────────────────

def test_single_value():
    r = _post({"data": [5.0], "usl": 10, "lsl": 0})
    assert r["status"] == 200
    m = r["body"]["metrics"]
    assert m["mean"] == 5.0
    assert m["cp"] == 0.0
    assert m["cpk"] == 0.0


def test_two_values():
    r = _post({"data": [4.0, 6.0], "usl": 10, "lsl": 0})
    assert r["status"] == 200
    m = r["body"]["metrics"]
    assert m["n"] == 2
    assert m["mean"] == pytest.approx(5.0)


def test_identical_values():
    r = _post({"data": [5.0, 5.0, 5.0, 5.0], "usl": 10, "lsl": 0})
    assert r["status"] == 200
    m = r["body"]["metrics"]
    assert m["std_dev"] == 0.0
    assert m["cp"] == 0.0


def test_large_dataset():
    data = [5.0 + (i % 10) * 0.1 for i in range(200)]
    r = _post({"data": data, "usl": 10, "lsl": 0})
    assert r["status"] == 200
    assert r["body"]["metrics"]["n"] == 200
