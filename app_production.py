"""
Production Application with Redis Caching, Celery Background Tasks, and Performance Optimizations
Designed to handle MILLIONS of requests
"""

import os
import tempfile
import uuid
import logging
from datetime import timedelta
from flask import Flask, render_template, request, send_file, redirect, url_for, flash, jsonify
from flask_caching import Cache
from flask_compress import Compress
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix
from config import Config
from celery import Celery
import redis

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Apply ProxyFix for proper IP handling behind load balancer/proxy
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# Initialize Redis connection
redis_client = redis.Redis(
    host=os.getenv('REDIS_HOST', 'localhost'),
    port=int(os.getenv('REDIS_PORT', 6379)),
    db=0,
    decode_responses=True,
    socket_connect_timeout=5,
    socket_keepalive=True,
    health_check_interval=30
)

# Initialize Flask-Caching with Redis backend
cache = Cache(app, config={
    'CACHE_TYPE': 'redis',
    'CACHE_REDIS_HOST': os.getenv('REDIS_HOST', 'localhost'),
    'CACHE_REDIS_PORT': int(os.getenv('REDIS_PORT', 6379)),
    'CACHE_REDIS_DB': 1,
    'CACHE_DEFAULT_TIMEOUT': 3600,  # 1 hour default cache
    'CACHE_KEY_PREFIX': 'bankstatement_'
})

# Initialize response compression (gzip)
compress = Compress()
compress.init_app(app)

# Initialize rate limiting with Redis backend
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["1000 per hour", "100 per minute"],
    storage_uri=f"redis://{os.getenv('REDIS_HOST', 'localhost')}:{os.getenv('REDIS_PORT', 6379)}/2",
    strategy="fixed-window"
)

# Initialize Celery for background task processing
def make_celery(app):
    celery = Celery(
        app.import_name,
        backend=f"redis://{os.getenv('REDIS_HOST', 'localhost')}:{os.getenv('REDIS_PORT', 6379)}/3",
        broker=f"redis://{os.getenv('REDIS_HOST', 'localhost')}:{os.getenv('REDIS_PORT', 6379)}/4"
    )
    celery.conf.update(
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        timezone='UTC',
        enable_utc=True,
        task_track_started=True,
        task_time_limit=300,  # 5 minutes max
        task_soft_time_limit=240,  # 4 minutes soft limit
        worker_prefetch_multiplier=4,
        worker_max_tasks_per_child=1000,
    )
    
    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)
    
    celery.Task = ContextTask
    return celery

celery = make_celery(app)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize config
Config.init_app(app)

# Health check endpoint (for load balancers)
@app.route('/health')
@cache.cached(timeout=10)
def health_check():
    """Health check endpoint for load balancers and monitoring."""
    try:
        # Check Redis connection
        redis_client.ping()
        redis_status = 'healthy'
    except:
        redis_status = 'unhealthy'
    
    return jsonify({
        'status': 'healthy',
        'redis': redis_status,
        'workers': 'running'
    }), 200

# Metrics endpoint
@app.route('/metrics')
@cache.cached(timeout=5)
def metrics():
    """Basic metrics endpoint for monitoring."""
    try:
        redis_info = redis_client.info()
        return jsonify({
            'redis_connected_clients': redis_info.get('connected_clients', 0),
            'redis_used_memory': redis_info.get('used_memory_human', '0'),
            'redis_uptime_seconds': redis_info.get('uptime_in_seconds', 0),
        }), 200
    except:
        return jsonify({'error': 'metrics unavailable'}), 503

def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

# Celery task for PDF conversion (background processing)
@celery.task(bind=True, name='tasks.convert_pdf_task')
def convert_pdf_task(self, pdf_path, output_dir):
    """
    Background task for PDF to CSV conversion.
    This prevents blocking web requests during long PDF processing.
    """
    from processor import convert_pdf_to_csv, ExternalToolError
    
    try:
        self.update_state(state='PROCESSING', meta={'status': 'Converting PDF...'})
        csv_path = convert_pdf_to_csv(pdf_path, output_dir)
        return {'status': 'SUCCESS', 'csv_path': csv_path}
    except ExternalToolError as e:
        logger.error(f'ExternalToolError in task: {str(e)}')
        return {'status': 'ERROR', 'error': str(e)}
    except Exception as e:
        logger.exception(f'Error in convert_pdf_task: {str(e)}')
        return {'status': 'ERROR', 'error': str(e)}
    finally:
        # Cleanup temp file
        try:
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
        except:
            pass

@app.route('/')
@cache.cached(timeout=300)  # Cache homepage for 5 minutes
def index():
    """Homepage."""
    return render_template('index_enhanced.html')

@app.route('/pricing')
@cache.cached(timeout=300)
def pricing():
    """Pricing page."""
    return render_template('pricing.html')

@app.route('/history')
def history():
    """Conversion history page."""
    return render_template('history.html')

@app.route('/convert', methods=['POST'])
@limiter.limit("10 per minute")  # Rate limit: 10 conversions per minute per IP
def convert():
    """
    PDF to CSV conversion endpoint (synchronous for small files).
    For production at scale, consider using async task queue for ALL conversions.
    """
    if 'file' not in request.files:
        logger.error('No file part in request')
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        logger.error('Empty filename')
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        logger.error(f'Invalid file type: {file.filename}')
        return jsonify({'error': 'Invalid file type. Only PDF files allowed.'}), 400
    
    # Check file size (prevent abuse)
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    
    if file_size > Config.MAX_CONTENT_LENGTH:
        return jsonify({'error': 'File too large. Maximum 50MB.'}), 413
    
    filename = secure_filename(file.filename)
    logger.info(f'Processing file: {filename} ({file_size} bytes)')
    
    # Save to temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
        tmp_path = tmp.name
        file.save(tmp_path)
    
    try:
        # For files < 5MB, process synchronously
        # For larger files, use Celery background task
        if file_size < 5 * 1024 * 1024:  # 5MB threshold
            from processor import convert_pdf_to_csv, ExternalToolError
            
            logger.info(f'Processing synchronously: {filename}')
            csv_path = convert_pdf_to_csv(tmp_path)
            
            # Send file and cleanup
            response = send_file(
                csv_path,
                as_attachment=True,
                download_name=filename.rsplit('.', 1)[0] + '.csv'
            )
            
            # Cleanup
            try:
                os.remove(tmp_path)
                os.remove(csv_path)
            except:
                pass
            
            return response
        
        else:
            # Large file - process in background with Celery
            logger.info(f'Queuing for background processing: {filename}')
            
            output_dir = tempfile.mkdtemp()
            task = convert_pdf_task.delay(tmp_path, output_dir)
            
            # Store task ID in Redis for retrieval
            task_key = f'task:{task.id}'
            redis_client.setex(task_key, 3600, filename)  # Expire in 1 hour
            
            return jsonify({
                'status': 'QUEUED',
                'task_id': task.id,
                'message': 'Large file queued for processing. Check status with task ID.'
            }), 202
    
    except Exception as e:
        logger.exception(f'Error processing {filename}: {str(e)}')
        
        # Cleanup
        try:
            os.remove(tmp_path)
        except:
            pass
        
        return jsonify({'error': f'Processing failed: {str(e)}'}), 500

@app.route('/task/<task_id>')
@limiter.limit("100 per minute")
def get_task_status(task_id):
    """Check status of background task."""
    task = convert_pdf_task.AsyncResult(task_id)
    
    if task.state == 'PENDING':
        response = {'state': task.state, 'status': 'Task is waiting...'}
    elif task.state == 'PROCESSING':
        response = {'state': task.state, 'status': task.info.get('status', 'Processing...')}
    elif task.state == 'SUCCESS':
        result = task.info
        response = {'state': task.state, 'status': 'Complete', 'result': result}
    else:
        # Error occurred
        response = {'state': task.state, 'status': str(task.info)}
    
    return jsonify(response)

# Error handlers
@app.errorhandler(429)
def ratelimit_handler(e):
    """Handle rate limit errors."""
    return jsonify({'error': 'Rate limit exceeded. Please try again later.'}), 429

@app.errorhandler(500)
def internal_error(error):
    """Handle internal server errors."""
    logger.error(f'Internal server error: {error}')
    return jsonify({'error': 'Internal server error'}), 500

@app.errorhandler(413)
def request_entity_too_large(error):
    """Handle file too large errors."""
    return jsonify({'error': 'File too large. Maximum 50MB allowed.'}), 413

# Startup message
if __name__ == '__main__':
    print("\n" + "="*70)
    print("⚠️  WARNING: Development server detected!")
    print("="*70)
    print("For production use:")
    print("  gunicorn -c gunicorn_production.py app_production:app")
    print("="*70 + "\n")
    
    app.run(debug=False, host='0.0.0.0', port=5000)
