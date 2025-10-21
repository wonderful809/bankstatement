"""
Production Startup Script for BankStatement.AI
Optimized for high performance with Gunicorn + Gevent
"""
import os
import sys
import subprocess
import multiprocessing

def check_dependencies():
    """Check if all required dependencies are installed"""
    print("🔍 Checking dependencies...")
    
    required_packages = [
        'gunicorn',
        'gevent',
        'redis',
        'flask_caching',
        'flask_compress'
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)
    
    if missing:
        print(f"❌ Missing packages: {', '.join(missing)}")
        print("📦 Installing missing packages...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
        print("✅ Dependencies installed!")
    else:
        print("✅ All dependencies are installed!")

def check_redis():
    """Check if Redis is running"""
    print("\n🔍 Checking Redis connection...")
    try:
        import redis
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        r = redis.from_url(redis_url)
        r.ping()
        print("✅ Redis is running!")
        return True
    except Exception as e:
        print(f"⚠️  Redis not available: {e}")
        print("💡 Install Redis for better performance:")
        print("   Windows: https://github.com/microsoftarchive/redis/releases")
        print("   Mac: brew install redis")
        print("   Linux: sudo apt-get install redis-server")
        print("\n📝 Continuing without Redis (using simple cache)...")
        return False

def start_server():
    """Start the production server with Gunicorn"""
    print("\n🚀 Starting production server...")
    print("=" * 60)
    
    # Number of workers (CPU cores * 2 + 1)
    workers = multiprocessing.cpu_count() * 2 + 1
    
    # Set environment variables
    os.environ['FLASK_ENV'] = 'production'
    os.environ['TESSERACT_CMD'] = os.getenv('TESSERACT_CMD', 
        r'C:\Program Files\Tesseract-OCR\tesseract.exe')
    os.environ['POPPLER_PATH'] = os.getenv('POPPLER_PATH',
        r'C:\Users\gadip\AppData\Local\Microsoft\WinGet\Packages\oschwartz10612.Poppler_Microsoft.Winget.Source_8wekyb3d8bbwe\poppler-25.07.0\Library\bin')
    
    # Gunicorn command
    cmd = [
        'gunicorn',
        '--config', 'gunicorn_config.py',
        '--workers', str(workers),
        '--worker-class', 'gevent',
        '--worker-connections', '1000',
        '--bind', '0.0.0.0:5000',
        '--timeout', '300',
        '--access-logfile', '-',
        '--error-logfile', '-',
        '--log-level', 'info',
        'app_saas:app'
    ]
    
    print(f"📊 Configuration:")
    print(f"   Workers: {workers}")
    print(f"   Worker Class: gevent (async)")
    print(f"   Max Connections: 1000 per worker")
    print(f"   Timeout: 300 seconds")
    print(f"   Bind: 0.0.0.0:5000")
    print("=" * 60)
    print(f"\n✨ Server will be available at: http://127.0.0.1:5000")
    print("Press CTRL+C to stop\n")
    
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down gracefully...")
        print("✅ Server stopped!")

def start_celery_worker():
    """Start Celery worker for background tasks"""
    print("\n🔧 Starting Celery worker...")
    
    cmd = [
        'celery',
        '-A', 'celery_tasks',
        'worker',
        '--loglevel=info',
        '--concurrency=4',
        '--pool=gevent'
    ]
    
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n👋 Stopping Celery worker...")

def main():
    """Main startup function"""
    print("""
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║          🏦 BankStatement.AI Production Server          ║
║          High Performance Mode                          ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
    """)
    
    # Check dependencies
    check_dependencies()
    
    # Check Redis
    redis_available = check_redis()
    
    # Ask user what to start
    print("\n📋 What would you like to start?")
    print("   1. Web Server (Gunicorn)")
    print("   2. Celery Worker (Background Tasks)")
    print("   3. Both (Requires 2 terminals)")
    
    choice = input("\nEnter choice (1-3): ").strip()
    
    if choice == '1':
        start_server()
    elif choice == '2':
        if not redis_available:
            print("❌ Redis is required for Celery. Please install and start Redis first.")
            sys.exit(1)
        start_celery_worker()
    elif choice == '3':
        print("\n📝 Instructions:")
        print("   1. Open TWO terminal windows")
        print("   2. Terminal 1: python start_production.py → Choose option 1")
        print("   3. Terminal 2: python start_production.py → Choose option 2")
        print("\nPress Enter to start Web Server in this terminal...")
        input()
        start_server()
    else:
        print("❌ Invalid choice!")
        sys.exit(1)

if __name__ == '__main__':
    main()
