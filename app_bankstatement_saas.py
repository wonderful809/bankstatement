"""
Bank Statement Conversion SaaS Platform
Supports: PDF, CSV, Excel, OFX with Stripe integration
"""

import os
import time
import logging
import tempfile
import uuid
import json
from datetime import datetime, timedelta
from functools import wraps

from flask import Flask, render_template, request, send_file, redirect, url_for, flash, jsonify, session
from werkzeug.utils import secure_filename
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import stripe

# Import models and processor
from models_saas import db, bcrypt, User, Conversion, Payment, Subscription, Feedback
from processor_multiformat import convert_bank_statement, UnsupportedFormatError, ProcessorError
from config import Config

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Additional configurations
app.config['STRIPE_PUBLIC_KEY'] = os.getenv('STRIPE_PUBLIC_KEY', '')
app.config['STRIPE_SECRET_KEY'] = os.getenv('STRIPE_SECRET_KEY', '')
app.config['STRIPE_WEBHOOK_SECRET'] = os.getenv('STRIPE_WEBHOOK_SECRET', '')

# Initialize extensions
db.init_app(app)
bcrypt.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'

# Initialize Stripe
stripe.api_key = app.config['STRIPE_SECRET_KEY']

# Rate limiting
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per hour", "50 per minute"],
    storage_uri=Config.RATELIMIT_STORAGE_URL
)

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

# Create database tables
with app.app_context():
    db.create_all()
    app.logger.info("Database initialized")


# Pricing tiers configuration
PRICING_TIERS = {
    'free': {
        'name': 'Free',
        'price': 0,
        'pages': 50,
        'description': 'Try our service with 50 pages/month'
    },
    'starter': {
        'name': 'Starter',
        'price': 15,
        'pages': 500,
        'price_id': os.getenv('STRIPE_PRICE_ID_STARTER', ''),
        'description': 'Perfect for individuals'
    },
    'professional': {
        'name': 'Professional',
        'price': 30,
        'pages': 2000,
        'price_id': os.getenv('STRIPE_PRICE_ID_PROFESSIONAL', ''),
        'description': 'For small businesses'
    },
    'business': {
        'name': 'Business',
        'price': 50,
        'pages': 5000,
        'price_id': os.getenv('STRIPE_PRICE_ID_BUSINESS', ''),
        'description': 'For growing companies'
    }
}


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def subscription_required(f):
    """Decorator to check if user has active subscription"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this feature.', 'warning')
            return redirect(url_for('login'))
        
        # Free tier users can still use the service with limits
        # Just check if they have pages remaining
        if current_user.get_pages_remaining() <= 0:
            flash('You have reached your monthly page limit. Please upgrade your plan.', 'warning')
            return redirect(url_for('pricing'))
        
        return f(*args, **kwargs)
    return decorated_function


# ===== ROUTES =====

@app.route('/')
def index():
    """Landing page"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        full_name = request.form.get('full_name', '').strip()
        
        # Validation
        if not email or not password:
            flash('Email and password are required.', 'danger')
            return redirect(url_for('register'))
        
        if len(password) < 8:
            flash('Password must be at least 8 characters long.', 'danger')
            return redirect(url_for('register'))
        
        # Check if user exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already registered. Please log in.', 'danger')
            return redirect(url_for('login'))
        
        # Create new user
        user = User(
            email=email,
            full_name=full_name,
            subscription_tier='free',
            monthly_pages_limit=50
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        # Log in the user
        login_user(user)
        flash(f'Welcome, {full_name or email}! Your account has been created.', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            login_user(user, remember=True)
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard'))
        else:
            flash('Invalid email or password.', 'danger')
    
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    """User logout"""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))


@app.route('/dashboard')
@login_required
def dashboard():
    """User dashboard"""
    recent_conversions = Conversion.query.filter_by(user_id=current_user.id)\
        .order_by(Conversion.created_at.desc())\
        .limit(10).all()
    
    # Get statistics
    total_conversions = Conversion.query.filter_by(user_id=current_user.id, status='completed').count()
    total_pages = db.session.query(db.func.sum(Conversion.page_count))\
        .filter_by(user_id=current_user.id, status='completed').scalar() or 0
    
    stats = {
        'total_conversions': total_conversions,
        'total_pages': total_pages,
        'pages_used': current_user.monthly_pages_used,
        'pages_limit': current_user.monthly_pages_limit,
        'pages_remaining': current_user.get_pages_remaining(),
        'subscription_tier': current_user.subscription_tier.title(),
        'subscription_status': current_user.subscription_status
    }
    
    return render_template('dashboard.html', conversions=recent_conversions, stats=stats)


@app.route('/pricing')
def pricing():
    """Pricing page"""
    return render_template('pricing.html', 
                          pricing_tiers=PRICING_TIERS,
                          stripe_public_key=app.config['STRIPE_PUBLIC_KEY'])


@app.route('/convert', methods=['POST'])
@login_required
@subscription_required
@limiter.limit("20 per minute")
def convert():
    """Handle file conversion"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'}), 400
    
    # Get original filename and sanitize
    original_filename = secure_filename(file.filename)
    unique_filename = f"{uuid.uuid4().hex}_{original_filename}"
    upload_path = os.path.join(Config.UPLOAD_FOLDER, unique_filename)
    
    # Create conversion record
    conversion = Conversion(
        user_id=current_user.id,
        original_filename=original_filename,
        status='processing'
    )
    db.session.add(conversion)
    db.session.commit()
    
    try:
        # Save uploaded file
        file.save(upload_path)
        file_size = os.path.getsize(upload_path)
        
        # Detect format and estimate pages (for CSV/Excel/OFX, 1 page)
        file_format = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else ''
        
        # Estimate page count (for quota tracking)
        if file_format == 'pdf':
            try:
                import pdfplumber
                with pdfplumber.open(upload_path) as pdf:
                    page_count = len(pdf.pages)
            except:
                page_count = 1
        else:
            page_count = 1  # CSV, Excel, OFX count as 1 page
        
        # Check if user has enough pages
        if not current_user.can_convert(page_count):
            conversion.status = 'failed'
            conversion.error_message = 'Insufficient page quota'
            db.session.commit()
            os.remove(upload_path)
            return jsonify({
                'success': False,
                'error': f'Insufficient quota. You need {page_count} pages but have {current_user.get_pages_remaining()} remaining.'
            }), 400
        
        # Update conversion record
        conversion.file_size = file_size
        conversion.file_format = file_format
        conversion.page_count = page_count
        db.session.commit()
        
        # Process file
        start_time = time.time()
        result = convert_bank_statement(
            upload_path,
            filename=original_filename,
            tesseract_cmd=app.config.get('TESSERACT_CMD'),
            poppler_path=app.config.get('POPPLER_PATH')
        )
        processing_time = time.time() - start_time
        
        if result['success']:
            # Update conversion record
            conversion.status = 'completed'
            conversion.conversion_type = result.get('conversion_type', 'unknown')
            conversion.row_count = result.get('row_count', 0)
            conversion.processing_time = processing_time
            conversion.quality_score = result.get('quality_score', 0)
            conversion.quality_message = result.get('quality_message', '')
            conversion.completed_at = datetime.utcnow()
            
            # Deduct pages from user quota
            current_user.use_pages(page_count)
            
            db.session.commit()
            
            app.logger.info(f'Conversion successful: User {current_user.id}, File {original_filename}, '
                          f'Pages {page_count}, Rows {conversion.row_count}')
            
            # Send CSV file
            csv_path = result['csv_path']
            response = send_file(
                csv_path,
                as_attachment=True,
                download_name=original_filename.rsplit('.', 1)[0] + '.csv'
            )
            
            # Cleanup files after sending
            @response.call_on_close
            def cleanup():
                try:
                    os.remove(upload_path)
                    os.remove(csv_path)
                except Exception:
                    pass
            
            return response
        
        else:
            # Conversion failed
            conversion.status = 'failed'
            conversion.error_message = result.get('error', 'Unknown error')
            db.session.commit()
            
            os.remove(upload_path)
            
            app.logger.error(f'Conversion failed: User {current_user.id}, Error: {result.get("error")}')
            return jsonify({'success': False, 'error': result.get('error', 'Conversion failed')}), 500
    
    except Exception as e:
        conversion.status = 'failed'
        conversion.error_message = str(e)
        db.session.commit()
        
        try:
            os.remove(upload_path)
        except:
            pass
        
        app.logger.exception(f'Unexpected error during conversion: {str(e)}')
        return jsonify({'success': False, 'error': f'Error processing file: {str(e)}'}), 500


@app.route('/create-checkout-session', methods=['POST'])
@login_required
def create_checkout_session():
    """Create Stripe checkout session"""
    try:
        data = request.get_json()
        price_id = data.get('price_id')
        tier = data.get('tier')
        
        if not price_id or tier not in PRICING_TIERS:
            return jsonify({'error': 'Invalid pricing tier'}), 400
        
        # Create or get Stripe customer
        if not current_user.stripe_customer_id:
            customer = stripe.Customer.create(
                email=current_user.email,
                name=current_user.full_name,
                metadata={'user_id': current_user.id}
            )
            current_user.stripe_customer_id = customer.id
            db.session.commit()
        
        # Create checkout session
        checkout_session = stripe.checkout.Session.create(
            customer=current_user.stripe_customer_id,
            payment_method_types=['card'],
            line_items=[{
                'price': price_id,
                'quantity': 1,
            }],
            mode='subscription',
            success_url=url_for('payment_success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=url_for('pricing', _external=True),
            metadata={
                'user_id': current_user.id,
                'tier': tier
            }
        )
        
        return jsonify({'sessionId': checkout_session.id})
    
    except Exception as e:
        app.logger.exception(f'Error creating checkout session: {str(e)}')
        return jsonify({'error': str(e)}), 500


@app.route('/create-custom-checkout', methods=['POST'])
@login_required
def create_custom_checkout():
    """Create custom pricing checkout (for slider)"""
    try:
        data = request.get_json()
        amount = data.get('amount')  # Amount in dollars
        pages = data.get('pages')
        
        if not amount or not pages or amount < 15 or amount > 300:
            return jsonify({'error': 'Invalid amount'}), 400
        
        # Create or get Stripe customer
        if not current_user.stripe_customer_id:
            customer = stripe.Customer.create(
                email=current_user.email,
                name=current_user.full_name,
                metadata={'user_id': current_user.id}
            )
            current_user.stripe_customer_id = customer.id
            db.session.commit()
        
        # Create one-time payment checkout
        checkout_session = stripe.checkout.Session.create(
            customer=current_user.stripe_customer_id,
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': f'Custom Plan - {pages} pages/month',
                        'description': f'${amount}/month for {pages} pages'
                    },
                    'unit_amount': int(amount * 100),  # Convert to cents
                    'recurring': {'interval': 'month'}
                },
                'quantity': 1,
            }],
            mode='subscription',
            success_url=url_for('payment_success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=url_for('pricing', _external=True),
            metadata={
                'user_id': current_user.id,
                'tier': 'custom',
                'pages': pages
            }
        )
        
        return jsonify({'sessionId': checkout_session.id})
    
    except Exception as e:
        app.logger.exception(f'Error creating custom checkout: {str(e)}')
        return jsonify({'error': str(e)}), 500


@app.route('/payment-success')
@login_required
def payment_success():
    """Payment success page"""
    session_id = request.args.get('session_id')
    return render_template('payment_success.html', session_id=session_id)


@app.route('/webhook/stripe', methods=['POST'])
@limiter.exempt
def stripe_webhook():
    """Handle Stripe webhooks"""
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')
    webhook_secret = app.config['STRIPE_WEBHOOK_SECRET']
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
    except ValueError:
        return 'Invalid payload', 400
    except stripe.error.SignatureVerificationError:
        return 'Invalid signature', 400
    
    # Handle events
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        handle_checkout_completed(session)
    
    elif event['type'] == 'customer.subscription.updated':
        subscription = event['data']['object']
        handle_subscription_updated(subscription)
    
    elif event['type'] == 'customer.subscription.deleted':
        subscription = event['data']['object']
        handle_subscription_deleted(subscription)
    
    elif event['type'] == 'invoice.payment_succeeded':
        invoice = event['data']['object']
        handle_invoice_paid(invoice)
    
    elif event['type'] == 'invoice.payment_failed':
        invoice = event['data']['object']
        handle_invoice_failed(invoice)
    
    return jsonify({'status': 'success'}), 200


def handle_checkout_completed(session):
    """Handle successful checkout"""
    try:
        user_id = session['metadata'].get('user_id')
        tier = session['metadata'].get('tier')
        
        user = User.query.get(int(user_id))
        if not user:
            app.logger.error(f'User {user_id} not found for checkout session')
            return
        
        # Update user subscription
        user.subscription_tier = tier
        user.subscription_status = 'active'
        user.stripe_subscription_id = session.get('subscription')
        
        # Set page limits based on tier
        if tier == 'custom':
            user.monthly_pages_limit = int(session['metadata'].get('pages', 500))
        else:
            user.monthly_pages_limit = PRICING_TIERS.get(tier, {}).get('pages', 500)
        
        # Reset usage for new subscription
        user.monthly_pages_used = 0
        user.last_reset_date = datetime.utcnow()
        
        db.session.commit()
        app.logger.info(f'Subscription activated for user {user_id}: {tier}')
    
    except Exception as e:
        app.logger.exception(f'Error handling checkout: {str(e)}')


def handle_subscription_updated(subscription):
    """Handle subscription update"""
    try:
        customer_id = subscription['customer']
        user = User.query.filter_by(stripe_customer_id=customer_id).first()
        
        if user:
            user.subscription_status = subscription['status']
            db.session.commit()
            app.logger.info(f'Subscription updated for user {user.id}: {subscription["status"]}')
    
    except Exception as e:
        app.logger.exception(f'Error handling subscription update: {str(e)}')


def handle_subscription_deleted(subscription):
    """Handle subscription cancellation"""
    try:
        customer_id = subscription['customer']
        user = User.query.filter_by(stripe_customer_id=customer_id).first()
        
        if user:
            user.subscription_tier = 'free'
            user.subscription_status = 'cancelled'
            user.monthly_pages_limit = 50
            db.session.commit()
            app.logger.info(f'Subscription cancelled for user {user.id}')
    
    except Exception as e:
        app.logger.exception(f'Error handling subscription deletion: {str(e)}')


def handle_invoice_paid(invoice):
    """Handle successful invoice payment"""
    try:
        customer_id = invoice['customer']
        user = User.query.filter_by(stripe_customer_id=customer_id).first()
        
        if user:
            # Create payment record
            payment = Payment(
                user_id=user.id,
                stripe_invoice_id=invoice['id'],
                stripe_charge_id=invoice.get('charge'),
                amount=invoice['amount_paid'],
                currency=invoice['currency'],
                status='succeeded',
                description=f'Subscription payment - {user.subscription_tier}',
                receipt_url=invoice.get('hosted_invoice_url')
            )
            db.session.add(payment)
            db.session.commit()
            app.logger.info(f'Payment recorded for user {user.id}: ${invoice["amount_paid"]/100}')
    
    except Exception as e:
        app.logger.exception(f'Error handling invoice payment: {str(e)}')


def handle_invoice_failed(invoice):
    """Handle failed invoice payment"""
    try:
        customer_id = invoice['customer']
        user = User.query.filter_by(stripe_customer_id=customer_id).first()
        
        if user:
            user.subscription_status = 'past_due'
            db.session.commit()
            app.logger.warning(f'Payment failed for user {user.id}')
    
    except Exception as e:
        app.logger.exception(f'Error handling invoice failure: {str(e)}')


@app.route('/api/history')
@login_required
@limiter.limit("30 per minute")
def get_history():
    """Get conversion history"""
    try:
        limit = request.args.get('limit', 20, type=int)
        limit = min(max(limit, 1), 100)  # Clamp between 1 and 100
        
        conversions = Conversion.query.filter_by(user_id=current_user.id)\
            .order_by(Conversion.created_at.desc())\
            .limit(limit).all()
        
        return jsonify({'conversions': [c.to_dict() for c in conversions]})
    except Exception as e:
        app.logger.exception("Error fetching history")
        return jsonify({'error': 'Failed to fetch history'}), 500


@app.route('/api/stats')
@login_required
@limiter.limit("30 per minute")
def get_stats():
    """Get user statistics"""
    try:
        total = Conversion.query.filter_by(user_id=current_user.id, status='completed').count()
        total_pages = db.session.query(db.func.sum(Conversion.page_count))\
            .filter_by(user_id=current_user.id, status='completed').scalar() or 0
        total_rows = db.session.query(db.func.sum(Conversion.row_count))\
            .filter_by(user_id=current_user.id, status='completed').scalar() or 0
        
        return jsonify({
            'total_conversions': total,
            'total_pages': int(total_pages),
            'total_rows': int(total_rows),
            'pages_used': current_user.monthly_pages_used,
            'pages_limit': current_user.monthly_pages_limit,
            'pages_remaining': current_user.get_pages_remaining(),
            'subscription_tier': current_user.subscription_tier
        })
    except Exception as e:
        app.logger.exception("Error fetching stats")
        return jsonify({'error': 'Failed to fetch stats'}), 500


@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Resource not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    app.logger.exception("Internal server error")
    return jsonify({'error': 'An internal error occurred'}), 500


@app.route('/favicon.ico')
def favicon():
    return '', 204


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
