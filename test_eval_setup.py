#!/usr/bin/env python3
"""
Quick test script to verify evaluation setup with Gemini 1.5 Flash and Kimi K2
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Verify API keys
required_keys = ['GEMINI_API_KEY', 'GROQ_API_KEY', 'TAVILY_API_KEY', 'LANGSMITH_API_KEY']
missing_keys = [key for key in required_keys if not os.getenv(key)]

if missing_keys:
    print(f"❌ Missing API keys: {', '.join(missing_keys)}")
    print("Please ensure all keys are set in your .env file")
    sys.exit(1)

print("✅ All API keys verified")

# Import the evaluation module
try:
    from evaluation.scripts.evaluate_agent_consolidated import run_evaluation
    import asyncio
    print("✅ Evaluation module imported successfully")
except ImportError as e:
    print(f"❌ Failed to import evaluation module: {e}")
    sys.exit(1)

# Test configuration
print("\n" + "="*50)
print("Test Evaluation Configuration:")
print("  Primary Model: gemini:gemini-1.5-flash")
print("  Orchestration Model: groq:moonshotai/kimi-k2-instruct")
print("  Dataset: log-analyzer-evaluation")
print("  Max Examples: 3 (for quick test)")
print("="*50 + "\n")

async def test_evaluation():
    """Run a quick test evaluation"""
    try:
        await run_evaluation(
            dataset_name="log-analyzer-evaluation",
            max_examples=3,  # Just 3 examples for quick test
            experiment_prefix="test-gemini15-kimik2",
            primary_model="gemini:gemini-1.5-flash",
            orchestration_model="groq:moonshotai/kimi-k2-instruct"
        )
        print("\n✅ Test evaluation completed successfully!")
    except Exception as e:
        print(f"\n❌ Test evaluation failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("Starting test evaluation...")
    asyncio.run(test_evaluation())