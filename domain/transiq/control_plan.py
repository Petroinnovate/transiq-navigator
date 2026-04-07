"""
Control Plan templates and checklists.

Covers ASQ Handbook Chapter 22: Control Plans and Statistical Process Control Plans.

Provides structured templates for creating DMAIC Control phase documentation.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def create_control_plan(
    process_name: str,
    items: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Create a structured control plan.

    Parameters
    ----------
    process_name : name of the process being controlled
    items : list of control plan items, each with:
        - "characteristic": what is being controlled (CTQ)
        - "specification": target specification with limits
        - "measurement_method": how to measure
        - "sample_size": how many to measure
        - "frequency": how often to measure
        - "control_method": chart type or monitoring tool
        - "reaction_plan": what to do when out of control
        - "responsible": who is responsible
    """
    return {
        "process_name": process_name,
        "items": items,
        "total_items": len(items),
        "revision": "1.0",
        "status": "Draft",
    }


def reaction_plan(
    out_of_control_signal: str,
    immediate_actions: List[str],
    containment: str,
    root_cause_method: str,
    escalation: str,
    verification: str,
) -> Dict[str, Any]:
    """
    Create a reaction plan for when a control chart signal is triggered.
    """
    return {
        "signal": out_of_control_signal,
        "immediate_actions": immediate_actions,
        "containment": containment,
        "root_cause_method": root_cause_method,
        "escalation": escalation,
        "verification": verification,
    }


def control_checklist(
    items: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Generate a control phase completion checklist.

    Parameters
    ----------
    items : list of dicts with:
        - "item": checklist item description
        - "completed": bool
        - "notes": optional notes
    """
    total = len(items)
    completed = sum(1 for i in items if i.get("completed", False))

    return {
        "items": items,
        "total": total,
        "completed": completed,
        "pct_complete": round(completed / total * 100, 1) if total > 0 else 0.0,
    }


# Standard control plan template items for manufacturing
MANUFACTURING_TEMPLATE = [
    {
        "characteristic": "Dimension A",
        "specification": "10.0 ± 0.1 mm",
        "measurement_method": "CMM / Caliper",
        "sample_size": 5,
        "frequency": "Every hour",
        "control_method": "X̄-R Chart",
        "reaction_plan": "Stop production, inspect last batch, adjust tool",
        "responsible": "Quality Inspector",
    },
    {
        "characteristic": "Surface Finish",
        "specification": "Ra ≤ 1.6 μm",
        "measurement_method": "Profilometer",
        "sample_size": 3,
        "frequency": "Every 2 hours",
        "control_method": "I-MR Chart",
        "reaction_plan": "Check tool wear, replace if needed",
        "responsible": "Machine Operator",
    },
    {
        "characteristic": "Defect Count",
        "specification": "≤ 2 defects/unit",
        "measurement_method": "Visual inspection",
        "sample_size": 50,
        "frequency": "Per shift",
        "control_method": "c Chart",
        "reaction_plan": "Pareto analysis on defect types, address top cause",
        "responsible": "Quality Engineer",
    },
]

# Standard control plan template for Oil & Gas operations
OIL_GAS_TEMPLATE = [
    {
        "characteristic": "Mud Weight",
        "specification": "Target ± 0.3 ppg",
        "measurement_method": "Mud balance",
        "sample_size": 1,
        "frequency": "Every 30 min during circulation",
        "control_method": "I-MR Chart",
        "reaction_plan": "Adjust mud mix, notify Drilling Supervisor",
        "responsible": "Mud Engineer",
    },
    {
        "characteristic": "ROP",
        "specification": "≥ 30 ft/hr (formation dependent)",
        "measurement_method": "EDR system",
        "sample_size": 1,
        "frequency": "Continuous / hourly average",
        "control_method": "I-MR Chart",
        "reaction_plan": "Review WOB/RPM, check bit condition",
        "responsible": "Driller",
    },
    {
        "characteristic": "NPT Rate",
        "specification": "≤ 5% per 24h period",
        "measurement_method": "DDR timeline analysis",
        "sample_size": 1,
        "frequency": "Daily",
        "control_method": "p Chart (per-rig)",
        "reaction_plan": "Root cause investigation on NPT events",
        "responsible": "Operations Manager",
    },
    {
        "characteristic": "TRIR",
        "specification": "≤ 0.50",
        "measurement_method": "HSE incident reporting",
        "sample_size": 1,
        "frequency": "Monthly cumulative",
        "control_method": "I-MR Chart",
        "reaction_plan": "Safety stand-down, investigate incidents",
        "responsible": "HSE Manager",
    },
]
