# 🗄️ Database Scaling for Production SaaS

## Current vs. Target Architecture

### Current (Development):
```
┌─────────────────┐
│  In-Memory Dict │  ← user_usage = {}
│  Flask Sessions │  ← filesystem
│  No Persistence │  ← Data lost on restart
└─────────────────┘
```

### Target (Production - Millions of Users):
```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  PostgreSQL  │     │    Redis     │     │   S3/CDN     │
│              │     │              │     │              │
│  • Users     │     │  • Sessions  │     │  • PDFs      │
│  • History   │     │  • Cache     │     │  • CSVs      │
│  • Usage     │     │  • Queues    │     │  • Static    │
└──────────────┘     └──────────────┘     └──────────────┘
        │                    │                    │
        └────────────────────┴────────────────────┘
                            │
                    ┌───────▼────────┐
                    │  Flask App     │
                    │  (Multiple     │
                    │   Instances)   │
                    └────────────────┘
```

---

## Option 1: PostgreSQL (Recommended for SaaS)

### Why PostgreSQL?
- ✅ ACID compliant (data integrity)
- ✅ Excellent for structured data (users, subscriptions, history)
- ✅ Strong consistency
- ✅ Rich query capabilities
- ✅ Built-in support for JSON (flexible data)
- ✅ Great for analytics and reporting
- ✅ Free managed hosting (Supabase, Railway, Neon)

### Installation & Setup

#### Step 1: Install PostgreSQL Locally (Development)

```powershell
# Using winget
winget install PostgreSQL.PostgreSQL

# Or using Chocolatey
choco install postgresql

# Or download from: https://www.postgresql.org/download/windows/
```

#### Step 2: Install Python Dependencies

```powershell
pip install psycopg2-binary sqlalchemy flask-sqlalchemy alembic
```

#### Step 3: Create Database Models

Create `models.py`:

```python
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy.dialects.postgresql import JSON

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(255), unique=True, nullable=False, index=True)
    email = db.Column(db.String(255), unique=True, nullable=True, index=True)
    plan = db.Column(db.String(50), default='free')  # free, premium, enterprise
    pages_used = db.Column(db.Integer, default=0)
    pages_limit = db.Column(db.Integer, default=5)
    last_reset = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    conversions = db.relationship('Conversion', back_populates='user', lazy='dynamic')
    subscriptions = db.relationship('Subscription', back_populates='user', lazy='dynamic')

class Conversion(db.Model):
    __tablename__ = 'conversions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    filename = db.Column(db.String(500), nullable=False)
    pages = db.Column(db.Integer, default=0)
    rows_extracted = db.Column(db.Integer, default=0)
    processing_time = db.Column(db.Float, default=0.0)
    file_size = db.Column(db.Integer, default=0)
    status = db.Column(db.String(50), default='pending')  # pending, success, failed
    error_message = db.Column(db.Text, nullable=True)
    metadata = db.Column(JSON, nullable=True)  # Store additional data
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    user = db.relationship('User', back_populates='conversions')

class Subscription(db.Model):
    __tablename__ = 'subscriptions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    plan = db.Column(db.String(50), nullable=False)  # free, premium, enterprise
    status = db.Column(db.String(50), default='active')  # active, canceled, expired
    stripe_subscription_id = db.Column(db.String(255), unique=True, nullable=True)
    stripe_customer_id = db.Column(db.String(255), nullable=True)
    current_period_start = db.Column(db.DateTime, nullable=True)
    current_period_end = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', back_populates='subscriptions')

class UsageLog(db.Model):
    __tablename__ = 'usage_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    action = db.Column(db.String(100), nullable=False)  # upload, convert, download
    pages = db.Column(db.Integer, default=0)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(500), nullable=True)
```

#### Step 4: Update `config.py`

```python
import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

class Config:
    # ... existing config ...
    
    # Database Configuration - PostgreSQL
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL',
        'postgresql://localhost:5432/bankstatement'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = os.getenv('FLASK_DEBUG', 'False').lower() in ('true', '1', 'yes')
    
    # Connection Pool Settings (for production)
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'pool_recycle': 3600,
        'pool_pre_ping': True,
        'max_overflow': 20
    }
```

#### Step 5: Update `.env`

```bash
# PostgreSQL Connection
DATABASE_URL=postgresql://username:password@localhost:5432/bankstatement

# Or for production (example with Supabase)
# DATABASE_URL=postgresql://postgres:password@db.supabase.co:5432/postgres
```

#### Step 6: Initialize Database

Create `init_db.py`:

```python
from app import app, db
from models import User, Conversion, Subscription, UsageLog

with app.app_context():
    # Drop all tables (development only!)
    # db.drop_all()
    
    # Create all tables
    db.create_all()
    
    print("✅ Database tables created successfully!")
    
    # Optional: Create test user
    test_user = User(
        session_id='test_session_123',
        email='test@example.com',
        plan='free',
        pages_used=0,
        pages_limit=5
    )
    db.session.add(test_user)
    db.session.commit()
    
    print("✅ Test user created!")
```

#### Step 7: Migrate Existing Logic

Update `app.py` to use database:

```python
from flask import Flask, session
from models import db, User, Conversion
from datetime import datetime
from sqlalchemy import func

app = Flask(__name__)
app.config.from_object(Config)

# Initialize database
db.init_app(app)

def get_or_create_user(session_id):
    """Get or create user based on session ID"""
    user = User.query.filter_by(session_id=session_id).first()
    
    if not user:
        user = User(
            session_id=session_id,
            plan='free',
            pages_used=0,
            pages_limit=5,
            last_reset=datetime.utcnow()
        )
        db.session.add(user)
        db.session.commit()
    
    return user

def check_and_reset_usage(user):
    """Check if usage should be reset (monthly)"""
    now = datetime.utcnow()
    
    # Check if it's a new month
    if (now.year > user.last_reset.year or 
        (now.year == user.last_reset.year and now.month > user.last_reset.month)):
        user.pages_used = 0
        user.last_reset = now
        db.session.commit()
    
    return user

def can_convert_pdf(user, pdf_pages):
    """Check if user can convert PDF"""
    check_and_reset_usage(user)
    
    if user.plan == 'free':
        return user.pages_used + pdf_pages <= user.pages_limit
    else:
        return True  # Premium/Enterprise unlimited

def record_conversion(user, filename, pages, rows, processing_time, file_size, status='success', error=None):
    """Record conversion in database"""
    conversion = Conversion(
        user_id=user.id,
        filename=filename,
        pages=pages,
        rows_extracted=rows,
        processing_time=processing_time,
        file_size=file_size,
        status=status,
        error_message=error
    )
    db.session.add(conversion)
    
    # Update user usage
    if status == 'success':
        user.pages_used += pages
    
    db.session.commit()
    
    return conversion

@app.route('/convert', methods=['POST'])
def convert():
    # Get or create user
    user_id = session.get('user_id')
    if not user_id:
        user_id = str(uuid.uuid4())
        session['user_id'] = user_id
    
    user = get_or_create_user(user_id)
    
    # ... upload file logic ...
    
    # Check if user can convert
    pdf_pages = count_pdf_pages(tmp_path)
    
    if not can_convert_pdf(user, pdf_pages):
        flash(f'Page limit exceeded! You have used {user.pages_used}/{user.pages_limit} pages.', 'error')
        return redirect(url_for('pricing'))
    
    try:
        # Convert PDF
        start_time = time.time()
        csv_path = convert_pdf_to_csv(tmp_path)
        processing_time = time.time() - start_time
        
        # Count rows
        row_count = count_csv_rows(csv_path)
        
        # Record in database
        record_conversion(
            user=user,
            filename=filename,
            pages=pdf_pages,
            rows=row_count,
            processing_time=processing_time,
            file_size=os.path.getsize(tmp_path),
            status='success'
        )
        
        return send_file(csv_path, as_attachment=True)
    
    except Exception as e:
        # Record failed conversion
        record_conversion(
            user=user,
            filename=filename,
            pages=pdf_pages,
            rows=0,
            processing_time=0,
            file_size=os.path.getsize(tmp_path),
            status='failed',
            error=str(e)
        )
        flash('Conversion failed', 'error')
        return redirect(url_for('index'))

@app.route('/api/stats')
def api_stats():
    """Get conversion statistics"""
    user_id = session.get('user_id')
    
    if user_id:
        user = get_or_create_user(user_id)
        check_and_reset_usage(user)
        
        # Get user stats
        total_conversions = Conversion.query.filter_by(user_id=user.id, status='success').count()
        total_pages = db.session.query(func.sum(Conversion.pages)).filter_by(
            user_id=user.id, status='success'
        ).scalar() or 0
        
        return jsonify({
            'user': {
                'plan': user.plan,
                'pages_used': user.pages_used,
                'pages_limit': user.pages_limit,
                'pages_remaining': max(0, user.pages_limit - user.pages_used)
            },
            'stats': {
                'total_conversions': total_conversions,
                'total_pages': total_pages
            }
        })
    
    return jsonify({'error': 'Not authenticated'}), 401
```

---

## Option 2: MongoDB (Alternative for Flexible Schema)

### Why MongoDB?
- ✅ Flexible schema (no migrations needed)
- ✅ Great for document storage
- ✅ Horizontal scaling
- ✅ JSON-native
- ✅ Free tier (MongoDB Atlas)

### Installation & Setup

```powershell
# Install MongoDB
winget install MongoDB.Server

# Or use MongoDB Atlas (cloud, free tier)
# https://www.mongodb.com/cloud/atlas
```

```powershell
# Install Python dependencies
pip install pymongo flask-pymongo
```

### MongoDB Models (PyMongo)

Create `mongo_models.py`:

```python
from pymongo import MongoClient
from datetime import datetime
import os

# Connect to MongoDB
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
client = MongoClient(MONGO_URI)
db = client['bankstatement']

# Collections
users = db['users']
conversions = db['conversions']
subscriptions = db['subscriptions']

# Create indexes
users.create_index('session_id', unique=True)
users.create_index('email', unique=True, sparse=True)
conversions.create_index('user_id')
conversions.create_index('created_at')
subscriptions.create_index('user_id')

def get_or_create_user_mongo(session_id):
    """Get or create user in MongoDB"""
    user = users.find_one({'session_id': session_id})
    
    if not user:
        user = {
            'session_id': session_id,
            'plan': 'free',
            'pages_used': 0,
            'pages_limit': 5,
            'last_reset': datetime.utcnow(),
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        users.insert_one(user)
    
    return user

def record_conversion_mongo(user_id, conversion_data):
    """Record conversion in MongoDB"""
    conversion = {
        'user_id': user_id,
        'filename': conversion_data['filename'],
        'pages': conversion_data['pages'],
        'rows_extracted': conversion_data['rows'],
        'processing_time': conversion_data['processing_time'],
        'file_size': conversion_data['file_size'],
        'status': conversion_data.get('status', 'success'),
        'error_message': conversion_data.get('error'),
        'created_at': datetime.utcnow()
    }
    conversions.insert_one(conversion)
    
    # Update user usage
    if conversion['status'] == 'success':
        users.update_one(
            {'_id': user_id},
            {'$inc': {'pages_used': conversion['pages']},
             '$set': {'updated_at': datetime.utcnow()}}
        )
```

---

## Redis Session Storage

### Why Redis?
- ✅ Fast in-memory storage
- ✅ Distributed sessions (multiple servers)
- ✅ Automatic expiration
- ✅ Pub/Sub for real-time features

### Installation

```powershell
# Windows: Use Docker or WSL
docker pull redis
docker run -d -p 6379:6379 redis

# Or use Redis Cloud (free tier)
# https://redis.com/try-free/
```

```powershell
# Install Python dependencies
pip install redis flask-session
```

### Configuration

Update `config.py`:

```python
class Config:
    # ... existing config ...
    
    # Redis Configuration
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    
    # Flask-Session Configuration
    SESSION_TYPE = 'redis'
    SESSION_PERMANENT = False
    SESSION_USE_SIGNER = True
    SESSION_KEY_PREFIX = 'bankstatement:'
    PERMANENT_SESSION_LIFETIME = 86400  # 24 hours
```

Update `app.py`:

```python
from flask import Flask
from flask_session import Session
from redis import Redis

app = Flask(__name__)
app.config.from_object(Config)

# Initialize Redis
redis_client = Redis.from_url(Config.REDIS_URL)

# Initialize Flask-Session
Session(app)
```

---

## Production Deployment Options

### Option 1: Heroku (Easiest)

```bash
# 1. Install Heroku CLI
winget install Heroku.HerokuCLI

# 2. Login
heroku login

# 3. Create app
heroku create your-app-name

# 4. Add PostgreSQL
heroku addons:create heroku-postgresql:essential-0

# 5. Add Redis
heroku addons:create heroku-redis:mini

# 6. Deploy
git push heroku main

# 7. Run migrations
heroku run python init_db.py
```

**Cost:** 
- Free tier: $0/month (limited)
- Hobby: $7/month + $9/month (PostgreSQL)
- Production: $25-50/month

### Option 2: Railway (Modern Alternative)

```bash
# 1. Install Railway CLI
npm install -g @railway/cli

# 2. Login
railway login

# 3. Initialize
railway init

# 4. Add PostgreSQL
railway add

# 5. Deploy
railway up
```

**Cost:**
- Free tier: $5 credit/month
- Pro: $10/month base + usage

### Option 3: DigitalOcean App Platform

```bash
# 1. Connect GitHub repo
# 2. Select Python
# 3. Add Managed PostgreSQL ($15/month)
# 4. Add Managed Redis ($15/month)
# 5. Deploy
```

**Cost:**
- App: $5-12/month
- PostgreSQL: $15/month
- Redis: $15/month
- Total: ~$35-45/month

### Option 4: AWS (Most Scalable)

```bash
# 1. Elastic Beanstalk for app
# 2. RDS for PostgreSQL
# 3. ElastiCache for Redis
# 4. S3 for file storage
```

**Cost:**
- EC2: $10-50/month
- RDS: $15-100/month
- ElastiCache: $15-50/month
- S3: $1-5/month
- Total: ~$40-200/month

---

## Migration Checklist

- [ ] Install PostgreSQL locally
- [ ] Create `models.py` with database schema
- [ ] Update `config.py` with database settings
- [ ] Create `init_db.py` migration script
- [ ] Run database initialization
- [ ] Update `app.py` routes to use database
- [ ] Install Redis (locally or cloud)
- [ ] Configure Flask-Session with Redis
- [ ] Test locally with PostgreSQL + Redis
- [ ] Choose deployment platform
- [ ] Set up production database
- [ ] Deploy application
- [ ] Run production migrations
- [ ] Test production deployment
- [ ] Set up monitoring (DataDog, New Relic, etc.)
- [ ] Configure backups
- [ ] Set up CI/CD pipeline

---

## Performance Benchmarks

### Expected Performance (with PostgreSQL + Redis):

| Users | Requests/sec | Database Load | Redis Load | Cost/month |
|-------|-------------|---------------|------------|------------|
| 100 | 10 | Low | Low | $10-20 |
| 1,000 | 100 | Medium | Medium | $50-100 |
| 10,000 | 1,000 | High | High | $200-500 |
| 100,000 | 10,000 | Very High | Very High | $1,000+ |

---

## Next Steps

1. **Choose your database:** PostgreSQL (recommended) or MongoDB
2. **Set up Redis** for session management
3. **Create database models** using the templates above
4. **Migrate your code** from in-memory to database
5. **Test locally** before deploying
6. **Choose deployment platform** (Heroku, Railway, DO, AWS)
7. **Deploy to production**
8. **Monitor and optimize**

---

**Ready to scale to millions of users!** 🚀
