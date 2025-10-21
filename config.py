import os
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    # Flask Configuration
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.getenv('FLASK_DEBUG', 'True').lower() in ('true', '1', 'yes')
    ENV = os.getenv('FLASK_ENV', 'development')
    
    # Server Configuration
    HOST = os.getenv('FLASK_HOST', '0.0.0.0')
    PORT = int(os.getenv('FLASK_PORT', 5000))
    
    # Database Configuration
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URI', 'sqlite:///bankstatements.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = os.getenv('SQLALCHEMY_TRACK_MODIFICATIONS', 'False').lower() in ('true', '1', 'yes')
    
    # File Upload Configuration
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))  # Default 16MB
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'uploads')
    ALLOWED_EXTENSIONS = set(os.getenv('ALLOWED_EXTENSIONS', 'pdf').split(','))
    
    # Session Configuration
    SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'False').lower() in ('true', '1', 'yes')
    SESSION_COOKIE_HTTPONLY = os.getenv('SESSION_COOKIE_HTTPONLY', 'True').lower() in ('true', '1', 'yes')
    SESSION_COOKIE_SAMESITE = os.getenv('SESSION_COOKIE_SAMESITE', 'Lax')
    PERMANENT_SESSION_LIFETIME = timedelta(seconds=int(os.getenv('PERMANENT_SESSION_LIFETIME', 86400)))
    SESSION_TYPE = 'filesystem'
    
    # External Tools Configuration
    TESSERACT_CMD = os.getenv('TESSERACT_CMD', '')
    POPPLER_PATH = os.getenv('POPPLER_PATH', '')
    
    # Rate Limiting Configuration
    RATELIMIT_STORAGE_URL = os.getenv('RATELIMIT_STORAGE_URL', 'memory://')
    RATELIMIT_DEFAULT = os.getenv('RATELIMIT_DEFAULT', '10 per minute')
    
    # File Cleanup Configuration
    FILE_CLEANUP_HOURS = int(os.getenv('FILE_CLEANUP_HOURS', 1))
    
    # Logging Configuration
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'app.log')
    
    @staticmethod
    def init_app(app):
        """Initialize application with config"""
        # Create upload folder if it doesn't exist
        if not os.path.exists(Config.UPLOAD_FOLDER):
            os.makedirs(Config.UPLOAD_FOLDER)
        
        # Set environment variables for external tools (so processor.py can access them)
        if Config.TESSERACT_CMD:
            os.environ['TESSERACT_CMD'] = Config.TESSERACT_CMD
            app.logger.info(f'✅ Tesseract configured: {Config.TESSERACT_CMD}')
        
        if Config.POPPLER_PATH:
            os.environ['POPPLER_PATH'] = Config.POPPLER_PATH
            app.logger.info(f'✅ Poppler configured: {Config.POPPLER_PATH}')
        
        # Validate required external tools in production
        if Config.ENV == 'production':
            if not Config.TESSERACT_CMD:
                app.logger.warning('⚠️  TESSERACT_CMD not set - OCR will not work')
            if not Config.POPPLER_PATH:
                app.logger.warning('POPPLER_PATH not set - OCR may not work')
