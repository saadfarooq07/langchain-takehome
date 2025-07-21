#!/bin/bash
# Start the demo with enhanced analysis

echo "🚀 Starting Log Analyzer Demo with Enhanced Analysis..."
echo ""

# Kill any existing processes
echo "Cleaning up old processes..."
pkill -f "python main.py" 2>/dev/null
pkill -f "npm start" 2>/dev/null
sleep 2

# Start backend
echo "Starting backend API..."
cd /home/shl0th/Documents/langchain-takehome
USE_ENHANCED_ANALYSIS=true python main.py --mode api > backend.log 2>&1 &
BACKEND_PID=$!
echo "Backend PID: $BACKEND_PID"

# Wait for backend to start
echo "Waiting for backend to start..."
sleep 5

# Check if backend is running
if ! curl -s http://localhost:8000/health > /dev/null; then
    echo "❌ Backend failed to start. Check backend.log"
    exit 1
fi
echo "✅ Backend is running at http://localhost:8000"

# Start frontend
echo ""
echo "Starting frontend..."
cd frontend
npm start > ../frontend.log 2>&1 &
FRONTEND_PID=$!
echo "Frontend PID: $FRONTEND_PID"

echo ""
echo "🎉 Demo is starting!"
echo ""
echo "📍 Frontend: http://localhost:3001"
echo "📍 Backend API: http://localhost:8000"
echo "📍 API Docs: http://localhost:8000/docs"
echo ""
echo "Demo Credentials:"
echo "  Email: demo2@example.com"
echo "  Password: demo123"
echo ""
echo "To stop the demo, run: pkill -f 'python main.py' && pkill -f 'npm start'"
echo ""
echo "Logs:"
echo "  Backend: tail -f backend.log"
echo "  Frontend: tail -f frontend.log"