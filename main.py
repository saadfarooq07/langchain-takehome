#!/usr/bin/env python3
"""Main entry point for the Log Analyzer Agent with CLI support."""

import os
import sys
import argparse
import asyncio
from typing import Optional, Set
from dotenv import load_dotenv
import logging
from pathlib import Path

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


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
        print("   Copy .env.example to .env and add your keys")
        sys.exit(1)
    
    logger.info("✅ All API keys validated")


async def run_cli_mode(args):
    """Run the log analyzer in CLI mode."""
    # Enable improved mode if requested
    if args.use_improved or args.mode == "improved":
        os.environ["USE_IMPROVED_LOG_ANALYZER"] = "true"
        logger.info("🚀 Using improved log analyzer implementation")
    
    # Determine features to enable based on mode
    features = set()
    if args.mode == "interactive":
        features.add("interactive")
    elif args.mode == "memory":
        features.add("memory")
    elif args.mode == "improved":
        features = {"streaming", "specialized", "caching"}
    elif args.mode == "minimal":
        features = set()  # No extra features
    
    # Read log content
    if args.log_file:
        log_path = Path(args.log_file)
        if not log_path.exists():
            print(f"❌ Log file not found: {args.log_file}")
            sys.exit(1)
        
        logger.info(f"📄 Reading log file: {args.log_file}")
        log_content = log_path.read_text()
    else:
        # Interactive mode - prompt for log content
        print("\n📝 Please paste your log content (press Ctrl+D or Ctrl+Z on Windows when done):")
        print("   Or provide a log file with --log-file option")
        print("   Example: python main.py --use-improved --log-file /path/to/log.txt\n")
        
        try:
            log_content = sys.stdin.read()
        except KeyboardInterrupt:
            print("\n\n❌ Input cancelled")
            sys.exit(0)
    
    if not log_content.strip():
        print("❌ No log content provided")
        sys.exit(1)
    
    # Check if we should use improved implementation
    if os.getenv("USE_IMPROVED_LOG_ANALYZER", "").lower() == "true":
        from src.log_analyzer_agent.core.improved_graph import run_improved_analysis
        
        logger.info(f"🔧 Running improved analysis with features: {features}")
        result = await run_improved_analysis(
            log_content=log_content,
            features=features
        )
    else:
        # Use regular implementation
        from src.log_analyzer_agent.graph import graph
        from langchain_core.messages import HumanMessage
        
        logger.info(f"🔧 Running standard analysis with mode: {args.mode}")
        
        # Create initial state
        initial_state = {
            "messages": [HumanMessage(content=f"Analyze this log:\n{log_content}")],
            "log_content": log_content,
            "log_metadata": {},
            "enabled_features": list(features)
        }
        
        # Run the graph
        result = await graph.ainvoke(initial_state)
    
    # Display results
    print("\n" + "="*80)
    print("📊 ANALYSIS RESULTS")
    print("="*80 + "\n")
    
    if isinstance(result, dict) and "analysis_result" in result:
        analysis = result["analysis_result"]
        
        # Summary
        print(f"📋 Summary: {analysis.get('summary', 'No summary available')}\n")
        
        # Issues found
        issues = analysis.get("issues", [])
        if issues:
            print(f"🔍 Found {len(issues)} issues:\n")
            for i, issue in enumerate(issues[:10], 1):  # Show first 10
                print(f"  {i}. [{issue.get('severity', 'unknown').upper()}] {issue.get('type', 'Unknown')}")
                print(f"     {issue.get('message', '')[:100]}...")
                if i == 10 and len(issues) > 10:
                    print(f"\n  ... and {len(issues) - 10} more issues")
        
        # Recommendations
        recommendations = analysis.get("recommendations", [])
        if recommendations:
            print(f"\n💡 Recommendations ({len(recommendations)}):\n")
            for i, rec in enumerate(recommendations[:5], 1):  # Show first 5
                print(f"  {i}. [{rec.get('priority', 'medium').upper()}] {rec.get('category', 'General')}")
                print(f"     {rec.get('action', 'No action specified')}")
                if "command" in rec:
                    print(f"     Command: {rec['command']}")
                elif "commands" in rec:
                    print(f"     Commands:")
                    for cmd in rec['commands'][:3]:
                        print(f"       - {cmd}")
        
        # Specialized insights (if using improved mode)
        if "specialized_insights" in analysis:
            insights = analysis["specialized_insights"]
            print("\n🎯 Specialized Insights:")
            
            # Different insights based on log type
            if analysis.get("log_type") == "hdfs":
                cluster_health = insights.get("cluster_health", {})
                print(f"  - Cluster Health: {cluster_health.get('status', 'unknown').upper()}")
                print(f"    {cluster_health.get('message', '')}")
                
            elif analysis.get("log_type") == "security":
                threat_assessment = insights.get("threat_assessment", {})
                print(f"  - Threat Level: {threat_assessment.get('level', 'unknown').upper()}")
                print(f"    {threat_assessment.get('message', '')}")
                
            elif analysis.get("log_type") == "application":
                service_health = insights.get("service_health", {})
                print(f"  - Service Health: {service_health.get('status', 'unknown').upper()}")
                print(f"    Availability: {service_health.get('availability', 0):.1f}%")
    else:
        print("❌ No analysis results available")
    
    print("\n" + "="*80)


async def run_benchmark_mode():
    """Run benchmarks comparing different implementations."""
    print("🏃 Running benchmark mode...")
    
    # Import benchmark module
    try:
        from src.log_analyzer_agent.benchmarks import run_benchmarks
        await run_benchmarks()
    except ImportError:
        print("❌ Benchmark module not found")
        print("   Benchmarks are not yet implemented")


def main():
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(
        description="Log Analyzer Agent - Analyze system logs and provide insights"
    )
    
    # Mode selection
    parser.add_argument(
        "--mode",
        choices=["minimal", "interactive", "memory", "improved", "benchmark"],
        default="minimal",
        help="Analysis mode (default: minimal)"
    )
    
    # File input
    parser.add_argument(
        "--log-file",
        type=str,
        help="Path to log file to analyze"
    )
    
    # Improved mode flag
    parser.add_argument(
        "--use-improved",
        action="store_true",
        help="Use improved implementation with all enhancements"
    )
    
    # API server mode
    parser.add_argument(
        "--api",
        action="store_true",
        help="Run as API server instead of CLI"
    )
    
    # Development mode
    parser.add_argument(
        "--dev",
        action="store_true",
        help="Run API server in development mode with auto-reload"
    )
    
    args = parser.parse_args()
    
    # Validate API keys
    validate_api_keys()
    
    # Run appropriate mode
    if args.api:
        # Import and run API server
        from main_api import run_server, run_dev_server
        
        if args.dev:
            run_dev_server()
        else:
            run_server()
    elif args.mode == "benchmark":
        asyncio.run(run_benchmark_mode())
    else:
        # Run CLI mode
        asyncio.run(run_cli_mode(args))


if __name__ == "__main__":
    main()