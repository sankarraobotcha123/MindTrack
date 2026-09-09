"""CSV export helper for MindTrack Pro."""
import csv
from io import StringIO
from utils.scoring import safe_json, record_score, classify_risk


def build_history_csv(records):
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Record ID", "Date", "Text", "Voice File", "Text Score", "Voice Score",
        "Final Score", "Stress Level", "Risk Level", "Primary Emotion"
    ])

    for r in records:
        data = safe_json(r.result_json)
        summary = data.get("summary", {})
        writer.writerow([
            r.id,
            r.created_at.strftime("%Y-%m-%d %H:%M:%S") if r.created_at else "",
            r.text_input or "",
            r.voice_file or "",
            getattr(r, "text_score", None) if getattr(r, "text_score", None) is not None else summary.get("Text Score", ""),
            getattr(r, "voice_score", None) if getattr(r, "voice_score", None) is not None else summary.get("Voice Score", ""),
            getattr(r, "final_score", None) if getattr(r, "final_score", None) is not None else record_score(r),
            r.stress_level or "",
            getattr(r, "risk_level", None) or classify_risk(record_score(r)),
            (getattr(r, "primary_emotion", None) or summary.get("Primary Emotion", "")).capitalize(),
        ])

    return output.getvalue()
