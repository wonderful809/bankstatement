#!/usr/bin/env python3
"""
Simple script to run the BankStatementAI SaaS platform
"""

import os
import sys

print("""
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║       🚀 BankStatementAI SaaS Platform Starting...       ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝

📍 Server will be available at:
   • http://localhost:5000
   • http://127.0.0.1:5000
   • http://0.0.0.0:5000

👤 Demo Account Credentials:
   • Email: demo@example.com
   • Password: demo123
   • Tier: Professional (2000 pages/month)

📖 Documentation:
   • See PREVIEW_READY.md for preview guide
   • See QUICK_START_SAAS.md for full setup

⏸️  Press Ctrl+C to stop the server

════════════════════════════════════════════════════════════
Starting Flask development server...
════════════════════════════════════════════════════════════
""")

# Change to workspace directory
os.chdir('/workspace')

# Import and run the app
try:
    from app_bankstatement_saas import app
    
    # Run the Flask app
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True,
        use_reloader=False  # Disable reloader to avoid double startup
    )
except KeyboardInterrupt:
    print("\n\n✅ Server stopped. Thank you for using BankStatementAI!")
    sys.exit(0)
except Exception as e:
    print(f"\n\n❌ Error starting server: {e}")
    print("\nCheck the logs above for details.")
    sys.exit(1)
