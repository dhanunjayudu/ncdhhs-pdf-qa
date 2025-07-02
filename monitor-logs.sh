#!/bin/bash

# Monitor backend processing logs
echo "🔍 Monitoring NC DHHS PDF Processing Logs..."

# Configuration
LOG_GROUP="/ecs/ncdhhs-pdf-qa-dev-backend"
AWS_REGION="us-east-1"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to get latest log stream
get_latest_log_stream() {
    # First try to get the current running task ID from ECS
    local current_task_id=$(aws ecs describe-services \
        --cluster "ncdhhs-pdf-qa-dev-cluster" \
        --services "ncdhhs-pdf-qa-dev-service" \
        --region "$AWS_REGION" \
        --query 'services[0].deployments[?status==`PRIMARY`].runningCount' \
        --output text 2>/dev/null)
    
    if [ "$current_task_id" != "0" ] && [ "$current_task_id" != "None" ]; then
        # Get the actual running task ARN
        local task_arn=$(aws ecs list-tasks \
            --cluster "ncdhhs-pdf-qa-dev-cluster" \
            --service-name "ncdhhs-pdf-qa-dev-service" \
            --region "$AWS_REGION" \
            --query 'taskArns[0]' \
            --output text 2>/dev/null)
        
        if [ "$task_arn" != "None" ] && [ ! -z "$task_arn" ]; then
            # Extract task ID from ARN
            local task_id=$(echo "$task_arn" | cut -d'/' -f3)
            echo "ecs/ncdhhs-pdf-qa-dev-backend/$task_id"
            return
        fi
    fi
    
    # Fallback to the original method
    aws logs describe-log-streams \
        --log-group-name "$LOG_GROUP" \
        --region "$AWS_REGION" \
        --order-by LastEventTime \
        --descending \
        --max-items 1 \
        --query 'logStreams[0].logStreamName' \
        --output text 2>/dev/null
}

# Function to tail logs
tail_logs() {
    local stream_name=$1
    local start_time=$2
    
    print_status "Tailing logs from stream: $stream_name"
    print_status "Press Ctrl+C to stop monitoring"
    echo ""
    
    while true; do
        # Get logs from the last 30 seconds
        local current_time=$(date +%s)
        local query_start_time=$((current_time - 30))
        
        if [ ! -z "$start_time" ]; then
            query_start_time=$start_time
            start_time=""  # Only use start_time for first query
        fi
        
        aws logs get-log-events \
            --log-group-name "$LOG_GROUP" \
            --log-stream-name "$stream_name" \
            --region "$AWS_REGION" \
            --start-time "${query_start_time}000" \
            --query 'events[].message' \
            --output text 2>/dev/null | \
        while IFS= read -r line; do
            if [ ! -z "$line" ] && [ "$line" != "None" ]; then
                # Color code different types of messages
                if echo "$line" | grep -q "ERROR\|Error\|error"; then
                    echo -e "${RED}$line${NC}"
                elif echo "$line" | grep -q "WARNING\|Warning\|warning"; then
                    echo -e "${YELLOW}$line${NC}"
                elif echo "$line" | grep -q "INFO\|Processing\|Found\|Uploading"; then
                    echo -e "${GREEN}$line${NC}"
                elif echo "$line" | grep -q "PDF\|S3\|Knowledge"; then
                    echo -e "${BLUE}$line${NC}"
                else
                    echo "$line"
                fi
            fi
        done
        
        sleep 5
    done
}

# Function to show recent logs
show_recent_logs() {
    local stream_name=$1
    local minutes=${2:-5}
    
    print_status "Showing logs from last $minutes minutes..."
    echo ""
    
    # Calculate start time (5 minutes ago)
    local start_time=$(date -d "$minutes minutes ago" +%s 2>/dev/null || date -v-${minutes}M +%s)
    
    aws logs get-log-events \
        --log-group-name "$LOG_GROUP" \
        --log-stream-name "$stream_name" \
        --region "$AWS_REGION" \
        --start-time "${start_time}000" \
        --query 'events[].message' \
        --output text 2>/dev/null | \
    while IFS= read -r line; do
        if [ ! -z "$line" ] && [ "$line" != "None" ]; then
            # Color code different types of messages
            if echo "$line" | grep -q "ERROR\|Error\|error"; then
                echo -e "${RED}$line${NC}"
            elif echo "$line" | grep -q "WARNING\|Warning\|warning"; then
                echo -e "${YELLOW}$line${NC}"
            elif echo "$line" | grep -q "INFO\|Processing\|Found\|Uploading"; then
                echo -e "${GREEN}$line${NC}"
            elif echo "$line" | grep -q "PDF\|S3\|Knowledge"; then
                echo -e "${BLUE}$line${NC}"
            else
                echo "$line"
            fi
        fi
    done
}

# Main menu
echo "Choose monitoring option:"
echo "1. Show recent logs (last 5 minutes)"
echo "2. Show recent logs (last 15 minutes)"
echo "3. Tail logs in real-time"
echo "4. Check processing status"
echo ""
read -p "Enter choice (1-4): " choice

# Get the latest log stream
print_status "Finding latest log stream..."
STREAM_NAME=$(get_latest_log_stream)

if [ -z "$STREAM_NAME" ] || [ "$STREAM_NAME" = "None" ]; then
    print_error "Could not find log stream. Check if:"
    echo "  - AWS CLI is configured correctly"
    echo "  - You have permissions to access CloudWatch logs"
    echo "  - The ECS service is running"
    exit 1
fi

print_success "Found log stream: $STREAM_NAME"
echo ""

case $choice in
    1)
        show_recent_logs "$STREAM_NAME" 5
        ;;
    2)
        show_recent_logs "$STREAM_NAME" 15
        ;;
    3)
        # Start from 1 minute ago for real-time tailing
        start_time=$(date -d "1 minute ago" +%s 2>/dev/null || date -v-1M +%s)
        tail_logs "$STREAM_NAME" "$start_time"
        ;;
    4)
        print_status "Checking processing status..."
        curl -s "http://ncdhhs-pdf-qa-dev-alb-940310890.us-east-1.elb.amazonaws.com/processing-status" | python3 -m json.tool 2>/dev/null || echo "Could not get processing status"
        ;;
    *)
        print_error "Invalid choice"
        exit 1
        ;;
esac
