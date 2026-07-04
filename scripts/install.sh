#!/bin/bash

echo "🔧 Installing Forex AI Trading System..."
echo "========================================="

# Install AI Service
echo "📦 Installing Python dependencies..."
cd ai-service
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cd ..

# Install Backend
echo "📦 Installing Node.js backend dependencies..."
cd backend
npm install
cd ..

# Install Frontend
echo "📦 Installing React frontend dependencies..."
cd frontend
npm install
cd ..

echo ""
echo "✅ Installation complete!"
echo ""
echo "To start the system:"
echo "  ./scripts/start.sh"
echo ""