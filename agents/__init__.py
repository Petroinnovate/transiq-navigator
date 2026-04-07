"""
TransIQ Multi-Agent Decision OS
================================
Orchestrators chain decision agents to produce board-grade intelligence.

Architecture:
  agents/
  ├── orchestrators/      → Pipeline coordinators (call agents in sequence)
  ├── decision_agents/    → Domain-specific LLM agents (each does one job)
  └── base_agent.py       → Abstract base class
"""
from agents.orchestrators.orchestrator import AgentOrchestrator
from agents.orchestrators.fixed_orchestrator import FixedAgentOrchestrator
from agents.base_agent import BaseAgent
from agents.decision_agents.outcome_agent import OutcomeIntelligenceAgent

__all__ = [
    "AgentOrchestrator",
    "FixedAgentOrchestrator",
    "BaseAgent",
    "OutcomeIntelligenceAgent",
]
