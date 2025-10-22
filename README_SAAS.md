# BankStatementAI - Professional SaaS Platform

A comprehensive SaaS web application that converts bank statements from various formats (PDF, CSV, Excel, OFX) into standardized, clean data formats with high accuracy.

## 🌟 Features

### Core Functionality
- **Multi-Format Support**: Process PDF, CSV, Excel (XLSX/XLS), and OFX files
- **AI-Powered Extraction**: Advanced OCR and parsing with 95%+ accuracy
- **Smart Categorization**: Automatic transaction type detection and categorization
- **High Performance**: Process hundreds of pages in seconds

### User Management
- **User Authentication**: Secure login/register with bcrypt password hashing
- **Subscription Tiers**: Free, Starter, Professional, Business, and Custom plans
- **Usage Tracking**: Monthly page quotas with automatic reset
- **Dashboard**: Beautiful user interface to track conversions and usage

### Payment Integration
- **Stripe Integration**: Secure payment processing with test mode support
- **Multiple Plans**: 
  - Free: 50 pages/month
  - Starter: $15/month - 500 pages
  - Professional: $30/month - 2000 pages  
  - Business: $50/month - 5000 pages
  - Custom: $15-$300/month with slider
- **Subscription Management**: Automatic billing, upgrades, and cancellations
- **Webhook Support**: Real-time subscription updates

### Security
- **Bank-Grade Security**: End-to-end encryption
- **File Privacy**: Automatic file deletion after processing
- **Rate Limiting**: Protection against abuse
- **Session Management**: Secure cookie-based sessions
- **CSRF Protection**: Built-in Flask security features

## 🎨 Design

Professional SaaS interface with modern color scheme:
- Primary: #2563EB (professional blue)
- Secondary: #059669 (success green)
- Background: #F8FAFC (light grey)
- Text: #1E293B (slate)
- Accent: #7C3AED (purple)
- Warning: #F59E0B (amber)

Inspired by Plaid and Mercury Bank's clean, professional design.

## 📋 Prerequisites

### Required
- **Python 3.8+**
- **pip** (Python package manager)

### Optional (for PDF OCR processing)
- **Tesseract OCR**: Required for scanned PDFs ([Installation Guide](https://github.com/UB-Mannheim/tesseract/wiki))
- **Poppler**: Required for PDF to image conversion ([Windows](https://github.com/oschwartz10612/poppler-windows/releases))

### Stripe Account
- Create a free account at [stripe.com](https://stripe.com)
- Get your API keys from the Stripe Dashboard
- Set up webhook endpoint for subscription events

## 🚀 Quick Start

### 1. Clone and Setup

```bash
git clone <your-repo-url>
cd <your-repo-directory>

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env and configure:
# 1. Generate secret key:
python -c "import secrets; print(secrets.token_hex(32))"

# 2. Add Stripe keys (from https://dashboard.stripe.com/apikeys)
# 3. Configure other settings as needed
```

### 3. Set Up Stripe

#### Create Products in Stripe Dashboard

1. Go to [Stripe Products](https://dashboard.stripe.com/products)
2. Create three recurring products:

**Starter Plan**
- Name: Starter
- Price: $15/month
- Copy the Price ID to `.env` as `STRIPE_PRICE_ID_STARTER`

**Professional Plan**
- Name: Professional
- Price: $30/month
- Copy the Price ID to `.env` as `STRIPE_PRICE_ID_PROFESSIONAL`

**Business Plan**
- Name: Business
- Price: $50/month
- Copy the Price ID to `.env` as `STRIPE_PRICE_ID_BUSINESS`

#### Set Up Webhook

1. Go to [Stripe Webhooks](https://dashboard.stripe.com/webhooks)
2. Click "Add endpoint"
3. URL: `http://your-domain.com/webhook/stripe`
4. Events to listen for:
   - `checkout.session.completed`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.payment_succeeded`
   - `invoice.payment_failed`
5. Copy the Webhook Secret to `.env` as `STRIPE_WEBHOOK_SECRET`

### 4. Initialize Database

```bash
python -c "from app_bankstatement_saas import app, db; app.app_context().push(); db.create_all(); print('Database initialized!')"
```

### 5. Run the Application

```bash
# Development mode
python app_bankstatement_saas.py

# Production mode (with gunicorn)
gunicorn -c gunicorn_config.py app_bankstatement_saas:app
```

Visit: http://localhost:5000

## 📁 Project Structure

```
.
├── app_bankstatement_saas.py    # Main Flask application
├── models_saas.py               # Database models (User, Subscription, Payment, etc.)
├── processor_multiformat.py     # Multi-format file processor
├── processor_enhanced.py        # Enhanced PDF processor with OCR
├── config.py                    # Configuration management
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment variables template
├── .env                         # Your environment variables (not in git)
│
├── templates/                   # HTML templates
│   ├── base.html               # Base template with navigation
│   ├── index.html              # Landing page
│   ├── dashboard.html          # User dashboard
│   ├── pricing.html            # Pricing page with plans
│   ├── login.html              # Login page
│   ├── register.html           # Registration page
│   └── payment_success.html    # Payment confirmation
│
├── static/                      # Static assets
│   ├── css/
│   │   └── style.css           # Main stylesheet
│   └── js/
│       └── main.js             # JavaScript utilities
│
└── uploads/                     # Temporary file storage (auto-created)
```

## 🔧 Configuration

### Environment Variables

Key configurations in `.env`:

```bash
# Flask
FLASK_SECRET_KEY=<generate-with-secrets>
FLASK_ENV=development
FLASK_DEBUG=True

# Database
DATABASE_URI=sqlite:///bankstatements_saas.db

# Stripe (REQUIRED)
STRIPE_PUBLIC_KEY=pk_test_...
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_ID_STARTER=price_...
STRIPE_PRICE_ID_PROFESSIONAL=price_...
STRIPE_PRICE_ID_BUSINESS=price_...

# OCR Tools (Optional)
TESSERACT_CMD=/path/to/tesseract
POPPLER_PATH=/path/to/poppler/bin
```

### Database

Development: SQLite (default, no setup needed)
```bash
DATABASE_URI=sqlite:///bankstatements_saas.db
```

Production: PostgreSQL (recommended)
```bash
DATABASE_URI=postgresql://user:password@localhost:5432/dbname
```

## 💳 Stripe Test Mode

The application is configured for Stripe test mode by default.

### Test Cards

Use these test card numbers:
- **Success**: `4242 4242 4242 4242`
- **Decline**: `4000 0000 0000 0002`
- **3D Secure**: `4000 0025 0000 3155`

Any future expiry date and any 3-digit CVC.

### Testing Webhooks Locally

```bash
# Install Stripe CLI
# https://stripe.com/docs/stripe-cli

# Login to Stripe
stripe login

# Forward webhooks to local server
stripe listen --forward-to localhost:5000/webhook/stripe

# Copy the webhook signing secret to .env
```

## 🎯 Usage

### For Users

1. **Register**: Create a free account (50 pages/month)
2. **Upload**: Drag and drop your bank statement
3. **Convert**: AI processes and extracts data
4. **Download**: Get clean CSV with categorized transactions
5. **Upgrade**: Choose a paid plan for more pages

### For Developers

#### Processing Files

```python
from processor_multiformat import convert_bank_statement

result = convert_bank_statement(
    file_path='path/to/statement.pdf',
    filename='statement.pdf'
)

if result['success']:
    csv_path = result['csv_path']
    print(f"Converted {result['row_count']} transactions")
    print(f"Quality: {result['quality_score']}%")
```

#### Creating Users Programmatically

```python
from app_bankstatement_saas import app, db
from models_saas import User

with app.app_context():
    user = User(
        email='user@example.com',
        full_name='John Doe',
        subscription_tier='professional',
        monthly_pages_limit=2000
    )
    user.set_password('secure_password')
    db.session.add(user)
    db.session.commit()
```

## 🔐 Security Best Practices

1. **Never commit `.env`** - Contains secrets and API keys
2. **Use HTTPS in production** - Enable SSL/TLS
3. **Rotate secrets regularly** - Change API keys periodically
4. **Enable rate limiting** - Prevent abuse
5. **Monitor logs** - Track suspicious activity
6. **Backup database** - Regular automated backups
7. **Update dependencies** - Keep packages current

## 📊 Supported File Formats

### PDF
- Native (text-based) PDFs - Direct text extraction
- Scanned (image-based) PDFs - OCR with Tesseract
- Multi-page statements
- Various bank formats

### CSV
- Any delimiter (comma, semicolon, tab)
- Various encodings (UTF-8, Latin-1, etc.)
- Header row detection
- Auto-column mapping

### Excel
- XLSX (Excel 2007+)
- XLS (Excel 97-2003)
- Multiple sheets (auto-detection)
- Formula evaluation

### OFX
- OFX 1.x and 2.x
- QFX (Quicken)
- Multiple accounts
- Transaction history

## 🚀 Deployment

### Using Gunicorn (Recommended)

```bash
# Install gunicorn
pip install gunicorn

# Run with 4 workers
gunicorn -w 4 -b 0.0.0.0:5000 app_bankstatement_saas:app

# Or use the config file
gunicorn -c gunicorn_config.py app_bankstatement_saas:app
```

### Using Docker

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 5000
CMD ["gunicorn", "-c", "gunicorn_config.py", "app_bankstatement_saas:app"]
```

### Environment Setup for Production

```bash
# Update .env for production
FLASK_ENV=production
FLASK_DEBUG=False
SESSION_COOKIE_SECURE=True

# Use PostgreSQL
DATABASE_URI=postgresql://user:pass@localhost/dbname

# Enable Redis for rate limiting
RATELIMIT_STORAGE_URL=redis://localhost:6379/0

# Add monitoring
SENTRY_DSN=https://...@sentry.io/...
```

## 🧪 Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=.

# Test specific module
pytest test_processor.py
```

## 📈 Scaling

### Database
- Use PostgreSQL for production
- Enable connection pooling
- Create indexes on frequently queried fields

### Caching
- Enable Redis for rate limiting
- Cache conversion results
- Use CDN for static assets

### File Storage
- Use AWS S3 for file uploads
- Enable CloudFront for distribution
- Implement file lifecycle policies

### Background Processing
- Use Celery for async tasks
- Queue large file conversions
- Send email notifications

## 🐛 Troubleshooting

### Common Issues

**Tesseract not found**
```bash
# Windows: Install from https://github.com/UB-Mannheim/tesseract/wiki
# Set in .env: TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe

# Linux:
sudo apt-get install tesseract-ocr

# Mac:
brew install tesseract
```

**Stripe webhook errors**
- Verify webhook secret matches Stripe dashboard
- Check endpoint URL is publicly accessible
- Use `stripe listen` for local testing

**Database errors**
```bash
# Reset database (WARNING: deletes all data)
python -c "from app_bankstatement_saas import app, db; app.app_context().push(); db.drop_all(); db.create_all()"
```

**File upload errors**
- Check `MAX_CONTENT_LENGTH` in .env
- Ensure `uploads/` directory exists and is writable
- Verify file format is supported

## 📝 License

This project is proprietary. All rights reserved.

## 🤝 Support

- Documentation: See this README and inline code comments
- Issues: Create a GitHub issue
- Email: support@bankstatementai.com

## 🔄 Updates

### Version 1.0.0 (Current)
- Multi-format support (PDF, CSV, Excel, OFX)
- Stripe payment integration
- User authentication and authorization
- Subscription management
- Modern SaaS UI
- Dashboard with analytics
- High-accuracy AI extraction
- Smart categorization

### Roadmap
- [ ] API access for Business tier
- [ ] Batch processing
- [ ] Custom bank format training
- [ ] Mobile app
- [ ] Advanced analytics
- [ ] Team collaboration features
- [ ] Webhook notifications
- [ ] Export to QuickBooks/Xero

## 🙏 Acknowledgments

- Flask framework
- Stripe for payment processing
- Tesseract OCR
- pdfplumber for PDF extraction
- All open-source contributors

---

**Built with ❤️ for the financial community**
