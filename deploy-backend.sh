#!/bin/bash

# Backend deployment script for AWS
echo "🚀 Deploying backend changes to AWS..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
ECR_REGISTRY="942713336312.dkr.ecr.us-east-1.amazonaws.com"
IMAGE_NAME="ncdhhs-pdf-qa-dev-backend"
ECS_CLUSTER="ncdhhs-pdf-qa-dev-cluster"
ECS_SERVICE="ncdhhs-pdf-qa-dev-service"
AWS_REGION="us-east-1"

# Function to print colored output
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

# Function to check if AWS CLI is configured
check_aws_cli() {
    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI is not installed. Please install it first."
        exit 1
    fi
    
    if ! aws sts get-caller-identity &> /dev/null; then
        print_error "AWS CLI is not configured. Please run 'aws configure' first."
        exit 1
    fi
    
    print_success "AWS CLI is configured"
}

# Function to check if Docker is running
check_docker() {
    if ! docker info &> /dev/null; then
        print_error "Docker is not running. Please start Docker first."
        exit 1
    fi
    
    print_success "Docker is running"
}

# Function to build Docker image
build_image() {
    print_status "Building Docker image..."
    
    cd backend
    if docker build -t $IMAGE_NAME .; then
        print_success "Docker image built successfully"
    else
        print_error "Failed to build Docker image"
        exit 1
    fi
    cd ..
}

# Function to tag and push image to ECR
push_to_ecr() {
    print_status "Logging in to Amazon ECR..."
    
    if aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REGISTRY; then
        print_success "Logged in to ECR"
    else
        print_error "Failed to login to ECR"
        exit 1
    fi
    
    print_status "Tagging image for ECR..."
    docker tag $IMAGE_NAME:latest $ECR_REGISTRY/$IMAGE_NAME:latest
    
    print_status "Pushing image to ECR..."
    if docker push $ECR_REGISTRY/$IMAGE_NAME:latest; then
        print_success "Image pushed to ECR successfully"
    else
        print_error "Failed to push image to ECR"
        exit 1
    fi
}

# Function to update ECS service
update_ecs_service() {
    print_status "Updating ECS service..."
    
    if aws ecs update-service \
        --cluster $ECS_CLUSTER \
        --service $ECS_SERVICE \
        --region $AWS_REGION \
        --output table > /dev/null; then
        print_success "ECS service update initiated"
    else
        print_error "Failed to update ECS service"
        exit 1
    fi
}

# Function to wait for deployment to complete
wait_for_deployment() {
    print_status "Waiting for deployment to complete..."
    
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        local status=$(aws ecs describe-services \
            --cluster $ECS_CLUSTER \
            --services $ECS_SERVICE \
            --region $AWS_REGION \
            --query 'services[0].deployments[?status==`PRIMARY`].rolloutState' \
            --output text)
        
        if [ "$status" = "COMPLETED" ]; then
            print_success "Deployment completed successfully!"
            return 0
        elif [ "$status" = "FAILED" ]; then
            print_error "Deployment failed!"
            return 1
        fi
        
        echo -n "."
        sleep 10
        ((attempt++))
    done
    
    print_warning "Deployment is taking longer than expected. Check AWS console for status."
    return 1
}

# Function to show deployment info
show_deployment_info() {
    echo ""
    print_success "Backend deployment completed!"
    echo ""
    echo "🔗 Backend URL: http://ncdhhs-pdf-qa-dev-alb-940310890.us-east-1.elb.amazonaws.com"
    echo "📚 API Docs: http://ncdhhs-pdf-qa-dev-alb-940310890.us-east-1.elb.amazonaws.com/docs"
    echo ""
    echo "💡 Your local frontend will automatically use the updated backend"
    echo "   No need to restart the frontend - just refresh your browser"
    echo ""
}

# Main deployment process
main() {
    echo "🔧 Backend Deployment to AWS"
    echo "=============================="
    echo ""
    
    # Pre-flight checks
    check_aws_cli
    check_docker
    
    # Build and deploy
    build_image
    push_to_ecr
    update_ecs_service
    
    # Wait for completion
    if wait_for_deployment; then
        show_deployment_info
    else
        print_error "Deployment may have issues. Please check AWS console."
        exit 1
    fi
}

# Run main function
main
