# models/model_loader.py
import os
from transformers import pipeline
import torch

# Choose models (you can change these to any HF model you prefer)
TEXT_MODEL = "j-hartmann/emotion-english-distilroberta-base"     # text emotion
VOICE_MODEL = "superb/wav2vec2-base-superb-er"                   # audio emotion

# Use GPU if available
device = 0 if torch.cuda.is_available() else -1

# Load pipelines (these download to cache on first run)
try:
    text_pipeline = pipeline("text-classification", model=TEXT_MODEL, device=device, return_all_scores=True)
except Exception as e:
    text_pipeline = None
    print(f"[model_loader] Failed to load text pipeline: {e}")

try:
    # audio-classification works with files or arrays depending on model.
    voice_pipeline = pipeline("audio-classification", model=VOICE_MODEL, device=device)
except Exception as e:
    voice_pipeline = None
    print(f"[model_loader] Failed to load voice pipeline: {e}")


def predict_text_raw(text):
    """Return raw HF pipeline output or raises if unavailable."""
    if text_pipeline is None:
        raise RuntimeError("Text pipeline not loaded.")
    out = text_pipeline(text)  # returns list of dicts (if return_all_scores True)
    return out


def predict_voice_raw(audio_path):
    """Return raw HF pipeline output for the audio file path."""
    if voice_pipeline is None:
        raise RuntimeError("Voice pipeline not loaded.")
    # voice_pipeline accepts path to file
    out = voice_pipeline(audio_path)
    return out
