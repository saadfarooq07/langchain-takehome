#!/bin/bash

# Script to manage Cloudflare Workers secrets

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    case $1 in
        "error")
            echo -e "${RED}✗ $2${NC}"
            ;;
        "success")
            echo -e "${GREEN}✓ $2${NC}"
            ;;
        "info")
            echo -e "${YELLOW}ℹ $2${NC}"
            ;;
    esac
}

# Check if wrangler is installed
if ! command -v wrangler &> /dev/null; then
    print_status "error" "Wrangler is not installed. Please run: bun add -d wrangler"
    exit 1
fi

# Function to set a secret
set_secret() {
    local secret_name=$1
    local environment=$2
    
    print_status "info" "Setting secret: $secret_name for environment: $environment"
    
    if [ "$environment" == "production" ]; then
        wrangler secret put $secret_name --env production
    else
        wrangler secret put $secret_name --env staging
    fi
}

# Function to list secrets
list_secrets() {
    local environment=$1
    
    print_status "info" "Listing secrets for environment: $environment"
    
    if [ "$environment" == "production" ]; then
        wrangler secret list --env production
    else
        wrangler secret list --env staging
    fi
}

# Main menu
echo "Cloudflare Workers Secret Management"
echo "===================================="
echo ""
echo "1. Set secrets for staging"
echo "2. Set secrets for production"
echo "3. List secrets for staging"
echo "4. List secrets for production"
echo "5. Set all secrets for an environment"
echo "6. Exit"
echo ""
read -p "Select an option: " choice

case $choice in
    1)
        echo "Which secret would you like to set?"
        echo "1. VITE_GOOGLE_CLIENT_ID"
        echo "2. VITE_API_URL"
        echo "3. VITE_AUTH_API_URL"
        echo "4. VITE_SUPABASE_URL"
        echo "5. VITE_SUPABASE_ANON_KEY"
        read -p "Select: " secret_choice
        
        case $secret_choice in
            1) set_secret "VITE_GOOGLE_CLIENT_ID" "staging" ;;
            2) set_secret "VITE_API_URL" "staging" ;;
            3) set_secret "VITE_AUTH_API_URL" "staging" ;;
            4) set_secret "VITE_SUPABASE_URL" "staging" ;;
            5) set_secret "VITE_SUPABASE_ANON_KEY" "staging" ;;
            *) print_status "error" "Invalid choice" ;;
        esac
        ;;
    2)
        echo "Which secret would you like to set?"
        echo "1. VITE_GOOGLE_CLIENT_ID"
        echo "2. VITE_API_URL"
        echo "3. VITE_AUTH_API_URL"
        echo "4. VITE_SUPABASE_URL"
        echo "5. VITE_SUPABASE_ANON_KEY"
        read -p "Select: " secret_choice
        
        case $secret_choice in
            1) set_secret "VITE_GOOGLE_CLIENT_ID" "production" ;;
            2) set_secret "VITE_API_URL" "production" ;;
            3) set_secret "VITE_AUTH_API_URL" "production" ;;
            4) set_secret "VITE_SUPABASE_URL" "production" ;;
            5) set_secret "VITE_SUPABASE_ANON_KEY" "production" ;;
            *) print_status "error" "Invalid choice" ;;
        esac
        ;;
    3)
        list_secrets "staging"
        ;;
    4)
        list_secrets "production"
        ;;
    5)
        read -p "Environment (staging/production): " env
        print_status "info" "Setting all secrets for $env environment"
        
        # Read from .env file if it exists
        if [ -f ".env.$env" ]; then
            print_status "info" "Reading from .env.$env file"
            export $(cat .env.$env | xargs)
            
            echo "$VITE_GOOGLE_CLIENT_ID" | wrangler secret put VITE_GOOGLE_CLIENT_ID --env $env
            echo "$VITE_API_URL" | wrangler secret put VITE_API_URL --env $env
            echo "$VITE_AUTH_API_URL" | wrangler secret put VITE_AUTH_API_URL --env $env
            echo "$VITE_SUPABASE_URL" | wrangler secret put VITE_SUPABASE_URL --env $env
            echo "$VITE_SUPABASE_ANON_KEY" | wrangler secret put VITE_SUPABASE_ANON_KEY --env $env
            
            print_status "success" "All secrets set from .env.$env"
        else
            print_status "info" "No .env.$env file found. Please enter values manually:"
            set_secret "VITE_GOOGLE_CLIENT_ID" "$env"
            set_secret "VITE_API_URL" "$env"
            set_secret "VITE_AUTH_API_URL" "$env"
            set_secret "VITE_SUPABASE_URL" "$env"
            set_secret "VITE_SUPABASE_ANON_KEY" "$env"
        fi
        ;;
    6)
        print_status "info" "Exiting..."
        exit 0
        ;;
    *)
        print_status "error" "Invalid choice"
        ;;
esac