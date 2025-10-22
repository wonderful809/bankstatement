# 🚀 Quick Start Guide - BankStatementAI SaaS

Get your bank statement conversion SaaS up and running in 5 minutes!

## ✅ Prerequisites Checklist

- [ ] Python 3.8+ installed
- [ ] pip installed
- [ ] Stripe account created (free at stripe.com)
- [ ] (Optional) Tesseract OCR for scanned PDFs

## 📦 Step 1: Installation

```bash
# Install dependencies
pip install -r requirements.txt
```

## 🔑 Step 2: Stripe Setup (5 minutes)

### 2.1 Get API Keys
1. Go to https://dashboard.stripe.com/test/apikeys
2. Copy your **Publishable key** (starts with `pk_test_`)
3. Copy your **Secret key** (starts with `sk_test_`)

### 2.2 Create Products & Prices

Go to https://dashboard.stripe.com/test/products

**Create Product 1: Starter**
- Name: Starter Plan
- Description: 500 pages per month
- Pricing: 
  - Price: $15
  - Billing period: Monthly
  - Click "Save product"
  - **Copy the Price ID** (starts with `price_`)

**Create Product 2: Professional**
- Name: Professional Plan
- Description: 2000 pages per month
- Pricing: $30/month
- **Copy the Price ID**

**Create Product 3: Business**
- Name: Business Plan
- Description: 5000 pages per month
- Pricing: $50/month
- **Copy the Price ID**

### 2.3 Setup Webhook (for local testing)

**Option A: Using Stripe CLI (Recommended for testing)**
```bash
# Install Stripe CLI: https://stripe.com/docs/stripe-cli
stripe login
stripe listen --forward-to localhost:5000/webhook/stripe
# Copy the webhook signing secret (starts with whsec_)
```

**Option B: Manual webhook setup (for deployed app)**
1. Go to https://dashboard.stripe.com/test/webhooks
2. Click "+ Add endpoint"
3. Endpoint URL: `http://your-domain.com/webhook/stripe`
4. Select events:
   - checkout.session.completed
   - customer.subscription.updated
   - customer.subscription.deleted
   - invoice.payment_succeeded
   - invoice.payment_failed
5. Click "Add endpoint"
6. **Copy the Signing secret**

## ⚙️ Step 3: Configure Environment

```bash
# Copy the example file
cp .env.example .env

# Generate secret key
python -c "import secrets; print('FLASK_SECRET_KEY=' + secrets.token_hex(32))"
```

Edit `.env` and add:

```bash
# Required - Flask
FLASK_SECRET_KEY=<paste-generated-secret-key>

# Required - Stripe
STRIPE_PUBLIC_KEY=pk_test_your_key_here
STRIPE_SECRET_KEY=sk_test_your_key_here
STRIPE_WEBHOOK_SECRET=whsec_your_secret_here

# Required - Stripe Price IDs
STRIPE_PRICE_ID_STARTER=price_your_starter_id
STRIPE_PRICE_ID_PROFESSIONAL=price_your_professional_id
STRIPE_PRICE_ID_BUSINESS=price_your_business_id
```

## 🗄️ Step 4: Initialize Database

```bash
python -c "from app_bankstatement_saas import app, db; app.app_context().push(); db.create_all(); print('✅ Database created!')"
```

## 🎉 Step 5: Run the App

```bash
python app_bankstatement_saas.py
```

Visit: **http://localhost:5000**

## 🧪 Step 6: Test It Out!

### Create Test Account
1. Go to http://localhost:5000
2. Click "Sign Up"
3. Create account with any email (e.g., test@example.com)
4. You'll get 50 free pages

### Test File Upload
1. Login to your account
2. Go to Dashboard
3. Upload a sample bank statement (PDF, CSV, or Excel)
4. Download the converted CSV

### Test Payment (Stripe Test Mode)
1. Go to Pricing page
2. Click "Choose Starter" (or any plan)
3. Use test card: `4242 4242 4242 4242`
4. Expiry: Any future date (e.g., 12/25)
5. CVC: Any 3 digits (e.g., 123)
6. Complete checkout
7. Check your dashboard - pages limit updated!

## 🎨 What You Get

### Landing Page
- Professional hero section
- Feature showcase
- How it works
- Call-to-action

### User Dashboard
- Conversion statistics
- Usage tracking (pages used/remaining)
- Upload interface with drag & drop
- Recent conversions history
- Quality metrics for each conversion

### Pricing Page
- 3 standard plans (Starter, Professional, Business)
- Custom pricing slider ($15-$300)
- FAQ section
- Stripe checkout integration

### Authentication
- Secure login/register
- Password hashing with bcrypt
- Session management
- Remember me functionality

## 🔒 Security Features

✅ HTTPS-ready (enable in production)
✅ CSRF protection
✅ Rate limiting
✅ Secure password hashing
✅ Session security
✅ File validation
✅ Automatic file cleanup

## 📊 Supported Formats

| Format | Extension | Features |
|--------|-----------|----------|
| PDF | .pdf | Text extraction + OCR for scanned docs |
| CSV | .csv | Auto-delimiter detection, encoding detection |
| Excel | .xlsx, .xls | Multiple sheets, formula evaluation |
| OFX | .ofx, .qfx | Banking standard format |

## 🎯 Test Files

Create test files to try:

**test_statement.csv**
```csv
Date,Description,Amount
2024-01-15,Grocery Store,-45.23
2024-01-16,Salary Deposit,2500.00
2024-01-17,Electric Bill,-120.50
```

**Upload it and see:**
- Automatic debit/credit separation
- Smart categorization (Food & Dining, Income, Bills)
- Clean CSV output

## 🚨 Common Issues & Solutions

### "Stripe key is invalid"
- Check you're using TEST keys (pk_test_ and sk_test_)
- Verify no extra spaces in .env file

### "Webhook signature verification failed"
- Use `stripe listen` for local testing
- Webhook secret must match Stripe CLI output

### "Database error"
- Run: `python -c "from app_bankstatement_saas import app, db; app.app_context().push(); db.drop_all(); db.create_all()"`

### "Tesseract not found" (only for scanned PDFs)
- Install Tesseract: https://github.com/UB-Mannheim/tesseract/wiki
- Add path to .env: `TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe`
- Optional - app works without it for text-based PDFs

## 📱 Next Steps

### For Development
- Customize colors in `static/css/style.css`
- Add your logo to templates
- Modify pricing plans
- Add custom features

### For Production
1. Get a domain name
2. Deploy to hosting (Heroku, AWS, DigitalOcean, etc.)
3. Switch to PostgreSQL database
4. Enable HTTPS
5. Switch Stripe to live mode (change pk_test_ to pk_live_)
6. Set up monitoring (Sentry)
7. Configure email notifications

## 💡 Pro Tips

1. **Test Mode is Free**: Stripe test mode is completely free, use it extensively
2. **Custom Plans**: Use the pricing slider to offer any price point
3. **Page Calculation**: Adjust page-to-price ratio in pricing.html
4. **Branding**: Update company name in templates and emails
5. **Analytics**: Add Google Analytics to track user behavior

## 🎓 Learning Resources

- [Flask Documentation](https://flask.palletsprojects.com/)
- [Stripe Documentation](https://stripe.com/docs)
- [Stripe Testing Guide](https://stripe.com/docs/testing)

## ✨ You're Ready!

Your SaaS platform is now running with:
- ✅ User authentication
- ✅ Subscription management  
- ✅ Payment processing
- ✅ File conversion engine
- ✅ Professional UI
- ✅ Usage tracking

**Start converting bank statements and building your business!** 🚀

---

Need help? Check the full README_SAAS.md or create an issue on GitHub.
