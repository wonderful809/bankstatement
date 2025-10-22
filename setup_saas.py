#!/usr/bin/env python
"""
Setup script for BankStatementAI SaaS Platform
Helps with initial configuration and database setup
"""

import os
import sys
import secrets
from pathlib import Path


def print_header(text):
    """Print formatted header"""
    print("\n" + "="*60)
    print(f"  {text}")
    print("="*60 + "\n")


def print_success(text):
    """Print success message"""
    print(f"✅ {text}")


def print_error(text):
    """Print error message"""
    print(f"❌ {text}")


def print_warning(text):
    """Print warning message"""
    print(f"⚠️  {text}")


def print_info(text):
    """Print info message"""
    print(f"ℹ️  {text}")


def check_python_version():
    """Check if Python version is 3.8+"""
    print_header("Checking Python Version")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 8:
        print_success(f"Python {version.major}.{version.minor}.{version.micro} detected")
        return True
    else:
        print_error(f"Python 3.8+ required. You have {version.major}.{version.minor}.{version.micro}")
        return False


def check_dependencies():
    """Check if required packages are installed"""
    print_header("Checking Dependencies")
    
    required_packages = [
        'flask',
        'flask_sqlalchemy',
        'flask_login',
        'flask_bcrypt',
        'stripe',
        'pdfplumber',
        'pandas',
        'openpyxl',
        'ofxparse'
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package)
            print_success(f"{package} is installed")
        except ImportError:
            print_error(f"{package} is missing")
            missing.append(package)
    
    if missing:
        print_warning("\nInstall missing packages with:")
        print("pip install -r requirements.txt")
        return False
    
    return True


def create_env_file():
    """Create .env file from template"""
    print_header("Setting Up Environment")
    
    env_path = Path('.env')
    env_example_path = Path('.env.example')
    
    if env_path.exists():
        response = input("\n.env file already exists. Overwrite? (y/N): ")
        if response.lower() != 'y':
            print_info("Keeping existing .env file")
            return True
    
    if not env_example_path.exists():
        print_error(".env.example not found!")
        return False
    
    # Generate secret key
    secret_key = secrets.token_hex(32)
    
    # Read template
    with open(env_example_path, 'r') as f:
        content = f.read()
    
    # Replace secret key
    content = content.replace('your-secret-key-here-generate-with-python-secrets', secret_key)
    
    # Write .env
    with open(env_path, 'w') as f:
        f.write(content)
    
    print_success(".env file created with generated secret key")
    print_warning("\nIMPORTANT: Update the following in .env:")
    print("  - STRIPE_PUBLIC_KEY")
    print("  - STRIPE_SECRET_KEY")
    print("  - STRIPE_WEBHOOK_SECRET")
    print("  - STRIPE_PRICE_ID_STARTER")
    print("  - STRIPE_PRICE_ID_PROFESSIONAL")
    print("  - STRIPE_PRICE_ID_BUSINESS")
    
    return True


def create_directories():
    """Create necessary directories"""
    print_header("Creating Directories")
    
    directories = ['uploads', 'instance']
    
    for directory in directories:
        path = Path(directory)
        if not path.exists():
            path.mkdir(parents=True)
            print_success(f"Created {directory}/ directory")
        else:
            print_info(f"{directory}/ directory already exists")
    
    return True


def initialize_database():
    """Initialize the database"""
    print_header("Initializing Database")
    
    try:
        from app_bankstatement_saas import app, db
        
        with app.app_context():
            # Create all tables
            db.create_all()
            print_success("Database tables created successfully")
            
            # Show table info
            from models_saas import User, Conversion, Payment, Subscription, Feedback
            tables = [User, Conversion, Payment, Subscription, Feedback]
            print_info(f"\nCreated {len(tables)} tables:")
            for table in tables:
                print(f"  - {table.__tablename__}")
        
        return True
    except Exception as e:
        print_error(f"Database initialization failed: {str(e)}")
        return False


def create_test_user():
    """Create a test user"""
    print_header("Creating Test User")
    
    response = input("\nCreate a test user? (y/N): ")
    if response.lower() != 'y':
        print_info("Skipping test user creation")
        return True
    
    try:
        from app_bankstatement_saas import app, db
        from models_saas import User
        
        email = input("Email (default: test@example.com): ").strip() or "test@example.com"
        password = input("Password (default: password123): ").strip() or "password123"
        full_name = input("Full Name (default: Test User): ").strip() or "Test User"
        
        with app.app_context():
            # Check if user exists
            existing = User.query.filter_by(email=email).first()
            if existing:
                print_warning(f"User {email} already exists")
                return True
            
            # Create user
            user = User(
                email=email,
                full_name=full_name,
                subscription_tier='free',
                monthly_pages_limit=50
            )
            user.set_password(password)
            
            db.session.add(user)
            db.session.commit()
            
            print_success(f"Test user created: {email}")
            print_info(f"Password: {password}")
            print_info(f"Tier: Free (50 pages/month)")
        
        return True
    except Exception as e:
        print_error(f"Failed to create test user: {str(e)}")
        return False


def show_stripe_setup():
    """Show Stripe setup instructions"""
    print_header("Stripe Setup Instructions")
    
    print("""
To complete the setup, you need to configure Stripe:

1. Create a Stripe account (if you don't have one):
   https://dashboard.stripe.com/register

2. Get your API keys (TEST MODE):
   https://dashboard.stripe.com/test/apikeys
   
   Copy:
   - Publishable key (pk_test_...)
   - Secret key (sk_test_...)

3. Create Products & Prices:
   https://dashboard.stripe.com/test/products
   
   Create 3 products:
   a) Starter Plan - $15/month (500 pages)
   b) Professional Plan - $30/month (2000 pages)
   c) Business Plan - $50/month (5000 pages)
   
   Copy the Price IDs for each (price_...)

4. Setup Webhook (for testing):
   
   Option A: Stripe CLI (recommended)
   $ stripe login
   $ stripe listen --forward-to localhost:5000/webhook/stripe
   
   Option B: Dashboard (for deployed apps)
   https://dashboard.stripe.com/test/webhooks
   Add endpoint: http://your-domain.com/webhook/stripe
   
   Copy the Webhook signing secret (whsec_...)

5. Update .env file with all the keys and IDs

See QUICK_START_SAAS.md for detailed instructions.
""")


def show_next_steps():
    """Show next steps"""
    print_header("Setup Complete! 🎉")
    
    print("""
Your BankStatementAI SaaS platform is ready!

Next Steps:

1. Configure Stripe (see instructions above)
   
2. Update .env with Stripe keys:
   $ nano .env  # or use your favorite editor

3. Start the application:
   $ python app_bankstatement_saas.py

4. Visit http://localhost:5000

5. Test the platform:
   - Register a new account
   - Upload a bank statement
   - Try the Stripe checkout (use test card: 4242 4242 4242 4242)

For detailed instructions, see:
- QUICK_START_SAAS.md (5-minute guide)
- README_SAAS.md (full documentation)

Need help? Create an issue on GitHub or contact support.

Happy converting! 🚀
""")


def main():
    """Main setup function"""
    print("""
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║           BankStatementAI SaaS Setup Wizard              ║
║                                                           ║
║     Professional Bank Statement Conversion Platform       ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
    """)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Check dependencies
    if not check_dependencies():
        print_warning("\nPlease install dependencies first:")
        print("pip install -r requirements.txt")
        response = input("\nContinue anyway? (y/N): ")
        if response.lower() != 'y':
            sys.exit(1)
    
    # Create .env file
    if not create_env_file():
        sys.exit(1)
    
    # Create directories
    if not create_directories():
        sys.exit(1)
    
    # Initialize database
    if not initialize_database():
        sys.exit(1)
    
    # Create test user
    create_test_user()
    
    # Show Stripe setup
    show_stripe_setup()
    
    # Show next steps
    show_next_steps()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nSetup cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print_error(f"Setup failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
