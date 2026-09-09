"""Risk helper kept for backward compatibility with external test suites."""
from utils.scoring import classify_risk


def get_risk_level(score):
    return classify_risk(score)
