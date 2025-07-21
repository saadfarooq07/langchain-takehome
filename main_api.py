"""Simple main entry point for the Log Analyzer API."""

import os
import sys
import uvicorn
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def validate_api_keys():
    """Validate required API keys are present."""
    required_keys = {
        "GEMINI_API_KEY": "Google AI API key for Gemini model",
        "GROQ_API_KEY": "Groq API key for Kimi K2 model",
        "TAVILY_API_KEY": "Tavily API key for documentation search"
    }
    
    missing_keys = []
    for key, description in required_keys.items():
        if not os.getenv(key):
            missing_keys.append(f"{key} - {description}")
    
    if missing_keys:
        print("❌ Missing required API keys:")
        for key in missing_keys:
            print(f"   • {key}")
        print("\n📝 Please add these to your .env file")
        sys.exit(1)
    
    print("✅ All API keys validated")


def run_server():
    """Run the production server."""
    validate_api_keys()
    
    # Import here to ensure environment is set up first
    from src.log_analyzer_agent.api.main_v2 import app
    
    print("🚀 Starting Log Analyzer API server...")
    print("📍 API: http://localhost:8000")
    print("📚 Docs: http://localhost:8000/docs")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )


def run_dev_server():
    """Run the development server with auto-reload."""
    validate_api_keys()
    
    # Import here to ensure environment is set up first
    from src.log_analyzer_agent.api.main_v2 import app
    
    print("🚀 Starting Log Analyzer API in development mode...")
    print("📍 API: http://localhost:8000")
    print("📚 Docs: http://localhost:8000/docs")
    print("🔄 Auto-reload enabled")
    
    uvicorn.run(
        "src.log_analyzer_agent.api.main_v2:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="debug"
    )


if __name__ == "__main__":
    # Simple: just run the dev server by default
    run_dev_server()