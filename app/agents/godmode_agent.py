"""
Minimal GodMode-style agent loop for TransIQ.

This module intentionally keeps the implementation small and reuses existing
TransIQ agents and intelligence modules as callable tools.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Callable, Dict, List, Optional

from app.agents.decision_agent import DecisionIntelligenceAgent
from app.agents.dmaic_agent import DMAICAgent
from app.agents.outcome_agent import OutcomeIntelligenceAgent
from app.config.settings import settings
from app.intelligence.pipeline import run_pipeline
from app.kpi_engine.kpi_engine import process_kpis
from app.kpi_engine.whatif_engine import compare_scenarios, run_scenario
from app.llm.factory import LLMFactory

logger = logging.getLogger(__name__)


class GodModeAgent:
    """Lightweight autonomous agent loop for goal-oriented analysis."""

    def __init__(self, provider_name: Optional[str] = None, max_steps: int = 5):
        resolved_provider = provider_name
        if not resolved_provider:
            if settings.GEMINI_API_KEY:
                resolved_provider = "gemini"
            elif settings.OPENAI_API_KEY:
                resolved_provider = "openai"
            elif settings.GROK_API_KEY:
                resolved_provider = "grok"

        self.llm = LLMFactory.get_provider(resolved_provider)
        self.max_steps = max_steps
        self.tools = self._build_tool_registry()

    def _build_tool_registry(self) -> Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]]:
        return {
            "run_dmaic": self._wrap_tool(self._run_dmaic),
            "run_decision": self._wrap_tool(self._run_decision),
            "run_outcome": self._wrap_tool(self._run_outcome),
            "run_kpi": self._wrap_tool(self._run_kpi),
            "run_whatif": self._wrap_tool(self._run_whatif),
            "run_pipeline": self._wrap_tool(self._run_pipeline),
        }

    def _wrap_tool(self, tool_fn: Callable[[Dict[str, Any]], Dict[str, Any]]) -> Callable[[Dict[str, Any]], Dict[str, Any]]:
        def _wrapped(payload: Dict[str, Any]) -> Dict[str, Any]:
            if not isinstance(payload, dict):
                return {"error": "Tool input must be an object"}
            result = tool_fn(payload)
            if isinstance(result, dict):
                return result
            return {"result": result}

        return _wrapped

    def _run_agent_tool(self, agent_cls: type, payload: Dict[str, Any]) -> Dict[str, Any]:
        agent = agent_cls(llm_client=None)
        prompt = agent.build_prompt(payload)
        full_prompt = f"SYSTEM PROMPT:\n{agent._system_instruction()}\n\nUSER INPUT:\n{prompt}"
        try:
            result = self.llm.generate_json(full_prompt, temperature=0.15)
            return result if isinstance(result, dict) else {"result": result}
        except Exception as exc:
            logger.exception("GodMode tool %s failed", agent_cls.__name__)
            fallback = agent._fallback()
            fallback["error"] = str(exc)
            return fallback

    def _run_dmaic(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._run_agent_tool(DMAICAgent, payload)

    def _run_decision(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._run_agent_tool(DecisionIntelligenceAgent, payload)

    def _run_outcome(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._run_agent_tool(OutcomeIntelligenceAgent, payload)

    def _run_kpi(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        kpis = payload.get("kpis", [])
        if not isinstance(kpis, list):
            return {"error": "run_kpi expects {'kpis': [...]}"}
        return {"kpis": process_kpis(kpis)}

    def _run_whatif(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        kpis = payload.get("kpis", [])
        if not isinstance(kpis, list):
            return {"error": "run_whatif expects {'kpis': [...]}"}

        scenarios = payload.get("scenarios")
        if isinstance(scenarios, list):
            return {"scenarios": compare_scenarios(kpis, scenarios)}

        inputs = payload.get("inputs", {})
        if not isinstance(inputs, dict):
            return {"error": "run_whatif expects 'inputs' to be an object"}

        scenario_name = payload.get("scenario_name", "Custom Scenario")
        return run_scenario(kpis, inputs, scenario_name=scenario_name)

    def _run_pipeline(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        combined_content = (
            payload.get("combined_content")
            or payload.get("content")
            or payload.get("raw_content")
            or ""
        )
        if not isinstance(combined_content, str) or not combined_content.strip():
            return {"error": "run_pipeline expects text in 'combined_content', 'content', or 'raw_content'"}

        model_info = self.llm.get_model_info()
        if model_info.get("provider") != "gemini":
            return {"error": "run_pipeline currently requires the Gemini provider"}

        try:
            from google import genai

            client = genai.Client(api_key=self.llm.api_key)
            return run_pipeline(
                combined_content=combined_content,
                num_files=int(payload.get("num_files", 1)),
                source_type=str(payload.get("source_type", "UNKNOWN")),
                client=client,
                content_limit=int(payload.get("content_limit", 500_000)),
            )
        except Exception as exc:
            logger.exception("GodMode tool run_pipeline failed")
            return {"error": str(exc)}

    def _tool_list(self) -> str:
        return "\n".join(f"- {name}" for name in self.tools)

    def _build_planner_prompt(self, goal: str, memory: Dict[str, Any]) -> str:
        tool_list = self._tool_list()
        context_json = json.dumps(memory, default=str, ensure_ascii=True)[:20_000]
        return (
            "SYSTEM PROMPT:\n\n"
            '"You are an autonomous business analyst agent.\n'
            "You solve problems step-by-step using available tools.\n"
            "You may use at most one tool per step.\n"
            "Only choose an action from the available tools list exactly as written.\n"
            "Never invent tool names, arguments, or tool results.\n"
            "If the current evidence is sufficient, set final to true and return the result.\n"
            "If more evidence is needed, set final to false and choose the single best next tool.\n"
            "Always respond as a single JSON object and never use markdown.\n"
            "Use one of these two schemas exactly:\n"
            '{"thought":"short reasoning","action":"tool_name","input":{},"final":false}\n'
            '{"thought":"short reasoning","final":true,"result":{}}\n\n'
            f"Available tools:\n{tool_list}\n\n"
            "Previous step results are available in Context.steps. Reuse them instead of repeating work.\n"
            "Decide the next best action to achieve the goal.\n\n"
            "USER INPUT:\n\n"
            f"Goal: {goal}\n"
            f"Context: {context_json}"
        )

    def run(self, goal: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        steps: List[Dict[str, Any]] = []
        memory: Dict[str, Any] = {
            "goal": goal,
            "context": context if isinstance(context, dict) else {},
            "steps": [],
        }

        for step_index in range(self.max_steps):
            prompt = self._build_planner_prompt(goal, memory)
            try:
                decision = self.llm.generate_json(prompt, temperature=0.2)
            except Exception as exc:
                logger.exception("GodMode planner failed")
                return {
                    "status": "failed",
                    "steps": steps,
                    "final_result": {"error": f"Planner failed: {exc}"},
                }

            if not isinstance(decision, dict):
                return {
                    "status": "failed",
                    "steps": steps,
                    "final_result": {"error": "Planner returned a non-object response"},
                }

            if decision.get("final") is True:
                final_result = decision.get("result", {})
                if not isinstance(final_result, dict):
                    final_result = {"result": final_result}
                return {
                    "status": "success",
                    "steps": steps,
                    "final_result": final_result,
                }

            action = decision.get("action")
            tool_input = decision.get("input", {})
            if not isinstance(tool_input, dict):
                tool_input = {}

            step_record: Dict[str, Any] = {
                "step": step_index + 1,
                "thought": decision.get("thought", ""),
                "action": action,
                "input": tool_input,
            }

            if action not in self.tools:
                step_record["error"] = f"Invalid tool requested: {action}"
                steps.append(step_record)
                return {
                    "status": "failed",
                    "steps": steps,
                    "final_result": {"error": f"Invalid tool requested: {action}"},
                }

            try:
                result = self.tools[action](tool_input)
                step_record["result"] = result
                logger.info("GodMode step %d: %s", step_index + 1, json.dumps({
                    "thought": step_record["thought"],
                    "action": action,
                    "result_keys": list(result.keys()) if isinstance(result, dict) else [],
                }, default=str))
            except Exception as exc:
                logger.exception("GodMode tool execution failed")
                result = {"error": str(exc)}
                step_record["error"] = str(exc)

            steps.append(step_record)
            memory["steps"].append({
                "step": step_record["step"],
                "thought": step_record.get("thought", ""),
                "action": action,
                "result": result,
            })

        return {
            "status": "failed",
            "steps": steps,
            "final_result": {"error": f"Maximum step limit ({self.max_steps}) reached"},
        }