#!/bin/bash

# NC DHHS PDF Q&A Terraform Deployment Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Check if terraform.tfvars exists
if [ ! -f "terraform.tfvars" ]; then
    print_warning "terraform.tfvars not found. Creating from example..."
    cp terraform.tfvars.example terraform.tfvars
    print_warning "Please edit terraform.tfvars with your specific values before proceeding."
    exit 1
fi

# Parse command line arguments
ACTION=${1:-plan}

case $ACTION in
    "init")
        print_status "Initializing Terraform..."
        terraform init
        print_success "Terraform initialized successfully!"
        ;;
    "plan")
        print_status "Planning Terraform deployment..."
        terraform plan
        ;;
    "apply")
        print_status "Applying Terraform configuration..."
        terraform apply
        if [ $? -eq 0 ]; then
            print_success "Infrastructure deployed successfully!"
            print_status "Getting outputs..."
            terraform output
        else
            print_error "Deployment failed!"
            exit 1
        fi
        ;;
    "destroy")
        print_warning "This will destroy all infrastructure!"
        read -p "Are you sure? (yes/no): " confirm
        if [ "$confirm" = "yes" ]; then
            print_status "Destroying infrastructure..."
            terraform destroy
            print_success "Infrastructure destroyed!"
        else
            print_status "Destruction cancelled."
        fi
        ;;
    "output")
        print_status "Showing Terraform outputs..."
        terraform output
        ;;
    *)
        echo "Usage: $0 {init|plan|apply|destroy|output}"
        echo ""
        echo "Commands:"
        echo "  init     - Initialize Terraform"
        echo "  plan     - Show deployment plan"
        echo "  apply    - Deploy infrastructure"
        echo "  destroy  - Destroy infrastructure"
        echo "  output   - Show outputs"
        exit 1
        ;;
esac
