from datetime import datetime

from app.infrastructure.db.database import db


class UserModel(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(180), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class ProgressModel(db.Model):
    __tablename__ = "progress"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    discipline = db.Column(db.String(40), nullable=False)
    level = db.Column(db.String(40), nullable=False)
    topic = db.Column(db.String(80), nullable=False)
    difficulty = db.Column(db.Integer, default=1, nullable=False)
    correct_count = db.Column(db.Integer, default=0, nullable=False)
    wrong_count = db.Column(db.Integer, default=0, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship("UserModel", backref="progress_items")


class ActivityLogModel(db.Model):
    __tablename__ = "activity_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    request_id = db.Column(db.String(64), nullable=False, index=True)
    discipline = db.Column(db.String(40), nullable=False)
    level = db.Column(db.String(40), nullable=False)
    topic = db.Column(db.String(80), nullable=False)
    difficulty = db.Column(db.Integer, nullable=False)
    question = db.Column(db.Text, nullable=False)
    expected_answer = db.Column(db.String(255), nullable=False)
    user_answer = db.Column(db.String(255), nullable=True)
    is_correct = db.Column(db.Boolean, nullable=True)
    feedback = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
