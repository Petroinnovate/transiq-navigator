"""Quick test of the Six Sigma engine."""
import json
from features.six_sigma import run_six_sigma

test_kpis = [
    {"id": "kpi_001", "title": "ROP Average", "value": 45.2, "unit": "ft/hr", "target": 60.0,
     "category": "operations", "trend": "deteriorating", "confidence": 0.85,
     "financialImpactScore": 75, "riskScore": 65, "changeType": "negative"},
    {"id": "kpi_002", "title": "NPT Rate", "value": 8.5, "unit": "%", "target": 5.0,
     "category": "efficiency", "trend": "deteriorating", "confidence": 0.90,
     "financialImpactScore": 85, "riskScore": 80, "changeType": "negative"},
    {"id": "kpi_003", "title": "Mud Weight", "value": 12.3, "unit": "ppg", "target": 12.0,
     "category": "operations", "trend": "stable", "confidence": 0.95,
     "financialImpactScore": 40, "riskScore": 30, "changeType": "neutral"},
    {"id": "kpi_004", "title": "TRIR", "value": 0.85, "unit": "", "target": 0.5,
     "category": "safety", "trend": "improving", "confidence": 0.80,
     "financialImpactScore": 70, "riskScore": 75, "changeType": "positive"},
    {"id": "kpi_005", "title": "Cost Per Foot", "value": 380, "unit": "$/ft", "target": 300,
     "category": "financial", "trend": "deteriorating", "confidence": 0.88,
     "financialImpactScore": 90, "riskScore": 70, "changeType": "negative"},
    {"id": "kpi_006", "title": "Uptime", "value": 92.5, "unit": "%", "target": 98.0,
     "category": "reliability", "trend": "deteriorating", "confidence": 0.92,
     "financialImpactScore": 80, "riskScore": 60, "changeType": "negative"},
]

result = run_six_sigma(test_kpis)

print(f"Sigma Level: {result['sigmaLevel']}")
print(f"Process Capability: {result['processCapability']}")
print(f"CTQs: {len(result['ctq'])}")
print(f"Root Causes: {len(result['rootCauses'])}")
print(f"Data Quality Grade: {result['dataQuality']['grade']}")
print()

print("--- CTQs ---")
for c in result["ctq"]:
    print(f"  {c['name']}: fin={c['financialImpactScore']}, risk={c['riskScore']}")

print()
print("--- Root Causes ---")
for rc in result["rootCauses"]:
    print(f"  [{rc['severity']}] {rc['cause'][:90]}")

print()
print("--- DMAIC Define ---")
print(f"  {result['dmaic']['define']['problemStatement']}")

print()
print("--- Capability per metric ---")
for m in result["capability"]["perMetric"]:
    print(f"  {m['metric']}: Cpk={m['cpk']}, sigma={m['sigmaLevel']}, {m['status']}")

print()
print("--- Full JSON (compact) ---")
print(json.dumps(result, indent=2, default=str)[:3000])
