from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    conversions = db.relationship('Conversion', backref='user', lazy=True, cascade='all, delete-orphan')

class Conversion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_size = db.Column(db.Integer)  # bytes
    conversion_type = db.Column(db.String(20))  # 'text' or 'ocr'
    row_count = db.Column(db.Integer)
    status = db.Column(db.String(20), default='processing')  # processing, completed, failed
    error_message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    processing_time = db.Column(db.Float)  # seconds
    
    def to_dict(self):
        return {
            'id': self.id,
            'filename': self.original_filename,
            'size': self.file_size,
            'type': self.conversion_type,
            'rows': self.row_count,
            'status': self.status,
            'error': self.error_message,
            'created_at': self.created_at.isoformat(),
            'processing_time': self.processing_time
        }


class Feedback(db.Model):
    """User feedback model for storing ratings and comments"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Optional, if user is known
    rating = db.Column(db.Integer, nullable=False)  # 1-5 stars
    feedback_text = db.Column(db.Text)  # Optional user comment
    email = db.Column(db.String(255))  # Optional email for follow-up
    user_agent = db.Column(db.String(500))  # Browser/device info
    ip_address = db.Column(db.String(45))  # IPv4 or IPv6
    conversion_id = db.Column(db.Integer, db.ForeignKey('conversion.id'), nullable=True)  # Link to specific conversion
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'rating': self.rating,
            'feedback': self.feedback_text,
            'email': self.email,
            'created_at': self.created_at.isoformat()
        }

