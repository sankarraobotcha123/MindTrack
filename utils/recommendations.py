"""Personalized wellness recommendation engine for MindTrack Pro."""

RECOMMENDATION_RULES = {
    "high": {
        "anger": [
            "Practice the 4-7-8 breathing technique for 3 minutes to decelerate heart rate.",
            "Take a short pause before sending responses or making major decisions.",
            "Drink cold water and physically step away from the immediate environment for 5 minutes."
        ],
        "fear": [
            "Write down the immediate concern and identify one small tangible action you can take right now.",
            "Use the 5-4-3-2-1 grounding technique: identify 5 things you see, 4 you feel, 3 you hear, 2 you smell, and 1 you taste.",
            "Discuss your current thoughts with a trusted mentor, friend, or counselor."
        ],
        "sadness": [
            "Take a 10-minute walk outdoors or do light stretching exercises.",
            "Listen to calming, instrumental music and avoid prolonged isolation.",
            "Reach out to someone you trust to talk through your current state of mind."
        ],
        "disgust": [
            "Step away from the current trigger and practice mindful sensory reset.",
            "Document what caused the emotional response and assess if an immediate boundary is required.",
            "Engage in a neutral, hands-on activity to transition your mental focus."
        ],
        "anxiety": [
            "Perform box breathing (inhale 4s, hold 4s, exhale 4s, hold 4s) for 4 cycles.",
            "Limit immediate caffeine intake and break your immediate to-do list into single, small tasks.",
            "Ground your feet flat on the floor and focus on rhythmic physical breathing."
        ],
        "default": [
            "Pause and take slow, deep abdominal breaths for 2 to 3 minutes.",
            "Avoid multitasking; focus solely on your immediate priority.",
            "Consider stepping away from screen devices for 15 minutes."
        ]
    },
    "medium": {
        "default": [
            "Schedule a structured 5-minute break away from digital screens.",
            "Organize pending tasks into an 'Urgent vs. Important' checklist.",
            "Do light neck and shoulder stretches to release accumulated physical tension.",
            "Ensure you are properly hydrated and have had balanced nutrition today."
        ]
    },
    "low": {
        "joy": [
            "Take note of what routines and habits contributed to your positive state today.",
            "Channel this positive focus toward completing your most challenging objectives.",
            "Maintain your current balanced sleep, diet, and physical schedule."
        ],
        "happy": [
            "Continue your current effective work-rest balance.",
            "Share positive reinforcement or collaborate productively with your peers.",
            "Set aside time to plan upcoming milestones while your focus is clear."
        ],
        "default": [
            "Your stress score is well-regulated. Continue your healthy daily balance.",
            "Maintain consistent hydration, balanced meals, and regular rest intervals.",
            "Use the dashboard history view to track long-term wellness stability."
        ]
    }
}

RECOMMENDATION_RULES["moderate"] = RECOMMENDATION_RULES["medium"]

DISCLAIMER = (
    "MindTrack Pro provides general mental wellness and stress tracking suggestions only. "
    "This application is not intended for medical diagnosis or clinical treatment. If you "
    "experience persistent or severe distress, please consult a qualified healthcare professional."
)


def normalize(value):
    return (value or "").strip().lower()


def get_recommendations(stress_level, emotion=None):
    stress = normalize(stress_level)
    emo = normalize(emotion)

    stress_rules = RECOMMENDATION_RULES.get(stress, RECOMMENDATION_RULES["medium"])
    tips = stress_rules.get(emo) or stress_rules.get("default") or RECOMMENDATION_RULES["medium"]["default"]

    return {
        "tips": tips,
        "disclaimer": DISCLAIMER
    }
