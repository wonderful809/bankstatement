# 🔧 Troubleshooting + Database Scaling Guide

## ✅ Current Status: Server is Running!

Your Flask server is running successfully at: **http://127.0.0.1:5000**

```
 * Running on http://127.0.0.1:5000
 * Debug mode: on
 * Debugger is active!
```

---

## 🐛 Conversion Not Working? - Debugging Steps

### Step 1: Open Your Browser
Go to: **http://127.0.0.1:5000**

### Step 2: Try Converting a PDF
1. Upload a PDF file
2. Click "Convert to CSV"
3. Watch the terminal for error messages

### Step 3: Check Terminal for Errors
Watch the terminal window where `python app.py` is running. You'll see:
- Request logs
- Any error messages
- Stack traces if something fails

### Common Issues & Fixes:

#### Issue 1: "pdfplumber" import error
**Error**: `ImportError: No module named 'pdfplumber'`
**Fix**:
```powershell
pip install pdfplumber
```

#### Issue 2: Page counting fails
**Error**: `AttributeError: 'module' object has no attribute 'open'`
**Fix**: The `count_pdf_pages()` function might be failing. Check if pdfplumber is imported correctly.

#### Issue 3: Session not working
**Error**: `RuntimeError: The session is unavailable because no secret key was set`
**Fix**: Check if `SECRET_KEY` is set in config.py

Let me check your config.py:

---

## 📊 Database Scaling Strategy (GitHub Student Pack)

Since you mentioned wanting to upgrade from SQLite for millions of users, here's my recommendation:

### 🎯 Recommended Architecture

#### Option 1: PostgreSQL on Heroku (BEST for SQLAlchemy migration)
**Why**: Easiest migration from SQLite, fully compatible with SQLAlchemy

**GitHub Student Pack Benefits**:
- Heroku: $13/month credit (free tier)
- PostgreSQL: Up to 10,000 rows free tier

**Migration Steps**:
```python
# 1. Change config.py
SQLALCHEMY_DATABASE_URI = os.getenv(
    'DATABASE_URL',
    'sqlite:///bankstatements.db'  # Fallback for local dev
)

# 2. Install PostgreSQL adapter
pip install psycopg2-binary

# 3. Deploy to Heroku
heroku create your-app-name
heroku addons:create heroku-postgresql:hobby-dev
git push heroku main
```

**Pros**:
- ✅ Zero code changes (SQLAlchemy works as-is)
- ✅ Built-in backups
- ✅ Scales to millions of rows
- ✅ ACID compliance
- ✅ Relational data (perfect for your User-Conversion-Feedback models)

**Cons**:
- ❌ Free tier limited to 10,000 rows
- ❌ Need to upgrade to paid ($9/month) for production

---

#### Option 2: MongoDB Atlas (Flexible schema, free tier generous)
**Why**: $200 credit, generous free tier, NoSQL flexibility

**GitHub Student Pack Benefits**:
- MongoDB Atlas: $200 credit
- Free tier: 512MB storage

**Migration Steps**:
```python
# 1. Install MongoDB driver
pip install pymongo flask-pymongo

# 2. Update models (convert from SQLAlchemy to MongoDB)
from flask_pymongo import PyMongo

app.config["MONGO_URI"] = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/bankstatements')
mongo = PyMongo(app)

# 3. Rewrite models as MongoDB documents
def create_user(session_id):
    return mongo.db.users.insert_one({
        'session_id': session_id,
        'created_at': datetime.utcnow(),
        'conversions': []
    })

def create_conversion(user_id, data):
    return mongo.db.conversions.insert_one({
        'user_id': user_id,
        'filename': data['filename'],
        'status': 'processing',
        'created_at': datetime.utcnow()
    })
```

**Pros**:
- ✅ $200 credit (lasts months!)
- ✅ Free tier: 512MB (enough for 100K+ documents)
- ✅ Flexible schema (easy to add fields)
- ✅ Built-in scaling
- ✅ Fast reads/writes

**Cons**:
- ❌ Requires rewriting all SQLAlchemy code
- ❌ No joins (need to denormalize data)
- ❌ Different query syntax

---

#### Option 3: DigitalOcean Managed PostgreSQL (Student Pack Credit)
**Why**: $200 credit, full PostgreSQL power

**GitHub Student Pack Benefits**:
- DigitalOcean: $200 credit
- Managed PostgreSQL: $15/month (13 months free!)

**Setup**:
```bash
# 1. Create DigitalOcean account with Student Pack
# 2. Create Managed Database (PostgreSQL)
# 3. Get connection string
# 4. Update config.py

SQLALCHEMY_DATABASE_URI = os.getenv(
    'DATABASE_URL',
    'postgresql://user:password@db-postgresql-nyc3-12345-do-user-1234567-0.db.ondigitalocean.com:25060/defaultdb?sslmode=require'
)
```

**Pros**:
- ✅ $200 credit = ~13 months free!
- ✅ Full PostgreSQL (no SQLAlchemy changes)
- ✅ Automatic backups
- ✅ Scales easily
- ✅ Better than Heroku free tier

**Cons**:
- ❌ After credit expires, $15/month minimum
- ❌ Need to manage scaling manually

---

### 🏆 My Recommendation for Your Use Case

**Phase 1: Current (Development)**
- Keep SQLite for local development
- Use in-memory storage for session data

**Phase 2: Production Launch (0-10K users)**
- **Use**: PostgreSQL on Heroku (Free tier)
- **Why**: Zero code changes, free tier sufficient
- **Cost**: $0/month

**Phase 3: Growth (10K-100K users)**
- **Use**: DigitalOcean Managed PostgreSQL
- **Why**: $200 student credit = free for 13 months
- **Upgrade**: After credit, $15/month
- **Cost**: $0/month (with student credit)

**Phase 4: Scale (100K+ users)**
- **Use**: DigitalOcean or AWS RDS PostgreSQL
- **Add**: Redis for caching, Celery for background jobs
- **Cost**: $50-200/month depending on traffic

---

### 📊 Specific to Your Current Setup

Your current models are **perfect for PostgreSQL**:

```python
# Your models work as-is with PostgreSQL!
class User(db.Model):
    # ✅ Primary key
    # ✅ Relationships
    # ✅ Timestamps

class Conversion(db.Model):
    # ✅ Foreign keys
    # ✅ Indexes possible

class Feedback(db.Model):
    # ✅ Text fields
    # ✅ Optional foreign keys
```

**Just change one line**:
```python
# config.py
SQLALCHEMY_DATABASE_URI = os.getenv(
    'DATABASE_URL',
    'sqlite:///bankstatements.db'  # Local dev
)
```

**Add to requirements.txt**:
```
psycopg2-binary
```

**Deploy and you're done!**

---

### 🎯 Immediate Next Steps

1. **Fix current conversion issue** (if any)
   - Check terminal for errors when you upload PDF
   - Share error message with me

2. **Add database models** (you mentioned but not implemented yet)
   - Create `models.py`
   - Add User, Conversion, Feedback models
   - Replace in-memory storage

3. **Deploy to Heroku with PostgreSQL**
   - Use GitHub Student Pack
   - Free tier for initial launch
   - Auto-scaling ready

4. **Add caching layer**
   - Redis for session storage (not in-memory dict)
   - Cache API responses
   - Rate limiting

---

### 🚀 Quick Heroku Deployment Guide

```bash
# 1. Install Heroku CLI
# Download from: https://devcenter.heroku.com/articles/heroku-cli

# 2. Login
heroku login

# 3. Create app
heroku create bankstatement-converter

# 4. Add PostgreSQL
heroku addons:create heroku-postgresql:hobby-dev

# 5. Set environment variables
heroku config:set SECRET_KEY=your-secret-key-here

# 6. Deploy
git push heroku main

# 7. Run migrations
heroku run python
>>> from app import db
>>> db.create_all()
>>> exit()

# 8. Open app
heroku open
```

---

### 💡 For Millions of Users - Architecture Recommendations

```
User Request
    ↓
Load Balancer (Heroku/DigitalOcean)
    ↓
Flask App (Multiple instances)
    ↓
├─ Redis Cache (Session, API responses)
│  └─ Redis Cloud (Free tier: 30MB)
│
├─ PostgreSQL (Main database)
│  └─ DigitalOcean Managed DB ($200 credit)
│
├─ Celery Workers (Background PDF processing)
│  └─ Separate dynos on Heroku
│
└─ S3/Spaces (File storage for PDFs/CSVs)
   └─ DigitalOcean Spaces ($200 credit)
```

---

## 🔍 Debug Current Conversion Issue

**Tell me**:
1. Can you access http://127.0.0.1:5000 in browser?
2. What happens when you upload a PDF?
3. Any error messages in the terminal?
4. Does the usage indicator show "0/5 free pages"?

Share the error and I'll fix it immediately!

---

**Summary**: Server is running ✅, now let's fix any conversion errors and then upgrade to PostgreSQL for scalability!
