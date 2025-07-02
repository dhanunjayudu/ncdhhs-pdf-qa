#!/bin/bash

# Local development startup script - Frontend only (connects to AWS backend)
echo "🚀 Starting NC DHHS PDF Q&A Application (Local Frontend + AWS Backend)..."

# Function to check if port is in use
check_port() {
    local port=$1
    if lsof -ti:$port > /dev/null 2>&1; then
        echo "⚠️  Port $port is in use. Stopping existing processes..."
        lsof -ti:$port | xargs kill -9 2>/dev/null || true
        sleep 2
    fi
}

# Function to check AWS backend connectivity
check_backend() {
    local backend_url="http://ncdhhs-pdf-qa-dev-alb-940310890.us-east-1.elb.amazonaws.com"
    echo "🔍 Checking AWS backend connectivity..."
    
    if curl -s --max-time 10 "$backend_url/health" > /dev/null 2>&1; then
        echo "✅ AWS backend is accessible at $backend_url"
        return 0
    else
        echo "❌ AWS backend is not accessible at $backend_url"
        echo "   Please check:"
        echo "   - Your internet connection"
        echo "   - AWS backend deployment status"
        echo "   - Load balancer URL is correct"
        return 1
    fi
}

# Function to start frontend only
start_frontend() {
    echo "⚛️  Starting React frontend (connecting to AWS backend)..."
    check_port 3000
    
    cd frontend
    
    # Ensure we're using the local development environment
    export NODE_ENV=development
    
    # Start the frontend
    npm start &
    FRONTEND_PID=$!
    echo $FRONTEND_PID > ../frontend.pid
    cd ..
    
    # Wait for frontend to start
    echo "Waiting for frontend to start..."
    for i in {1..30}; do
        if curl -s -I http://localhost:3000 > /dev/null 2>&1; then
            echo "✅ Frontend started successfully"
            return 0
        fi
        sleep 2
    done
    
    echo "❌ Frontend failed to start"
    return 1
}

# Function to show development info
show_dev_info() {
    echo ""
    echo "🎉 Local development environment started successfully!"
    echo ""
    echo "📱 Frontend (Local):  http://localhost:3000"
    echo "🔧 Backend (AWS):     http://ncdhhs-pdf-qa-dev-alb-940310890.us-east-1.elb.amazonaws.com"
    echo "📚 API Docs (AWS):    http://ncdhhs-pdf-qa-dev-alb-940310890.us-east-1.elb.amazonaws.com/docs"
    echo ""
    echo "💡 Development Tips:"
    echo "   - Frontend changes will auto-reload"
    echo "   - Backend is running on AWS (no local changes needed)"
    echo "   - Check browser console for any errors"
    echo ""
    echo "✅ The blank screen issue has been fixed!"
    echo "   - React hook dependencies are now properly configured"
    echo "   - Functions are declared before being used"
    echo ""
    echo "🔄 To deploy backend changes:"
    echo "   1. Make changes to backend code"
    echo "   2. Run: cd backend && docker build -t ncdhhs-pdf-qa-dev-backend ."
    echo "   3. Run: docker tag ncdhhs-pdf-qa-dev-backend:latest 942713336312.dkr.ecr.us-east-1.amazonaws.com/ncdhhs-pdf-qa-dev-backend:latest"
    echo "   4. Run: docker push 942713336312.dkr.ecr.us-east-1.amazonaws.com/ncdhhs-pdf-qa-dev-backend:latest"
    echo "   5. Update ECS service to deploy new image"
    echo ""
    echo "Press Ctrl+C to stop the frontend"
}

# Cleanup function
cleanup() {
    echo ""
    echo "🛑 Stopping frontend..."
    if [ -f "frontend.pid" ]; then
        kill $(cat frontend.pid) 2>/dev/null || true
        rm frontend.pid
    fi
    
    # Kill any remaining processes on frontend port
    lsof -ti:3000 | xargs kill -9 2>/dev/null || true
    
    echo "✅ Frontend stopped"
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Check backend connectivity first
if ! check_backend; then
    echo ""
    echo "⚠️  Warning: AWS backend is not accessible."
    echo "   You can still start the frontend, but it won't be able to connect to the backend."
    echo ""
    read -p "Do you want to continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Exiting..."
        exit 1
    fi
fi

# Start frontend
if start_frontend; then
    show_dev_info
    # Wait for user to stop
    wait
else
    echo "❌ Failed to start frontend"
    exit 1
fi
