"""
Production Server Launcher
===========================

This script launches the application using Waitress (production WSGI server).
Waitress is recommended for Windows and is much more robust than Flask's
development server.

Features:
- Multi-threaded request handling
- Proper HTTP/1.1 support
- Production-grade performance
- Works on Windows without additional setup

Installation:
    pip install waitress

Usage:
    python run_production.py

Or with environment variables:
    set FLASK_ENV=production
    python run_production.py
"""

import os
import sys
from waitress import serve
from app import app

def main():
    """Launch production server"""
    
    # Configuration
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 8000))
    threads = int(os.environ.get('THREADS', 4))
    
    print("=" * 60)
    print("🚀 Starting Production Server")
    print("=" * 60)
    print(f"📍 Host: {host}")
    print(f"🔌 Port: {port}")
    print(f"🧵 Threads: {threads}")
    print(f"🌍 URL: http://{host}:{port}")
    print("=" * 60)
    print()
    print("✅ Server is ready to accept connections")
    print("⚠️  Press CTRL+C to stop the server")
    print()
    
    try:
        # Ensure app is in production mode
        app.config['DEBUG'] = False
        app.config['ENV'] = 'production'
        
        # Serve application with Waitress
        serve(
            app,
            host=host,
            port=port,
            threads=threads,
            url_scheme='http',
            ident='BankStatementConverter/1.0',  # Server identifier
            connection_limit=1000,  # Max simultaneous connections
            channel_timeout=120,    # Timeout for large file uploads (2 minutes)
            cleanup_interval=30,    # Cleanup stale connections every 30s
            asyncore_use_poll=True  # Better performance on Windows
        )
    except KeyboardInterrupt:
        print("\n\n⚠️  Server shutting down...")
        print("✅ Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Server error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    # Check if waitress is installed
    try:
        import waitress
    except ImportError:
        print("❌ Waitress not installed!")
        print("📦 Install it with: pip install waitress")
        sys.exit(1)
    
    main()
