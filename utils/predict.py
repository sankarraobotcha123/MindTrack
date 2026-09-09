"""Prediction pipelines for text and voice stress detection."""
from models.model_loader import predict_text_raw, predict_voice_raw
from utils.scoring import (
    blend_scores,
    classify_stress,
    emotion_to_score,
    rule_based_text_score,
    stress_to_score,
)

EMOTION_TO_STRESS = {
    "joy": "low", "happiness": "low", "happy": "low", "relaxed": "low", "calm": "low", "positive": "low",
    "surprise": "medium", "neutral": "medium", "confident": "low",
    "anger": "high", "angry": "high", "fear": "high", "sadness": "high", "disgust": "high", "panic": "high",
    "sad": "high", "frustration": "high", "anxiety": "high", "anxious": "high"
}

SHORT_LABEL_MAP = {
    "ang": "anger",
    "hap": "happiness",
    "sad": "sadness",
    "neu": "neutral"
}

FULL_EMOTION_ORDER = ["sadness", "neutral", "anger", "happiness", "surprise", "fear", "disgust"]

def map_short_label(label):
    if not label:
        return label
    return SHORT_LABEL_MAP.get(str(label).lower(), str(label).lower())


def map_emotion_to_stress(label):
    label_low = (label or "").lower()
    return EMOTION_TO_STRESS.get(label_low, "medium")


def top_label_from_scores_hf(score_list):
    if not score_list:
        return None, 0.0
    best = max(score_list, key=lambda x: x.get("score", 0.0))
    return best.get("label"), float(best.get("score", 0.0))


def _normalise_hf_output(raw):
    if isinstance(raw, list) and raw:
        if isinstance(raw[0], dict):
            return raw
        if isinstance(raw[0], list):
            return raw[0]
    return []


def predict_text_stress(text):
    rule_score = rule_based_text_score(text)
    model_score = None
    top_label, conf, raw, model_error = None, 0.0, None, None

    try:
        raw = predict_text_raw(text)
        scores = _normalise_hf_output(raw)
        top_label, conf = top_label_from_scores_hf(scores)
        top_label = map_short_label(top_label)
        model_score = emotion_to_score(top_label, conf)
    except Exception as e:
        model_error = str(e)

    if not top_label:
        if rule_score is not None:
            if rule_score >= 68:
                top_label = "anxiety"
            elif rule_score <= 35:
                top_label = "joy"
            else:
                top_label = "neutral"
            conf = 0.60
        else:
            top_label = "neutral"
            conf = 0.50

    final_score = blend_scores((model_score, 0.65), (rule_score, 0.35))
    if final_score is None:
        final_score = 55.0
    stress = classify_stress(final_score).lower()

    result = {
        "emotion": top_label,
        "confidence": conf,
        "stress": stress,
        "stress_score": final_score,
        "model_score": model_score,
        "rule_score": rule_score,
        "raw": raw,
    }
    if model_error:
        result["model_warning"] = model_error
    return result


def predict_voice_stress(audio_path):
    try:
        raw = predict_voice_raw(audio_path)
        scores = _normalise_hf_output(raw)

        score_dict = {}
        for item in scores:
            if isinstance(item, dict) and "label" in item:
                mapped_label = map_short_label(item["label"]).lower()
                score_dict[mapped_label] = float(item.get("score", 0.0))

        completed_raw = []
        for emo in FULL_EMOTION_ORDER:
            completed_raw.append({
                "label": emo.capitalize(),
                "score": score_dict.get(emo, 0.0)
            })

        completed_raw.sort(key=lambda x: x["score"], reverse=True)

        top_item = completed_raw[0] if completed_raw else {"label": "Neutral", "score": 0.0}
        label = top_item["label"].lower()
        conf = top_item["score"]

        score = emotion_to_score(label, conf) if label else stress_to_score("medium", conf)
        stress = classify_stress(score).lower()

        return {
            "emotion": label or "neutral",
            "confidence": conf,
            "stress": stress,
            "stress_score": score,
            "raw": completed_raw
        }
    except Exception as e:
        return {"error": str(e)}


def predict_combined(text=None, audio_path=None):
    text_res = predict_text_stress(text) if text else None
    voice_res = predict_voice_stress(audio_path) if audio_path else None
    text_score = text_res.get("stress_score") if text_res and "error" not in text_res else None
    voice_score = voice_res.get("stress_score") if voice_res and "error" not in voice_res else None
    combined_score = blend_scores((text_score, 0.6), (voice_score, 0.4))
    combined_stress = classify_stress(combined_score).lower() if combined_score is not None else "unknown"
    return {"text": text_res, "voice": voice_res, "combined_stress": combined_stress, "combined_score": combined_score}
