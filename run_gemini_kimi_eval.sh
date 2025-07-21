#!/bin/bash

# Script to run evaluation with Gemini 2.5 Flash and Kimi K2 Instruct
# This script sources the .env file and runs the evaluation

echo "=========================================="
echo "Log Analyzer Evaluation"
echo "Primary Model: Gemini 1.5 Flash"
echo "Orchestration Model: Kimi K2 Instruct"
echo "=========================================="

# Source environment variables
if [ -f .env ]; then
    echo "Loading environment variables from .env..."
    export $(cat .env | grep -v '^#' | xargs)
else
    echo "Error: .env file not found!"
    echo "Please copy .env.example to .env and add your API keys"
    exit 1
fi

# Verify API keys are set
if [ -z "$GEMINI_API_KEY" ] || [ -z "$GROQ_API_KEY" ] || [ -z "$TAVILY_API_KEY" ]; then
    echo "Error: Missing required API keys!"
    echo "Please ensure GEMINI_API_KEY, GROQ_API_KEY, and TAVILY_API_KEY are set in .env"
    exit 1
fi

echo ""
echo "API Keys verified ✓"
echo ""

# Default values
DATASET="log-analyzer-evaluation"
MAX_EXAMPLES=10
EXPERIMENT_PREFIX="gemini25-kimik2"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dataset)
            DATASET="$2"
            shift 2
            ;;
        --max-examples)
            MAX_EXAMPLES="$2"
            shift 2
            ;;
        --experiment-prefix)
            EXPERIMENT_PREFIX="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  --dataset DATASET           Dataset name (default: log-analyzer-evaluation)"
            echo "  --max-examples N            Max examples to evaluate (default: 10)"
            echo "  --experiment-prefix PREFIX  Experiment prefix (default: gemini25-kimik2)"
            echo "  --help                      Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

echo "Configuration:"
echo "  Dataset: $DATASET"
echo "  Max Examples: $MAX_EXAMPLES"
echo "  Experiment Prefix: $EXPERIMENT_PREFIX"
echo ""

# Run the evaluation
echo "Starting evaluation..."
echo ""

python evaluation/scripts/evaluate_agent_consolidated.py \
    --dataset "$DATASET" \
    --primary-model "gemini:gemini-1.5-flash" \
    --orchestration-model "groq:moonshotai/kimi-k2-instruct" \
    --max-examples "$MAX_EXAMPLES" \
    --experiment-prefix "$EXPERIMENT_PREFIX"

echo ""
echo "=========================================="
echo "Evaluation complete!"
echo "Check the results in the generated JSON file and LangSmith dashboard"
echo "=========================================="