#!/bin/bash
# Script to run langgraph dev with environment variables loaded

# Load environment variables from .env file
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
    echo "✓ Environment variables loaded from .env"
else
    echo "✗ Error: .env file not found"
    exit 1
fi

# Verify required environment variables
required_vars=("GEMINI_API_KEY" "GROQ_API_KEY" "TAVILY_API_KEY")
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "✗ Error: $var is not set"
        exit 1
    else
        echo "✓ $var is set"
    fi
done

# Run langgraph dev
echo ""
echo "Starting LangGraph development server..."
langgraph dev