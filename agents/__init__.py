"""
TransIQ Multi-Agent Decision OS
================================
Eight specialized agents that chain together to produce board-grade intelligence.
"""
from .orchestrator import AgentOrchestrator
from .base_agent import BaseAgent
from .outcome_agent import OutcomeIntelligenceAgent

__all__ = ["AgentOrchestrator", "BaseAgent", "OutcomeIntelligenceAgent"]
