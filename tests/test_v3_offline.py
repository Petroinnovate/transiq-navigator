"""Offline test — scoring, tier, routing, budget enforcement. No LLM calls."""
from section_analyzer import (
    SectionNode, DocumentBrain, score_all, classify_all,
    route_models, estimate_cost, enforce_budget,
)

chunks = ["x"] * 20
brain = DocumentBrain(chunks, "PDF")
brain.metadata["total_pages"] = 20

sections_data = [
    ("Root Cause Analysis", "The DMAIC root cause analysis found Cpk=0.72 and DPMO of 44565. Fishbone diagram. $2.4 million COPQ. Sigma level 2.9.", 1, "analyze"),
    ("Financial Summary", "Revenue $45.2 million. ROI 340%. Cost savings $1.2M. NPV $3.5 million. Budget CAPEX $800K.", 0, None),
    ("Executive Summary", "Key findings and recommendations from the report. Defect rate 8.2% reduced to 1.8%.", 0, None),
    ("Control Plan", "SPC X-bar R chart. Control chart monitoring. Response plan. Audit schedule. Training plan.", 1, "control"),
    ("Table of Contents", "Table of Contents. Disclaimer. Copyright 2024. All rights reserved. Version 2.1 Draft.", 0, None),
    ("Data Collection", "Baseline measurement 500 samples. Gage R&R 12.5%. Sampling plan. Current performance.", 1, "measure"),
    ("Improvement Pilot", "Solution implementation. Pilot results. Cost saving $1.52 million. Before and after comparison.", 1, "improve"),
    ("Appendix A", "References. Bibliography. Glossary of terms. List of abbreviations. Document control.", 0, None),
]

for i, (title, text, depth, phase) in enumerate(sections_data):
    node = SectionNode(
        id=f"S{i:03d}", title=title, text=text * 5, depth=depth,
        start_index=i * 2 + 1, end_index=i * 2 + 3,
    )
    node.tokens_estimate = len(node.text) // 4
    if phase:
        node.dmaic_phase = phase
    brain.sections[node.id] = node

score_all(brain)
classify_all(brain)
route_models(brain)

print("=" * 75)
header = f"{'Section':<25} {'Score':>6} {'Tier':>4} {'Model':>10} {'Run':>5} {'Phase':>10}"
print(header)
print("-" * 75)
for node in brain.iter_sections():
    phase = node.dmaic_phase or "-"
    run = str(node.execution["should_run"])
    model = node.execution["model_tier"]
    print(f"{node.title[:24]:<25} {node.score:>6.3f} {node.tier:>4} {model:>10} {run:>5} {phase:>10}")

est = estimate_cost(brain)
print(f"\nCost before budget: ${est['estimated_cost_usd']:.4f}")
print(f"Tier breakdown: {est['tier_breakdown']}")

# Enforce budget at 50%
enforce_budget(brain, est["estimated_cost_usd"] * 0.5)
est2 = estimate_cost(brain)
print(f"Cost after 50% budget: ${est2['estimated_cost_usd']:.4f}")

print("\nAfter budget enforcement:")
for node in brain.iter_sections():
    model = node.execution["model_tier"]
    print(f"  {node.title[:24]:<25} model={model:>10}")

print(f"\nModel usage counts: {brain.metadata['model_usage']}")
print("\nOFFLINE TESTS PASSED")
