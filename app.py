import os
import json
from datetime import datetime, timezone

from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, send_file, Response
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from config import Config
from database.db_setup import db
from database.models import User, StressRecord
from utils.predict import predict_text_stress, predict_voice_stress
from utils.recommendations import get_recommendations
from utils.report_generator import build_stress_report
from utils.csv_export import build_history_csv
from utils.scoring import (
    stress_to_score, fuse_scores, classify_stress, classify_risk, risk_badge_class,
    build_analytics, safe_json
)

ALLOWED_EXT = {"wav", "mp3", "flac", "m4a", "ogg", "webm"}

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"

os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)


@login_manager.user_loader
def load_user(user_id):
    try:
        return db.session.get(User, int(user_id))
    except Exception:
        return User.query.get(int(user_id))


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT


def emotion_color_and_intensity(emotion: str, score: float):
    emotion = (emotion or "").lower()
    intensity = "Low / Other"
    color_class = "bg-light text-dark"
    if emotion in ["anger", "ang", "fear", "sad", "sadness", "disgust", "anxiety"]:
        if score >= 0.5:
            intensity = "High Negative"
            color_class = "bg-danger"
        elif score >= 0.25:
            intensity = "Medium Negative"
            color_class = "bg-warning text-dark"
    elif emotion in ["joy", "hap", "happy", "happiness", "calm", "relaxed"]:
        intensity = "Positive" if score >= 0.5 else "Low Positive"
        color_class = "bg-success"
    elif emotion in ["neutral", "neu"]:
        intensity = "Neutral"
        color_class = "bg-secondary text-white"
    return intensity, color_class


def extract_primary_emotion(raw_text=None, raw_audio=None):
    candidates = []
    for result in (raw_text, raw_audio):
        if isinstance(result, dict) and result.get("emotion"):
            emo = result.get("emotion")
            if emo and emo != "text-rule":
                candidates.append((emo, float(result.get("confidence") or 0)))
    if not candidates:
        return "neutral"
    return max(candidates, key=lambda x: x[1])[0]


def is_admin_user():
    return bool(current_user.is_authenticated and (getattr(current_user, "is_admin", False) or current_user.id == 1))


def migrate_database():
    db.create_all()
    try:
        user_cols = [row[1] for row in db.session.execute(text("PRAGMA table_info(user)")).fetchall()]
        record_cols = [row[1] for row in db.session.execute(text("PRAGMA table_info(stress_record)")).fetchall()]

        if "is_admin" not in user_cols:
            db.session.execute(text("ALTER TABLE user ADD COLUMN is_admin BOOLEAN DEFAULT 0"))

        additions = {
            "risk_level": "VARCHAR(50)",
            "primary_emotion": "VARCHAR(80)",
            "text_score": "FLOAT",
            "voice_score": "FLOAT",
            "final_score": "FLOAT",
        }
        for col, sql_type in additions.items():
            if col not in record_cols:
                db.session.execute(text(f"ALTER TABLE stress_record ADD COLUMN {col} {sql_type}"))
        db.session.commit()
    except Exception:
        db.session.rollback()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not (username and email and password):
            flash("Please fill in all fields.")
            return redirect(url_for("register"))

        if User.query.filter_by(email=email).first():
            flash("That email is already registered. Please log in or use a different email.")
            return redirect(url_for("register"))

        if User.query.filter_by(username=username).first():
            flash("That username is already taken. Please choose another username.")
            return redirect(url_for("register"))

        first_user = User.query.count() == 0
        user = User(
            username=username,
            email=email,
            password=generate_password_hash(password),
            is_admin=first_user
        )

        try:
            db.session.add(user)
            db.session.commit()
            flash("Registration successful. Please log in.")
            return redirect(url_for("login"))
        except IntegrityError:
            db.session.rollback()
            flash("An account with that username or email already exists.")
            return redirect(url_for("register"))
        except Exception as e:
            db.session.rollback()
            flash(f"An unexpected error occurred: {str(e)}")
            return redirect(url_for("register"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for("dashboard"))
        flash("Invalid email or password.")
    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))


@app.route("/dashboard")
@login_required
def dashboard():
    records = StressRecord.query.filter_by(user_id=current_user.id).order_by(StressRecord.created_at.desc()).all()
    stats = build_analytics(records, days=7)
    return render_template("dashboard.html", stats=stats, risk_badge_class=risk_badge_class)


@app.route("/detect", methods=["GET", "POST"])
@login_required
def detect():
    result_summary = None
    detailed = None
    recommendations = None
    saved_record_id = None

    if request.method == "POST":
        text_input = request.form.get("text_input", "").strip()
        voice_file = request.files.get("voice_file")
        text_score = voice_score = None
        raw_text = raw_audio = None
        saved_path = None

        if voice_file and voice_file.filename:
            if not allowed_file(voice_file.filename):
                flash("Unsupported audio format. Use WAV, MP3, FLAC, M4A, OGG, or WebM.")
                return redirect(url_for("detect"))
            filename = secure_filename(f"{current_user.id}_{int(datetime.now(timezone.utc).timestamp())}_{voice_file.filename}")
            saved_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            voice_file.save(saved_path)

        if not text_input and not saved_path:
            flash("Please provide text, audio, or both.")
            return redirect(url_for("detect"))

        if text_input:
            raw_text = predict_text_stress(text_input)
            if "error" not in raw_text:
                score_val = raw_text.get("stress_score")
                text_score = score_val if score_val is not None else stress_to_score(raw_text.get("stress"), raw_text.get("confidence"))

        if saved_path:
            raw_audio = predict_voice_stress(saved_path)
            if "error" not in raw_audio:
                score_val = raw_audio.get("stress_score")
                voice_score = score_val if score_val is not None else stress_to_score(raw_audio.get("stress"), raw_audio.get("confidence"))

        final_score = fuse_scores(text_score, voice_score, text_weight=0.6, voice_weight=0.4)
        overall = classify_stress(final_score)
        risk_level = classify_risk(final_score)
        primary_emotion = extract_primary_emotion(raw_text, raw_audio)
        recommendations = get_recommendations(overall, primary_emotion)

        result_summary = {
            "Text Score": f"{text_score:.2f}" if text_score is not None else "N/A",
            "Voice Score": f"{voice_score:.2f}" if voice_score is not None else "N/A",
            "Fusion Score": f"{final_score:.2f}/100",
            "Overall Stress": overall,
            "Risk Level": risk_level,
            "Primary Emotion": (primary_emotion or "N/A").capitalize(),
        }

        rel_voice = None
        if saved_path:
            rel_voice = ("static/" + os.path.relpath(saved_path, start=os.path.join(app.root_path, "static"))).replace("\\", "/")

        record = StressRecord(
            user_id=current_user.id,
            text_input=text_input or None,
            voice_file=rel_voice,
            result_json=json.dumps({
                "summary": result_summary,
                "raw_text": raw_text,
                "raw_audio": raw_audio,
                "recommendations": recommendations,
                "fusion": {"text_weight": 0.6, "voice_weight": 0.4},
            }),
            stress_level=overall,
            risk_level=risk_level,
            primary_emotion=primary_emotion,
            text_score=text_score,
            voice_score=voice_score,
            final_score=final_score,
        )

        try:
            db.session.add(record)
            db.session.commit()
            saved_record_id = record.id
        except Exception as e:
            db.session.rollback()
            flash(f"Error saving analysis record: {str(e)}")

        detailed = {"text": raw_text, "voice": raw_audio}

    return render_template(
        "detect.html",
        result=result_summary,
        detailed=detailed,
        recommendations=recommendations,
        saved_record_id=saved_record_id,
        emotion_style_fn=emotion_color_and_intensity,
        risk_badge_class=risk_badge_class,
    )


@app.route("/history")
@login_required
def history():
    records = StressRecord.query.filter_by(user_id=current_user.id).order_by(StressRecord.created_at.desc()).all()
    return render_template("history.html", records=records, parse_result_json=safe_json, risk_badge_class=risk_badge_class)


@app.route("/export/csv")
@login_required
def export_csv():
    records = StressRecord.query.filter_by(user_id=current_user.id).order_by(StressRecord.created_at.desc()).all()
    csv_data = build_history_csv(records)
    filename = f"MindTrack_History_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(csv_data, mimetype="text/csv", headers={"Content-Disposition": f"attachment; filename={filename}"})


@app.route("/report/<int:record_id>")
@login_required
def report(record_id):
    record = StressRecord.query.filter_by(id=record_id, user_id=current_user.id).first_or_404()
    pdf = build_stress_report(current_user, record)
    filename = f"MindTrack_Report_{record.id}.pdf"
    return send_file(pdf, mimetype="application/pdf", as_attachment=True, download_name=filename)


@app.route("/admin")
@login_required
def admin_dashboard():
    if not is_admin_user():
        flash("Admin access required.")
        return redirect(url_for("dashboard"))
    records = StressRecord.query.order_by(StressRecord.created_at.desc()).all()
    users = User.query.order_by(User.id.asc()).all()
    stats = build_analytics(records, days=7)
    return render_template("admin.html", stats=stats, users=users, records=records[:10], risk_badge_class=risk_badge_class)


@app.route("/uploads/<path:filename>")
@login_required
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


with app.app_context():
    migrate_database()


if __name__ == "__main__":
    app.run(debug=True)
