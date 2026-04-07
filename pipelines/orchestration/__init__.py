"""
Pipeline Orchestration
======================
High-level **deterministic** pipeline flows that compose services, pipelines,
and models into end-to-end workflows.

These are the DEFAULT execution paths. Agents may *override* or *modify*
pipeline behavior through the agents/orchestrators layer, but pipelines
themselves contain NO LLM reasoning.

Pipelines:
  - TrainingPipeline: data → features → train → evaluate → register
  - InferencePipeline: document → process → retrieve → infer → respond
  - EvaluationPipeline: predictions → metrics → compare → report
  - RetrainingPipeline: drift check → retrain → evaluate → promote
"""
