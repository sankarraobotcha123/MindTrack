"""Safe Hugging Face model loader.

The app still runs for demo/testing even if transformers, torch, ffmpeg,
or model caches are unavailable. In that case, predict_*_raw raises a clear error,
and utils.predict automatically falls back to rule-based scoring.
"""

TEXT_MODEL = "j-hartmann/emotion-english-distilroberta-base"
VOICE_MODEL = "superb/wav2vec2-base-superb-er"

text_pipeline = None
voice_pipeline = None
load_errors = []

try:
    import torch
    from transformers import pipeline
    device = 0 if torch.cuda.is_available() else -1

    try:
        text_pipeline = pipeline("text-classification", model=TEXT_MODEL, device=device, top_k=None)
    except Exception as e:
        load_errors.append(f"Text pipeline failed: {e}")

    try:
        voice_pipeline = pipeline("audio-classification", model=VOICE_MODEL, device=device)
    except Exception as e:
        load_errors.append(f"Voice pipeline failed: {e}")
except Exception as e:
    load_errors.append(f"ML libraries unavailable: {e}")


def predict_text_raw(text):
    if text_pipeline is None:
        raise RuntimeError("Text pipeline not loaded. " + " | ".join(load_errors))
    return text_pipeline(str(text), truncation=True, max_length=512)


def predict_voice_raw(audio_path):
    if voice_pipeline is None:
        raise RuntimeError("Voice pipeline not loaded. " + " | ".join(load_errors))
    return voice_pipeline(audio_path)
