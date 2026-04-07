"""
Project Management tools — Charter, SIPOC, Stakeholder Analysis.

Covers ASQ Handbook Chapters 4, 6: Project Identification, Management & Planning.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def create_project_charter(
    project_name: str,
    problem_statement: str,
    goal: str,
    scope: str,
    *,
    business_case: str = "",
    team: Optional[List[Dict[str, str]]] = None,
    timeline: Optional[Dict[str, str]] = None,
    metrics: Optional[List[str]] = None,
    constraints: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Create a Six Sigma project charter.

    A project charter formally authorises the project and defines its boundaries.
    """
    return {
        "project_name": project_name,
        "problem_statement": problem_statement,
        "goal": goal,
        "scope": scope,
        "business_case": business_case,
        "team": team or [],
        "timeline": timeline or {
            "define": "",
            "measure": "",
            "analyze": "",
            "improve": "",
            "control": "",
        },
        "metrics": metrics or [],
        "constraints": constraints or [],
        "status": "Draft",
    }


def generate_sipoc(
    process_name: str,
    suppliers: List[str],
    inputs: List[str],
    process_steps: List[str],
    outputs: List[str],
    customers: List[str],
) -> Dict[str, Any]:
    """
    Generate a SIPOC diagram data structure.

    SIPOC = Suppliers → Inputs → Process → Outputs → Customers
    Used in the Define phase to scope the process at a high level.
    """
    return {
        "process_name": process_name,
        "S": suppliers,
        "I": inputs,
        "P": process_steps,
        "O": outputs,
        "C": customers,
    }


def stakeholder_analysis(
    stakeholders: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Classify stakeholders by influence and interest.

    Parameters
    ----------
    stakeholders : list of dicts with:
        - "name": stakeholder name/role
        - "influence": 1–5 (power to affect project)
        - "interest": 1–5 (level of concern)
        - "attitude": "supporter" | "neutral" | "resistor"

    Returns
    -------
    dict with stakeholders classified into 4 quadrants:
        - Manage Closely (high influence, high interest)
        - Keep Satisfied (high influence, low interest)
        - Keep Informed (low influence, high interest)
        - Monitor (low influence, low interest)
    """
    quadrants = {
        "Manage Closely": [],
        "Keep Satisfied": [],
        "Keep Informed": [],
        "Monitor": [],
    }

    for sh in stakeholders:
        inf = sh.get("influence", 3)
        interest = sh.get("interest", 3)

        if inf >= 3 and interest >= 3:
            quadrants["Manage Closely"].append(sh)
        elif inf >= 3 and interest < 3:
            quadrants["Keep Satisfied"].append(sh)
        elif inf < 3 and interest >= 3:
            quadrants["Keep Informed"].append(sh)
        else:
            quadrants["Monitor"].append(sh)

    return {
        "quadrants": quadrants,
        "total": len(stakeholders),
        "supporters": sum(1 for s in stakeholders if s.get("attitude") == "supporter"),
        "resistors": sum(1 for s in stakeholders if s.get("attitude") == "resistor"),
    }
