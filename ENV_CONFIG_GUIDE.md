# Environment Configuration Guide

## Overview

This application uses `.env` files for configuration management with `python-dotenv`. This approach provides:
- **Security**: Sensitive data stays out of version control
- **Flexibility**: Easy configuration per environment (dev/staging/prod)
- **Portability**: Simple deployment across different systems

---

## Quick Start

### 1. Create Your `.env` File

Copy the example file:
```bash
cp .env.example .env
```

### 2. Configure Required Values

Edit `.env` and set at minimum:
```bash
# Change this secret key!
FLASK_SECRET_KEY=your-very-secret-random-key-here

# Set paths to external tools
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
POPPLER_PATH=C:\path\to\poppler\bin
```

### 3. Run the Application

The application will automatically load `.env` on startup:
```bash
python app_saas.py
```

---

## Configuration Reference

### Flask Configuration

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `FLASK_SECRET_KEY` | Secret key for sessions/cookies | `dev-secret-key...` | `abc123xyz789...` |
| `FLASK_DEBUG` | Enable debug mode | `True` | `True` / `False` |
| `FLASK_ENV` | Environment name | `development` | `production` |
| `FLASK_HOST` | Server bind address | `0.0.0.0` | `127.0.0.1` |
| `FLASK_PORT` | Server port | `5000` | `8080` |

**⚠️ Important**: 
- Always change `FLASK_SECRET_KEY` in production
- Generate with: `python -c "import secrets; print(secrets.token_hex(32))"`
- Set `FLASK_DEBUG=False` in production

---

### File Upload Configuration

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `MAX_CONTENT_LENGTH` | Max upload size in bytes | `16777216` (16MB) | `33554432` (32MB) |
| `UPLOAD_FOLDER` | Upload directory path | `uploads` | `./temp/uploads` |
| `ALLOWED_EXTENSIONS` | Allowed file types | `pdf` | `pdf,doc,docx` |

**Size Reference**:
- 5MB = `5242880`
- 10MB = `10485760`
- 16MB = `16777216` (default)
- 32MB = `33554432`
- 50MB = `52428800`

---

### Database Configuration

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `DATABASE_URI` | SQLAlchemy database URI | `sqlite:///bankstatements.db` | `postgresql://user:pass@localhost/db` |
| `SQLALCHEMY_TRACK_MODIFICATIONS` | Track object changes | `False` | `True` / `False` |

**Database Examples**:
- SQLite: `sqlite:///database.db`
- PostgreSQL: `postgresql://user:password@localhost:5432/dbname`
- MySQL: `mysql://user:password@localhost:3306/dbname`

---

### External Tools Configuration

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `TESSERACT_CMD` | Path to Tesseract executable | (empty) | `C:\Program Files\Tesseract-OCR\tesseract.exe` |
| `POPPLER_PATH` | Path to Poppler bin directory | (empty) | `C:\poppler-xx\Library\bin` |

**Platform-Specific Paths**:

**Windows**:
```bash
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
POPPLER_PATH=C:\Users\username\poppler-xx.xx.x\Library\bin
```

**Linux**:
```bash
TESSERACT_CMD=/usr/bin/tesseract
POPPLER_PATH=/usr/bin
```

**macOS** (Homebrew):
```bash
TESSERACT_CMD=/opt/homebrew/bin/tesseract
POPPLER_PATH=/opt/homebrew/bin
```

---

### Rate Limiting Configuration

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `RATELIMIT_STORAGE_URL` | Storage backend for limits | `memory://` | `redis://localhost:6379` |
| `RATELIMIT_DEFAULT` | Default per-minute limit | `10 per minute` | `50 per minute` |
| `RATELIMIT_PER_HOUR` | Hourly limit | `50 per hour` | `100 per hour` |
| `RATELIMIT_PER_DAY` | Daily limit | `200 per day` | `1000 per day` |

**Rate Limit Format**:
- `10 per minute`
- `100 per hour`
- `1000 per day`
- `5 per second`

**Storage Backends**:
- `memory://` - In-memory (development only)
- `redis://localhost:6379` - Redis (recommended for production)
- `memcached://localhost:11211` - Memcached

---

### File Cleanup Configuration

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `FILE_CLEANUP_HOURS` | Hours before file deletion | `1` | `24` |

**Cleanup Schedule**:
- `0.5` = 30 minutes
- `1` = 1 hour (default)
- `24` = 1 day
- `168` = 1 week

---

### Security Configuration

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `SESSION_COOKIE_SECURE` | HTTPS-only cookies | `False` | `True` (production) |
| `SESSION_COOKIE_HTTPONLY` | JavaScript-inaccessible | `True` | `True` |
| `SESSION_COOKIE_SAMESITE` | CSRF protection | `Lax` | `Strict` / `Lax` / `None` |
| `PERMANENT_SESSION_LIFETIME` | Session duration (seconds) | `86400` (1 day) | `604800` (1 week) |

**⚠️ Production Security**:
```bash
SESSION_COOKIE_SECURE=True
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=Strict
```

**Session Lifetime Reference**:
- 1 hour = `3600`
- 1 day = `86400` (default)
- 1 week = `604800`
- 30 days = `2592000`

---

### Logging Configuration

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `LOG_LEVEL` | Logging verbosity | `INFO` | `DEBUG` / `WARNING` / `ERROR` |
| `LOG_FILE` | Log file path | `app.log` | `/var/log/bankapp.log` |

**Log Levels** (from most to least verbose):
1. `DEBUG` - Detailed diagnostic info
2. `INFO` - General informational messages (default)
3. `WARNING` - Warning messages
4. `ERROR` - Error messages only
5. `CRITICAL` - Critical errors only

---

## Environment-Specific Configurations

### Development (.env)

```bash
# Development configuration
FLASK_SECRET_KEY=dev-secret-key-not-for-production
FLASK_DEBUG=True
FLASK_ENV=development
FLASK_HOST=127.0.0.1
FLASK_PORT=5000

MAX_CONTENT_LENGTH=16777216
UPLOAD_FOLDER=uploads

DATABASE_URI=sqlite:///bankstatements_dev.db

TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
POPPLER_PATH=C:\poppler\Library\bin

RATELIMIT_STORAGE_URL=memory://
RATELIMIT_DEFAULT=100 per minute

FILE_CLEANUP_HOURS=1

SESSION_COOKIE_SECURE=False
LOG_LEVEL=DEBUG
```

### Production (.env.production)

```bash
# Production configuration
FLASK_SECRET_KEY=<generate-with-secrets.token_hex(32)>
FLASK_DEBUG=False
FLASK_ENV=production
FLASK_HOST=0.0.0.0
FLASK_PORT=8000

MAX_CONTENT_LENGTH=16777216
UPLOAD_FOLDER=/var/app/uploads

DATABASE_URI=postgresql://user:password@localhost:5432/bankapp_prod

TESSERACT_CMD=/usr/bin/tesseract
POPPLER_PATH=/usr/bin

RATELIMIT_STORAGE_URL=redis://localhost:6379/0
RATELIMIT_DEFAULT=10 per minute
RATELIMIT_PER_HOUR=50 per hour
RATELIMIT_PER_DAY=200 per day

FILE_CLEANUP_HOURS=2

SESSION_COOKIE_SECURE=True
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=Strict
PERMANENT_SESSION_LIFETIME=86400

LOG_LEVEL=WARNING
LOG_FILE=/var/log/bankapp/app.log
```

---

## Usage Examples

### Accessing Config in Code

```python
from config import Config

# Get configuration values
secret_key = Config.SECRET_KEY
upload_folder = Config.UPLOAD_FOLDER
max_size = Config.MAX_CONTENT_LENGTH

# Check environment
if Config.ENV == 'production':
    # Production-specific code
    pass
```

### Environment Detection

```python
import os
from dotenv import load_dotenv

# Load specific environment
env_file = '.env.production' if os.getenv('ENV') == 'production' else '.env'
load_dotenv(env_file)
```

### Overriding Values

Environment variables set in the system take precedence:
```bash
# Windows
$env:FLASK_DEBUG="False"
python app_saas.py

# Linux/Mac
export FLASK_DEBUG=False
python app_saas.py
```

---

## Security Best Practices

### 1. Secret Key Generation

Generate a strong secret key:
```python
import secrets
print(secrets.token_hex(32))
```

### 2. Never Commit `.env`

Ensure `.env` is in `.gitignore`:
```
.env
.env.local
.env.*.local
```

### 3. Use Different Keys Per Environment

- Development: Simple key is OK
- Staging: Moderate security
- Production: Strong randomly generated key

### 4. Rotate Keys Regularly

Change `FLASK_SECRET_KEY` periodically in production (will invalidate sessions).

### 5. Restrict File Permissions

```bash
# Linux/Mac
chmod 600 .env

# Windows
icacls .env /inheritance:r /grant:r "%USERNAME%:F"
```

---

## Troubleshooting

### Issue: `.env` file not loaded

**Solution**: Ensure `python-dotenv` is installed:
```bash
pip install python-dotenv
```

### Issue: Config values not updating

**Solution**: 
1. Restart the Flask server (debug mode auto-reloads code but not env vars)
2. Check `.env` file syntax (no spaces around `=`)
3. Verify file is named exactly `.env` (not `.env.txt`)

### Issue: Tesseract/Poppler not found

**Solution**: 
1. Verify paths in `.env` are correct
2. Use absolute paths
3. Check file exists: `Test-Path "C:\Program Files\Tesseract-OCR\tesseract.exe"`

### Issue: Import errors for Config

**Solution**: Ensure `config.py` imports `load_dotenv`:
```python
from dotenv import load_dotenv
load_dotenv()
```

---

## Migration from Hardcoded Config

### Before (Hardcoded)
```python
SECRET_KEY = 'my-secret-key'
MAX_CONTENT_LENGTH = 16 * 1024 * 1024
```

### After (.env + Config)
```python
# .env file
FLASK_SECRET_KEY=my-secret-key
MAX_CONTENT_LENGTH=16777216

# config.py
from dotenv import load_dotenv
load_dotenv()

SECRET_KEY = os.getenv('FLASK_SECRET_KEY')
MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH'))
```

---

## Additional Resources

- [python-dotenv Documentation](https://pypi.org/project/python-dotenv/)
- [Flask Configuration](https://flask.palletsprojects.com/en/2.3.x/config/)
- [12-Factor App Config](https://12factor.net/config)

---

## Quick Reference Commands

```bash
# Install python-dotenv
pip install python-dotenv

# Generate secret key
python -c "import secrets; print(secrets.token_hex(32))"

# Create .env from example
cp .env.example .env

# Check environment variables
# Windows
Get-Content .env

# Linux/Mac
cat .env

# Run with specific environment
# Windows
$env:FLASK_ENV="production"; python app_saas.py

# Linux/Mac
FLASK_ENV=production python app_saas.py
```

---

## Support

For questions or issues:
1. Check `.env.example` for correct format
2. Verify all required variables are set
3. Check logs in `app.log`
4. Review `config.py` for variable names
