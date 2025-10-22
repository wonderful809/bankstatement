from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from flask_bcrypt import Bcrypt
from datetime import datetime, timedelta
import uuid

db = SQLAlchemy()
bcrypt = Bcrypt()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(100))
    
    # Account status
    is_active = db.Column(db.Boolean, default=True)
    is_email_verified = db.Column(db.Boolean, default=False)
    email_verification_token = db.Column(db.String(100))
    
    # Subscription details
    subscription_tier = db.Column(db.String(20), default='free')  # free, starter, professional, business, custom
    subscription_status = db.Column(db.String(20), default='inactive')  # inactive, active, cancelled, past_due
    stripe_customer_id = db.Column(db.String(100), unique=True, index=True)
    stripe_subscription_id = db.Column(db.String(100))
    
    # Usage tracking
    monthly_pages_used = db.Column(db.Integer, default=0)
    monthly_pages_limit = db.Column(db.Integer, default=50)  # Free tier: 50 pages/month
    last_reset_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Relationships
    conversions = db.relationship('Conversion', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    payments = db.relationship('Payment', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    
    def set_password(self, password):
        """Hash and set user password"""
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    
    def check_password(self, password):
        """Verify password against hash"""
        return bcrypt.check_password_hash(self.password_hash, password)
    
    def get_pages_remaining(self):
        """Get remaining pages for current month"""
        # Reset if new month
        now = datetime.utcnow()
        if self.last_reset_date and (now - self.last_reset_date).days >= 30:
            self.monthly_pages_used = 0
            self.last_reset_date = now
            db.session.commit()
        
        return max(0, self.monthly_pages_limit - self.monthly_pages_used)
    
    def can_convert(self, pages):
        """Check if user can convert given number of pages"""
        return self.get_pages_remaining() >= pages
    
    def use_pages(self, pages):
        """Deduct pages from monthly quota"""
        self.monthly_pages_used += pages
        db.session.commit()
    
    def to_dict(self):
        """Convert user to dictionary"""
        return {
            'id': self.id,
            'email': self.email,
            'full_name': self.full_name,
            'subscription_tier': self.subscription_tier,
            'subscription_status': self.subscription_status,
            'monthly_pages_used': self.monthly_pages_used,
            'monthly_pages_limit': self.monthly_pages_limit,
            'pages_remaining': self.get_pages_remaining(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }


class Conversion(db.Model):
    __tablename__ = 'conversions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    # File details
    original_filename = db.Column(db.String(255), nullable=False)
    file_format = db.Column(db.String(20))  # pdf, csv, excel, ofx
    file_size = db.Column(db.Integer)  # bytes
    page_count = db.Column(db.Integer, default=1)
    
    # Conversion details
    conversion_type = db.Column(db.String(20))  # text, ocr, parse
    row_count = db.Column(db.Integer)
    processing_time = db.Column(db.Float)  # seconds
    
    # Status
    status = db.Column(db.String(20), default='processing')  # processing, completed, failed
    error_message = db.Column(db.Text)
    
    # Quality metrics
    quality_score = db.Column(db.Float)  # 0-100
    quality_message = db.Column(db.String(255))
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    completed_at = db.Column(db.DateTime)
    
    def to_dict(self):
        return {
            'id': self.id,
            'filename': self.original_filename,
            'format': self.file_format,
            'size': self.file_size,
            'pages': self.page_count,
            'type': self.conversion_type,
            'rows': self.row_count,
            'status': self.status,
            'error': self.error_message,
            'quality_score': self.quality_score,
            'quality_message': self.quality_message,
            'processing_time': self.processing_time,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }


class Payment(db.Model):
    __tablename__ = 'payments'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    # Stripe details
    stripe_payment_intent_id = db.Column(db.String(100), unique=True)
    stripe_charge_id = db.Column(db.String(100))
    stripe_invoice_id = db.Column(db.String(100))
    
    # Payment details
    amount = db.Column(db.Integer)  # Amount in cents
    currency = db.Column(db.String(3), default='usd')
    status = db.Column(db.String(20))  # pending, succeeded, failed, refunded
    
    # Subscription details
    subscription_tier = db.Column(db.String(20))
    billing_period_start = db.Column(db.DateTime)
    billing_period_end = db.Column(db.DateTime)
    
    # Metadata
    description = db.Column(db.String(255))
    receipt_url = db.Column(db.String(500))
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'amount': self.amount / 100,  # Convert cents to dollars
            'currency': self.currency.upper(),
            'status': self.status,
            'subscription_tier': self.subscription_tier,
            'description': self.description,
            'receipt_url': self.receipt_url,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Subscription(db.Model):
    __tablename__ = 'subscriptions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True, index=True)
    
    # Stripe details
    stripe_subscription_id = db.Column(db.String(100), unique=True)
    stripe_price_id = db.Column(db.String(100))
    stripe_customer_id = db.Column(db.String(100))
    
    # Subscription details
    tier = db.Column(db.String(20), nullable=False)  # starter, professional, business, custom
    status = db.Column(db.String(20), default='active')  # active, cancelled, past_due, incomplete
    
    # Pricing
    amount = db.Column(db.Integer)  # Amount in cents
    currency = db.Column(db.String(3), default='usd')
    interval = db.Column(db.String(20), default='month')  # month, year
    
    # Limits
    pages_limit = db.Column(db.Integer)
    
    # Billing dates
    current_period_start = db.Column(db.DateTime)
    current_period_end = db.Column(db.DateTime)
    cancel_at_period_end = db.Column(db.Boolean, default=False)
    cancelled_at = db.Column(db.DateTime)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    user = db.relationship('User', backref=db.backref('subscription_details', uselist=False))
    
    def to_dict(self):
        return {
            'id': self.id,
            'tier': self.tier,
            'status': self.status,
            'amount': self.amount / 100 if self.amount else 0,
            'currency': self.currency.upper(),
            'interval': self.interval,
            'pages_limit': self.pages_limit,
            'current_period_end': self.current_period_end.isoformat() if self.current_period_end else None,
            'cancel_at_period_end': self.cancel_at_period_end,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Feedback(db.Model):
    __tablename__ = 'feedback'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    conversion_id = db.Column(db.Integer, db.ForeignKey('conversions.id'), nullable=True)
    
    # Feedback data
    rating = db.Column(db.Integer, nullable=False)  # 1-5 stars
    feedback_text = db.Column(db.Text)
    email = db.Column(db.String(255))
    
    # Metadata
    user_agent = db.Column(db.String(500))
    ip_address = db.Column(db.String(45))
    
    # Timestamp
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'rating': self.rating,
            'feedback': self.feedback_text,
            'email': self.email,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
