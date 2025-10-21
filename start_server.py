"""
Simplified Production Server Launcher for Windows
"""

import subprocess
import sys
import os

print("\n" + "="*75)
print("🏦 BANK STATEMENT CONVERTER - PRODUCTION SERVER")
print("="*75 + "\n")

print("📋 Prerequisites:")
print("   1. Redis must be running (redis-server or Docker)")
print("   2. All dependencies installed (pip install -r requirements.txt)")
print("\n" + "="*75 + "\n")

# Check if Redis is accessible
try:
    import redis
    client = redis.Redis(host='localhost', port=6379, socket_connect_timeout=2)
    client.ping()
    print("✅ Redis connection: OK\n")
except:
    print("❌ Redis connection: FAILED")
    print("\n🔴 Start Redis first:")
    print("   Option 1: docker run -d -p 6379:6379 redis:latest")
    print("   Option 2: redis-server.exe (if installed)")
    print("\n")
    sys.exit(1)

# Choose server type
print("Select server configuration:")
print("  1. High Performance (CPU×4 workers) - For production")
print("  2. Balanced (CPU×2 workers) - For testing")
print("  3. Development (Flask dev server) - For debugging\n")

choice = input("Enter choice (1-3) [1]: ").strip() or "1"

if choice == "3":
    print("\n🔧 Starting development server...")
    print("   URL: http://localhost:5000\n")
    subprocess.run([sys.executable, 'app.py'])

elif choice == "2":
    print("\n⚖️  Starting balanced production server...")
    print("   Workers: CPU×2")
    print("   URL: http://localhost:5000\n")
    subprocess.run(['gunicorn', '-c', 'gunicorn_config.py', 'app:app'])

else:
    print("\n🚀 Starting high-performance production server...")
    print("   Workers: CPU×4")
    print("   URL: http://localhost:5000\n")
    subprocess.run(['gunicorn', '-c', 'gunicorn_production.py', 'app_production:app'])
