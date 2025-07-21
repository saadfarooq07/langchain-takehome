#!/usr/bin/env python3
"""Management script for LangSmith prompts.

This script provides commands to push, pull, and manage prompts in LangSmith.
It can be used to:
- Push all local prompts to LangSmith
- Pull prompts from LangSmith
- List available prompts
- Test prompt versions
"""

import asyncio
import os
import sys
import argparse
import json
from pathlib import Path
from typing import Optional, Dict, Any, List

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from langsmith import Client
from langchain_core.prompts import ChatPromptTemplate

from src.log_analyzer_agent.prompts import (
    MAIN_PROMPT,
    ANALYSIS_CHECKER_PROMPT,
    FOLLOWUP_PROMPT,
    DOCUMENTATION_SEARCH_PROMPT,
)
from src.log_analyzer_agent.prompt_registry import PromptRegistry


# Define all prompts to manage (using base names, prefix will be added by registry)
PROMPTS_TO_PUSH = {
    "main": {
        "template": MAIN_PROMPT,
        "description": "Main prompt for log analysis - identifies issues, provides explanations, and suggests solutions",
        "tags": ["log-analyzer", "main", "analysis"],
    },
    "validation": {
        "template": ANALYSIS_CHECKER_PROMPT,
        "description": "Prompt for validating analysis completeness and accuracy",
        "tags": ["log-analyzer", "validation", "quality-check"],
    },
    "followup": {
        "template": FOLLOWUP_PROMPT,
        "description": "Prompt for requesting additional information from users",
        "tags": ["log-analyzer", "followup", "interactive"],
    },
    "doc-search": {
        "template": DOCUMENTATION_SEARCH_PROMPT,
        "description": "Prompt for formulating documentation search queries",
        "tags": ["log-analyzer", "documentation", "search"],
    },
}


async def push_prompts(
    client: Client,
    prompts: Optional[List[str]] = None,
    dry_run: bool = False,
) -> None:
    """Push prompts to LangSmith.
    
    Args:
        client: LangSmith client
        prompts: List of prompt names to push (None = push all)
        dry_run: If True, show what would be pushed without actually pushing
    """
    registry = PromptRegistry(client=client)
    
    # Filter prompts if specified
    prompts_to_push = PROMPTS_TO_PUSH
    if prompts:
        prompts_to_push = {k: v for k, v in PROMPTS_TO_PUSH.items() if k in prompts}
    
    print(f"{'[DRY RUN] ' if dry_run else ''}Pushing {len(prompts_to_push)} prompts to LangSmith...")
    
    for prompt_name, prompt_info in prompts_to_push.items():
        try:
            # Create prompt template
            prompt_template = ChatPromptTemplate.from_template(prompt_info["template"])
            
            if dry_run:
                print(f"  Would push: {prompt_name}")
                print(f"    Description: {prompt_info['description']}")
                print(f"    Tags: {', '.join(prompt_info['tags'])}")
            else:
                # Push to LangSmith
                version = await registry.push_prompt(
                    prompt_name=prompt_name,
                    prompt=prompt_template,
                    description=prompt_info["description"],
                    tags=prompt_info["tags"],
                )
                print(f"  ✓ Pushed: {prompt_name} (version: {version})")
                
        except Exception as e:
            print(f"  ✗ Failed to push {prompt_name}: {e}")


async def pull_prompts(
    client: Client,
    prompts: Optional[List[str]] = None,
    version: Optional[str] = None,
    save_local: bool = False,
) -> None:
    """Pull prompts from LangSmith.
    
    Args:
        client: LangSmith client
        prompts: List of prompt names to pull (None = pull all)
        version: Specific version to pull (default: latest)
        save_local: Save pulled prompts to local files
    """
    registry = PromptRegistry(client=client)
    
    # Determine which prompts to pull
    prompt_names = prompts or list(PROMPTS_TO_PUSH.keys())
    
    print(f"Pulling {len(prompt_names)} prompts from LangSmith...")
    
    pulled_prompts = {}
    for prompt_name in prompt_names:
        try:
            prompt = await registry.get_prompt(prompt_name, version=version)
            pulled_prompts[prompt_name] = prompt
            print(f"  ✓ Pulled: {prompt_name}")
            
            # Display prompt content if requested
            if save_local:
                # Extract template string
                template_str = ""
                if hasattr(prompt, 'messages') and prompt.messages:
                    template_str = prompt.messages[0].prompt.template
                elif hasattr(prompt, 'template'):
                    template_str = prompt.template
                
                # Save to file
                output_dir = Path("prompts_backup")
                output_dir.mkdir(exist_ok=True)
                output_file = output_dir / f"{prompt_name.replace('/', '_')}.txt"
                
                with open(output_file, 'w') as f:
                    f.write(template_str)
                print(f"    Saved to: {output_file}")
                
        except Exception as e:
            print(f"  ✗ Failed to pull {prompt_name}: {e}")
    
    return pulled_prompts


def list_prompts(registry: PromptRegistry) -> None:
    """List all registered prompts."""
    prompts = registry.list_prompts()
    
    print(f"Registered prompts ({len(prompts)}):")
    for name, config in prompts.items():
        print(f"\n  {name}:")
        print(f"    Version: {config.version}")
        print(f"    Cache TTL: {config.cache_ttl}s")
        print(f"    Has fallback: {'Yes' if config.fallback_template else 'No'}")


async def test_prompt(
    client: Client,
    prompt_name: str,
    test_input: Dict[str, Any],
    versions: List[str] = None,
) -> None:
    """Test different versions of a prompt.
    
    Args:
        client: LangSmith client
        prompt_name: Name of the prompt to test
        test_input: Input variables for the prompt
        versions: List of versions to test (default: ["latest"])
    """
    registry = PromptRegistry(client=client)
    versions = versions or ["latest"]
    
    print(f"Testing prompt: {prompt_name}")
    print(f"Input: {json.dumps(test_input, indent=2)}")
    print("-" * 50)
    
    for version in versions:
        try:
            prompt = await registry.get_prompt(prompt_name, version=version)
            
            # Format the prompt with test input
            formatted = prompt.format(**test_input)
            
            print(f"\nVersion: {version}")
            print(f"Output:\n{formatted}")
            print("-" * 50)
            
        except Exception as e:
            print(f"\nVersion: {version}")
            print(f"Error: {e}")
            print("-" * 50)


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Manage LangSmith prompts for the log analyzer agent"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Push command
    push_parser = subparsers.add_parser("push", help="Push prompts to LangSmith")
    push_parser.add_argument(
        "--prompts",
        nargs="+",
        help="Specific prompts to push (default: all)"
    )
    push_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be pushed without actually pushing"
    )
    
    # Pull command
    pull_parser = subparsers.add_parser("pull", help="Pull prompts from LangSmith")
    pull_parser.add_argument(
        "--prompts",
        nargs="+",
        help="Specific prompts to pull (default: all)"
    )
    pull_parser.add_argument(
        "--version",
        help="Specific version to pull (default: latest)"
    )
    pull_parser.add_argument(
        "--save-local",
        action="store_true",
        help="Save pulled prompts to local files"
    )
    
    # List command
    list_parser = subparsers.add_parser("list", help="List registered prompts")
    
    # Test command
    test_parser = subparsers.add_parser("test", help="Test a prompt with sample input")
    test_parser.add_argument(
        "prompt",
        help="Name of the prompt to test"
    )
    test_parser.add_argument(
        "--input",
        type=json.loads,
        default='{"log_content": "Test log content", "environment_context": "Test environment"}',
        help="JSON input for the prompt"
    )
    test_parser.add_argument(
        "--versions",
        nargs="+",
        default=["latest"],
        help="Versions to test"
    )
    
    args = parser.parse_args()
    
    # Check for API key
    if not os.getenv("LANGSMITH_API_KEY"):
        print("Error: LANGSMITH_API_KEY environment variable not set")
        print("Please set your LangSmith API key to use this script")
        sys.exit(1)
    
    # Create client
    client = Client()
    
    # Run the appropriate command
    if args.command == "push":
        asyncio.run(push_prompts(
            client=client,
            prompts=args.prompts,
            dry_run=args.dry_run
        ))
    
    elif args.command == "pull":
        asyncio.run(pull_prompts(
            client=client,
            prompts=args.prompts,
            version=args.version,
            save_local=args.save_local
        ))
    
    elif args.command == "list":
        registry = PromptRegistry(client=client)
        list_prompts(registry)
    
    elif args.command == "test":
        asyncio.run(test_prompt(
            client=client,
            prompt_name=args.prompt,
            test_input=args.input,
            versions=args.versions
        ))
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()