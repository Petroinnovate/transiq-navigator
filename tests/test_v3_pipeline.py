"""Full pipeline test for v3 centralized architecture."""
import logging
import json
import time

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

from section_analyzer import generate_full_report_analysis

# Simulate a multi-page Six Sigma report
chunks = [
    """Project Charter - Define Phase
Problem Statement: Widget production line experiencing 8.2% defect rate, well above industry standard of 2%.
Project Scope: Main assembly line, Building A, shifts 1-3.
CTQ: Dimensional accuracy within +/- 0.05mm tolerance.
Voice of Customer: 47 complaints in Q3 about widget fit issues.
Financial Exposure: Estimated COPQ of $1.8 million annually from scrap, rework, and warranty claims.
Project Team: John (BB), Sarah (GB), Mike (Champion), Lisa (Process Owner).
Tollgate Review: Approved by steering committee on Jan 15.""",

    """Baseline Measurement - Measure Phase
Data Collection: 500 samples over 4 weeks from all 3 shifts.
Measurement System Analysis: Gage R&R = 12.5% (acceptable).
Baseline Sigma Level: 2.9 sigma (DPMO = 80,757).
Process Capability: Cpk = 0.72, Ppk = 0.68.
Key Metrics:
- Defect Rate: 8.2% (target: < 2%)
- Cycle Time: 45 sec/unit (target: 38 sec/unit)
- First Pass Yield: 91.8% (target: > 98%)
- Scrap Rate: 4.1% of total production
SIPOC Map: Supplier -> Input(steel rods) -> Process(cutting,forming,assembly) -> Output(widgets) -> Customer(OEMs).""",

    """Root Cause Analysis - Analyze Phase
Fishbone Diagram identified 23 potential causes across 6M categories.
Pareto Analysis: Top 3 causes account for 78% of defects:
1. Tool wear (42%) - cutting tools not replaced per schedule
2. Material variation (21%) - incoming steel hardness varies +/- 15%
3. Operator technique (15%) - inconsistent fixture clamping force

Statistical Analysis:
- ANOVA: Tool age vs defect rate, F=34.2, p<0.001 (significant)
- Regression: R-squared = 0.82, hardness explains 82% of dimensional variation
- Chi-square: Shift 2 defect rate significantly higher (p=0.003)
- Correlation: fixture pressure vs tolerance deviation r = -0.76

5-Why Analysis on tool wear:
Why 1: Tools not replaced -> Why 2: No tracking system -> Why 3: Manual logs lost
Why 4: No digital system -> Why 5: No budget allocated for tool management software.""",

    """Improvement Actions - Improve Phase
Solution 1: Implement digital tool life tracking system ($45,000 one-time)
- Expected impact: Reduce tool-wear defects by 85%
- Pilot results: Defect rate dropped from 8.2% to 3.1% in 2-week pilot

Solution 2: Incoming material inspection with hardness testing ($12,000/year)
- Expected impact: Reject out-of-spec material before production
- Pilot: 95% of hardness-related defects eliminated

Solution 3: Standardized clamping procedure with torque wrench ($8,000)
- Training completed for all 45 operators across 3 shifts
- Fixture-related defects reduced by 70% in pilot

Combined pilot results (4 weeks):
- Defect rate: 1.8% (from 8.2% - target achieved!)
- Sigma level improved from 2.9 to 3.6
- First Pass Yield: 98.2% (target: >98% - achieved!)
- Projected annual savings: $1.52 million""",

    """Control Plan - Control Phase
Statistical Process Control:
- X-bar and R charts for critical dimensions (hourly sampling, n=5)
- P-chart for defect rate (daily, all units)
- Alert threshold: 2 consecutive points outside 2-sigma

Control Plan Items:
1. Tool life monitoring: automated alerts at 80% tool life
2. Material inspection: 100% hardness testing on incoming lots
3. Operator certification: quarterly re-certification on clamping procedure
4. Monthly management review of SPC dashboard

Response Plan:
- Out of control signal -> Stop production -> Root cause -> Corrective action within 4 hours
- KPI dashboard updated real-time for shift supervisors

Sustainment:
- Training plan for new operators (2-day program)
- Annual process audit by Quality team
- Lessons learned documented in knowledge base""",

    """Executive Summary and Conclusions
This Six Sigma DMAIC project successfully reduced the widget defect rate from 8.2% to 1.8%,
achieving a sigma level improvement from 2.9 to 3.6.

Key Results:
- Defect rate: 8.2% -> 1.8% (78% reduction)
- Sigma level: 2.9 -> 3.6 (0.7 sigma lift)
- Annual savings: $1.52 million (ROI: 2,338% in year 1)
- First Pass Yield: 91.8% -> 98.2%
- Customer complaints: projected 75% reduction

Total investment: $65,000
Payback period: 16 days

Project completed on schedule. Control plan implemented and verified stable for 8 weeks.""",
]

print("=" * 60)
print("FULL PIPELINE TEST - 6-page Six Sigma Report")
print("=" * 60)

start = time.time()
dashboard = generate_full_report_analysis(
    chunks=chunks,
    num_files=1,
    source_type="PDF",
    progress_callback=lambda s, t, m: print(f"  [{s}/{t}] {m}"),
)
elapsed = time.time() - start

print()
print("=" * 60)
print(f"PIPELINE COMPLETE in {elapsed:.1f}s")
print("=" * 60)

meta = dashboard.get("meta", {})
print(f"Report ID: {meta.get('reportId', '?')}")
print(f"Confidence: {meta.get('confidenceOverall', '?')}")
print(f"Decision Readiness: {meta.get('decisionReadinessScore', '?')}")
print(f"Tiers Used: {meta.get('tiersUsed', {})}")
print(f"Model Usage: {meta.get('modelUsage', {})}")
print(f"Reprocessed: {meta.get('reprocessed', 0)}")
cost_est = meta.get("estimatedCost", {})
print(f"Est Cost: ${cost_est.get('estimated_cost_usd', '?')}")

dash = dashboard.get("dashboard", {})
print(f"Title: {dash.get('title', '?')}")
sections = dash.get("sections", [])
print(f"Sections: {len(sections)}")
for s in sections:
    t = s.get("tier", "?")
    m = s.get("modelUsed", "?")
    p = s.get("dmaicPhase", "?")
    title = s.get("title", "?")[:50]
    nk = len(s.get("kpis", []))
    nf = len(s.get("keyFindings", []))
    conf = s.get("confidence", 0)
    print(f"  [T{t}] [{m:>9s}] [{p:>10s}] {title} - {nk} KPIs, {nf} findings, {conf:.0%} conf")

kpis = dash.get("kpis", [])
print(f"\nTop KPIs: {len(kpis)}")
for k in kpis[:8]:
    print(f"  {k.get('title', '?')}: {k.get('value', '?')} {k.get('unit', '')}")

charts = dash.get("charts", [])
print(f"\nCharts: {len(charts)}")
for c in charts[:5]:
    print(f"  {c.get('type', '?')}: {c.get('title', '?')}")

ss = dash.get("sixSigma", {})
print(f"\nSigma Level: {ss.get('sigmaLevel', '?')}")
print(f"Defect Rate: {ss.get('defectRate', '?')}")
print(f"Process Capability: {ss.get('processCapability', '?')}")
dmaic = ss.get("dmaic", {})
if dmaic:
    for phase in ["define", "measure", "analyze", "improve", "control"]:
        pd = dmaic.get(phase, {})
        if pd:
            keys = list(pd.keys())[:3]
            print(f"  DMAIC.{phase}: {keys}")

# Cross-phase insights
cpi = meta.get("crossPhaseInsights", [])
print(f"\nCross-phase insights: {len(cpi)}")
for ci in cpi:
    print(f"  [{ci.get('type')}] {ci.get('insight', '')[:80]}")

insights = dash.get("insights", {})
print(f"\nAlerts: {len(insights.get('alerts', []))}")
print(f"Recommendations: {len(insights.get('recommendations', []))}")

# Optimization suggestions
opts = dash.get("optimizationSuggestions", [])
print(f"Optimization Suggestions: {len(opts)}")
for o in opts[:3]:
    print(f"  [{o.get('impact','?')}] {o.get('title','?')[:60]}")

print()
print("=" * 60)
print("FULL PIPELINE TEST PASSED" if sections else "WARNING: No sections in output")
print("=" * 60)

# Save full output for inspection
with open("test_v3_result.json", "w") as f:
    json.dump(dashboard, f, indent=2, default=str)
print("Full dashboard saved to test_v3_result.json")
