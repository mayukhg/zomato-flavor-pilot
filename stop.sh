#!/usr/bin/env bash

# FlavorPilot Development Server Shutdown Script

set -e

echo "🛑 Stopping FlavorPilot Development Environment..."

# Find and kill FastAPI backend processes
echo "📊 Stopping FastAPI backend..."
pkill -f "python -m app.main" 2>/dev/null && echo "   ✓ Backend stopped" || echo "   ℹ️  No backend process found"

# Find and kill Vite frontend processes
echo "⚡ Stopping Vite frontend..."
pkill -f "vite" 2>/dev/null && echo "   ✓ Frontend stopped" || echo "   ℹ️  No frontend process found"

# Additional cleanup for any node processes running on default ports
lsof -ti:5173 2>/dev/null | xargs kill -9 2>/dev/null || true
lsof -ti:8000 2>/dev/null | xargs kill -9 2>/dev/null || true

echo ""
echo "✅ FlavorPilot has been stopped!"
echo ""
