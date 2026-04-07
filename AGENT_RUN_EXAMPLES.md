# Agent Run Examples

The lightweight autonomous agent is exposed at `POST /api/v2/agent/run`.

Request shape:

```json
{
  "goal": "string",
  "context": {}
}
```

Example 1: decision-support goal

```json
{
  "goal": "Decide how to reduce the defect rate fastest for the assembly line",
  "context": {
    "kpis": [
      {"name": "Defect Rate", "value": 8.2, "target": 2.0, "unit": "%"},
      {"name": "First Pass Yield", "value": 91.8, "target": 98.0, "unit": "%"}
    ],
    "constraints": {
      "deadline_days": 30,
      "budget_usd": 50000
    }
  }
}
```

Example 2: KPI triage goal

```json
{
  "goal": "Identify which KPIs need immediate intervention and explain why",
  "context": {
    "kpis": [
      {"name": "Scrap Rate", "value": 4.1, "target": 2.0, "unit": "%"},
      {"name": "Cycle Time", "value": 45, "target": 38, "unit": "sec/unit"}
    ],
    "department": "Assembly"
  }
}
```

Example curl:

```bash
curl -X POST http://localhost:8000/api/v2/agent/run \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d '{
    "goal": "Decide how to reduce the defect rate fastest for the assembly line",
    "context": {
      "kpis": [
        {"name": "Defect Rate", "value": 8.2, "target": 2.0, "unit": "%"}
      ]
    }
  }'
```

Typical response shape:

```json
{
  "status": "success",
  "steps": [
    {
      "step": 1,
      "thought": "Generate decision options first.",
      "action": "run_decision",
      "input": {"problem": "Reduce defect rate"},
      "result": {"options": []}
    }
  ],
  "final_result": {
    "summary": "Recommended next action",
    "recommended_tool": "run_decision"
  }
}
```