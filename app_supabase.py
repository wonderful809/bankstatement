"""
Flask App with Supabase Authentication
========================================

Bank Statement Converter SaaS with Supabase Auth integration.
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash, send_file
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
import os
from datetime import datetime, timedelta
import time

# Import modules
from config import Config
from processor_enhanced import convert_pdf_to_csv
from auth_supabase import SupabaseAuth, User, AnonymousUser

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'signin'
login_manager.anonymous_user = AnonymousUser

@login_manager.user_loader
def load_user(user_id):
    """Load user from session"""
    # Get user data from session
    user_data = session.get('user_data')
    if user_data and user_data.get('id') == user_id:
        return User.from_supabase(user_data)
    return None


# ============================================================================
# AUTHENTICATION ROUTES
# ============================================================================

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """User registration with Supabase"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        name = request.form.get('name', '').strip()
        
        # Validation
        if not email or not password or not name:
            flash('All fields are required', 'error')
            return render_template('signup.html')
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('signup.html')
        
        if len(password) < 6:
            flash('Password must be at least 6 characters', 'error')
            return render_template('signup.html')
        
        # Create user with Supabase
        success, message, user_data = SupabaseAuth.sign_up(email, password, name)
        
        if success:
            # Store user data in session
            session['user_data'] = user_data
            session.permanent = True
            
            # Create User object and login
            user = User.from_supabase(user_data)
            login_user(user)
            
            flash('Account created successfully!', 'success')
            return redirect(url_for('index'))
        else:
            flash(message, 'error')
            return render_template('signup.html')
    
    return render_template('signup.html')


@app.route('/signin', methods=['GET', 'POST'])
def signin():
    """User login with Supabase"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        remember = request.form.get('remember', False)
        
        # Validation
        if not email or not password:
            flash('Email and password are required', 'error')
            return render_template('signin.html')
        
        # Sign in with Supabase
        success, message, user_data = SupabaseAuth.sign_in(email, password)
        
        if success:
            # Store user data in session
            session['user_data'] = user_data
            session.permanent = bool(remember)
            
            # Create User object and login
            user = User.from_supabase(user_data)
            login_user(user, remember=bool(remember))
            
            flash('Signed in successfully!', 'success')
            
            # Redirect to next page or index
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            flash(message, 'error')
            return render_template('signin.html')
    
    return render_template('signin.html')


@app.route('/logout')
@login_required
def logout():
    """User logout"""
    # Sign out from Supabase
    SupabaseAuth.sign_out()
    
    # Clear session
    session.pop('user_data', None)
    
    # Logout from Flask-Login
    logout_user()
    
    flash('Signed out successfully', 'success')
    return redirect(url_for('index'))


@app.route('/dashboard')
@login_required
def dashboard():
    """User dashboard"""
    usage_info = current_user.get_usage_info()
    
    return render_template('dashboard.html', 
                         user=current_user,
                         usage=usage_info)


# ============================================================================
# MAIN ROUTES
# ============================================================================

@app.route('/')
def index():
    """Homepage"""
    # Mock stats for display
    stats = {
        'total_conversions': 1250,
        'total_rows': 8960,
        'avg_time': 2
    }
    
    # Get usage info if user is logged in
    if current_user.is_authenticated:
        usage = current_user.get_usage_info()
    else:
        # Default usage for anonymous users
        usage = {
            'plan': 'free',
            'pages_used': 0,
            'pages_limit': 5,
            'pages_remaining': 5,
            'usage_percentage': 0
        }
    
    return render_template('index_enhanced.html', stats=stats, usage=usage)


@app.route('/pricing')
def pricing():
    """Pricing page"""
    return render_template('pricing.html')


@app.route('/convert', methods=['POST'])
@login_required
def convert():
    """Convert PDF bank statement to CSV"""
    try:
        # Check if file is present
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not file.filename.lower().endswith('.pdf'):
            return jsonify({'error': 'Only PDF files are allowed'}), 400
        
        # Secure the filename
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_filename = f"{timestamp}_{filename}"
        
        # Save uploaded file
        upload_folder = app.config['UPLOAD_FOLDER']
        os.makedirs(upload_folder, exist_ok=True)
        
        pdf_path = os.path.join(upload_folder, unique_filename)
        file.save(pdf_path)
        
        # Get bank type from form
        bank_type = request.form.get('bank_type', 'auto')
        
        # Convert PDF to CSV
        start_time = time.time()
        result = convert_pdf_to_csv(pdf_path, bank_type)
        processing_time = time.time() - start_time
        
        if result['status'] == 'success':
            # Get page count (estimate)
            pages = result.get('metadata', {}).get('pages', 1)
            
            # Check if user can convert
            if not current_user.can_convert(pages):
                # Clean up files
                os.remove(pdf_path)
                if os.path.exists(result['csv_path']):
                    os.remove(result['csv_path'])
                
                usage_info = current_user.get_usage_info()
                return jsonify({
                    'error': f"Page limit exceeded. You've used {usage_info['pages_used']}/{usage_info['pages_limit']} pages.",
                    'usage': usage_info
                }), 403
            
            # Update usage
            current_user.update_usage(pages)
            
            # Update session
            user_data = session.get('user_data', {})
            user_data['pages_used'] = current_user.pages_used
            session['user_data'] = user_data
            
            # Get quality information
            quality = result.get('quality', {})
            confidence = quality.get('confidence', 0)
            quality_message = quality.get('message', '')
            
            # Send CSV file with quality info in headers
            response = send_file(
                result['csv_path'],
                as_attachment=True,
                download_name=f"{filename.replace('.pdf', '')}.csv",
                mimetype='text/csv'
            )
            
            # Add quality and metadata headers
            response.headers['X-Quality-Confidence'] = str(round(confidence, 1))
            response.headers['X-Quality-Message'] = quality_message
            response.headers['X-Row-Count'] = str(result.get('row_count', 0))
            response.headers['X-Processing-Time'] = str(round(processing_time, 2))
            response.headers['X-Pages-Processed'] = str(pages)
            
            # Add quality warning if confidence is low
            if confidence < 60:
                response.headers['X-Quality-Warning'] = '⚠️ Some data may need manual review.'
            
            return response
        else:
            return jsonify({
                'status': 'error',
                'error': result.get('error', 'Unknown error')
            }), 500
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500


# ============================================================================
# API ROUTES
# ============================================================================

@app.route('/api/stats')
def api_stats():
    """Get conversion statistics"""
    # Mock stats for now
    stats = {
        'total_conversions': 1250,
        'total_users': 342,
        'total_pages': 8960,
        'success_rate': 98.5
    }
    return jsonify(stats)


@app.route('/api/usage')
@login_required
def api_usage():
    """Get current user's usage statistics"""
    usage_info = current_user.get_usage_info()
    return jsonify(usage_info)


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(401)
def unauthorized(error):
    """Handle unauthorized access"""
    flash('Please sign in to access this page', 'error')
    return redirect(url_for('signin', next=request.url))


@app.errorhandler(403)
def forbidden(error):
    """Handle forbidden access"""
    return render_template('error.html', error='Access forbidden'), 403


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return render_template('error.html', error='Page not found'), 404


@app.errorhandler(500)
def server_error(error):
    """Handle 500 errors"""
    return render_template('error.html', error='Internal server error'), 500


# ============================================================================
# RUN APP
# ============================================================================

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 Bank Statement Converter (Supabase Auth)")
    print("=" * 60)
    print(f"📍 Server: http://{app.config['HOST']}:{app.config['PORT']}")
    print(f"🔒 Authentication: Supabase")
    print(f"📦 Upload folder: {app.config['UPLOAD_FOLDER']}")
    print("=" * 60)
    print()
    
    app.run(
        host=app.config['HOST'],
        port=app.config['PORT'],
        debug=app.config['DEBUG']
    )
