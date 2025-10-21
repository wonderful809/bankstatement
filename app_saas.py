import os
import time
import logging
import tempfile
import uuid
import re
from datetime import datetime, timedelta
from flask import Flask, render_template, request, send_file, send_from_directory, redirect, url_for, flash, jsonify, session
from werkzeug.utils import secure_filename
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Production Performance Imports
try:
    from flask_compress import Compress
    from flask_caching import Cache
    import sentry_sdk
    from sentry_sdk.integrations.flask import FlaskIntegration
    PERFORMANCE_FEATURES = True
except ImportError:
    PERFORMANCE_FEATURES = False
    print("⚠️  Performance features not available. Run: pip install -r requirements.txt")

from config import Config
from models import db, User, Conversion, Feedback
from processor_enhanced import convert_pdf_to_csv, ExternalToolError

app = Flask(__name__)
app.config.from_object(Config)

# Initialize Performance Features
if PERFORMANCE_FEATURES:
    # Enable Response Compression
    compress = Compress()
    compress.init_app(app)
    
    # Initialize Cache
    cache = Cache()
    cache.init_app(app, config={
        'CACHE_TYPE': 'simple' if not os.getenv('REDIS_URL') else 'redis',
        'CACHE_REDIS_URL': os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
        'CACHE_DEFAULT_TIMEOUT': 300
    })
    
    # Initialize Sentry Error Tracking
    sentry_dsn = os.getenv('SENTRY_DSN', '')
    if sentry_dsn:
        sentry_sdk.init(
            dsn=sentry_dsn,
            integrations=[FlaskIntegration()],
            traces_sample_rate=0.1,  # Sample 10% of requests
            profiles_sample_rate=0.1,
        )
else:
    # Dummy cache decorator for development
    class DummyCache:
        def cached(self, *args, **kwargs):
            def decorator(f):
                return f
            return decorator
    cache = DummyCache()

# Initialize config
Config.init_app(app)

# Configure logging
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL.upper(), logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(Config.LOG_FILE),
        logging.StreamHandler()
    ]
)
app.logger.setLevel(getattr(logging, Config.LOG_LEVEL.upper(), logging.INFO))

# Initialize extensions
db.init_app(app)
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=[Config.RATELIMIT_DEFAULT, "50 per hour", "200 per day"],
    storage_uri=Config.RATELIMIT_STORAGE_URL
)

# Create tables
with app.app_context():
    db.create_all()


# ===== SECURITY MIDDLEWARE =====

@app.after_request
def set_security_headers(response):
    """Add comprehensive security headers to all responses"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    
    # Only set HSTS in production with HTTPS
    if Config.ENV == 'production':
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    
    # Content Security Policy - Allow inline styles for our enhanced UI
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "font-src 'self'; "
        "connect-src 'self'; "
        "frame-ancestors 'none'"
    )
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
    
    # Remove server version header
    response.headers.pop('Server', None)
    
    return response


@app.before_request
def log_request_info():
    """Log all requests for security monitoring"""
    app.logger.info(f"{request.method} {request.path} from {get_remote_address()}")


@app.before_request
def limit_json_request_size():
    """Limit JSON request body size to prevent memory exhaustion"""
    if request.content_type and 'application/json' in request.content_type:
        if request.content_length and request.content_length > 1024 * 1024:  # 1MB max for JSON
            app.logger.warning(f'Large JSON request blocked from {get_remote_address()}')
            return jsonify({'error': 'Request payload too large'}), 413


# ===== SECURITY HELPER FUNCTIONS =====

def secure_filename_enhanced(filename):
    """Enhanced filename sanitization with strict validation"""
    if not filename:
        return 'unnamed.pdf'
    
    # Remove path components
    filename = os.path.basename(filename)
    
    # Use werkzeug's secure_filename first
    filename = secure_filename(filename)
    
    # Additional sanitization: allow only alphanumeric, underscore, hyphen, dot
    filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
    
    # Prevent directory traversal
    filename = filename.replace('..', '')
    
    # Limit length and ensure extension
    name, ext = os.path.splitext(filename)
    name = name[:100]  # Max 100 chars for name
    
    # Ensure .pdf extension
    if ext.lower() != '.pdf':
        ext = '.pdf'
    
    return f"{name}{ext}"


def is_safe_path(base_dir, path, follow_symlinks=True):
    """Prevent directory traversal attacks"""
    if follow_symlinks:
        return os.path.realpath(path).startswith(os.path.realpath(base_dir))
    return os.path.abspath(path).startswith(os.path.abspath(base_dir))



def validate_pdf_thoroughly(file_path):
    """Comprehensive PDF validation with security checks"""
    try:
        # Check file exists
        if not os.path.isfile(file_path):
            return False, "File does not exist"
        
        # Check file size (prevent DoS with huge files)
        file_size = os.path.getsize(file_path)
        if file_size > 50 * 1024 * 1024:  # 50MB absolute max
            return False, "PDF file too large (max 50MB)"
        
        if file_size < 100:  # Too small to be valid PDF
            return False, "File too small to be a valid PDF"
        
        # Check magic bytes (PDF signature)
        with open(file_path, 'rb') as f:
            header = f.read(8)
            if not header.startswith(b'%PDF'):
                return False, "Invalid PDF signature - file is not a PDF"
            
            # Check for PDF version
            version_match = re.search(rb'%PDF-(\d\.\d)', header)
            if not version_match:
                return False, "Invalid PDF version format"
        
        # Try to open with pdfplumber to verify structure
        try:
            import pdfplumber
            with pdfplumber.open(file_path) as pdf:
                page_count = len(pdf.pages)
                
                # Validate page count
                if page_count == 0:
                    return False, "PDF has no pages"
                
                if page_count > 500:  # Reasonable limit for bank statements
                    return False, "PDF has too many pages (max 500)"
                
        except Exception as e:
            return False, f"PDF structure validation failed: {str(e)}"
        
        return True, "Valid PDF"
    
    except Exception as e:
        app.logger.error(f"PDF validation error: {str(e)}")
        return False, f"PDF validation failed: {str(e)}"


def is_valid_pdf(file_path):
    """Check if file is a valid PDF (legacy compatibility wrapper)"""
    valid, _ = validate_pdf_thoroughly(file_path)
    return valid

def cleanup_old_files():
    """Delete files older than configured hours from uploads folder"""
    try:
        now = time.time()
        cutoff = now - (Config.FILE_CLEANUP_HOURS * 60 * 60)
        
        if os.path.exists(Config.UPLOAD_FOLDER):
            for filename in os.listdir(Config.UPLOAD_FOLDER):
                filepath = os.path.join(Config.UPLOAD_FOLDER, filename)
                if os.path.isfile(filepath):
                    file_modified = os.path.getmtime(filepath)
                    if file_modified < cutoff:
                        try:
                            os.remove(filepath)
                            app.logger.info(f'Cleaned up old file: {filename}')
                        except Exception as e:
                            app.logger.warning(f'Failed to delete old file {filename}: {e}')
    except Exception as e:
        app.logger.error(f'Cleanup failed: {e}')


def get_or_create_user():
    """Get or create user session"""
    if 'user_id' not in session:
        user = User()
        db.session.add(user)
        db.session.commit()
        session['user_id'] = user.id
        session['session_id'] = user.session_id
        session.permanent = True
    return User.query.get(session['user_id'])


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


@app.route('/')
def index():
    user = get_or_create_user()
    recent_conversions = Conversion.query.filter_by(user_id=user.id).order_by(Conversion.created_at.desc()).limit(10).all()
    
    # Calculate real statistics
    total_conversions = Conversion.query.filter_by(user_id=user.id).count()
    total_rows = db.session.query(db.func.sum(Conversion.row_count)).filter_by(user_id=user.id).scalar() or 0
    
    # Calculate average processing time
    avg_time_seconds = db.session.query(db.func.avg(Conversion.processing_time)).filter_by(user_id=user.id).scalar() or 120
    avg_time_minutes = round(avg_time_seconds / 60, 1) if avg_time_seconds < 600 else round(avg_time_seconds / 60)
    
    # Add base numbers for social proof (starting from 5000 statements)
    BASE_CONVERSIONS = 5000
    BASE_TRANSACTIONS = 125000  # Assuming ~25 transactions per statement on average
    
    stats = {
        'total_conversions': total_conversions + BASE_CONVERSIONS,
        'total_rows': total_rows + BASE_TRANSACTIONS,
        'avg_time': avg_time_minutes if avg_time_minutes > 0 else 2.0
    }
    
    return render_template('index_enhanced.html', conversions=recent_conversions, stats=stats)


@app.route('/history')
def history():
    """Show recent conversions history page"""
    user = get_or_create_user()
    recent_conversions = Conversion.query.filter_by(user_id=user.id).order_by(Conversion.created_at.desc()).limit(50).all()
    return render_template('history.html', conversions=recent_conversions)


@app.route('/favicon.ico')
def favicon():
    """Return 204 No Content for favicon to prevent 404 errors"""
    return '', 204


@app.route('/pricing')
def pricing():
    """Render pricing page"""
    return render_template('pricing.html')


@app.route('/convert', methods=['POST'])
@limiter.limit("10 per minute")
def convert():
    user = get_or_create_user()
    
    # Run cleanup of old files
    cleanup_old_files()
    
    if 'file' not in request.files:
        app.logger.warning(f'Upload attempt without file from {get_remote_address()}')
        return jsonify({'success': False, 'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        app.logger.warning(f'Invalid file type attempted: {file.filename} from {get_remote_address()}')
        return jsonify({'success': False, 'error': 'Invalid file type. Only PDF files are allowed.'}), 400
    
    # Sanitize filename with enhanced security
    original_filename = secure_filename_enhanced(file.filename)
    unique_filename = f"{uuid.uuid4().hex}_{original_filename}"
    upload_path = os.path.join(Config.UPLOAD_FOLDER, unique_filename)
    
    # Validate path to prevent directory traversal
    if not is_safe_path(Config.UPLOAD_FOLDER, upload_path):
        app.logger.error(f'Directory traversal attempt detected from {get_remote_address()}')
        return jsonify({'success': False, 'error': 'Invalid file path'}), 400
    
    # Create conversion record
    conversion = Conversion(
        user_id=user.id,
        original_filename=original_filename,
        status='processing'
    )
    db.session.add(conversion)
    db.session.commit()
    
    # Save uploaded file
    try:
        file.save(upload_path)
        conversion.file_size = os.path.getsize(upload_path)
        db.session.commit()
    except Exception as e:
        conversion.status = 'failed'
        conversion.error_message = f'Failed to save file: {str(e)}'
        db.session.commit()
        app.logger.error(f'File save failed: {str(e)}')
        return jsonify({'success': False, 'error': 'Failed to save uploaded file'}), 500
    
    # Comprehensive PDF validation (security checks)
    is_valid, validation_message = validate_pdf_thoroughly(upload_path)
    if not is_valid:
        conversion.status = 'failed'
        conversion.error_message = f'PDF validation failed: {validation_message}'
        db.session.commit()
        app.logger.warning(f'PDF validation failed for {original_filename}: {validation_message}')
        try:
            os.remove(upload_path)
        except Exception:
            pass
        return jsonify({'success': False, 'error': f'Invalid PDF: {validation_message}'}), 400
    
    start_time = time.time()
    
    try:
        app.logger.info(f'Processing file: {original_filename} (ID: {conversion.id}, Size: {conversion.file_size} bytes)')
        
        csv_path, conversion_type, row_count, quality_report = convert_pdf_to_csv(
            upload_path,
            tesseract_cmd=app.config['TESSERACT_CMD'],
            poppler_path=app.config['POPPLER_PATH']
        )
        
        processing_time = time.time() - start_time
        confidence = quality_report.get('confidence', 100)
        
        # Update conversion record
        conversion.status = 'completed'
        conversion.conversion_type = conversion_type
        conversion.row_count = row_count
        conversion.processing_time = processing_time
        db.session.commit()
        
        # Log quality metrics (without emoji for Windows console compatibility)
        app.logger.info(f'Conversion successful (ID: {conversion.id}, Type: {conversion_type}, Rows: {row_count}, Time: {processing_time:.2f}s, Confidence: {confidence}%)')
        app.logger.info(f'Quality Report: {quality_report["message_plain"]} - Complete rows: {quality_report["complete_rows"]}/{quality_report["total_rows"]}')
        
        # Send file and clean up
        response = send_file(
            csv_path,
            as_attachment=True,
            download_name=original_filename.rsplit('.', 1)[0] + '.csv'
        )
        
        # Add quality warning as custom header if confidence is low (use plain text for HTTP header)
        if confidence < 60:
            response.headers['X-Quality-Warning'] = quality_report['message_plain']
        
        # Schedule cleanup (in production, use celery or background task)
        @response.call_on_close
        def cleanup():
            try:
                os.remove(upload_path)
                os.remove(csv_path)
            except Exception:
                pass
        
        return response
        
    except ExternalToolError as e:
        conversion.status = 'failed'
        error_msg = str(e)
        
        # Provide better error messages for common OCR dependency issues
        if 'Tesseract not found' in error_msg:
            error_msg = '⚠️ Tesseract OCR is not installed. This PDF requires OCR processing. Please install Tesseract from https://github.com/UB-Mannheim/tesseract/wiki'
        elif 'Poppler' in error_msg or 'pdftoppm' in error_msg:
            error_msg = '⚠️ Poppler is not installed. This PDF requires image conversion for OCR. Please install Poppler from https://github.com/oschwartz10612/poppler-windows/releases'
        
        conversion.error_message = error_msg
        db.session.commit()
        app.logger.error(f'ExternalToolError (ID: {conversion.id}): {error_msg}')
        
        # Clean up uploaded file
        try:
            os.remove(upload_path)
        except Exception:
            pass
        
        return jsonify({'success': False, 'error': error_msg}), 400
        
    except Exception as e:
        conversion.status = 'failed'
        conversion.error_message = str(e)
        db.session.commit()
        app.logger.exception(f'Unexpected error (ID: {conversion.id}): {str(e)}')
        
        # Clean up uploaded file
        try:
            os.remove(upload_path)
        except Exception:
            pass
        
        return jsonify({'success': False, 'error': f'Error processing PDF: {str(e)}'}), 500


@app.route('/api/history')
@limiter.limit("30 per minute")
def get_history():
    """Get conversion history with pagination and sanitized output"""
    try:
        user = get_or_create_user()
        limit = request.args.get('limit', 20, type=int)
        
        # Validate limit parameter
        if limit < 1 or limit > 100:
            return jsonify({'error': 'Invalid limit parameter (1-100)'}), 400
        
        conversions = Conversion.query.filter_by(user_id=user.id).order_by(Conversion.created_at.desc()).limit(limit).all()
        return jsonify({'conversions': [c.to_dict() for c in conversions]})
    except Exception as e:
        app.logger.exception("Error fetching history")
        return jsonify({'error': 'Failed to fetch conversion history'}), 500


@app.route('/api/stats')
@limiter.limit("30 per minute")
@cache.cached(timeout=30)
def get_stats():
    """Get user statistics (cached for 30 seconds)"""
    try:
        user = get_or_create_user()
        total = Conversion.query.filter_by(user_id=user.id).count()
        completed = Conversion.query.filter_by(user_id=user.id, status='completed').count()
        failed = Conversion.query.filter_by(user_id=user.id, status='failed').count()
        total_rows = db.session.query(db.func.sum(Conversion.row_count)).filter_by(user_id=user.id, status='completed').scalar() or 0
        
        # Calculate average processing time
        avg_time_seconds = db.session.query(db.func.avg(Conversion.processing_time)).filter_by(user_id=user.id).scalar() or 120
        avg_time_minutes = round(avg_time_seconds / 60, 1) if avg_time_seconds < 600 else round(avg_time_seconds / 60)
        
        # Add base numbers for social proof (starting from 5000 statements)
        BASE_CONVERSIONS = 5000
        BASE_TRANSACTIONS = 125000  # Assuming ~25 transactions per statement on average
        
        return jsonify({
            'total_conversions': total + BASE_CONVERSIONS,
            'completed': completed,
            'failed': failed,
            'total_rows': int(total_rows) + BASE_TRANSACTIONS,
            'total_rows_processed': int(total_rows) + BASE_TRANSACTIONS,  # Keep for backwards compatibility
            'avg_time': avg_time_minutes if avg_time_minutes > 0 else 2.0
        })
    except Exception as e:
        app.logger.exception("Error fetching stats")
        return jsonify({'error': 'Failed to fetch statistics'}), 500


@app.route('/api/feedback', methods=['POST'])
@limiter.limit("10 per minute")
def submit_feedback():
    """Submit user feedback"""
    try:
        data = request.get_json()
        rating = data.get('rating')
        feedback_text = data.get('feedback', '')
        email = data.get('email', '')
        conversion_id = data.get('conversion_id')  # Optional link to specific conversion
        
        if not rating or rating < 1 or rating > 5:
            return jsonify({'error': 'Invalid rating'}), 400
        
        # Get current user
        user = get_or_create_user()
        
        # Get user agent and IP for analytics
        user_agent = request.headers.get('User-Agent', '')[:500]  # Truncate to 500 chars
        ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
        
        # Create feedback record
        feedback = Feedback(
            user_id=user.id,
            rating=rating,
            feedback_text=feedback_text.strip() if feedback_text else None,
            email=email.strip() if email else None,
            user_agent=user_agent,
            ip_address=ip_address,
            conversion_id=conversion_id
        )
        
        db.session.add(feedback)
        db.session.commit()
        
        # Log feedback for immediate visibility
        app.logger.info(f"FEEDBACK SAVED - ID: {feedback.id}, Rating: {rating}/5, User: {user.id}, Email: {email}")
        
        return jsonify({
            'success': True,
            'message': 'Thank you for your feedback!',
            'feedback_id': feedback.id
        })
    except Exception as e:
        app.logger.exception("Error submitting feedback")
        return jsonify({'error': 'Failed to submit feedback'}), 500


@app.route('/admin/feedback')
def admin_feedback():
    """Admin page to view all feedback (basic auth should be added in production)"""
    try:
        # In production, add authentication here
        # For now, simple query parameter protection
        auth_token = request.args.get('token')
        if auth_token != 'admin123':  # Change this to proper auth in production
            return "Unauthorized", 401
        
        # Get all feedback, ordered by most recent
        feedbacks = Feedback.query.order_by(Feedback.created_at.desc()).limit(100).all()
        
        # Calculate stats
        total_feedback = Feedback.query.count()
        avg_rating = db.session.query(db.func.avg(Feedback.rating)).scalar()
        rating_distribution = db.session.query(
            Feedback.rating,
            db.func.count(Feedback.id)
        ).group_by(Feedback.rating).all()
        
        return render_template('admin_feedback.html',
                             feedbacks=feedbacks,
                             total_feedback=total_feedback,
                             avg_rating=round(avg_rating, 2) if avg_rating else 0,
                             rating_distribution=dict(rating_distribution))
    except Exception as e:
        app.logger.exception("Error viewing feedback")
        return "Error loading feedback", 500


@app.route('/api/delete/<int:conversion_id>', methods=['DELETE'])
@limiter.limit("20 per minute")
def delete_conversion(conversion_id):
    """Delete a conversion record with proper authorization"""
    try:
        # Validate conversion_id
        if not isinstance(conversion_id, int) or conversion_id < 1:
            return jsonify({'success': False, 'error': 'Invalid conversion ID'}), 400
        
        user = get_or_create_user()
        conversion = Conversion.query.filter_by(id=conversion_id, user_id=user.id).first()
        
        if not conversion:
            app.logger.warning(f'Unauthorized delete attempt: conversion {conversion_id} by user {user.id}')
            return jsonify({'success': False, 'error': 'Conversion not found'}), 404
        
        db.session.delete(conversion)
        db.session.commit()
        
        app.logger.info(f'Conversion {conversion_id} deleted by user {user.id}')
        return jsonify({'success': True})
    except Exception as e:
        app.logger.exception(f"Error deleting conversion {conversion_id}")
        return jsonify({'success': False, 'error': 'Failed to delete conversion'}), 500


@app.errorhandler(413)
def request_entity_too_large(error):
    app.logger.warning(f'File upload rejected: File too large from {get_remote_address()}')
    return jsonify({
        'success': False, 
        'error': '📦 File too large. Maximum file size is 16MB. Please compress your PDF or split it into smaller files.'
    }), 413


@app.errorhandler(429)
def ratelimit_handler(e):
    app.logger.warning(f'Rate limit exceeded: {get_remote_address()}')
    return jsonify({
        'success': False, 
        'error': '⏱️ Rate limit exceeded. You can convert up to 10 files per minute, 50 per hour. Please wait and try again.'
    }), 429


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors without revealing system information"""
    return jsonify({'error': 'Resource not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors - log details but show generic message"""
    app.logger.exception("Internal server error")
    return jsonify({'error': 'An internal error occurred. Please try again later.'}), 500


@app.errorhandler(Exception)
def handle_unexpected_error(error):
    """Catch-all for unhandled exceptions - prevents information disclosure"""
    app.logger.exception(f"Unhandled exception: {str(error)}")
    
    # Return generic error message (no system details to user)
    return jsonify({
        'success': False,
        'error': 'An unexpected error occurred. Please try again later.'
    }), 500


if __name__ == '__main__':
    # Run cleanup on startup
    cleanup_old_files()
    app.run(debug=True, host='0.0.0.0', port=5000)
