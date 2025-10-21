"""
Production Configuration
========================

This file contains production-specific settings that override
the development configuration in config.py.

Security Enhancements:
- Debug mode disabled
- Secure session cookies
- HTTPS enforcement
- CORS restrictions
- Rate limiting
"""

import os
from datetime import timedelta

class ProductionConfig:
    """Production configuration settings"""
    
    # Flask Core Settings
    DEBUG = False
    TESTING = False
    ENV = 'production'
    
    # Security Settings
    SECRET_KEY = os.environ.get('FLASK_SECRET_KEY')
    if not SECRET_KEY:
        raise ValueError("FLASK_SECRET_KEY must be set in production!")
    
    # Session Security
    SESSION_COOKIE_SECURE = True  # Requires HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    
    # File Upload Settings
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB max file size
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', 'uploads')
    
    # CORS Settings (restrict to your domains)
    ALLOWED_ORIGINS = os.environ.get('ALLOWED_ORIGINS', '').split(',')
    
    # Rate Limiting
    RATELIMIT_ENABLED = True
    RATELIMIT_STORAGE_URL = os.environ.get('REDIS_URL', 'memory://')
    
    # Logging
    LOG_LEVEL = 'INFO'
    LOG_FILE = 'logs/production.log'
    
    # Database (when you migrate from in-memory)
    DATABASE_URL = os.environ.get('DATABASE_URL')
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Redis Cache (for session storage)
    REDIS_URL = os.environ.get('REDIS_URL')
    
    # OCR Configuration
    TESSERACT_CMD = os.environ.get('TESSERACT_CMD')
    POPPLER_PATH = os.environ.get('POPPLER_PATH')
    
    # Monitoring
    SENTRY_DSN = os.environ.get('SENTRY_DSN')  # Error tracking
    
    # Performance
    SEND_FILE_MAX_AGE_DEFAULT = 31536000  # 1 year cache for static files


class StagingConfig(ProductionConfig):
    """Staging configuration (testing production settings)"""
    ENV = 'staging'
    DEBUG = False
    SESSION_COOKIE_SECURE = False  # Allow HTTP in staging
    

# Configuration dictionary
config = {
    'production': ProductionConfig,
    'staging': StagingConfig,
    'default': ProductionConfig
}
