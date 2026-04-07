"""
Agent Orchestrators — **adaptive AI decision flow**.

BOUNDARY RULE:
  | Layer                   | Role                           |
  |-------------------------|--------------------------------|
  | pipelines/orchestration | Deterministic system flow      |
  | agents/orchestrators    | Adaptive AI decision flow      |

  - Pipelines = DEFAULT execution path (data movement, sequencing)
  - Agents = OVERRIDE / intelligence layer (reasoning, judgment)
  - Example: pipeline runs → agent modifies pipeline behavior

These orchestrators chain decision_agents/ for LLM-based reasoning.
Pipelines should never be called FROM agents. Agents are called BY pipelines
(or directly by API endpoints) when adaptive reasoning is needed.
"""
from agents.orchestrators.orchestrator import AgentOrchestrator
from agents.orchestrators.fixed_orchestrator import FixedAgentOrchestrator
from agents.orchestrators.godmode_agent import GodModeAgent

__all__ = ["AgentOrchestrator", "FixedAgentOrchestrator", "GodModeAgent"]
