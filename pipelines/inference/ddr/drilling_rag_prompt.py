"""
Drilling RAG System Prompt — Specialized Retrieval-Augmented Generation
for DDR (Daily Drilling Report) question-answering.

Enforces citation discipline, prioritizes factual field-level answers,
and avoids hallucination through structured context and answer formatting.
"""

# ---------------------------------------------------------------------------
# The master system prompt sent to the LLM for drilling-related Q&A
# ---------------------------------------------------------------------------

DRILLING_RAG_SYSTEM_PROMPT = """You are TransIQ Drilling Intelligence, a world-class AI assistant specializing in Daily Drilling Report (DDR) analytics for oil & gas operations.

## YOUR ROLE
You answer questions about drilling operations using ONLY the DDR data provided in the context below. You are precise, factual, and auditable.

## CITATION RULES — MANDATORY
Every fact you state MUST include a citation in this exact format:
  [RigID–Pg#–Section–Field]

Examples:
  - "Mud weight was 10.5 ppg [RIG-12–Pg3–MudData–MudWeight]"
  - "NPT of 2.5 hours due to stuck pipe [RIG-07–Pg2–NPT–Duration]"
  - "ROP averaged 45 ft/hr [RIG-12–Pg1–Drilling–ROP]"

If a citation is available in the context data, you MUST use it verbatim.
If no citation is available, use the format [RigID–Data–Field] with the best available identifiers.

## CONTEXT FORMAT
You will receive context in this structure:

### DDR Report Data
- report_date: The date of the report
- rig_id / rig_name: Rig identifier
- well_name: Well being drilled
- kpis: Dictionary of extracted metrics, each with:
  - value: The metric value
  - citation: The provenance citation
  - confidence: Extraction confidence (0-1)
  - extraction_method: How it was extracted (regex/ocr/llm/imputed)

### Related Tables (if provided)
- timeline: 24-hour activity log
- npt_events: Non-Productive Time events with cause codes
- surveys: Directional survey data (MD, inclination, azimuth)
- mud_data: Drilling fluid properties
- drill_string: BHA composition
- hse_data: Safety and environmental data
- foreman_remarks: Supervisor observations

## ANSWER FORMATTING RULES

1. **Be specific** — Always include numeric values with units.
2. **Cite everything** — Every data point gets a citation.
3. **Flag low confidence** — If a metric has confidence < 0.7, note: "(low confidence: {method} extraction)"
4. **Flag imputed values** — If is_imputed=true, note: "(imputed value — verify manually)"
5. **Never invent data** — If the context does not contain an answer, say: "This information is not available in the provided DDR data."
6. **Use tables for comparisons** — When comparing across rigs or time periods, use markdown tables.
7. **Structured answers** — Use headers and bullet points for clarity.

## ANSWER STRUCTURE

For each answer, follow this template:

### Finding
[Direct answer with citations]

### Supporting Data
[Relevant metrics and context with citations]

### Confidence Assessment
[High/Medium/Low based on extraction methods and data availability]

### Recommendations (if applicable)
[Actionable next steps based on the data]

## WHAT YOU MUST NEVER DO
- Never fabricate rig IDs, dates, or metric values
- Never answer questions outside the scope of the provided DDR data
- Never omit citations from factual statements
- Never present imputed or low-confidence data as certain
- Never ignore safety-critical findings in HSE data

## SPECIAL HANDLING

### NPT Questions
When asked about Non-Productive Time:
1. List events with cause codes and durations
2. Calculate total NPT percentage (NPT hours / 24)
3. Identify top contributors (Pareto)
4. Include cost impact if available

### Trend Questions
When asked about trends:
1. Present data chronologically
2. Note SPC violations if any
3. Flag deviations beyond ±2σ from mean
4. Reference control chart data

### Safety / HSE Questions
When asked about safety:
1. Always prioritize LTI (Lost Time Injury) data
2. Flag any non-zero incident counts prominently
3. Include BOP test status if available
4. Note permit-to-work counts
"""


# ---------------------------------------------------------------------------
# Context builder — formats DDR data for injection into the RAG prompt
# ---------------------------------------------------------------------------

def build_rag_context(
    report_data: dict,
    related_data: dict | None = None,
) -> str:
    """
    Build the context block to inject into the RAG prompt.

    Args:
        report_data: Dict with keys: rig_id, rig_name, report_date, well_name, kpis.
        related_data: Optional dict with keys: timeline, npt_events, surveys,
                      mud_data, drill_string, hse_data, foreman_remarks.

    Returns:
        Formatted context string for LLM injection.
    """
    lines = ["## DDR Report Context\n"]

    # Header
    lines.append(f"- **Rig**: {report_data.get('rig_name', report_data.get('rig_id', 'Unknown'))}")
    lines.append(f"- **Date**: {report_data.get('report_date', 'N/A')}")
    lines.append(f"- **Well**: {report_data.get('well_name', 'N/A')}")
    lines.append("")

    # KPIs
    kpis = report_data.get("kpis", {})
    if kpis:
        lines.append("### Extracted KPIs\n")
        for field, data in kpis.items():
            if isinstance(data, dict):
                val = data.get("value", "N/A")
                cite = data.get("citation", "")
                conf = data.get("confidence", 1.0)
                method = data.get("extraction_method", "unknown")
                imputed = data.get("is_imputed", False)
                flag = ""
                if imputed:
                    flag = " **(IMPUTED)**"
                elif conf < 0.7:
                    flag = f" **(low confidence: {method})**"
                lines.append(f"- **{field}**: {val} {cite}{flag}")
            else:
                lines.append(f"- **{field}**: {data}")
        lines.append("")

    # Related data sections
    if related_data:
        if related_data.get("timeline"):
            lines.append("### 24-Hour Timeline\n")
            for entry in related_data["timeline"][:30]:  # cap for context window
                desc = entry.get("description", "")
                start = entry.get("start_time", "")
                end = entry.get("end_time", "")
                npt = " [NPT]" if entry.get("is_npt") else ""
                lines.append(f"- {start}–{end}: {desc}{npt}")
            lines.append("")

        if related_data.get("npt_events"):
            lines.append("### NPT Events\n")
            for evt in related_data["npt_events"]:
                cat = evt.get("category", "Unknown")
                dur = evt.get("duration_hours", 0)
                desc = evt.get("description", "")
                lines.append(f"- **{cat}** ({dur} hrs): {desc}")
            lines.append("")

        if related_data.get("surveys"):
            lines.append("### Directional Surveys\n")
            lines.append("| MD | Inc | Azi | TVD | DLS |")
            lines.append("|---|---|---|---|---|")
            for s in related_data["surveys"][:20]:
                lines.append(
                    f"| {s.get('depth_md','')} | {s.get('inclination','')} "
                    f"| {s.get('azimuth','')} | {s.get('tvd','')} "
                    f"| {s.get('dog_leg_severity','')} |"
                )
            lines.append("")

        if related_data.get("mud_data"):
            md = related_data["mud_data"]
            lines.append("### Mud Data\n")
            for k, v in md.items():
                if v is not None and k != "unit":
                    lines.append(f"- **{k}**: {v}")
            lines.append("")

        if related_data.get("hse_data"):
            hse = related_data["hse_data"]
            lines.append("### HSE Data\n")
            for k, v in hse.items():
                if v is not None:
                    lines.append(f"- **{k}**: {v}")
            lines.append("")

        if related_data.get("foreman_remarks"):
            lines.append("### Foreman Remarks\n")
            for r in related_data["foreman_remarks"]:
                lines.append(f"- ({r.get('author_role', 'Foreman')}): {r.get('text', '')}")
            lines.append("")

    return "\n".join(lines)


def build_full_prompt(user_question: str, context: str) -> str:
    """
    Combine system prompt + context + user question into a complete RAG prompt.

    Args:
        user_question: The user's drilling question.
        context: Pre-built context string from build_rag_context().

    Returns:
        Full prompt string ready for LLM.generate().
    """
    return f"""{DRILLING_RAG_SYSTEM_PROMPT}

---

{context}

---

## User Question
{user_question}

## Your Answer (with citations)
"""
