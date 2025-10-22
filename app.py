# app.py
import os
import json
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from config import Config
from database.db_setup import db
from database.models import User, StressRecord
from utils.predict import predict_combined, predict_text_stress, predict_voice_stress
from datetime import datetime

ALLOWED_EXT = {"wav", "mp3", "flac", "m4a", "ogg", "webm"}

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"

if not os.path.exists(app.config["UPLOAD_FOLDER"]):
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# @app.before_first_request
# def create_tables():
#     db.create_all()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT

# 🎨 Unified emotion-to-color and intensity mapping for both text & voice
# def get_emotion_intensity_label(label, score):
def emotion_color_and_intensity(emotion: str, score: float):
    """
    Determine the intensity label and progress bar color based on emotion and score.

    Args:
        emotion (str): full emotion name (anger, sad, happy, neutral, etc.)
        score (float): probability/score (0.0 to 1.0)

    Returns:
        intensity (str), color_class (str)
    """
    # Normalize emotion name
    emotion = emotion.lower()

    # Default values
    intensity = "Low / Other"
    color_class = "bg-light text-dark"

    # Negative emotions
    if emotion in ["anger", "ang", "fear", "sad", "sadness", "disgust"]:
        if score >= 0.5:
            intensity = "High Negative"
            color_class = "bg-danger"
        elif score >= 0.25:
            intensity = "Medium Negative"
            color_class = "bg-warning"
        else:
            intensity = "Low / Other"
            color_class = "bg-light text-dark"

    # Positive emotions
    elif emotion in ["joy", "hap", "happy"]:
        if score >= 0.5:
            intensity = "Positive"
            color_class = "bg-success"
        else:
            intensity = "Low Positive"
            color_class = "bg-light text-dark"

    # Neutral
    elif emotion in ["neutral", "neu"]:
        intensity = "Neutral"
        color_class = "bg-secondary text-white"

    return intensity, color_class


@app.route("/")
def index():
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        if not (username and email and password):
            flash("Please fill all fields")
            return redirect(url_for("register"))
        if User.query.filter_by(email=email).first():
            flash("Email already registered")
            return redirect(url_for("register"))
        user = User(username=username, email=email, password=generate_password_hash(password))
        db.session.add(user)
        db.session.commit()
        flash("Registration successful. Please log in.")
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for("detect"))
        flash("Invalid credentials")
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))

@app.route("/detect", methods=["GET", "POST"])
@login_required
def detect():
    result_summary = None
    detailed = None  # store raw emotion details

    if request.method == "POST":
        text_input = request.form.get("text_input", "").strip()
        voice_file = request.files.get("voice_file")

        score_text = None
        score_audio = None
        raw_text = None
        raw_audio = None

        saved_path = None
        if voice_file and voice_file.filename != "" and allowed_file(voice_file.filename):
            filename = secure_filename(f"{current_user.id}_{int(datetime.utcnow().timestamp())}_{voice_file.filename}")
            saved_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            voice_file.save(saved_path)

        # Predict text stress
        if text_input:
            text_result = predict_text_stress(text_input)  # returns dict like {'emotion':..., 'stress':..., 'raw':...}
            raw_text = text_result
            # Map to numeric score
            stress_map = {"low": 0.2, "medium": 0.5, "high": 0.9}
            score_text = stress_map.get(text_result.get("stress", "medium"), 0.5)

        # Predict voice stress
        if saved_path:
            voice_result = predict_voice_stress(saved_path)  # same format as text
            raw_audio = voice_result
            stress_map = {"low": 0.2, "medium": 0.5, "high": 0.9}
            score_audio = stress_map.get(voice_result.get("stress", "medium"), 0.5)

        if not text_input and not saved_path:
            flash("Please provide text, audio, or both.")
            return redirect(url_for("detect"))

        # Determine overall stress
        if score_text is not None and score_audio is not None:
            combined = (score_text + score_audio) / 2
        elif score_text is not None:
            combined = score_text
        elif score_audio is not None:
            combined = score_audio

        if combined < 0.4:
            overall = "Low"
        elif combined < 0.7:
            overall = "Medium"
        else:
            overall = "High"

        # Prepare summary for badges
        result_summary = {
            "Text Stress": f"{score_text:.2f}" if score_text is not None else "N/A",
            "Voice Stress": f"{score_audio:.2f}" if score_audio is not None else "N/A",
            "Overall Stress": overall
        }

        # Save record
        record = StressRecord(
            user_id=current_user.id,
            text_input=text_input or None,
            voice_file=("static/" + os.path.relpath(saved_path, start=os.path.join(app.root_path, "static"))).replace("\\", "/") if saved_path else None,
            result_json=json.dumps({"summary": result_summary, "raw_text": raw_text, "raw_audio": raw_audio}),
            stress_level=overall
        )
        db.session.add(record)
        db.session.commit()

        # send raw details to template
        detailed = {"text": raw_text, "voice": raw_audio}

        print('\n\n',detailed,result_summary,'\n\n')

    return render_template("detect.html", result=result_summary, detailed=detailed, emotion_style_fn=emotion_color_and_intensity)

@app.route("/history")
@login_required
def history():
    records = StressRecord.query.filter_by(user_id=current_user.id).order_by(StressRecord.created_at.desc()).all()
    return render_template("history.html", records=records)

# serve uploaded files safely (optional)
@app.route('/uploads/<path:filename>')
@login_required
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
