import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get("MINDTRACK_SECRET") or "change_this_secret_for_prod"
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or "sqlite:///" + os.path.join(BASE_DIR, "mindtrack.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads", "voices")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max upload
