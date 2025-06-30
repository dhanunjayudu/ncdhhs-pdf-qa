#!/bin/bash

# Enhanced startup script with port checking
echo "🚀 Starting NC DHHS PDF Q&A Application..."

# Function to check if port is in use
check_port() {
    local port=$1
    if lsof -ti:$port > /dev/null 2>&1; then
        echo "⚠️  Port $port is in use. Stopping existing processes..."
        lsof -ti:$port | xargs kill -9 2>/dev/null || true
        sleep 2
    fi
}

# Function to start backend
start_backend() {
    echo "🐍 Starting FastAPI backend..."
    check_port 8000
    
    cd backend
    source venv/bin/activate
    
    echo "Starting FastAPI server on http://localhost:8000"
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
    BACKEND_PID=$!
    echo $BACKEND_PID > ../backend.pid
    cd ..
    
    # Wait for backend to start
    echo "Waiting for backend to start..."
    for i in {1..10}; do
        if curl -s http://localhost:8000/health > /dev/null 2>&1; then
            echo "✅ Backend started successfully"
            break
        fi
        sleep 1
    done
}

# Function to start frontend
start_frontend() {
    echo "⚛️  Starting React frontend..."
    check_port 5173
    
    cd frontend
    npm run dev &
    FRONTEND_PID=$!
    echo $FRONTEND_PID > ../frontend.pid
    cd ..
    
    # Wait for frontend to start
    echo "Waiting for frontend to start..."
    for i in {1..10}; do
        if curl -s -I http://localhost:5173 > /dev/null 2>&1; then
            echo "✅ Frontend started successfully"
            break
        fi
        sleep 1
    done
}

# Cleanup function
cleanup() {
    echo ""
    echo "🛑 Stopping services..."
    if [ -f "backend.pid" ]; then
        kill $(cat backend.pid) 2>/dev/null || true
        rm backend.pid
    fi
    if [ -f "frontend.pid" ]; then
        kill $(cat frontend.pid) 2>/dev/null || true
        rm frontend.pid
    fi
    
    # Also kill any remaining processes on our ports
    lsof -ti:8000 | xargs kill -9 2>/dev/null || true
    lsof -ti:5173 | xargs kill -9 2>/dev/null || true
    
    echo "✅ Services stopped"
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Start services
start_backend
start_frontend

echo ""
echo "🎉 Application started successfully!"
echo ""
echo "📱 Frontend: http://localhost:5173"
echo "🔧 Backend API: http://localhost:8000"
echo "📚 API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop both services"

# Wait for user to stop
wait
