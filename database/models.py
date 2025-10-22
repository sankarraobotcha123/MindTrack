from datetime import datetime
from database.db_setup import db
from flask_login import UserMixin

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

    records = db.relationship("StressRecord", backref="user", lazy=True)

class StressRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    text_input = db.Column(db.Text)
    voice_file = db.Column(db.String(300))
    result_json = db.Column(db.Text)  # store full combined JSON result if desired
    stress_level = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
