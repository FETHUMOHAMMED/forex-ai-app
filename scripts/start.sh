#!/bin/bash

echo "🚀 Starting Forex AI Trading System..."
echo "======================================="

# Check if ports are available
check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null ; then
        echo "❌ Port $1 is already in use"
        exit 1
    fi
}

check_port 3001
check_port 8080
check_port 3000

# Start AI Service (background)
echo "🤖 Starting AI Service..."
cd ai-service
source venv/bin/activate
python ai_service.py &
AI_PID=$!
cd ..

# Start Backend
echo "🔧 Starting Backend Server..."
cd backend
npm run dev &
BACKEND_PID=$!
cd ..

# Start Frontend
echo "🎨 Starting Frontend Dashboard..."
cd frontend
npm start &
FRONTEND_PID=$!
cd ..

echo ""
echo "✅ All services started!"
echo ""
echo "📊 Dashboard: http://localhost:3000"
echo "🔌 API: http://localhost:3001"
echo "📡 WebSocket: ws://localhost:8080"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for Ctrl+C
wait