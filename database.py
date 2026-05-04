from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = "users"
    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email         = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128), nullable=False)
    full_name     = db.Column(db.String(100))
    bio           = db.Column(db.Text)
    is_admin      = db.Column(db.Boolean, default=False)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Conversation(db.Model):
    __tablename__ = "conversations"
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.String(64), nullable=False, index=True)
    title      = db.Column(db.String(120), nullable=False, default="New Chat")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    messages   = db.relationship("Message", backref="conversation", lazy=True, cascade="all, delete-orphan")

class Message(db.Model):
    __tablename__ = "messages"
    id              = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey("conversations.id"), nullable=False, index=True)
    role            = db.Column(db.String(16), nullable=False)
    content         = db.Column(db.Text, nullable=False)
    mode            = db.Column(db.String(16), default="normal")
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)

class InterviewSession(db.Model):
    __tablename__ = "interview_sessions"
    id               = db.Column(db.Integer, primary_key=True)
    user_id          = db.Column(db.String(64), nullable=False, index=True)
    name             = db.Column(db.String(100), nullable=False)
    role             = db.Column(db.String(100), nullable=False)
    skills           = db.Column(db.Text, default="")
    interviewer_mode = db.Column(db.String(20), default="friendly")   # friendly | strict
    system_prompt    = db.Column(db.Text, nullable=False)
    transcript       = db.Column(db.Text, default="[]")               # JSON array
    question_count   = db.Column(db.Integer, default=0)
    completed        = db.Column(db.Boolean, default=False)
    created_at       = db.Column(db.DateTime, default=datetime.utcnow)

class QuizResult(db.Model):
    __tablename__ = "quiz_results"
    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.String(64), nullable=False, index=True)
    topic       = db.Column(db.String(100), nullable=False)
    difficulty  = db.Column(db.String(20), default="Moderate")
    score       = db.Column(db.Integer, nullable=False)
    total       = db.Column(db.Integer, nullable=False)
    weak_areas  = db.Column(db.Text, default="[]") # JSON list
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

class CareerRoadmap(db.Model):
    __tablename__ = "career_roadmaps"
    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.String(64), nullable=False, index=True)
    target_role = db.Column(db.String(100), nullable=False)
    skills      = db.Column(db.Text, default="[]") # JSON list
    roadmap_json = db.Column(db.Text, nullable=False) # Full roadmap JSON
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

class CheatLog(db.Model):
    __tablename__ = "cheat_logs"
    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.String(64), nullable=False, index=True)
    quiz_id     = db.Column(db.Integer, nullable=True) # can link to quiz session if added later
    violation   = db.Column(db.String(100), nullable=False) # "Tab Switch", "Face Mismatch", etc.
    details     = db.Column(db.Text, nullable=True)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)