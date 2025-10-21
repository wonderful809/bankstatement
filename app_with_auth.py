"""
Flask App with Authentication
===============================

Enhanced version of app.py with user authentication (Sign In/Sign Up).
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
import os
from datetime import datetime, timedelta
import time

# Import modules
from config import Config
from processor import convert_pdf_to_csv
from auth_models import User, AnonymousUser

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
    return User.get_by_id(user_id)


# ============================================================================
# AUTHENTICATION ROUTES
# ============================================================================

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """User registration"""
    
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Validation
        if not all([name, email, password, confirm_password]):
            return render_template('signup.html', error="All fields are required")
        
        if password != confirm_password:
            return render_template('signup.html', error="Passwords do not match")
        
        # Create user
        user, message = User.create(email, password, name)
        
        if user:
            # Auto login
            login_user(user)
            flash('Account created successfully! Welcome to Bank Statement Converter.', 'success')
            return redirect(url_for('index'))
        else:
            return render_template('signup.html', error=message)
    
    return render_template('signup.html')


@app.route('/signin', methods=['GET', 'POST'])
def signin():
    """User login"""
    
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        remember = request.form.get('remember') == '1'
        
        if not all([email, password]):
            return render_template('signin.html', error="Email and password are required")
        
        # Authenticate
        user, message = User.authenticate(email, password)
        
        if user:
            login_user(user, remember=remember)
            
            # Redirect to next page or index
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            
            return redirect(url_for('index'))
        else:
            return render_template('signin.html', error=message)
    
    return render_template('signin.html')


@app.route('/logout')
@login_required
def logout():
    """User logout"""
    logout_user()
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('index'))


@app.route('/dashboard')
@login_required
def dashboard():
    """User dashboard"""
    usage = current_user.get_usage_info()
    return render_template('dashboard.html', user=current_user.to_dict(), usage=usage)


# ============================================================================
# MAIN ROUTES
# ============================================================================

@app.route('/')
def index():
    """Homepage"""
    return render_template('index.html')


@app.route('/pricing')
def pricing():
    """Pricing page"""
    return render_template('pricing.html')


@app.route('/convert', methods=['POST'])
@login_required
def convert():
    """Convert PDF to CSV - REQUIRES AUTHENTICATION"""
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not file.filename.lower().endswith('.pdf'):
        return jsonify({'error': 'Only PDF files are allowed'}), 400
    
    try:
        # Get PDF page count (simplified - you may want to use PyPDF2)
        pages = 2  # Placeholder - implement actual page counting
        
        # Check if user can convert
        if not current_user.can_convert(pages):
            usage = current_user.get_usage_info()
            return jsonify({
                'error': f"Page limit exceeded. You've used {usage['pages_used']} of {usage['pages_limit']} pages this month.",
                'upgrade_url': '/pricing'
            }), 403
        
        # Save uploaded file
        filename = secure_filename(file.filename)
        timestamp = int(time.time())
        unique_filename = f"{timestamp}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        file.save(filepath)
        
        # Convert PDF to CSV
        start_time = time.time()
        csv_path = convert_pdf_to_csv(filepath)
        processing_time = time.time() - start_time
        
        # Update user usage
        current_user.update_usage(pages)
        
        # Get updated usage
        usage = current_user.get_usage_info()
        
        # Return CSV file
        from flask import send_file
        return send_file(
            csv_path,
            as_attachment=True,
            download_name=f"{filename.replace('.pdf', '')}_transactions.csv",
            mimetype='text/csv'
        )
        
    except Exception as e:
        app.logger.error(f"Conversion error: {str(e)}")
        return jsonify({'error': f'Conversion failed: {str(e)}'}), 500


# ============================================================================
# API ROUTES
# ============================================================================

@app.route('/api/stats')
def api_stats():
    """Get conversion statistics"""
    
    stats = {
        'total_conversions': 5000,
        'total_rows': 125000,
        'avg_time': 5.2,
        'success_rate': 98.5
    }
    
    return jsonify(stats)


@app.route('/api/usage')
@login_required
def api_usage():
    """Get user usage information"""
    usage = current_user.get_usage_info()
    return jsonify(usage)


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(401)
def unauthorized(error):
    """Handle unauthorized access"""
    if request.is_json:
        return jsonify({'error': 'Authentication required'}), 401
    return redirect(url_for('signin', next=request.url))


@app.errorhandler(403)
def forbidden(error):
    """Handle forbidden access"""
    if request.is_json:
        return jsonify({'error': 'Access forbidden'}), 403
    return render_template('error.html', error='Access forbidden'), 403


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    if request.is_json:
        return jsonify({'error': 'Not found'}), 404
    return render_template('error.html', error='Page not found'), 404


@app.errorhandler(500)
def server_error(error):
    """Handle 500 errors"""
    if request.is_json:
        return jsonify({'error': 'Internal server error'}), 500
    return render_template('error.html', error='Internal server error'), 500


# ============================================================================
# RUN APP
# ============================================================================

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 Bank Statement Converter (with Authentication)")
    print("=" * 60)
    print(f"📍 Server: http://{app.config['HOST']}:{app.config['PORT']}")
    print(f"🔒 Authentication: Enabled")
    print(f"📦 Upload folder: {app.config['UPLOAD_FOLDER']}")
    print("=" * 60)
    print()
    
    app.run(
        host=app.config['HOST'],
        port=app.config['PORT'],
        debug=app.config['DEBUG']
    )
