#!/usr/bin/env bash

# FlavorPilot Development Server Startup Script

set -e

echo "🚀 Starting FlavorPilot Development Environment..."

# Check if PostgreSQL is running
if ! command -v pg_isready &> /dev/null; then
    echo "⚠️  PostgreSQL not found. Please install PostgreSQL 14+ with pgvector extension."
    echo "   Installation guide: https://www.postgresql.org/download/"
fi

# Create database if it doesn't exist
echo "📊 Setting up database..."
psql -h localhost -U postgres -tc "SELECT 1 FROM pg_database WHERE datname = 'flavorpilot'" | grep -q 1 || \
    psql -h localhost -U postgres -c "CREATE DATABASE flavorpilot"

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install -q -r backend/requirements.txt

# Generate golden dataset
if [ ! -f "/workspace/scratch/golden_dataset_flavorpilot.json" ]; then
    echo "🔧 Generating golden dataset..."
    python seed_data_flavorpilot.py
fi

# Seed database
echo "🌱 Seeding database..."
python scripts/seed_database.py

# Start FastAPI backend in background
echo "🔥 Starting FastAPI backend server..."
cd backend && python -m app.main &
BACKEND_PID=$!

# Wait for backend to be ready
echo "⏳ Waiting for backend to be ready..."
sleep 3

# Start frontend dev server
echo "⚡ Starting Vite frontend dev server..."
cd ..
npm run dev &
FRONTEND_PID=$!

echo ""
echo "✅ FlavorPilot is running!"
echo ""
echo "   Frontend: http://localhost:5173"
echo "   Backend API: http://localhost:8000"
echo "   API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop all services"

# Trap SIGINT and cleanup
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" SIGINT

wait
