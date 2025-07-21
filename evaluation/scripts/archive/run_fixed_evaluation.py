#!/usr/bin/env python3
"""
Script to run the fixed evaluators from evaluate_agent_fixed.py
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import defaultdict

from langsmith import Client
from langsmith.evaluation import aevaluate
from langsmith.schemas import Example, Run

# Add parent directories to path
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

# Import the fixed evaluators
from evaluation.scripts.evaluate_agent_fixed import (
    evaluate_issue_type_accuracy,
    evaluate_severity_accuracy,
    evaluate_diagnostic_commands
)

# Import the agent
from log_analyzer_agent.graph import graph


async def run_agent_on_input(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """Run the agent on a single input."""
    try:
        print(f"\nProcessing log: {inputs.get('log_type', 'unknown')}")
        
        # Initialize state with just the log content
        initial_state = {
            "log_content": inputs.get("log_content", ""),
            "messages": []
        }
        
        # Run the agent
        config = {"configurable": {"thread_id": "eval-thread"}}
        final_state = await graph.ainvoke(initial_state, config)
        
        # Extract outputs from the analysis result
        analysis_result = final_state.get("analysis_result", {})
        
        # Convert analysis result format to expected output format
        issues = []
        if "issues" in analysis_result:
            issues = analysis_result["issues"]
        elif "identified_issues" in analysis_result:
            # Handle alternative format
            for issue in analysis_result["identified_issues"]:
                issues.append({
                    "type": issue.get("issue_type", "unknown"),
                    "description": issue.get("description", ""),
                    "severity": issue.get("severity", "info")
                })
        
        return {
            "issues": issues,
            "explanations": analysis_result.get("explanations", []),
            "suggestions": analysis_result.get("suggestions", []),
            "documentation_references": analysis_result.get("documentation_references", []),
            "diagnostic_commands": analysis_result.get("diagnostic_commands", [])
        }
    except Exception as e:
        print(f"Error running agent: {e}")
        return {
            "issues": [{"type": "execution_error", "description": str(e), "severity": "critical"}],
            "explanations": [f"Agent encountered an execution error: {e}"],
            "suggestions": [],
            "documentation_references": [],
            "diagnostic_commands": []
        }


async def run_evaluation(
    dataset_name: str = "log-analyzer-evaluation-v3",
    max_examples: Optional[int] = None,
    experiment_prefix: Optional[str] = None,
):
    """Run the evaluation using the fixed evaluators."""
    print(f"Starting evaluation with FIXED evaluators for dataset: {dataset_name}")
    if max_examples:
        print(f"Limiting to {max_examples} examples")
    
    # Use only the fixed evaluators
    evaluators = [
        evaluate_issue_type_accuracy,
        evaluate_severity_accuracy,
        evaluate_diagnostic_commands
    ]
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if not experiment_prefix:
        experiment_prefix = f"log-analyzer-fixed-eval-{timestamp}"
    
    print("\nRunning evaluation with fixed evaluators...")
    print("Fixed evaluators:")
    print("- evaluate_issue_type_accuracy (with flexible semantic matching)")
    print("- evaluate_severity_accuracy (with severity aliases)")
    print("- evaluate_diagnostic_commands (with balanced scoring)")
    
    results_generator = await aevaluate(
        run_agent_on_input,
        data=dataset_name,
        evaluators=evaluators,
        experiment_prefix=experiment_prefix,
        max_concurrency=2,  # Be gentle on APIs
        metadata={
            "agent_version": "1.1",
            "evaluation_script": "fixed_evaluators",
            "evaluator_type": "flexible"
        },
    )
    
    print("\n" + "="*60)
    print("EVALUATION RESULTS (FIXED EVALUATORS)")
    print("="*60)
    
    results_list = [res async for res in results_generator]
    total_examples = len(results_list)
    
    # Handle both dict and object-style results
    errors = 0
    for res in results_list:
        if isinstance(res, dict):
            if res.get("error"):
                errors += 1
        elif hasattr(res, "error") and res.error:
            errors += 1
    
    metrics = defaultdict(list)
    for result in results_list:
        # Skip if there's an error
        if isinstance(result, dict):
            if result.get("error"):
                continue
            feedback_list = result.get("feedback", [])
        else:
            if hasattr(result, "error") and result.error:
                continue
            feedback_list = getattr(result, "feedback", [])
        
        # Process feedback
        for feedback in feedback_list:
            if isinstance(feedback, dict):
                key = feedback.get("key")
                score = feedback.get("score")
            else:
                key = getattr(feedback, "key", None)
                score = getattr(feedback, "score", None)
            
            if key and score is not None:
                metrics[key].append(score)
    
    print(f"Total examples evaluated: {total_examples}")
    print(f"Errors encountered: {errors}")
    if total_examples > 0:
        print(f"Success rate: {((total_examples - errors) / total_examples * 100):.1f}%")
    
    print("\nFixed Evaluator Scores (Averages):")
    print("-" * 50)
    for metric_name, scores in sorted(metrics.items()):
        if scores:
            avg_score = sum(scores) / len(scores)
            print(f"{metric_name:.<35} {avg_score:.2%}")
        else:
            print(f"{metric_name:.<35} No data")
    
    # Save detailed results
    results_file = Path(f"fixed_evaluation_results_{timestamp}.json")
    detailed_results = {
        "dataset": dataset_name,
        "experiment_prefix": experiment_prefix,
        "timestamp": timestamp,
        "total_examples": total_examples,
        "errors": errors,
        "evaluator_type": "fixed",
        "metrics": {
            name: {
                "average": sum(scores)/len(scores) if scores else 0,
                "count": len(scores),
                "scores": scores
            }
            for name, scores in metrics.items()
        }
    }
    
    with open(results_file, 'w') as f:
        json.dump(detailed_results, f, indent=2)
    
    print(f"\nDetailed results saved to: {results_file}")
    print(f"View full results in LangSmith: https://smith.langchain.com/")
    print("\nNote: These fixed evaluators use more flexible matching:")
    print("- Issue types: Semantic grouping instead of exact matching")
    print("- Severities: Aliases and distribution-based scoring")
    print("- Commands: Rewards relevant commands without exact matches")


if __name__ == "__main__":
    import sys
    print(f"Python path: {sys.path}")
    print(f"Running from: {Path.cwd()}")
    
    # You can customize these parameters
    asyncio.run(run_evaluation(
        dataset_name="log-analyzer-evaluation-v3",
        max_examples=5,  # Limit to 5 examples for testing
        experiment_prefix=None  # Will auto-generate if not provided
    ))