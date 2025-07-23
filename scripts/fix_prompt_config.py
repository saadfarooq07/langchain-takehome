#!/usr/bin/env python3
"""Script to fix prompt configuration issues."""

import os
import sys
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def fix_environment_config():
    """Fix environment configuration for prompts."""
    env_file = Path(__file__).parent.parent / ".env"
    
    print("🔧 Fixing Prompt Configuration")
    print("=" * 40)
    
    # Read existing .env file
    env_content = ""
    if env_file.exists():
        with open(env_file, 'r') as f:
            env_content = f.read()
    
    # Configuration fixes
    fixes = {
        "# Disable LangSmith prompt fetching by default": "",
        "USE_LANGSMITH_PROMPTS": "false",
        "LANGSMITH_PROMPT_PREFIX": "log-analyzer",
        "# Use local fallback prompts": "",
        "PROMPT_CACHE_ENABLED": "true",
        "PROMPT_CACHE_TTL": "3600",
    }
    
    lines = env_content.split('\n') if env_content else []
    
    # Update or add configuration
    for key, value in fixes.items():
        if key.startswith("#"):
            # Add comment
            if key not in env_content:
                lines.append(key)
            continue
            
        # Find existing line
        found = False
        for i, line in enumerate(lines):
            if line.startswith(f"{key}="):
                lines[i] = f"{key}={value}"
                found = True
                break
        
        if not found:
            lines.append(f"{key}={value}")
    
    # Write back to .env file
    with open(env_file, 'w') as f:
        f.write('\n'.join(lines))
    
    print(f"✅ Updated {env_file}")
    print("\nConfiguration changes:")
    for key, value in fixes.items():
        if not key.startswith("#"):
            print(f"  {key}={value}")
    
    print("\n💡 Restart the LangGraph server to apply changes:")
    print("   Ctrl+C to stop, then run: langgraph dev")

if __name__ == "__main__":
    fix_environment_config()