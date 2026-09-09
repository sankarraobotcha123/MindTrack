# MindTrack Pro

**MindTrack Pro: AI-Based Multimodal Mental Wellness Monitoring and Recommendation System**

MindTrack Pro is an MCA major-project Flask application that estimates mental wellness/stress level using text emotion analysis and voice emotion recognition. It includes fusion scoring, risk classification, analytics dashboards, personalized recommendations, PDF reports, CSV export, history tracking, and an admin dashboard.

> Important: This project is for educational and wellness-awareness purposes only. It is not a medical diagnosis system.

## Major Project Features

- User registration and login
- Text-based emotion/stress analysis using Hugging Face Transformers
- Voice emotion recognition using audio classification
- Fusion AI Engine: combines text and voice scores using 60:40 weighting
- Risk classification: Low Risk, Moderate Risk, High Risk
- Personalized wellness recommendation engine
- User dashboard with 7-day trend charts
- Stress, risk, and emotion distribution charts
- Detection history with audio playback
- PDF report generation for each prediction
- CSV history export
- Admin dashboard with overall user and prediction analytics
- SQLite database with automatic lightweight migration for new fields

## Tech Stack

- Python
- Flask
- Flask-Login
- Flask-SQLAlchemy
- Hugging Face Transformers
- PyTorch
- Librosa / SoundFile
- ReportLab
- Bootstrap 5
- Chart.js
- SQLite

## Project Structure

```text
MindTrack Pro
├── app.py
├── config.py
├── requirements.txt
├── database/
│   ├── db_setup.py
│   └── models.py
├── models/
│   └── model_loader.py
├── utils/
│   ├── predict.py
│   ├── scoring.py
│   ├── recommendations.py
│   ├── report_generator.py
│   └── csv_export.py
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   ├── detect.html
│   ├── history.html
│   └── admin.html
└── static/
```

## Installation

```bash
python -m venv venv
venv\Scripts\activate     # Windows
# source venv/bin/activate # Linux/Mac

pip install -r requirements.txt
python app.py
```

Open in browser:

```text
http://127.0.0.1:5000
```

## Admin Access

The first registered user is automatically marked as admin. Admin users can access:

```text
/admin
```

## Fusion Score Logic

Text and voice outputs are converted to 0-100 scores:

- Low stress: around 25
- Medium stress: around 55
- High stress: around 85

When both inputs are available:

```python
final_score = text_score * 0.6 + voice_score * 0.4
```

Risk classification:

| Fusion Score | Stress Level | Risk Level |
|---|---|---|
| 0-39 | Low | Low Risk |
| 40-69 | Medium | Moderate Risk |
| 70-100 | High | High Risk |

## Suggested Viva Explanation

MindTrack Pro performs multimodal analysis by collecting text and/or voice input. Text is processed through an emotion classification model, while voice is processed through an audio emotion recognition model. The system maps detected emotions into stress categories, converts them into numerical scores, applies weighted fusion, classifies risk level, stores the result, and visualizes trends through dashboards and downloadable reports.

## Disclaimer

The system provides estimated wellness/stress indicators only. It should not be used for clinical diagnosis or emergency mental-health assessment.

## Latest Scoring Optimization

The updated package avoids identical `55 / Moderate Risk` history rows by adding:

- Safe model loading: the Flask app can start even if `transformers` or `torch` is unavailable.
- Text rule-based fallback scoring for demo/offline testing.
- Emotion-to-score mapping instead of only `low/medium/high` fixed values.
- Fusion score uses available scores only; text-only, voice-only, and combined inputs now produce different results.

Score convention:

- `0-39` = Low Stress / Low Risk
- `40-69` = Medium Stress / Moderate Risk
- `70-100` = High Stress / High Risk

Note: this is still an educational wellness-awareness system, not a medical diagnosis tool.
