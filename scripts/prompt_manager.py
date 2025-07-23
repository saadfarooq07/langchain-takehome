#!/usr/bin/env python3
"""Comprehensive prompt management script for the log analyzer agent."""

import os
import sys
import asyncio
import argparse
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

async def list_prompts():
    """List all available prompts."""
    print("📋 Available Prompts")
    print("=" * 30)
    
    registry = get_prompt_registry()
    prompts = registry.list_prompts()
    
    for name, config in prompts.items():
        formatted_name = registry._format_prompt_name(name)
        print(f"\n• {name}")
        print(f"  LangSmith Name: {formatted_name}")
        print(f"  Version: {config.version}")
        print(f"  Has Fallback: {'✅' if config.fallback_template else '❌'}")
        
        # Test loading
        try:
            prompt = await registry.get_prompt(name)
            print(f"  Status: ✅ Loads successfully")
            # Show first 100 chars of template
            template_preview = str(prompt)[:100].replace('\n', ' ')
            print(f"  Preview: {template_preview}...")
        except Exception as e:
            print(f"  Status: ❌ Failed to load - {e}")

async def test_configuration():
    """Test current configuration."""
    print("\n🔧 Configuration Test")
    print("=" * 25)
    
    config = Configuration()
    
    print(f"LangSmith Enabled: {config.prompt_config.use_langsmith}")
    print(f"Cache Enabled: {config.prompt_config.cache_prompts}")
    print(f"Cache TTL: {config.prompt_config.cache_ttl} seconds")
    print(f"LangSmith API Key: {'✅ Set' if config.prompt_config.langsmith_api_key else '❌ Not set'}")
    
    print("\nNode → Prompt Mapping:")
    nodes = ["analyze_logs", "validate_analysis", "handle_user_input", "search_documentation"]
    for node in nodes:
        prompt_name = config.get_prompt_name_for_node(node)
        prompt_version = config.get_prompt_version(prompt_name)
        print(f"  {node} → {prompt_name}:{prompt_version}")

async def push_prompts():
    """Push local prompts to LangSmith."""
    if not os.getenv("LANGSMITH_API_KEY"):
        print("❌ LANGSMITH_API_KEY not set. Cannot push prompts.")
        print("Set your LangSmith API key in .env file:")
        print("LANGSMITH_API_KEY=your_key_here")
        return
    
    print("📤 Pushing Prompts to LangSmith")
    print("=" * 35)
    
    registry = PromptRegistry(enable_langsmith=True)
    
    prompts_to_push = {
        "main": main_prompt_template,
        "validation": analysis_checker_template,
        "followup": followup_template,
        "doc-search": documentation_search_template,
    }
    
    for name, template in prompts_to_push.items():
        try:
            print(f"\nPushing {name}...")
            version = await registry.push_prompt(
                name,
                template,
                description=f"Log analyzer {name} prompt - auto-generated",
                tags=["log-analyzer", "auto-generated", "v1.0"]
            )
            print(f"✅ {name}: Successfully pushed (version: {version})")
        except Exception as e:
            print(f"❌ {name}: Failed to push - {e}")

async def clear_cache():
    """Clear prompt cache."""
    print("🗑️  Clearing Prompt Cache")
    print("=" * 25)
    
    registry = get_prompt_registry()
    
    # Clear memory cache
    registry.memory_cache.clear()
    print("✅ Memory cache cleared")
    
    # Clear disk cache
    if registry.cache_dir.exists():
        cache_files = list(registry.cache_dir.glob("*.json"))
        for cache_file in cache_files:
            try:
                cache_file.unlink()
                print(f"✅ Removed {cache_file.name}")
            except Exception as e:
                print(f"❌ Failed to remove {cache_file.name}: {e}")
    
    print(f"Cache directory: {registry.cache_dir}")

async def validate_setup():
    """Validate the entire prompt setup."""
    print("🔍 Validating Prompt Setup")
    print("=" * 30)
    
    # Check environment
    langsmith_key = os.getenv("LANGSMITH_API_KEY")
    use_langsmith = os.getenv("USE_LANGSMITH_PROMPTS", "false").lower() == "true"
    
    print(f"LangSmith API Key: {'✅ Set' if langsmith_key else '❌ Not set'}")
    print(f"Use LangSmith: {'✅ Enabled' if use_langsmith else '❌ Disabled (using local fallbacks)'}")
    
    if use_langsmith and not langsmith_key:
        print("⚠️  Warning: LangSmith enabled but API key not set!")
    
    # Test all prompts
    print("\nTesting all prompts:")
    registry = get_prompt_registry()
    prompts = registry.list_prompts()
    
    all_working = True
    for name in prompts.keys():
        try:
            await registry.get_prompt(name)
            print(f"✅ {name}: OK")
        except Exception as e:
            print(f"❌ {name}: FAILED - {e}")
            all_working = False
    
    if all_working:
        print("\n🎉 All prompts are working correctly!")
    else:
        print("\n⚠️  Some prompts have issues. Check the errors above.")
    
    return all_working

def main():
    """Main CLI interface."""
    parser = argparse.ArgumentParser(description="Manage prompts for the log analyzer agent")
    parser.add_argument("command", choices=["list", "test", "push", "clear", "validate"], 
                       help="Command to execute")
    
    args = parser.parse_args()
    
    print("🚀 Log Analyzer Agent - Prompt Manager")
    print("=" * 45)
    
    if args.command == "list":
        asyncio.run(list_prompts())
    elif args.command == "test":
        asyncio.run(test_configuration())
    elif args.command == "push":
        asyncio.run(push_prompts())
    elif args.command == "clear":
        asyncio.run(clear_cache())
    elif args.command == "validate":
        asyncio.run(validate_setup())

if __name__ == "__main__":
    main()