#!/usr/bin/env python3
"""Simple evaluation test with just a few examples."""

import asyncio
import json
from typing import Dict, Any
from langsmith import Client
from log_analyzer_agent.graph import graph
from log_analyzer_agent.state import State

async def run_agent_on_input(log_content: str) -> Dict[str, Any]:
    """Run the agent on a single input."""
    try:
        initial_state = State(
            log_content=log_content,
            messages=[],
            analysis_result=None,
            needs_user_input=False,
            user_response=""
        )
        
        result = await graph.ainvoke(initial_state)
        
        # Extract and parse the analysis result
        analysis_result = result.get("analysis_result", {})
        if "analysis" in analysis_result and isinstance(analysis_result["analysis"], str):
            try:
                return json.loads(analysis_result["analysis"])
            except:
                return analysis_result
        return analysis_result
        
    except Exception as e:
        print(f"Error running agent: {e}")
        return {
            "issues": [{
                "type": "execution_error",
                "description": f"Error analyzing log: {str(e)}",
                "severity": "critical"
            }],
            "explanations": [f"The agent encountered an error: {str(e)}"],
            "suggestions": ["Check the log format and try again"],
            "documentation_references": [],
            "diagnostic_commands": []
        }

async def test_evaluation():
    """Test evaluation with a few examples from the dataset."""
    client = Client()
    
    # Get a few examples from the dataset
    dataset_name = "log-analyzer-evaluation-v3"
    print(f"Loading examples from dataset: {dataset_name}")
    
    try:
        dataset = client.read_dataset(dataset_name=dataset_name)
        examples = list(client.list_examples(dataset_id=dataset.id, limit=3))
        
        print(f"\nTesting with {len(examples)} examples...")
        
        for i, example in enumerate(examples):
            print(f"\n--- Example {i+1} ---")
            log_content = example.inputs.get("log_content", "")
            print(f"Log preview: {log_content[:100]}...")
            
            # Run the agent
            print("Running agent...")
            result = await run_agent_on_input(log_content)
            
            # Compare with expected
            expected = example.outputs
            
            # Check issue detection
            actual_has_issues = len(result.get("issues", [])) > 0
            expected_has_issues = len(expected.get("issues", [])) > 0
            
            print(f"Expected issues: {expected_has_issues}")
            print(f"Found issues: {actual_has_issues}")
            print(f"Match: {'✓' if actual_has_issues == expected_has_issues else '✗'}")
            
            if result.get("issues"):
                print(f"Issues found: {len(result['issues'])}")
                for issue in result["issues"][:2]:  # Show first 2
                    print(f"  - {issue.get('description', 'No description')[:80]}...")
            
            # Add delay to avoid rate limits
            await asyncio.sleep(2)
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_evaluation())