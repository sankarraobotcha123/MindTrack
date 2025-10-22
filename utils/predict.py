# utils/predict.py
import json
from models.model_loader import predict_text_raw, predict_voice_raw

# Example mapping from emotion labels to stress categories.
# You can tune this mapping for your use case.
EMOTION_TO_STRESS = {
    # low stress / positive
    "joy": "low", "happiness": "low", "happy": "low", "relaxed": "low", "calm": "low", "positive": "low",
    # medium stress / neutral or mixed
    "surprise": "medium", "neutral": "medium", "confident": "medium",
    # high stress / negative
    "anger": "high", "angry": "high", "fear": "high", "sadness": "high", "disgust": "high", "panic": "high",
    # some HF tags vary: add common alternatives
    "sad": "high", "frustration": "high", "anxiety": "high", "anxious": "high"
}

# Mapping from short 3-letter codes to full emotion names
SHORT_LABEL_MAP = {
    "ang": "anger",
    "hap": "happy",
    "sad": "sadness",
    "neu": "neutral"
}

def map_short_label(label):
    """Convert 3-letter emotion code to full name."""
    if not label:
        return label
    return SHORT_LABEL_MAP.get(label.lower(), label)

def map_emotion_to_stress(label):
    label_low = label.lower()
    return EMOTION_TO_STRESS.get(label_low, "medium")  # default to medium

def top_label_from_scores_hf(score_list):
    """
    score_list is like [{"label": "joy", "score": 0.8}, {"label":"sadness","score":0.2}, ...]
    return top label and confidence
    """
    if not score_list:
        return None, 0.0
    best = max(score_list, key=lambda x: x.get("score", 0.0))
    return best.get("label"), float(best.get("score", 0.0))

def predict_text_stress(text):
    try:
        raw = predict_text_raw(text)  # list of dicts when return_all_scores True
        if isinstance(raw, list) and len(raw) > 0 and isinstance(raw[0], dict):
            if isinstance(raw[0].get("label", None), str):
                top_label, conf = top_label_from_scores_hf(raw)
            else:
                top_label, conf = top_label_from_scores_hf(raw[0])
        else:
            top_label, conf = None, 0.0

        top_label = map_short_label(top_label)
        print('top_label', top_label)
        stress = map_emotion_to_stress(top_label or "")
        print('stress', stress)
        return {"emotion": top_label, "confidence": conf, "stress": stress, "raw": raw}
    except Exception as e:
        return {"error": str(e)}

def predict_voice_stress(audio_path):
    try:
        raw = predict_voice_raw(audio_path)
        print('raw data\n', raw)
        if isinstance(raw, list):
            top = max(raw, key=lambda x: x.get("score", 0.0))
            label = top.get("label")
            conf = float(top.get("score", 0.0))
        else:
            label = None
            conf = 0.0

        # Convert short label (e.g. "ang") to full name (e.g. "anger")
        label = map_short_label(label)

        stress = map_emotion_to_stress(label or "")
        return {"emotion": label, "confidence": conf, "stress": stress, "raw": raw}
    except Exception as e:
        return {"error": str(e)}

def predict_combined(text=None, audio_path=None):
    text_res = predict_text_stress(text) if text else None
    voice_res = predict_voice_stress(audio_path) if audio_path else None

    combined_stress = None
    if text_res and voice_res and "error" not in text_res and "error" not in voice_res:
        if text_res["stress"] == voice_res["stress"]:
            combined_stress = text_res["stress"]
        else:
            if text_res["confidence"] >= voice_res["confidence"]:
                combined_stress = text_res["stress"]
            else:
                combined_stress = voice_res["stress"]
    elif text_res and "error" not in text_res:
        combined_stress = text_res["stress"]
    elif voice_res and "error" not in voice_res:
        combined_stress = voice_res["stress"]
    else:
        combined_stress = "unknown"

    return {
        "text": text_res,
        "voice": voice_res,
        "combined_stress": combined_stress
    }
