"""
WSGI Entry Point for Production Deployment
===========================================

This file serves as the entry point for production WSGI servers
like Gunicorn, uWSGI, or Waitress.

Usage Examples:
---------------

1. With Waitress (Windows-friendly):
   pip install waitress
   waitress-serve --host=0.0.0.0 --port=8000 wsgi:app

2. With Gunicorn (Linux):
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:8000 wsgi:app

3. With uWSGI:
   pip install uwsgi
   uwsgi --http :8000 --wsgi-file wsgi.py --callable app

Configuration:
--------------
- Workers: 4 (adjust based on CPU cores: 2-4 x cores)
- Timeout: 120 seconds (for large PDF processing)
- Max requests: 1000 (restarts worker after 1000 requests to prevent memory leaks)
"""

from app import app

# Application instance for WSGI server
application = app

if __name__ == "__main__":
    # This block is for local testing only
    # In production, use a proper WSGI server
    print("⚠️  Starting development server...")
    print("⚠️  For production, use: waitress-serve --host=0.0.0.0 --port=8000 wsgi:app")
    app.run(host='0.0.0.0', port=8000, debug=False)
