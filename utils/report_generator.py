"""PDF report generator for MindTrack Pro."""
from io import BytesIO
from datetime import datetime
import json
from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle


def _safe_json(value):
    if isinstance(value, dict):
        return value
    try:
        return json.loads(value or "{}")
    except Exception:
        return {}


def build_stress_report(user, record):
    """Return a BytesIO PDF report for a StressRecord."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()

    cell_style = ParagraphStyle(
        "CellRegular",
        parent=styles["Normal"],
        fontSize=9,
        leading=11
    )
    cell_bold = ParagraphStyle(
        "CellBold",
        parent=styles["Normal"],
        fontSize=9,
        leading=11,
        fontName="Helvetica-Bold"
    )

    data = _safe_json(record.result_json)
    summary = data.get("summary", {})
    recs = data.get("recommendations", {})
    tips = recs.get("tips", [])
    disclaimer = recs.get("disclaimer", "")

    detection_time = record.created_at.strftime("%Y-%m-%d %H:%M:%S") if record.created_at else "-"

    story = [
        Paragraph("MindTrack Pro Stress & Wellness Analysis Report", styles["Title"]),
        Spacer(1, 10),
        Paragraph("AI-powered multimodal mental wellness monitoring using text, voice, weighted fusion scoring, risk classification, and recommendations.", styles["BodyText"]),
        Spacer(1, 15),
    ]

    details = [
        ["User", getattr(user, "username", "-")],
        ["Email", getattr(user, "email", "-")],
        ["Report Generated", datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
        ["Detection Time", detection_time],
        ["Text Score", str(getattr(record, "text_score", None) if getattr(record, "text_score", None) is not None else summary.get("Text Score", "N/A"))],
        ["Voice Score", str(getattr(record, "voice_score", None) if getattr(record, "voice_score", None) is not None else summary.get("Voice Score", "N/A"))],
        ["Fusion Score", str(getattr(record, "final_score", None) if getattr(record, "final_score", None) is not None else summary.get("Fusion Score", "N/A"))],
        ["Overall Stress", str(record.stress_level or "-")],
        ["Risk Level", str(getattr(record, "risk_level", None) or summary.get("Risk Level", "-"))],
        ["Primary Emotion", str(getattr(record, "primary_emotion", None) or summary.get("Primary Emotion", "N/A")).capitalize()],
    ]

    table_data = [
        [Paragraph(escape(str(row[0])), cell_bold), Paragraph(escape(str(row[1])), cell_style)]
        for row in details
    ]

    table = Table(table_data, colWidths=[150, 340])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f1f5f9")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(table)
    story.append(Spacer(1, 16))

    if record.text_input:
        story.append(Paragraph("Submitted Text Analysis", styles["Heading2"]))
        story.append(Spacer(1, 4))
        story.append(Paragraph(escape(record.text_input), styles["BodyText"]))
        story.append(Spacer(1, 14))

    story.append(Paragraph("Personalized Wellness Recommendations", styles["Heading2"]))
    story.append(Spacer(1, 4))
    if tips:
        for idx, tip in enumerate(tips, 1):
            story.append(Paragraph(escape(f"{idx}. {tip}"), styles["BodyText"]))
            story.append(Spacer(1, 2))
    else:
        story.append(Paragraph("No recommendation data available for this record.", styles["BodyText"]))
    story.append(Spacer(1, 14))

    story.append(Paragraph("Clinical Notice", styles["Heading2"]))
    story.append(Spacer(1, 4))
    notice = disclaimer or "This report is for educational and personal wellness tracking only. It is not a clinical medical diagnosis."
    story.append(Paragraph(escape(notice), styles["BodyText"]))

    doc.build(story)
    buffer.seek(0)
    return buffer
