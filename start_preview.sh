#!/bin/bash

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║                                                           ║"
echo "║         BankStatementAI SaaS Platform Preview            ║"
echo "║                                                           ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""
echo "🚀 Starting the SaaS platform..."
echo ""
echo "📍 The application will be available at:"
echo "   http://localhost:5000"
echo "   http://127.0.0.1:5000"
echo ""
echo "👤 Demo Account Credentials:"
echo "   Email: demo@example.com"
echo "   Password: demo123"
echo "   Tier: Professional (2000 pages/month)"
echo ""
echo "📄 See PREVIEW_INSTRUCTIONS.md for detailed preview guide"
echo ""
echo "⏸️  Press Ctrl+C to stop the server"
echo ""
echo "════════════════════════════════════════════════════════════"
echo ""

cd /workspace
python3 app_bankstatement_saas.py
