"""
Export Service — PDF and Excel dashboard export generation.

Converts dashboard JSON data into downloadable PDF and Excel files.

Uses:
  - reportlab for PDF generation
  - openpyxl (via pandas) for Excel generation
"""
from __future__ import annotations

import io
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ============================================================================
# PDF Export
# ============================================================================

def generate_dashboard_pdf(doc_id: str, dashboard_data: Dict[str, Any]) -> bytes:
    """
    Generate a formatted PDF report from dashboard data.

    Args:
        doc_id: Document identifier
        dashboard_data: Full dashboard response dict

    Returns:
        PDF file content as bytes
    """
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch, cm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        PageBreak, HRFlowable,
    )

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    # Custom styles
    styles.add(ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        fontSize=22,
        spaceAfter=6,
        textColor=colors.HexColor("#003366"),
    ))
    styles.add(ParagraphStyle(
        "SectionHead",
        parent=styles["Heading2"],
        fontSize=14,
        spaceBefore=16,
        spaceAfter=8,
        textColor=colors.HexColor("#00A651"),
    ))
    styles.add(ParagraphStyle(
        "SubHead",
        parent=styles["Heading3"],
        fontSize=11,
        spaceBefore=10,
        spaceAfter=4,
        textColor=colors.HexColor("#333333"),
    ))
    styles.add(ParagraphStyle(
        "CellText",
        parent=styles["Normal"],
        fontSize=9,
        leading=11,
    ))

    elements: list = []

    # ── Title Page ──────────────────────────────────────────────
    elements.append(Spacer(1, 2 * inch))
    elements.append(Paragraph("TransIQ Dashboard Report", styles["ReportTitle"]))
    elements.append(Spacer(1, 0.3 * inch))

    meta = dashboard_data.get("meta", {})
    elements.append(Paragraph(
        f"Report ID: {meta.get('reportId', doc_id)}", styles["Normal"]
    ))
    elements.append(Paragraph(
        f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}", styles["Normal"]
    ))
    elements.append(Paragraph(
        f"Source Type: {meta.get('sourceType', 'N/A')}", styles["Normal"]
    ))
    elements.append(Paragraph(
        f"Confidence: {meta.get('confidenceOverall', 'N/A')}", styles["Normal"]
    ))
    elements.append(Spacer(1, 0.5 * inch))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#003366")))

    # ── Auto Classification ─────────────────────────────────────
    ac = dashboard_data.get("autoClassification", {})
    if ac:
        elements.append(Paragraph("Auto-Classification", styles["SectionHead"]))
        ac_data = [
            ["Report Type", ", ".join(ac.get("reportType", []))],
            ["Asset Scope", str(ac.get("assetScope", "N/A"))],
            ["Time Horizon", str(ac.get("timeHorizon", "N/A"))],
            ["Decision Level", str(ac.get("decisionLevel", "N/A"))],
            ["Confidence", f"{ac.get('confidence', 0):.0%}"],
        ]
        t = Table(ac_data, colWidths=[2.5 * inch, 4 * inch])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#E8F4FD")),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ]))
        elements.append(t)

    # ── KPIs ────────────────────────────────────────────────────
    kpis = dashboard_data.get("kpis", [])
    if kpis:
        elements.append(Paragraph("Key Performance Indicators", styles["SectionHead"]))
        kpi_header = ["KPI", "Value", "Unit", "Trend", "Confidence"]
        kpi_rows = [kpi_header]
        for kpi in kpis[:30]:  # Cap at 30 to avoid overly long PDFs
            kpi_rows.append([
                str(kpi.get("title") or kpi.get("name", "—")),
                str(kpi.get("value", "—")),
                str(kpi.get("unit", "")),
                str(kpi.get("changeType") or kpi.get("trend", "—")),
                f"{kpi.get('confidence', 0):.0%}" if isinstance(kpi.get("confidence"), (int, float)) else "—",
            ])
        t = Table(kpi_rows, repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#003366")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F5F5")]),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(t)

    # ── Six Sigma / DMAIC ───────────────────────────────────────
    ss = dashboard_data.get("sixSigma", {})
    if ss:
        elements.append(PageBreak())
        elements.append(Paragraph("Six Sigma Analysis", styles["SectionHead"]))
        ss_data = [
            ["Sigma Level", str(ss.get("sigmaLevel", "N/A"))],
            ["Defect Rate", str(ss.get("defectRate", "N/A"))],
            ["Process Capability", str(ss.get("processCapability", "N/A"))],
        ]
        t = Table(ss_data, colWidths=[2.5 * inch, 4 * inch])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#E8F4FD")),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
        ]))
        elements.append(t)

        dmaic = ss.get("dmaic", {})
        if dmaic:
            for phase in ["define", "measure", "analyze", "improve", "control"]:
                phase_data = dmaic.get(phase, {})
                if phase_data:
                    elements.append(Paragraph(f"DMAIC — {phase.upper()}", styles["SubHead"]))
                    if isinstance(phase_data, str):
                        elements.append(Paragraph(phase_data, styles["CellText"]))
                    elif isinstance(phase_data, dict):
                        summary = phase_data.get("problemStatement") or phase_data.get("dataCollectionPlan") or json.dumps(phase_data, default=str)[:500]
                        elements.append(Paragraph(str(summary), styles["CellText"]))

    # ── Predictive Forecasts ────────────────────────────────────
    predictive = dashboard_data.get("predictive", {})
    forecasts = predictive.get("forecast", []) if isinstance(predictive, dict) else []
    if forecasts:
        elements.append(Paragraph("Predictive Forecasts", styles["SectionHead"]))
        fc_header = ["Metric", "Current", "Forecast", "Trend", "Risk", "Confidence"]
        fc_rows = [fc_header]
        for fc in forecasts[:20]:
            fc_rows.append([
                str(fc.get("metric", "—")),
                str(fc.get("currentValue", "—")),
                str(fc.get("forecastValue", "—")),
                str(fc.get("trend", "—")),
                str(fc.get("riskLevel", "—")),
                f"{fc.get('confidence', 0):.0%}" if isinstance(fc.get("confidence"), (int, float)) else "—",
            ])
        t = Table(fc_rows, repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#003366")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F5F5")]),
        ]))
        elements.append(t)

    # ── Insights ────────────────────────────────────────────────
    insights = dashboard_data.get("insights", {})
    if insights:
        elements.append(Paragraph("Insights & Recommendations", styles["SectionHead"]))
        summary_text = insights.get("summary", "")
        if summary_text:
            elements.append(Paragraph(f"Summary: {summary_text}", styles["Normal"]))
            elements.append(Spacer(1, 0.2 * inch))

        for alert in (insights.get("alerts") or [])[:10]:
            sev = alert.get("severity", "Info")
            msg = alert.get("message", "")
            elements.append(Paragraph(f"[{sev}] {msg}", styles["CellText"]))

        for rec in (insights.get("recommendations") or [])[:10]:
            title = rec.get("title", rec) if isinstance(rec, dict) else str(rec)
            elements.append(Paragraph(f"• {title}", styles["CellText"]))

    # ── Explainability ──────────────────────────────────────────
    expl = dashboard_data.get("explainability", {})
    if expl:
        elements.append(Paragraph("Explainability & Audit Trail", styles["SectionHead"]))
        reasoning = expl.get("reasoning", "")
        if reasoning:
            elements.append(Paragraph(f"Reasoning: {reasoning}", styles["CellText"]))
        for lim in (expl.get("limitations") or []):
            elements.append(Paragraph(f"Limitation: {lim}", styles["CellText"]))

    # ── Build PDF ───────────────────────────────────────────────
    doc.build(elements)
    return buf.getvalue()


# ============================================================================
# Excel Export
# ============================================================================

def generate_dashboard_excel(doc_id: str, dashboard_data: Dict[str, Any]) -> bytes:
    """
    Generate a multi-sheet Excel workbook from dashboard data.

    Sheets:
      1. KPIs
      2. Forecast Data
      3. Risk Analysis
      4. Six Sigma

    Args:
        doc_id: Document identifier
        dashboard_data: Full dashboard response dict

    Returns:
        Excel (.xlsx) file content as bytes
    """
    import pandas as pd

    buf = io.BytesIO()

    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        # ── Sheet 1: KPIs ───────────────────────────────────────
        kpis = dashboard_data.get("kpis", [])
        if kpis:
            rows = []
            for kpi in kpis:
                rows.append({
                    "KPI": kpi.get("title") or kpi.get("name", ""),
                    "Value": kpi.get("value", ""),
                    "Unit": kpi.get("unit", ""),
                    "Change": kpi.get("change", kpi.get("context", "")),
                    "Trend": kpi.get("changeType") or kpi.get("trend", ""),
                    "Category": kpi.get("category", ""),
                    "Confidence": kpi.get("confidence", ""),
                    "Status": kpi.get("status", ""),
                    "Priority Score": kpi.get("priorityScore", ""),
                    "Visibility": kpi.get("visibility", ""),
                })
            df_kpis = pd.DataFrame(rows)
        else:
            df_kpis = pd.DataFrame({"Info": ["No KPIs available"]})
        df_kpis.to_excel(writer, sheet_name="KPIs", index=False)

        # ── Sheet 2: Forecast Data ──────────────────────────────
        predictive = dashboard_data.get("predictive", {})
        forecasts = predictive.get("forecast", []) if isinstance(predictive, dict) else []
        if forecasts:
            fc_rows = []
            for fc in forecasts:
                base = {
                    "Metric": fc.get("metric", ""),
                    "Current Value": fc.get("currentValue", ""),
                    "Forecast Value": fc.get("forecastValue", ""),
                    "Unit": fc.get("unit", ""),
                    "Trend": fc.get("trend", ""),
                    "Confidence": fc.get("confidence", ""),
                    "Risk Level": fc.get("riskLevel", ""),
                    "Breach Predicted": fc.get("breachPredicted", ""),
                    "Time To Breach": fc.get("timeToBreach", ""),
                    "Financial Risk": fc.get("financialRisk", ""),
                    "Decision": fc.get("decision", ""),
                }
                # Add per-step forecast columns
                for i, val in enumerate(fc.get("forecast", []), start=1):
                    base[f"Step {i}"] = val
                fc_rows.append(base)
            df_fc = pd.DataFrame(fc_rows)
        else:
            df_fc = pd.DataFrame({"Info": ["No forecast data available"]})
        df_fc.to_excel(writer, sheet_name="Forecast Data", index=False)

        # ── Sheet 3: Risk Analysis ──────────────────────────────
        risk_rows = []
        for fc in forecasts:
            if fc.get("riskLevel") and fc.get("riskLevel") != "low":
                risk_rows.append({
                    "Metric": fc.get("metric", ""),
                    "Risk Level": fc.get("riskLevel", ""),
                    "Breach Predicted": fc.get("breachPredicted", False),
                    "Time to Breach": fc.get("timeToBreach", "N/A"),
                    "Financial Risk ($)": fc.get("financialRisk", ""),
                    "Decision": fc.get("decision", ""),
                    "Current Value": fc.get("currentValue", ""),
                    "Forecast Value": fc.get("forecastValue", ""),
                })
        # Also add alerts
        for alert in (dashboard_data.get("insights", {}).get("alerts") or []):
            risk_rows.append({
                "Metric": alert.get("category", "Alert"),
                "Risk Level": alert.get("severity", "medium"),
                "Breach Predicted": "",
                "Time to Breach": "",
                "Financial Risk ($)": "",
                "Decision": alert.get("message", ""),
                "Current Value": "",
                "Forecast Value": "",
            })
        df_risk = pd.DataFrame(risk_rows) if risk_rows else pd.DataFrame({"Info": ["No elevated risks"]})
        df_risk.to_excel(writer, sheet_name="Risk Analysis", index=False)

        # ── Sheet 4: Six Sigma ──────────────────────────────────
        ss = dashboard_data.get("sixSigma", {})
        ss_rows = [
            {"Parameter": "Sigma Level", "Value": ss.get("sigmaLevel", "N/A")},
            {"Parameter": "Defect Rate", "Value": ss.get("defectRate", "N/A")},
            {"Parameter": "Process Capability", "Value": ss.get("processCapability", "N/A")},
            {"Parameter": "Statistical Validity", "Value": str(ss.get("statisticalValidity", "N/A"))},
        ]
        df_ss = pd.DataFrame(ss_rows)
        df_ss.to_excel(writer, sheet_name="Six Sigma", index=False)

        # Auto-adjust column widths
        for sheet_name in writer.sheets:
            ws = writer.sheets[sheet_name]
            for col_cells in ws.columns:
                max_len = 0
                col_letter = col_cells[0].column_letter
                for cell in col_cells:
                    try:
                        cell_len = len(str(cell.value)) if cell.value else 0
                        max_len = max(max_len, cell_len)
                    except Exception:
                        pass
                ws.column_dimensions[col_letter].width = min(max_len + 4, 50)

    return buf.getvalue()
