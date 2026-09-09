"""Scoring, fusion, risk, and analytics helpers for MindTrack Pro.

Score convention:
    0   = very low stress / low risk
    100 = very high stress / high risk
"""
from collections import Counter
from datetime import datetime, timedelta
import json
import re

STRESS_SCORE_MAP = {"low": 25.0, "medium": 55.0, "high": 85.0}

POSITIVE_WORDS = {
    "happy", "excited", "great", "good", "amazing", "joy", "joyful", "calm", "relaxed",
    "peaceful", "motivated", "confident", "energetic", "successful", "hopeful", "optimistic",
    "comfortable", "fine", "better", "love", "enjoy", "proud", "grateful", "positive"
}

NEGATIVE_WORDS = {
    "sad", "lonely", "tired", "unhappy", "angry", "frustrated", "upset", "fear", "afraid",
    "anxious", "anxiety", "worried", "worry", "nervous", "panic", "depressed", "hopeless",
    "exhausted", "weak", "cry", "crying", "bad", "terrible", "pressure", "overwhelmed",
    "stress", "stressed", "deadline", "deadlines", "problem", "problems", "difficult", "unable"
}

HIGH_RISK_PHRASES = {
    "nothing seems interesting": 14,
    "difficult to relax": 12,
    "mind is always racing": 14,
    "too many deadlines": 10,
    "constantly worried": 12,
    "feeling lonely": 10,
    "no energy": 10,
    "unable to focus": 12,
    "feel overwhelmed": 14,
}

LOW_RISK_PHRASES = {
    "feel motivated": -12,
    "feel energetic": -10,
    "everything is going well": -14,
    "quality time": -8,
    "completed all my tasks": -8,
    "feel calm": -12,
    "feel relaxed": -12,
}

EMOTION_SCORE_MAP = {
    "joy": 18, "happy": 18, "happiness": 18, "positive": 20, "calm": 22, "relaxed": 22,
    "neutral": 50, "confident": 35, "surprise": 55,
    "sad": 60, "sadness": 60,
    "disgust": 70,
    "frustration": 74,
    "anger": 85, "angry": 85,
    "fear": 88,
    "anxiety": 90, "anxious": 90, "panic": 94,
}


def clamp_score(score):
    try:
        return round(max(0.0, min(100.0, float(score))), 2)
    except (ValueError, TypeError):
        return 50.0


def stress_to_score(stress_label, confidence=0.0):
    stress = (stress_label or "medium").lower()
    try:
        confidence = max(0.0, min(1.0, float(confidence or 0.0)))
    except (ValueError, TypeError):
        confidence = 0.0

    base = STRESS_SCORE_MAP.get(stress, 55.0)
    if stress == "high":
        base += confidence * 12
    elif stress == "low":
        base -= confidence * 12
    elif stress == "medium":
        base += (confidence - 0.5) * 10
    return clamp_score(base)


def emotion_to_score(emotion, confidence=0.0):
    label = (emotion or "").lower().strip()
    try:
        confidence = max(0.0, min(1.0, float(confidence or 0.0)))
    except (ValueError, TypeError):
        confidence = 0.0

    base = EMOTION_SCORE_MAP.get(label, 55.0)
    score = 50 + (base - 50) * (0.45 + 0.55 * confidence)
    return clamp_score(score)


def rule_based_text_score(text):
    text = (text or "").strip().lower()
    if not text:
        return None
    words = re.findall(r"[a-zA-Z']+", text)
    if not words:
        return 50.0
    pos = sum(1 for w in words if w in POSITIVE_WORDS)
    neg = sum(1 for w in words if w in NEGATIVE_WORDS)
    score = 50 + (neg * 8) - (pos * 7)
    for phrase, delta in HIGH_RISK_PHRASES.items():
        if phrase in text:
            score += delta
    for phrase, delta in LOW_RISK_PHRASES.items():
        if phrase in text:
            score += delta
    if len(words) < 8:
        score = 50 + (score - 50) * 0.6
    return clamp_score(score)


def blend_scores(*weighted_scores):
    pairs = []
    for s, w in weighted_scores:
        if s is not None and w > 0:
            try:
                pairs.append((float(s), float(w)))
            except (ValueError, TypeError):
                continue
    if not pairs:
        return None
    total_weight = sum(w for _, w in pairs)
    return clamp_score(sum(s * w for s, w in pairs) / total_weight)


def fuse_scores(text_score=None, voice_score=None, text_weight=0.6, voice_weight=0.4):
    fused = blend_scores((text_score, text_weight), (voice_score, voice_weight))
    return fused if fused is not None else 55.0


def classify_stress(score):
    try:
        score = float(score or 0)
    except (ValueError, TypeError):
        score = 50.0
    if score < 40:
        return "Low"
    if score < 70:
        return "Medium"
    return "High"


def classify_risk(score):
    try:
        score = float(score or 0)
    except (ValueError, TypeError):
        score = 50.0
    if score >= 70:
        return "High Risk"
    if score >= 40:
        return "Moderate Risk"
    return "Low Risk"


def risk_badge_class(risk_level):
    risk = (risk_level or "").lower()
    if "high" in risk:
        return "bg-danger"
    if "moderate" in risk:
        return "bg-warning text-dark"
    return "bg-success"


def safe_json(value):
    if isinstance(value, dict):
        return value
    try:
        return json.loads(value or "{}")
    except Exception:
        return {}


def record_score(record):
    if getattr(record, "final_score", None) is not None:
        try:
            return float(record.final_score)
        except (ValueError, TypeError):
            pass
    return {"Low": 25.0, "Medium": 55.0, "High": 85.0}.get(getattr(record, "stress_level", None), 55.0)


def build_analytics(records, days=7):
    records = list(records or [])
    total = len(records)
    level_counts = Counter((r.stress_level or "Unknown") for r in records)
    risk_counts = Counter((getattr(r, "risk_level", None) or classify_risk(record_score(r))) for r in records)

    today = datetime.now().date()
    date_range = [today - timedelta(days=i) for i in range(days - 1, -1, -1)]
    trend_labels = [d.strftime("%d %b") for d in date_range]
    trend_scores = []
    for day in date_range:
        day_scores = [record_score(r) for r in records if r.created_at and r.created_at.date() == day]
        trend_scores.append(round(sum(day_scores) / len(day_scores), 2) if day_scores else 0)

    emotion_counts = Counter()
    for r in records:
        emotion = getattr(r, "primary_emotion", None)
        if not emotion:
            data = safe_json(r.result_json)
            summary = data.get("summary", {})
            emotion = summary.get("Primary Emotion")
        if emotion and emotion != "N/A":
            emotion_counts[str(emotion).capitalize()] += 1

    avg_score = round(sum(record_score(r) for r in records) / total, 2) if total else 0
    best = min(records, key=record_score) if records else None
    worst = max(records, key=record_score) if records else None

    if not records:
        risk_message = "No records available yet. Start by running a detection."
    elif avg_score >= 70:
        risk_message = "Average stress is high. Follow recommendations and consider support if this pattern continues."
    elif avg_score >= 40:
        risk_message = "Average stress is moderate. Regular breaks and routine tracking are recommended."
    else:
        risk_message = "Average stress is low. Maintain healthy habits and continue monitoring."

    return {
        "total": total,
        "low_count": level_counts.get("Low", 0),
        "medium_count": level_counts.get("Medium", 0),
        "high_count": level_counts.get("High", 0),
        "low_risk_count": risk_counts.get("Low Risk", 0),
        "moderate_risk_count": risk_counts.get("Moderate Risk", 0),
        "high_risk_count": risk_counts.get("High Risk", 0),
        "avg_score": avg_score,
        "latest": records[0] if records else None,
        "best": best,
        "worst": worst,
        "risk_message": risk_message,
        "trend_labels": trend_labels,
        "trend_scores": trend_scores,
        "stress_labels": ["Low", "Medium", "High"],
        "stress_counts": [level_counts.get("Low", 0), level_counts.get("Medium", 0), level_counts.get("High", 0)],
        "risk_labels": ["Low Risk", "Moderate Risk", "High Risk"],
        "risk_counts": [risk_counts.get("Low Risk", 0), risk_counts.get("Moderate Risk", 0), risk_counts.get("High Risk", 0)],
        "emotion_labels": list(emotion_counts.keys()) or ["No Data"],
        "emotion_counts": list(emotion_counts.values()) or [0],
    }
