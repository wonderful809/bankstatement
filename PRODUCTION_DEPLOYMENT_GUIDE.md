# 🚀 Production Deployment Guide - BankStatementAI SaaS

Complete guide to deploy your SaaS platform to production.

## 📋 Pre-Deployment Checklist

### Required
- [ ] Domain name purchased
- [ ] Hosting account set up
- [ ] PostgreSQL database provisioned
- [ ] Stripe account verified (live mode enabled)
- [ ] SSL certificate (HTTPS)
- [ ] Email service configured
- [ ] Backup strategy planned

### Recommended
- [ ] Monitoring service (Sentry)
- [ ] CDN for static assets
- [ ] Redis for caching
- [ ] Load balancer (for scaling)

## 🌐 Deployment Options

### Option 1: Heroku (Easiest)

**Pros**: Simple, managed infrastructure
**Cost**: ~$7-25/month to start

```bash
# Install Heroku CLI
# https://devcenter.heroku.com/articles/heroku-cli

# Login
heroku login

# Create app
heroku create your-app-name

# Add PostgreSQL
heroku addons:create heroku-postgresql:mini

# Add Redis (optional)
heroku addons:create heroku-redis:mini

# Set environment variables
heroku config:set FLASK_SECRET_KEY=your-secret-key
heroku config:set STRIPE_PUBLIC_KEY=pk_live_...
heroku config:set STRIPE_SECRET_KEY=sk_live_...
# ... (add all from .env)

# Deploy
git push heroku main

# Open app
heroku open
```

### Option 2: DigitalOcean (Best Value)

**Pros**: Good performance, affordable
**Cost**: ~$12-24/month

```bash
# Create a droplet (Ubuntu 22.04)
# Size: 2GB RAM minimum

# SSH into server
ssh root@your-server-ip

# Update system
apt update && apt upgrade -y

# Install dependencies
apt install python3.9 python3-pip python3-venv nginx postgresql redis-server

# Install Tesseract (for OCR)
apt install tesseract-ocr

# Install Poppler (for PDF processing)
apt install poppler-utils

# Create app user
adduser bankstatement
usermod -aG sudo bankstatement
su - bankstatement

# Clone your code
git clone <your-repo-url>
cd <your-repo>

# Set up Python environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install gunicorn

# Configure PostgreSQL
sudo -u postgres createdb bankstatements_saas
sudo -u postgres createuser -P bankstatement

# Set up environment variables
cp .env.example .env
nano .env  # Update with production values

# Initialize database
python -c "from app_bankstatement_saas import app, db; app.app_context().push(); db.create_all()"

# Set up systemd service (see below)
# Set up Nginx (see below)
```

### Option 3: AWS (Most Scalable)

**Pros**: Enterprise-grade, unlimited scaling
**Cost**: ~$20-50/month to start

1. **EC2 Instance**: Launch Ubuntu instance
2. **RDS**: PostgreSQL database
3. **ElastiCache**: Redis for sessions
4. **S3**: File storage
5. **CloudFront**: CDN
6. **Route 53**: DNS
7. **ELB**: Load balancer

Follow AWS deployment guides for Flask apps.

## 🔧 Production Configuration

### 1. Update .env for Production

```bash
# Flask
FLASK_ENV=production
FLASK_DEBUG=False
FLASK_SECRET_KEY=<generate-new-64-char-key>

# Database (PostgreSQL)
DATABASE_URI=postgresql://user:password@localhost:5432/bankstatements_saas

# Security
SESSION_COOKIE_SECURE=True
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=Strict

# Stripe (LIVE MODE)
STRIPE_PUBLIC_KEY=pk_live_...
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Rate Limiting (Redis)
RATELIMIT_STORAGE_URL=redis://localhost:6379/0

# Monitoring
SENTRY_DSN=https://...@sentry.io/...

# Email
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USERNAME=apikey
SMTP_PASSWORD=<sendgrid-api-key>
SMTP_FROM=noreply@yourdomain.com

# File Cleanup (more aggressive in production)
FILE_CLEANUP_HOURS=1

# Logging
LOG_LEVEL=WARNING
LOG_FILE=/var/log/bankstatement/app.log
```

### 2. Systemd Service (Linux)

Create `/etc/systemd/system/bankstatement.service`:

```ini
[Unit]
Description=BankStatementAI SaaS
After=network.target

[Service]
User=bankstatement
WorkingDirectory=/home/bankstatement/app
Environment="PATH=/home/bankstatement/app/venv/bin"
ExecStart=/home/bankstatement/app/venv/bin/gunicorn -c gunicorn_config.py app_bankstatement_saas:app
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable bankstatement
sudo systemctl start bankstatement
sudo systemctl status bankstatement
```

### 3. Nginx Configuration

Create `/etc/nginx/sites-available/bankstatement`:

```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    
    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Security Headers
    add_header X-Frame-Options "DENY";
    add_header X-Content-Type-Options "nosniff";
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # Static files
    location /static {
        alias /home/bankstatement/app/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Upload size limit
    client_max_body_size 16M;

    # Proxy to Gunicorn
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts for long uploads
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }
}
```

Enable site:
```bash
sudo ln -s /etc/nginx/sites-available/bankstatement /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 4. SSL Certificate (Let's Encrypt)

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Auto-renewal is set up automatically
# Test renewal
sudo certbot renew --dry-run
```

### 5. Gunicorn Configuration

Update `gunicorn_config.py` for production:

```python
import os
import multiprocessing

# Server socket
bind = '127.0.0.1:8000'
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = 'sync'
worker_connections = 1000
timeout = 300
keepalive = 2

# Logging
accesslog = '/var/log/bankstatement/access.log'
errorlog = '/var/log/bankstatement/error.log'
loglevel = 'warning'

# Process naming
proc_name = 'bankstatement'

# Server mechanics
daemon = False
pidfile = '/tmp/bankstatement.pid'
```

## 🔐 Security Hardening

### 1. Firewall (UFW)

```bash
# Enable firewall
sudo ufw enable

# Allow SSH
sudo ufw allow 22

# Allow HTTP/HTTPS
sudo ufw allow 80
sudo ufw allow 443

# Check status
sudo ufw status
```

### 2. Fail2Ban (Brute Force Protection)

```bash
# Install
sudo apt install fail2ban

# Configure for Nginx
sudo nano /etc/fail2ban/jail.local
```

Add:
```ini
[nginx-limit-req]
enabled = true
filter = nginx-limit-req
logpath = /var/log/nginx/error.log

[nginx-http-auth]
enabled = true
```

### 3. Regular Updates

```bash
# Set up automatic security updates
sudo apt install unattended-upgrades
sudo dpkg-reconfigure --priority=low unattended-upgrades
```

## 📊 Monitoring & Logging

### 1. Sentry (Error Tracking)

Already integrated! Just add SENTRY_DSN to .env:

```bash
# Sign up at sentry.io
# Create project
# Copy DSN
SENTRY_DSN=https://...@sentry.io/...
```

### 2. Application Logs

```bash
# Create log directory
sudo mkdir -p /var/log/bankstatement
sudo chown bankstatement:bankstatement /var/log/bankstatement

# View logs
tail -f /var/log/bankstatement/app.log
tail -f /var/log/bankstatement/access.log
tail -f /var/log/bankstatement/error.log
```

### 3. System Monitoring

```bash
# Install monitoring tools
sudo apt install htop iotop

# Check system resources
htop

# Check disk usage
df -h

# Check database
sudo -u postgres psql bankstatements_saas
```

## 💾 Backup Strategy

### 1. Database Backups

Create `/home/bankstatement/backup.sh`:

```bash
#!/bin/bash
BACKUP_DIR="/home/bankstatement/backups"
DATE=$(date +%Y%m%d_%H%M%S)
FILENAME="db_backup_$DATE.sql"

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup database
pg_dump bankstatements_saas > $BACKUP_DIR/$FILENAME

# Compress
gzip $BACKUP_DIR/$FILENAME

# Delete backups older than 30 days
find $BACKUP_DIR -name "*.gz" -mtime +30 -delete

echo "Backup completed: $FILENAME.gz"
```

Make executable and schedule:
```bash
chmod +x /home/bankstatement/backup.sh

# Add to crontab (daily at 2 AM)
crontab -e
# Add: 0 2 * * * /home/bankstatement/backup.sh
```

### 2. Code Backups

Use Git! Push to private repository regularly.

## 🎛️ Stripe Production Setup

### 1. Switch to Live Mode

In Stripe Dashboard:
1. Toggle from "Test" to "Live" mode
2. Go to Developers → API keys
3. Copy **Live** keys (pk_live_ and sk_live_)
4. Update .env with live keys

### 2. Update Products

Create products in **Live mode**:
- Starter: $15/month
- Professional: $30/month
- Business: $50/month

Copy the **live** Price IDs to .env

### 3. Production Webhook

1. Go to Developers → Webhooks
2. Add endpoint: `https://yourdomain.com/webhook/stripe`
3. Select same events as test mode
4. Copy signing secret (whsec_...)
5. Update STRIPE_WEBHOOK_SECRET in .env

### 4. Test Payment Flow

Before going live:
- Create test account
- Go through full checkout
- Verify subscription activation
- Test webhook events
- Check database updates

## 📈 Performance Optimization

### 1. Database

```sql
-- Add indexes for performance
CREATE INDEX idx_conversions_user_created ON conversions(user_id, created_at DESC);
CREATE INDEX idx_payments_user_created ON payments(user_id, created_at DESC);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_stripe_customer ON users(stripe_customer_id);
```

### 2. Redis Caching

```python
# Add to .env
RATELIMIT_STORAGE_URL=redis://localhost:6379/0

# Install Redis
sudo apt install redis-server
sudo systemctl enable redis-server
```

### 3. CDN for Static Files

Use CloudFlare, AWS CloudFront, or similar for:
- CSS files
- JavaScript files
- Images
- Fonts

## 🚦 Health Checks

Create `/health` endpoint in your app:

```python
@app.route('/health')
def health_check():
    try:
        # Check database
        db.session.execute('SELECT 1')
        
        # Check disk space
        import shutil
        total, used, free = shutil.disk_usage('/')
        if free < 1024**3:  # Less than 1GB free
            return jsonify({'status': 'warning', 'disk': 'low'}), 200
        
        return jsonify({'status': 'healthy'}), 200
    except Exception as e:
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 500
```

## 📱 Post-Deployment

### 1. DNS Configuration

Point your domain to server:
```
A Record: @ → Your-Server-IP
A Record: www → Your-Server-IP
```

### 2. Email Setup

Configure email service (SendGrid, Mailgun, etc.) for:
- Welcome emails
- Password resets
- Payment receipts
- Usage alerts

### 3. Analytics

Add Google Analytics:

In `templates/base.html`:
```html
<!-- Google Analytics -->
<script async src="https://www.googletagmanager.com/gtag/js?id=GA_MEASUREMENT_ID"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'GA_MEASUREMENT_ID');
</script>
```

### 4. Marketing

- Set up landing page SEO
- Create social media accounts
- Start content marketing
- Run ads (Google, Facebook)

## ✅ Go-Live Checklist

Before announcing:

- [ ] SSL certificate installed and working
- [ ] All Stripe keys switched to live mode
- [ ] Test complete user flow (register → convert → payment)
- [ ] Webhook endpoint working
- [ ] Database backups automated
- [ ] Monitoring enabled (Sentry)
- [ ] Error logs configured
- [ ] Terms of Service page created
- [ ] Privacy Policy page created
- [ ] Contact/Support email set up
- [ ] Domain email configured
- [ ] Analytics tracking working
- [ ] Performance tested
- [ ] Security audit passed
- [ ] Mobile responsiveness verified

## 🆘 Troubleshooting Production Issues

### Database Connection Issues
```bash
# Check if PostgreSQL is running
sudo systemctl status postgresql

# Check connection
psql -h localhost -U bankstatement -d bankstatements_saas

# View logs
sudo tail -f /var/log/postgresql/postgresql-14-main.log
```

### Application Not Starting
```bash
# Check service status
sudo systemctl status bankstatement

# View logs
sudo journalctl -u bankstatement -n 50

# Check for Python errors
source venv/bin/activate
python app_bankstatement_saas.py
```

### Nginx Issues
```bash
# Test configuration
sudo nginx -t

# View error logs
sudo tail -f /var/log/nginx/error.log

# Restart
sudo systemctl restart nginx
```

## 📞 Support Resources

- **Heroku**: https://help.heroku.com/
- **DigitalOcean**: https://docs.digitalocean.com/
- **Stripe**: https://support.stripe.com/
- **Let's Encrypt**: https://letsencrypt.org/docs/

---

**You're ready for production! 🚀**

Questions? Check the main README or create an issue.
