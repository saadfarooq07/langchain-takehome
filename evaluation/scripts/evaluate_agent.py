#!/usr/bin/env python3
"""
Comprehensive evaluation script for the log analyzer agent using LangSmith.
This script provides nuanced, robust, and accurate evaluation of the agent's
performance by matching issues by type and calculating detailed metrics.
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import defaultdict, Counter

from langsmith import Client
from langsmith.evaluation import aevaluate, run_evaluator
from langsmith.schemas import Example, Run

from log_analyzer_agent.graph import graph
from log_analyzer_agent.state import State


# ==================== Core Evaluators ====================

@run_evaluator
def evaluate_issue_type_accuracy(run: Run, example: Example) -> Dict[str, Any]:
    """
    Evaluate if the agent identifies the correct types of issues.
    Calculates F1 score based on the counts of each issue type.
    """
    try:
        actual = run.outputs or {}
        expected = example.outputs or {}
        
        actual_issues = actual.get("issues", [])
        expected_issues = expected.get("issues", [])
        
        if not expected_issues:
            score = 1.0 if not actual_issues else 0.0
            comment = "No issues expected. Score is 1.0 if none found, 0.0 otherwise."
            return {"key": "issue_type_accuracy", "score": score, "comment": comment}
        actual_types = Counter(issue.get("type") for issue in actual_issues)
        expected_types = Counter(issue.get("type") for issue in expected_issues)
        
        if not actual_issues:
            return {
            "key": "issue_type_accuracy",
                "score": 0.0,
                "comment": f"No issues found, but expected {sum(expected_types.values())} issues of types: {list(expected_types.keys())}"
        }

        intersection_count = sum((actual_types & expected_types).values())

        precision = intersection_count / sum(actual_types.values()) if sum(actual_types.values()) > 0 else 0
        recall = intersection_count / sum(expected_types.values()) if sum(expected_types.values()) > 0 else 0

        score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

        comment = (f"F1 score based on issue types. "
                   f"Precision: {precision:.2%}, Recall: {recall:.2%}. "
                   f"Expected: {dict(expected_types)}, Found: {dict(actual_types)}")
        return {
            "key": "issue_type_accuracy",
            "score": score,
            "comment": comment
        }
    except Exception as e:
        return {
            "key": "issue_type_accuracy",
            "score": 0.0,
            "comment": f"Error in evaluation: {str(e)}"
        }


@run_evaluator
def evaluate_severity_accuracy(run: Run, example: Example) -> Dict[str, Any]:
    """
    Evaluate severity assessment accuracy for issues matched by type.
    Compares the highest severity for each common issue type.
    """
    try:
        actual = run.outputs or {}
        expected = example.outputs or {}
        
        actual_issues = actual.get("issues", [])
        expected_issues = expected.get("issues", [])
        
        if not expected_issues:
            score = 1.0 if not actual_issues else 0.0
            comment = "No issues expected. Score is 1.0 if none found, 0.0 otherwise."
            return {"key": "severity_accuracy", "score": score, "comment": comment}

        severity_order = ["critical", "error", "warning", "info"]

        def get_severity_score(expected_sev, actual_sev):
            if expected_sev not in severity_order or actual_sev not in severity_order:
                return 0.0
            expected_idx = severity_order.index(expected_sev)
            actual_idx = severity_order.index(actual_sev)
            distance = abs(expected_idx - actual_idx)
            # Max distance of 3 (critical vs. info) results in a score near 0
            return max(0.0, 1.0 - (distance * 0.34))

        actual_by_type = defaultdict(list)
        for issue in actual_issues:
            actual_by_type[issue.get('type')].append(issue.get('severity', 'info'))

        expected_by_type = defaultdict(list)
        for issue in expected_issues:
            expected_by_type[issue.get('type')].append(issue.get('severity', 'info'))

        total_score = 0
        matches = 0

        # Iterate over expected issue types to find matches
        for issue_type, expected_sevs in expected_by_type.items():
            actual_sevs = actual_by_type.get(issue_type)
            if not actual_sevs:
                continue
            matches += 1
            # For each matched type, compare the highest severity found
            highest_expected_sev = min(expected_sevs, key=lambda s: severity_order.index(s) if s in severity_order else 99)
            highest_actual_sev = min(actual_sevs, key=lambda s: severity_order.index(s) if s in severity_order else 99)

            total_score += get_severity_score(highest_expected_sev, highest_actual_sev)

        if matches == 0:
            score = 0.0
            comment = "No common issue types found to compare severity."
        else:
            score = total_score / matches
            comment = f"Average severity score for {matches} matched issue types: {score:.2%}"
        
        return {
            "key": "severity_accuracy",
            "score": score,
            "comment": comment
        }
    except Exception as e:
        return {
            "key": "severity_accuracy",
            "score": 0.0,
            "comment": f"Error in evaluation: {str(e)}"
        }


@run_evaluator
def evaluate_explanation_quality(run: Run, example: Example) -> Dict[str, Any]:
    """Evaluate if explanations are provided and relevant to issues."""
    try:
        actual = run.outputs or {}
        actual_issues = actual.get("issues", [])
        actual_explanations = actual.get("explanations", [])
        
        if not actual_issues:
            score = 1.0 if not actual_explanations else 0.5
            comment = "No issues found" if score == 1.0 else "Explanations provided without issues"
        else:
            if len(actual_explanations) >= len(actual_issues):
                score = 1.0
                comment = f"Adequate explanations provided ({len(actual_explanations)} for {len(actual_issues)} issues)"
            elif actual_explanations:
                score = len(actual_explanations) / len(actual_issues)
                comment = f"Partial explanations ({len(actual_explanations)} for {len(actual_issues)} issues)"
            else:
                score = 0.0
                comment = "No explanations provided for identified issues"

        if actual_explanations and any(actual_explanations):
            avg_length = sum(len(exp) for exp in actual_explanations) / len(actual_explanations)
            if avg_length < 20:
                score *= 0.5
                comment += " - Explanations too brief"

        return {"key": "explanation_quality", "score": score, "comment": comment}
    except Exception as e:
        return {"key": "explanation_quality", "score": 0.0, "comment": f"Error in evaluation: {str(e)}"}


@run_evaluator
def evaluate_suggestion_quality(run: Run, example: Example) -> Dict[str, Any]:
    """Evaluate the quality and relevance of suggestions."""
    try:
        actual = run.outputs or {}
        actual_issues = actual.get("issues", [])
        actual_suggestions = actual.get("suggestions", [])
        
        if not actual_issues:
            score = 1.0 if not actual_suggestions else 0.5
            comment = "No issues, no suggestions needed" if score == 1.0 else "Suggestions without issues"
        else:
            if actual_suggestions and any(actual_suggestions):
                ratio = len(actual_suggestions) / len(actual_issues)
                score = min(1.0, ratio)
                comment = f"{len(actual_suggestions)} suggestions for {len(actual_issues)} issues"
                
                avg_length = sum(len(s) for s in actual_suggestions) / len(actual_suggestions)
                if avg_length < 10:
                    score *= 0.5
                    comment += " - Suggestions too brief"
            else:
                score = 0.0
                comment = "No suggestions provided for identified issues"

        return {"key": "suggestion_quality", "score": score, "comment": comment}
    except Exception as e:
        return {"key": "suggestion_quality", "score": 0.0, "comment": f"Error in evaluation: {str(e)}"}


@run_evaluator
def evaluate_documentation_relevance(run: Run, example: Example) -> Dict[str, Any]:
    """Evaluate if documentation references are provided when appropriate."""
    try:
        actual = run.outputs or {}
        actual_issues = actual.get("issues", [])
        actual_docs = actual.get("documentation_references", [])
        
        has_critical_issues = any(
            issue.get("severity") in ["critical", "error"] 
            for issue in actual_issues
        )
        
        if not actual_issues:
            score = 1.0
            comment = "No issues, documentation not required"
        elif has_critical_issues:
            if actual_docs:
                score = 1.0
                comment = f"Documentation provided for critical issues ({len(actual_docs)} references)"
            else:
                score = 0.0
                comment = "No documentation for critical issues"
        else:
            if actual_docs:
                score = 1.0
                comment = f"Documentation provided ({len(actual_docs)} references)"
            else:
                score = 0.7
                comment = "No documentation, but issues are non-critical"

        return {"key": "documentation_relevance", "score": score, "comment": comment}
    except Exception as e:
        return {"key": "documentation_relevance", "score": 0.0, "comment": f"Error in evaluation: {str(e)}"}


@run_evaluator
def evaluate_diagnostic_commands(run: Run, example: Example) -> Dict[str, Any]:
    """Evaluate if diagnostic commands are appropriate for the issues."""
    try:
        actual = run.outputs or {}
        actual_issues = actual.get("issues", [])
        actual_commands = actual.get("diagnostic_commands", [])
        
        if not actual_issues:
            score = 1.0
            comment = "No issues, diagnostic commands not required"
        else:
            if actual_commands:
                valid_commands = all(
                    isinstance(cmd, dict) and "command" in cmd and "description" in cmd
                    for cmd in actual_commands
                )
                
                if valid_commands:
                    ratio = len(actual_commands) / len(actual_issues)
                    score = min(1.0, ratio)
                    comment = f"{len(actual_commands)} commands for {len(actual_issues)} issues"
                else:
                    score = 0.5
                    comment = "Commands provided but improperly formatted"
            else:
                score = 0.0
                comment = "No diagnostic commands for identified issues"

        return {"key": "diagnostic_commands", "score": score, "comment": comment}
    except Exception as e:
        return {"key": "diagnostic_commands", "score": 0.0, "comment": f"Error in evaluation: {str(e)}"}


@run_evaluator
def evaluate_response_completeness(run: Run, example: Example) -> Dict[str, Any]:
    """Evaluate if the response has all required components."""
    try:
        actual = run.outputs or {}
        required_fields = ["issues", "explanations", "suggestions", "documentation_references", "diagnostic_commands"]
        present_fields = [field for field in required_fields if field in actual]
        score = len(present_fields) / len(required_fields)
        
        if score == 1.0:
            comment = "All required fields present"
        else:
            missing = [f for f in required_fields if f not in present_fields]
            comment = f"Missing fields: {', '.join(missing)}"

        return {"key": "response_completeness", "score": score, "comment": comment}
    except Exception as e:
        return {"key": "response_completeness", "score": 0.0, "comment": f"Error in evaluation: {str(e)}"}


# ==================== Summary Evaluators ====================

def precision_summary_evaluator(runs: List[Run], examples: List[Example]) -> Dict[str, Any]:
    """Calculate precision of issue detection across all examples based on issue types."""
    total_tp, total_fp = 0, 0
    for run, example in zip(runs, examples):
        if run.error: continue
        actual = run.outputs or {}
        expected = example.outputs or {}
        
        # Ensure actual and expected are dictionaries
        if isinstance(actual, str):
            try:
                actual = json.loads(actual)
            except:
                print(f"Warning: Could not parse actual output as JSON: {actual[:100]}...")
                continue
        if isinstance(expected, str):
            try:
                expected = json.loads(expected)
            except:
                print(f"Warning: Could not parse expected output as JSON: {expected[:100]}...")
                continue
        
        # Ensure we have dictionaries with 'issues' field
        if not isinstance(actual, dict) or "issues" not in actual:
            print(f"Warning: Actual output missing 'issues' field")
            continue
        if not isinstance(expected, dict) or "issues" not in expected:
            print(f"Warning: Expected output missing 'issues' field")
            continue
            
        actual_types = Counter(issue.get("type") for issue in actual.get("issues", []) if isinstance(issue, dict))
        expected_types = Counter(issue.get("type") for issue in expected.get("issues", []) if isinstance(issue, dict))
        intersection = actual_types & expected_types
        total_tp += sum(intersection.values())
        total_fp += sum((actual_types - expected_types).values())

    precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0
    return {"key": "precision", "score": precision, "comment": f"Precision: {precision:.2%} (TP: {total_tp}, FP: {total_fp})"}


def recall_summary_evaluator(runs: List[Run], examples: List[Example]) -> Dict[str, Any]:
    """Calculate recall of issue detection across all examples based on issue types."""
    total_tp, total_fn = 0, 0
    for run, example in zip(runs, examples):
        if run.error: continue
        actual = run.outputs or {}
        expected = example.outputs or {}
        
        # Ensure actual and expected are dictionaries
        if isinstance(actual, str):
            try:
                actual = json.loads(actual)
            except:
                print(f"Warning: Could not parse actual output as JSON: {actual[:100]}...")
                continue
        if isinstance(expected, str):
            try:
                expected = json.loads(expected)
            except:
                print(f"Warning: Could not parse expected output as JSON: {expected[:100]}...")
                continue
        
        # Ensure we have dictionaries with 'issues' field
        if not isinstance(actual, dict) or "issues" not in actual:
            print(f"Warning: Actual output missing 'issues' field")
            continue
        if not isinstance(expected, dict) or "issues" not in expected:
            print(f"Warning: Expected output missing 'issues' field")
            continue
            
        actual_types = Counter(issue.get("type") for issue in actual.get("issues", []) if isinstance(issue, dict))
        expected_types = Counter(issue.get("type") for issue in expected.get("issues", []) if isinstance(issue, dict))
        intersection = actual_types & expected_types
        total_tp += sum(intersection.values())
        total_fn += sum((expected_types - actual_types).values())

    recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0
    return {"key": "recall", "score": recall, "comment": f"Recall: {recall:.2%} (TP: {total_tp}, FN: {total_fn})"}


def f1_summary_evaluator(runs: List[Run], examples: List[Example]) -> Dict[str, Any]:
    """Calculate F1 score combining precision and recall."""
    precision_result = precision_summary_evaluator(runs, examples)
    recall_result = recall_summary_evaluator(runs, examples)
    precision = precision_result["score"]
    recall = recall_result["score"]
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    return {"key": "f1_score", "score": f1, "comment": f"F1 Score: {f1:.2%} (P: {precision:.2%}, R: {recall:.2%})"}


# ==================== Agent Runner ====================

async def run_agent_on_input(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """Run the log analyzer agent on a single input, with robust error handling."""
    try:
        await asyncio.sleep(1)  # Avoid rate limits
        initial_state = State(log_content=inputs["log_content"], messages=[], analysis_result=None, needs_user_input=False, user_response="")
        result = await graph.ainvoke(initial_state)

        analysis_result = result.get("analysis_result", {})
        
        # Handle different possible formats of analysis_result
        if analysis_result is None:
            # No analysis result found
            return {
                "issues": [{"type": "no_analysis", "description": "No analysis result found", "severity": "critical"}],
                "explanations": ["Agent did not produce an analysis."], "suggestions": [], "documentation_references": [], "diagnostic_commands": []
            }
        
        # If analysis_result is already a dict with the expected structure, return it
        if isinstance(analysis_result, dict) and "issues" in analysis_result:
            return analysis_result
        
        # If analysis_result has an "analysis" field that's a string, try to parse it
        if isinstance(analysis_result, dict) and "analysis" in analysis_result:
            if isinstance(analysis_result["analysis"], str):
                try:
                    parsed = json.loads(analysis_result["analysis"])
                    # Ensure it has the expected structure
                    if isinstance(parsed, dict) and "issues" in parsed:
                        return parsed
                    else:
                        return {
                            "issues": [{"type": "invalid_structure", "description": "Parsed JSON lacks required 'issues' field", "severity": "critical"}],
                            "explanations": ["Agent returned invalid analysis structure."], "suggestions": [], "documentation_references": [], "diagnostic_commands": []
                        }
                except json.JSONDecodeError as e:
                    print(f"Failed to parse analysis JSON: {e}")
                    # Try to extract the problematic part for debugging
                    try:
                        problematic_part = analysis_result["analysis"][max(0, e.pos-50):e.pos+50]
                        print(f"Problematic JSON around position {e.pos}: ...{problematic_part}...")
                    except:
                        pass
                    return {
                        "issues": [{"type": "json_parsing_error", "description": str(e), "severity": "critical"}],
                        "explanations": ["Agent returned malformed JSON."], "suggestions": [], "documentation_references": [], "diagnostic_commands": []
                    }
            elif isinstance(analysis_result["analysis"], dict):
                # If analysis is already a dict, return it
                return analysis_result["analysis"]
        
        # If we get here, the format is unexpected
        print(f"Unexpected analysis_result format: {type(analysis_result)}")
        return {
            "issues": [{"type": "unexpected_format", "description": f"Unexpected format: {type(analysis_result)}", "severity": "critical"}],
            "explanations": ["Agent returned unexpected format."], "suggestions": [], "documentation_references": [], "diagnostic_commands": []
        }
    except Exception as e:
        print(f"Error running agent: {e}")
        return {
            "issues": [{"type": "execution_error", "description": str(e), "severity": "critical"}],
            "explanations": [f"Agent encountered an execution error: {e}"], "suggestions": [], "documentation_references": [], "diagnostic_commands": []
        }


# ==================== Main Evaluation Function ====================

async def run_evaluation(
    dataset_name: str = "log-analyzer-evaluation-v3",
    max_examples: Optional[int] = None,
    experiment_prefix: Optional[str] = None,
):
    """Run the evaluation on the LangSmith dataset."""
    print(f"Starting evaluation for dataset: {dataset_name}")
    if max_examples: print(f"Limiting to {max_examples} examples")

    # Define the set of evaluators to run on each example
    evaluators = [
        evaluate_issue_type_accuracy,
        evaluate_severity_accuracy,
        evaluate_explanation_quality,
        evaluate_suggestion_quality,
        evaluate_documentation_relevance,
        evaluate_diagnostic_commands,
        evaluate_response_completeness,
    ]
    # Define summary evaluators to run over the entire dataset
    summary_evaluators = [
        precision_summary_evaluator,
        recall_summary_evaluator,
        f1_summary_evaluator,
    ]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if not experiment_prefix:
        experiment_prefix = f"log-analyzer-eval-{timestamp}"
    
    print("\nRunning evaluation...")
    results_generator = await aevaluate(
        run_agent_on_input,
        data=dataset_name,
        evaluators=evaluators,
        summary_evaluators=summary_evaluators,
        experiment_prefix=experiment_prefix,
        max_concurrency=2,  # Be gentle on APIs
        metadata={"agent_version": "1.1", "evaluation_script": "consolidated_v3"},
    )

    print("\n" + "="*60)
    print("EVALUATION RESULTS")
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
    if total_examples > 0: print(f"Success rate: {((total_examples - errors) / total_examples * 100):.1f}%")

    print("\nIndividual Metric Scores (Averages):")
    print("-" * 50)
    for metric_name, scores in sorted(metrics.items()):
        if scores:
            avg_score = sum(scores) / len(scores)
            print(f"{metric_name:.<35} {avg_score:.2%}")
        else:
            print(f"{metric_name:.<35} No data")

    print("\nSummary metrics (precision, recall, F1) are calculated over the full dataset.")
    print("Please view the full results in your LangSmith project.")

    # Save detailed local summary
    results_file = Path(f"evaluation_results_{timestamp}.json")
    detailed_results = {
        "dataset": dataset_name, "experiment_prefix": experiment_prefix, "timestamp": timestamp,
        "total_examples": total_examples, "errors": errors,
        "metrics": {
            name: {"average": sum(scores)/len(scores) if scores else 0, "count": len(scores)}
            for name, scores in metrics.items()
        }
    }
    with open(results_file, 'w') as f:
        json.dump(detailed_results, f, indent=2)
    
    print(f"\nDetailed local summary saved to: {results_file}")
    print(f"View full, authoritative results in LangSmith: https://smith.langchain.com/")
    
# ==================== CLI Interface ====================

if __name__ == "__main__":
    asyncio.run(run_evaluation())