#!/usr/bin/env python3
"""Script to list and manage prompts for the log analyzer agent."""

import os
import sys
import asyncio
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from log_analyzer_agent.prompt_registry import get_prompt_registry, PromptRegistry
from log_analyzer_agent.configuration import Configuration
from log_analyzer_agent.prompts import (
    main_prompt_template,
    analysis_checker_template,
    followup_template,
    documentation_search_template,
)

async def list_available_prompts():
    """List all available prompts in the registry."""
    print("🔍 Log Analyzer Agent - Prompt Management")
    print("=" * 50)
    
    # Check environment
    langsmith_key = os.getenv("LANGSMITH_API_KEY")
    prompt_prefix = os.getenv("LANGSMITH_PROMPT_PREFIX", "log-analyzer")
    
    print(f"LangSmith API Key: {'✅ Set' if langsmith_key else '❌ Not set'}")
    print(f"Prompt Prefix: {prompt_prefix}")
    print()
    
    # Initialize registry
    registry = get_prompt_registry()
    
    print("📋 Available Prompts:")
    print("-" * 30)
    
    prompts = registry.list_prompts()
    for name, config in prompts.items():
        formatted_name = registry._format_prompt_name(name)
        print(f"• {name}")
        print(f"  LangSmith Name: {formatted_name}")
        print(f"  Version: {config.version}")
        print(f"  Has Fallback: {'✅' if config.fallback_template else '❌'}")
        print()
    
    # Test prompt fetching
    print("🧪 Testing Prompt Fetching:")
    print("-" * 30)
    
    for name in prompts.keys():
        try:
            prompt = await registry.get_prompt(name)
            print(f"✅ {name}: Successfully loaded")
        except Exception as e:
            print(f"❌ {name}: Failed - {e}")
    
    print()

async def push_local_prompts():
    """Push local prompts to LangSmith."""
    if not os.getenv("LANGSMITH_API_KEY"):
        print("❌ LANGSMITH_API_KEY not set. Cannot push prompts.")
        return
    
    print("📤 Pushing Local Prompts to LangSmith:")
    print("-" * 40)
    
    registry = PromptRegistry(enable_langsmith=True)
    
    prompts_to_push = {
        "main": main_prompt_template,
        "validation": analysis_checker_template,
        "followup": followup_template,
        "doc-search": documentation_search_template,
    }
    
    for name, template in prompts_to_push.items():
        try:
            version = await registry.push_prompt(
                name,
                template,
                description=f"Log analyzer {name} prompt",
                tags=["log-analyzer", "v1.0"]
            )
            print(f"✅ {name}: Pushed successfully (version: {version})")
        except Exception as e:
            print(f"❌ {name}: Failed to push - {e}")
    
    print()

async def test_prompt_resolution():
    """Test prompt resolution with different configurations."""
    print("🔧 Testing Prompt Resolution:")
    print("-" * 35)
    
    config = Configuration()
    
    # Test different node mappings
    nodes = ["analyze_logs", "validate_analysis", "handle_user_input", "search_documentation"]
    
    for node in nodes:
        prompt_name = config.get_prompt_name_for_node(node)
        prompt_version = config.get_prompt_version(prompt_name)
        print(f"• {node} → {prompt_name}:{prompt_version}")
    
    print()

async def main():
    """Main function."""
    print("Log Analyzer Agent - Prompt Management Tool")
    print("=" * 50)
    print()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "push":
            await push_local_prompts()
        elif command == "test":
            await test_prompt_resolution()
        else:
            print(f"Unknown command: {command}")
            print("Available commands: push, test")
            return
    
    await list_available_prompts()
    await test_prompt_resolution()

if __name__ == "__main__":
    asyncio.run(main())