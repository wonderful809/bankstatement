import os
import tempfile
import uuid
import logging
import json
import time
from datetime import datetime, timedelta
from threading import Thread
from flask import Flask, render_template, request, send_file, redirect, url_for, flash, jsonify, session
from werkzeug.utils import secure_filename
from config import Config
from processor import convert_pdf_to_csv, ExternalToolError
import pdfplumber

app = Flask(__name__)
app.config.from_object(Config)

# Initialize config
Config.init_app(app)

# Configure logging
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL.upper(), logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
app.logger.setLevel(getattr(logging, Config.LOG_LEVEL.upper(), logging.INFO))

# In-memory storage for conversion history and stats
conversion_history = []
stats = {
    'total_conversions': 5000,
    'total_rows': 125000,
    'total_processing_time': 15000.0  # 5000 conversions * 3 seconds average
}

# Track user usage (session_id -> {pages_used, last_reset, plan})
user_usage = {}

# Free tier limits
FREE_PAGES_PER_MONTH = 5

# Track files for auto-deletion
file_cleanup_queue = []


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS


def get_user_id():
    """Get or create a unique user session ID"""
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())
    return session['user_id']


def get_user_usage(user_id):
    """Get user usage data, reset if new month"""
    if user_id not in user_usage:
        user_usage[user_id] = {
            'pages_used': 0,
            'last_reset': datetime.now(),
            'plan': 'free'
        }
    
    # Check if we need to reset (new month)
    user_data = user_usage[user_id]
    now = datetime.now()
    if now.month != user_data['last_reset'].month or now.year != user_data['last_reset'].year:
        user_data['pages_used'] = 0
        user_data['last_reset'] = now
    
    return user_data


def count_pdf_pages(pdf_path):
    """Count the number of pages in a PDF"""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            return len(pdf.pages)
    except Exception as e:
        app.logger.error(f"Error counting PDF pages: {e}")
        return 1  # Default to 1 page if error


def check_page_limit(user_id, pdf_pages):
    """Check if user has enough pages remaining"""
    user_data = get_user_usage(user_id)
    
    # If user has a paid plan, allow unlimited
    if user_data['plan'] != 'free':
        return True, user_data['pages_used'], None
    
    # Check free tier limit
    pages_remaining = FREE_PAGES_PER_MONTH - user_data['pages_used']
    
    if user_data['pages_used'] + pdf_pages > FREE_PAGES_PER_MONTH:
        return False, user_data['pages_used'], pages_remaining
    
    return True, user_data['pages_used'], pages_remaining


def update_page_usage(user_id, pages_used):
    """Update the page count for a user"""
    user_data = get_user_usage(user_id)
    user_data['pages_used'] += pages_used


def cleanup_old_files():
    """Background task to delete files after 1 hour"""
    while True:
        try:
            current_time = time.time()
            files_to_remove = []
            
            for file_info in file_cleanup_queue:
                if current_time - file_info['timestamp'] > 3600:  # 1 hour
                    try:
                        if os.path.exists(file_info['path']):
                            os.remove(file_info['path'])
                            app.logger.info(f"Auto-deleted file: {file_info['path']}")
                    except Exception as e:
                        app.logger.error(f"Failed to auto-delete {file_info['path']}: {e}")
                    files_to_remove.append(file_info)
            
            # Remove from queue
            for file_info in files_to_remove:
                file_cleanup_queue.remove(file_info)
            
            time.sleep(300)  # Check every 5 minutes
        except Exception as e:
            app.logger.error(f"Cleanup thread error: {e}")
            time.sleep(60)


# Start cleanup thread
cleanup_thread = Thread(target=cleanup_old_files, daemon=True)
cleanup_thread.start()


@app.route('/')
def index():
    # Get user ID and usage
    user_id = get_user_id()
    user_data = get_user_usage(user_id)
    
    # Calculate average time in minutes
    avg_time_seconds = (stats['total_processing_time'] / stats['total_conversions'] 
                       if stats['total_conversions'] > 0 else 0)
    avg_time_minutes = max(1, round(avg_time_seconds / 60))  # At least 1 minute
    
    display_stats = {
        'total_conversions': stats['total_conversions'],
        'total_rows': stats['total_rows'],
        'avg_time': avg_time_minutes
    }
    
    # Add usage info
    usage_info = {
        'pages_used': user_data['pages_used'],
        'pages_limit': FREE_PAGES_PER_MONTH,
        'pages_remaining': FREE_PAGES_PER_MONTH - user_data['pages_used'],
        'plan': user_data['plan']
    }
    
    return render_template('index_enhanced.html', stats=display_stats, usage=usage_info)


@app.route('/convert', methods=['POST'])
def convert():
    if 'file' not in request.files:
        app.logger.error('No file part in request')
        flash('No file part', 'error')
        return redirect(url_for('index'))
    file = request.files['file']
    if file.filename == '':
        app.logger.error('Empty filename')
        flash('No selected file', 'error')
        return redirect(url_for('index'))
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        app.logger.info(f'Processing file: {filename}')
        start_time = time.time()
        
        # Get user ID
        user_id = get_user_id()
        
        # write to a secure temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            tmp_name = tmp.name
            file.save(tmp_name)
        app.logger.info(f'Saved to temp file: {tmp_name}')
        
        # Count PDF pages
        pdf_pages = count_pdf_pages(tmp_name)
        app.logger.info(f'PDF has {pdf_pages} pages')
        
        # Check page limit
        can_convert, pages_used, pages_remaining = check_page_limit(user_id, pdf_pages)
        
        if not can_convert:
            # Clean up temp file
            try:
                os.remove(tmp_name)
            except:
                pass
            
            app.logger.warning(f'User {user_id} exceeded page limit: {pages_used}/{FREE_PAGES_PER_MONTH}')
            flash(f'⚠️ You have used all {FREE_PAGES_PER_MONTH} free pages this month! This PDF has {pdf_pages} pages. Please upgrade to a paid plan to continue converting.', 'error')
            return redirect(url_for('pricing'))
        
        try:
            app.logger.info('Starting conversion...')
            csv_path = convert_pdf_to_csv(tmp_name)
            processing_time = time.time() - start_time
            app.logger.info(f'Conversion successful, CSV at: {csv_path}')
            
            # Update page usage
            update_page_usage(user_id, pdf_pages)
            app.logger.info(f'Updated usage for user {user_id}: +{pdf_pages} pages')
            
            # Count rows in CSV
            try:
                with open(csv_path, 'r', encoding='utf-8') as f:
                    row_count = sum(1 for line in f) - 1  # Exclude header
            except:
                row_count = 0
            
            # Update stats
            stats['total_conversions'] += 1
            stats['total_rows'] += row_count
            stats['total_processing_time'] += processing_time
            
            # Add to conversion history
            conversion_record = {
                'id': str(uuid.uuid4()),
                'filename': filename,
                'timestamp': datetime.now().isoformat(),
                'status': 'success',
                'rows_processed': row_count,
                'processing_time': round(processing_time, 2),
                'file_size': os.path.getsize(tmp_name),
                'pages': pdf_pages
            }
            conversion_history.insert(0, conversion_record)  # Add to beginning
            
            # Keep only last 100 records
            if len(conversion_history) > 100:
                conversion_history.pop()
            
            # Schedule CSV for auto-deletion after 1 hour
            file_cleanup_queue.append({
                'path': csv_path,
                'timestamp': time.time()
            })
            
            # send file and then delete CSV
            return send_file(csv_path, as_attachment=True, download_name=filename.rsplit('.',1)[0]+'.csv')
        except ExternalToolError as e:
            app.logger.error(f'ExternalToolError: {str(e)}')
            processing_time = time.time() - start_time
            
            # Add failed conversion to history
            conversion_record = {
                'id': str(uuid.uuid4()),
                'filename': filename,
                'timestamp': datetime.now().isoformat(),
                'status': 'failed',
                'error': str(e),
                'processing_time': round(processing_time, 2)
            }
            conversion_history.insert(0, conversion_record)
            
            flash(str(e) + ' See README for installation instructions.', 'error')
            return redirect(url_for('index')), 400
        except Exception as e:
            app.logger.exception(f'Unexpected error: {str(e)}')
            processing_time = time.time() - start_time
            
            # Add failed conversion to history
            conversion_record = {
                'id': str(uuid.uuid4()),
                'filename': filename,
                'timestamp': datetime.now().isoformat(),
                'status': 'failed',
                'error': str(e),
                'processing_time': round(processing_time, 2)
            }
            conversion_history.insert(0, conversion_record)
            
            flash(f'Error processing PDF: {str(e)}', 'error')
            return redirect(url_for('index')), 500
        finally:
            try:
                os.remove(tmp_name)
                app.logger.info(f'Cleaned up temp file: {tmp_name}')
            except Exception as cleanup_err:
                app.logger.warning(f'Failed to cleanup temp file: {cleanup_err}')
    else:
        app.logger.error(f'Invalid file type for file: {file.filename}')
        flash('Invalid file type. Please upload a PDF.', 'error')
        return redirect(url_for('index'))


@app.route('/pricing')
def pricing():
    """Pricing page route"""
    return render_template('pricing.html')


@app.route('/history')
def history():
    """Conversion history page"""
    return render_template('history.html', conversions=conversion_history)


@app.route('/api/stats')
def api_stats():
    """API endpoint for stats"""
    # Get user usage info
    user_id = get_user_id()
    user_data = get_user_usage(user_id)
    
    avg_time_seconds = (stats['total_processing_time'] / stats['total_conversions'] 
                       if stats['total_conversions'] > 0 else 0)
    avg_time_minutes = max(1, round(avg_time_seconds / 60))  # At least 1 minute
    
    return jsonify({
        'total_conversions': stats['total_conversions'],
        'total_rows': stats['total_rows'],
        'avg_time': avg_time_minutes,
        'avg_processing_time': round(avg_time_seconds, 2),
        'recent_conversions': len(conversion_history),
        'user_usage': {
            'pages_used': user_data['pages_used'],
            'pages_limit': FREE_PAGES_PER_MONTH,
            'pages_remaining': FREE_PAGES_PER_MONTH - user_data['pages_used'],
            'plan': user_data['plan']
        }
    })


@app.route('/dashboard')
def dashboard():
    """Admin dashboard"""
    avg_time = (stats['total_processing_time'] / stats['total_conversions'] 
                if stats['total_conversions'] > 0 else 0)
    
    dashboard_stats = {
        'total_conversions': stats['total_conversions'],
        'total_rows': stats['total_rows'],
        'avg_processing_time': round(avg_time, 2),
        'files_pending_deletion': len(file_cleanup_queue),
        'recent_conversions': conversion_history[:10]  # Last 10
    }
    
    return render_template('dashboard.html', stats=dashboard_stats)


@app.route('/upgrade-plan', methods=['POST'])
def upgrade_plan():
    """Upgrade user plan (simulated for demo)"""
    user_id = get_user_id()
    plan = request.form.get('plan', 'starter')
    
    if user_id in user_usage:
        user_usage[user_id]['plan'] = plan
        flash(f'✅ Successfully upgraded to {plan.title()} plan! You now have unlimited pages.', 'success')
    
    return redirect(url_for('index'))


@app.route('/reset-usage', methods=['POST'])
def reset_usage():
    """Reset user usage (for testing)"""
    user_id = get_user_id()
    
    if user_id in user_usage:
        user_usage[user_id]['pages_used'] = 0
        user_usage[user_id]['plan'] = 'free'
        flash('✅ Usage reset successfully!', 'success')
    
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True)
