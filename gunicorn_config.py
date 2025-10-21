"""
Gunicorn Configuration for Production - Optimized for MILLIONS of Requests
Designed to handle 50K-100K concurrent connections per server
"""
import multiprocessing
import os

# Server Socket
bind = '0.0.0.0:5000'
backlog = 4096  # Increased for high traffic (max pending connections)

# Worker Processes - Optimized for Maximum Throughput
workers = multiprocessing.cpu_count() * 4  # 4 workers per CPU core for maximum performance
worker_class = 'gevent'  # Async workers - each can handle 1000+ concurrent connections
worker_connections = 2000  # Max concurrent connections per worker (increased from 1000)
max_requests = 10000  # Restart after 10K requests (prevents memory leaks)
max_requests_jitter = 100  # Add randomness to prevent thundering herd
timeout = 120  # Reduced timeout (2 minutes) - long tasks should go to Celery
keepalive = 10  # Increased keep-alive for persistent connections

# Threading - Hybrid model for I/O operations
threads = 2  # 2 threads per worker for I/O-bound tasks

# Server Mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# Logging
accesslog = '-'  # Log to stdout
errorlog = '-'   # Log to stderr
loglevel = 'info'
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process Naming
proc_name = 'bankstatement-ai'

# Server Hooks
def on_starting(server):
    """Called just before the master process is initialized."""
    print(f"🚀 Starting BankStatement.AI with {workers} workers...")

def on_reload(server):
    """Called to recycle workers during a reload via SIGHUP."""
    print("🔄 Reloading workers...")

def when_ready(server):
    """Called just after the server is started."""
    print("✅ Server is ready! Listening on", bind)

def worker_int(worker):
    """Called just after a worker exited on SIGINT or SIGQUIT."""
    print(f"⚠️  Worker {worker.pid} received INT or QUIT signal")

def worker_abort(worker):
    """Called when a worker received the SIGABRT signal."""
    print(f"❌ Worker {worker.pid} received SIGABRT signal")

# Performance Tuning
preload_app = True  # Load app before forking workers (saves memory)
reuse_port = True   # Allow multiple workers to bind to same port

# SSL Configuration (if using HTTPS directly)
# keyfile = '/path/to/keyfile'
# certfile = '/path/to/certfile'

# Environment Variables
raw_env = [
    'FLASK_ENV=production',
]
