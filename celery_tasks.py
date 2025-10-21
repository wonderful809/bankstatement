"""
Celery Tasks for Async PDF Processing
Handles CPU-intensive OCR and PDF conversion in background
"""
from celery import Celery
import os
from datetime import datetime

# Initialize Celery
celery = Celery(
    'bankstatement_tasks',
    broker=os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
    backend=os.getenv('REDIS_URL', 'redis://localhost:6379/0')
)

# Configure Celery
celery.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,  # 10 minutes max per task
    task_soft_time_limit=540,  # 9 minutes soft limit
    worker_prefetch_multiplier=1,  # Only fetch one task at a time
    worker_max_tasks_per_child=50,  # Restart worker after 50 tasks
)

@celery.task(bind=True, name='tasks.process_pdf_async')
def process_pdf_async(self, file_path, user_id, conversion_id):
    """
    Async task to process PDF file
    
    Args:
        file_path: Path to uploaded PDF file
        user_id: User ID who uploaded the file
        conversion_id: Database ID of the conversion record
    
    Returns:
        dict: Result with CSV data and metadata
    """
    try:
        # Update task state to PROCESSING
        self.update_state(
            state='PROCESSING',
            meta={'current': 0, 'total': 100, 'status': 'Starting PDF extraction...'}
        )
        
        # Import here to avoid circular imports
        from processor_enhanced import extract_and_convert
        from models import db, Conversion
        from app_saas import app
        
        with app.app_context():
            # Update conversion status
            conversion = Conversion.query.get(conversion_id)
            if not conversion:
                raise ValueError(f"Conversion {conversion_id} not found")
            
            conversion.status = 'processing'
            db.session.commit()
            
            # Update progress
            self.update_state(
                state='PROCESSING',
                meta={'current': 25, 'total': 100, 'status': 'Extracting text from PDF...'}
            )
            
            # Process the PDF
            start_time = datetime.now()
            result = extract_and_convert(file_path)
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Update progress
            self.update_state(
                state='PROCESSING',
                meta={'current': 75, 'total': 100, 'status': 'Generating CSV...'}
            )
            
            # Update conversion record
            conversion.status = 'completed'
            conversion.processing_time = processing_time
            conversion.row_count = len(result.get('data', []))
            conversion.extraction_method = result.get('method', 'unknown')
            conversion.confidence_score = result.get('confidence', 0)
            db.session.commit()
            
            # Clean up uploaded file
            if os.path.exists(file_path):
                os.remove(file_path)
            
            return {
                'status': 'success',
                'conversion_id': conversion_id,
                'csv_data': result.get('csv_content', ''),
                'row_count': conversion.row_count,
                'processing_time': processing_time,
                'method': conversion.extraction_method
            }
            
    except Exception as e:
        # Update conversion status to failed
        with app.app_context():
            conversion = Conversion.query.get(conversion_id)
            if conversion:
                conversion.status = 'failed'
                conversion.error_message = str(e)
                db.session.commit()
        
        # Re-raise exception so Celery can handle retry
        raise

@celery.task(name='tasks.cleanup_old_files')
def cleanup_old_files():
    """
    Periodic task to clean up old uploaded files
    Run this every hour via Celery Beat
    """
    from app_saas import app
    import time
    
    with app.app_context():
        upload_folder = app.config['UPLOAD_FOLDER']
        if not os.path.exists(upload_folder):
            return
        
        current_time = time.time()
        cleaned_count = 0
        
        for filename in os.listdir(upload_folder):
            file_path = os.path.join(upload_folder, filename)
            
            # Delete files older than 2 hours
            if os.path.isfile(file_path):
                file_age = current_time - os.path.getmtime(file_path)
                if file_age > 7200:  # 2 hours
                    try:
                        os.remove(file_path)
                        cleaned_count += 1
                    except Exception as e:
                        print(f"Error deleting {file_path}: {e}")
        
        return f"Cleaned up {cleaned_count} old files"

@celery.task(name='tasks.generate_statistics')
def generate_statistics():
    """
    Periodic task to pre-calculate statistics for dashboard
    Run this every 5 minutes via Celery Beat
    """
    from app_saas import app
    from models import db, Conversion
    
    with app.app_context():
        stats = {
            'total_conversions': Conversion.query.count(),
            'completed': Conversion.query.filter_by(status='completed').count(),
            'failed': Conversion.query.filter_by(status='failed').count(),
            'avg_processing_time': db.session.query(
                db.func.avg(Conversion.processing_time)
            ).filter_by(status='completed').scalar() or 0
        }
        
        # Cache these stats in Redis for fast access
        # (Will implement caching in next step)
        
        return stats

# Celery Beat Schedule (periodic tasks)
celery.conf.beat_schedule = {
    'cleanup-old-files': {
        'task': 'tasks.cleanup_old_files',
        'schedule': 3600.0,  # Every hour
    },
    'generate-statistics': {
        'task': 'tasks.generate_statistics',
        'schedule': 300.0,  # Every 5 minutes
    },
}
