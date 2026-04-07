import importlib

from fastapi import FastAPI
from fastapi.testclient import TestClient

from agents import godmode_agent as godmode_module
from app.api.v2 import endpoints


class FakeLLM:
    def __init__(self, responses):
        self.responses = list(responses)
        self.prompts = []

    def generate_json(self, prompt, temperature=0.2):
        self.prompts.append(prompt)
        if not self.responses:
            raise AssertionError("FakeLLM exhausted")
        return self.responses.pop(0)

    def get_model_info(self):
        return {"provider": "gemini", "model": "fake-model"}


def _build_test_client():
    app = FastAPI()
    app.include_router(endpoints.router, prefix="/api/v2")
    return TestClient(app)


def test_agent_run_endpoint_smoke(monkeypatch):
    godmode_runtime = importlib.import_module("app.agents.godmode_agent")

    class StubAgent:
        def __init__(self, provider_name=None, max_steps=5):
            self.provider_name = provider_name
            self.max_steps = max_steps

        def run(self, goal, context=None):
            return {
                "status": "success",
                "steps": [],
                "final_result": {
                    "summary": f"Handled: {goal}",
                    "context_keys": sorted((context or {}).keys()),
                },
            }

    monkeypatch.setattr(godmode_runtime, "GodModeAgent", StubAgent)

    client = _build_test_client()
    response = client.post(
        "/api/v2/agent/run",
        json={
            "goal": "Assess throughput risk for the current line",
            "context": {"kpis": [], "notes": "pilot batch"},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    assert payload["final_result"]["summary"] == "Handled: Assess throughput risk for the current line"
    assert payload["final_result"]["context_keys"] == ["kpis", "notes"]


def test_godmode_agent_example_goal_decision_flow(monkeypatch):
    fake_llm = FakeLLM(
        [
            {
                "thought": "Generate decision options first.",
                "action": "run_decision",
                "input": {"problem": "Reduce defect rate", "deadline": "30 days"},
                "final": False,
            },
            {
                "thought": "Enough evidence collected.",
                "final": True,
                "result": {
                    "summary": "Prioritize tool-life tracking and operator standardization.",
                    "recommended_tool": "run_decision",
                },
            },
        ]
    )

    monkeypatch.setattr(godmode_module.LLMFactory, "get_provider", lambda provider_name=None: fake_llm)

    agent = godmode_module.GodModeAgent()
    agent.tools = {
        "run_decision": lambda payload: {
            "options": ["Tool-life tracking", "Operator retraining"],
            "received": payload,
        }
    }

    result = agent.run(
        goal="Decide how to reduce the defect rate fastest",
        context={"kpis": [{"name": "Defect Rate", "value": 8.2, "target": 2.0}]},
    )

    assert result["status"] == "success"
    assert len(result["steps"]) == 1
    assert result["steps"][0]["action"] == "run_decision"
    assert result["steps"][0]["result"]["options"][0] == "Tool-life tracking"
    assert result["final_result"]["recommended_tool"] == "run_decision"
    assert "Always respond as a single JSON object" in fake_llm.prompts[0]
    assert "Context.steps" in fake_llm.prompts[0]


def test_godmode_agent_example_goal_kpi_flow(monkeypatch):
    fake_llm = FakeLLM(
        [
            {
                "thought": "Score the KPI set before making a recommendation.",
                "action": "run_kpi",
                "input": {
                    "kpis": [
                        {"name": "First Pass Yield", "value": 91.8, "target": 98.0},
                        {"name": "Scrap Rate", "value": 4.1, "target": 2.0},
                    ]
                },
                "final": False,
            },
            {
                "thought": "The KPI scoring is enough to summarize the problem.",
                "final": True,
                "result": {
                    "summary": "First Pass Yield and Scrap Rate should be escalated immediately.",
                    "risk_level": "high",
                },
            },
        ]
    )

    monkeypatch.setattr(godmode_module.LLMFactory, "get_provider", lambda provider_name=None: fake_llm)

    agent = godmode_module.GodModeAgent()
    agent.tools = {
        "run_kpi": lambda payload: {
            "kpis": [
                {"name": "First Pass Yield", "priorityScore": 0.94},
                {"name": "Scrap Rate", "priorityScore": 0.91},
            ],
            "received": payload,
        }
    }

    result = agent.run(
        goal="Identify which KPIs need immediate intervention",
        context={"department": "Assembly"},
    )

    assert result["status"] == "success"
    assert result["steps"][0]["action"] == "run_kpi"
    assert result["steps"][0]["result"]["kpis"][0]["priorityScore"] == 0.94
    assert result["final_result"]["risk_level"] == "high"


def test_godmode_agent_invalid_tool_fails_cleanly(monkeypatch):
    fake_llm = FakeLLM(
        [
            {
                "thought": "Call a tool that does not exist.",
                "action": "run_magic",
                "input": {},
                "final": False,
            }
        ]
    )

    monkeypatch.setattr(godmode_module.LLMFactory, "get_provider", lambda provider_name=None: fake_llm)

    agent = godmode_module.GodModeAgent()
    result = agent.run(goal="Try an unsupported tool", context={})

    assert result["status"] == "failed"
    assert result["steps"][0]["action"] == "run_magic"
    assert result["steps"][0]["error"] == "Invalid tool requested: run_magic"
    assert result["final_result"]["error"] == "Invalid tool requested: run_magic"


def test_godmode_agent_prefers_gemini_when_provider_unspecified(monkeypatch):
    captured = {}

    class StubProvider:
        def generate_json(self, prompt, temperature=0.2):
            return {"final": True, "result": {"ok": True}}

        def get_model_info(self):
            return {"provider": "gemini", "model": "fake-model"}

    def fake_get_provider(name=None, **kwargs):
        captured["name"] = name
        return StubProvider()

    monkeypatch.setattr(godmode_module.settings, "GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.setattr(godmode_module.settings, "OPENAI_API_KEY", None)
    monkeypatch.setattr(godmode_module.settings, "GROK_API_KEY", "test-grok-key")
    monkeypatch.setattr(godmode_module.LLMFactory, "get_provider", fake_get_provider)

    godmode_module.GodModeAgent()

    assert captured["name"] == "gemini"
