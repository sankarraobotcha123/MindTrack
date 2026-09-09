"""Fusion helper kept for backward compatibility with external test suites."""
from utils.scoring import fuse_scores


def fusion_score(text_score=None, voice_score=None, text_weight=0.6, voice_weight=0.4):
    return fuse_scores(text_score, voice_score, text_weight, voice_weight)
