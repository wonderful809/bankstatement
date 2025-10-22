#!/bin/bash

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║                                                           ║"
echo "║           Quick Commands - BankStatementAI SaaS          ║"
echo "║                                                           ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""
echo "Choose an option:"
echo ""
echo "1. Start the server (REQUIRED before accessing website)"
echo "2. Check if server is running"
echo "3. Stop the server"
echo "4. View server logs"
echo "5. Test database connection"
echo ""
read -p "Enter choice (1-5): " choice

case $choice in
    1)
        echo ""
        echo "🚀 Starting server..."
        echo "Once started, visit: http://localhost:5000"
        echo "Login: demo@example.com / demo123"
        echo ""
        echo "Press Ctrl+C to stop the server when done"
        echo ""
        cd /workspace
        python3 RUN_SERVER.py
        ;;
    2)
        echo ""
        if lsof -Pi :5000 -sTCP:LISTEN -t >/dev/null 2>&1; then
            echo "✅ Server IS running on port 5000"
            echo "   Visit: http://localhost:5000"
        else
            echo "❌ Server is NOT running"
            echo "   Run option 1 to start it"
        fi
        ;;
    3)
        echo ""
        echo "⏸️  Stopping server..."
        pkill -f "python3.*app_bankstatement_saas"
        echo "✅ Server stopped"
        ;;
    4)
        echo ""
        echo "📋 Recent logs:"
        tail -20 /workspace/app.log
        ;;
    5)
        echo ""
        cd /workspace
        python3 -c "from app_bankstatement_saas import app, db; from models_saas import User; app.app_context().push(); print(f'✅ Database OK - Users: {User.query.count()}')"
        ;;
    *)
        echo "Invalid choice"
        ;;
esac
