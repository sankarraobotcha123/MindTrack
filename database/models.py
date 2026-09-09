from datetime import datetime, timezone
from database.db_setup import db
from flask_login import UserMixin


class User(UserMixin, db.Model):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

    records = db.relationship("StressRecord", backref="user", lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User id={self.id} username='{self.username}'>"


class StressRecord(db.Model):
    __tablename__ = "stress_record"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    text_input = db.Column(db.Text, nullable=True)
    voice_file = db.Column(db.String(300), nullable=True)
    result_json = db.Column(db.Text, nullable=True)
    stress_level = db.Column(db.String(50), nullable=True)
    risk_level = db.Column(db.String(50), nullable=True)
    primary_emotion = db.Column(db.String(80), nullable=True)
    text_score = db.Column(db.Float, nullable=True)
    voice_score = db.Column(db.Float, nullable=True)
    final_score = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    def __repr__(self):
        return f"<StressRecord id={self.id} user_id={self.user_id} score={self.final_score}>"
