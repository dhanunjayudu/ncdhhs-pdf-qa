#!/bin/bash

# Full local development startup script - Both Frontend and Backend local
echo "🚀 Starting NC DHHS PDF Q&A Application (Full Local Development)..."

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
    echo "🐍 Starting FastAPI backend locally..."
    check_port 8000
    
    cd backend
    
    # Check if virtual environment exists
    if [ ! -d "venv" ]; then
        echo "Creating Python virtual environment..."
        python3 -m venv venv
    fi
    
    source venv/bin/activate
    
    # Install dependencies if needed
    if [ ! -f "venv/installed" ]; then
        echo "Installing Python dependencies..."
        pip install -r requirements.txt
        touch venv/installed
    fi
    
    echo "Starting FastAPI server on http://localhost:8000"
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
    BACKEND_PID=$!
    echo $BACKEND_PID > ../backend.pid
    cd ..
    
    # Wait for backend to start
    echo "Waiting for backend to start..."
    for i in {1..15}; do
        if curl -s http://localhost:8000/health > /dev/null 2>&1; then
            echo "✅ Backend started successfully"
            return 0
        fi
        sleep 1
    done
    
    echo "❌ Backend failed to start"
    return 1
}

# Function to start frontend with local backend
start_frontend() {
    echo "⚛️  Starting React frontend (connecting to local backend)..."
    check_port 3000
    
    cd frontend
    
    # Create local environment file for local backend
    cat > .env.local << EOF
# Local development environment - connects to local backend
REACT_APP_API_URL=http://localhost:8000
REACT_APP_TITLE=NC DHHS PDF Q&A Assistant (Full Local)
REACT_APP_AWS_REGION=us-east-1
REACT_APP_ENVIRONMENT=local-full
REACT_APP_VERSION=4.0.0
EOF
    
    # Install dependencies if needed
    if [ ! -d "node_modules" ]; then
        echo "Installing Node.js dependencies..."
        npm install
    fi
    
    npm start &
    FRONTEND_PID=$!
    echo $FRONTEND_PID > ../frontend.pid
    cd ..
    
    # Wait for frontend to start
    echo "Waiting for frontend to start..."
    for i in {1..15}; do
        if curl -s -I http://localhost:3000 > /dev/null 2>&1; then
            echo "✅ Frontend started successfully"
            return 0
        fi
        sleep 1
    done
    
    echo "❌ Frontend failed to start"
    return 1
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
    lsof -ti:3000 | xargs kill -9 2>/dev/null || true
    
    echo "✅ Services stopped"
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Start services
echo "Starting backend..."
if start_backend; then
    echo "Starting frontend..."
    if start_frontend; then
        echo ""
        echo "🎉 Full local development environment started successfully!"
        echo ""
        echo "📱 Frontend: http://localhost:3000"
        echo "🔧 Backend API: http://localhost:8000"
        echo "📚 API Docs: http://localhost:8000/docs"
        echo ""
        echo "💡 Both frontend and backend are running locally"
        echo "   - Frontend changes will auto-reload"
        echo "   - Backend changes will auto-reload"
        echo ""
        echo "Press Ctrl+C to stop both services"
        
        # Wait for user to stop
        wait
    else
        echo "❌ Failed to start frontend"
        cleanup
        exit 1
    fi
else
    echo "❌ Failed to start backend"
    exit 1
fi
