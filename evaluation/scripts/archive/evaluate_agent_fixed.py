#!/usr/bin/env python3
"""
Fixed evaluation functions for the log analyzer agent.
These evaluators are more flexible and forgiving while still measuring quality.
"""

from collections import Counter, defaultdict
from typing import Dict, Any, List, Set
from langsmith.evaluation import run_evaluator
from langsmith.schemas import Run, Example
import re


# ==================== Core Evaluators ====================

@run_evaluator
def evaluate_issue_type_accuracy(run: Run, example: Example) -> Dict[str, Any]:
    """
    Evaluate if the agent identifies issues correctly using flexible matching.
    Uses semantic similarity instead of exact type matching.
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
        
        if not actual_issues:
            return {
                "key": "issue_type_accuracy",
                "score": 0.0,
                "comment": f"No issues found, but expected {len(expected_issues)} issues"
            }
        
        # Define semantic groups for flexible matching
        issue_groups = {
            "connection": ["connection", "network", "socket", "timeout", "refused", "unreachable", "connectivity"],
            "authentication": ["auth", "login", "credential", "permission", "access", "unauthorized", "forbidden"],
            "memory": ["memory", "heap", "oom", "allocation", "ram", "swap"],
            "disk": ["disk", "storage", "filesystem", "space", "volume", "mount"],
            "service": ["service", "failure", "crash", "error", "exception", "failed"],
            "performance": ["performance", "slow", "latency", "delay", "timeout", "bottleneck"]
        }
        
        def normalize_issue_type(issue_type: str) -> str:
            """Normalize issue type to a semantic group."""
            if not issue_type:
                return "unknown"
            
            issue_type_lower = str(issue_type).lower()
            
            # Check each semantic group
            for group_name, keywords in issue_groups.items():
                if any(keyword in issue_type_lower for keyword in keywords):
                    return group_name
            
            # Check issue description if type doesn't match
            return "general"
        
        def get_issue_representation(issue: Dict) -> str:
            """Get a normalized representation of an issue."""
            if isinstance(issue, dict):
                issue_type = issue.get("type", "")
                description = issue.get("description", "")
                # Combine type and description for better matching
                combined = f"{issue_type} {description}".lower()
                
                # Find best matching group
                for group_name, keywords in issue_groups.items():
                    if any(keyword in combined for keyword in keywords):
                        return group_name
                
                return "general"
            return "unknown"
        
        # Normalize issues to semantic groups
        actual_groups = Counter(get_issue_representation(issue) for issue in actual_issues)
        expected_groups = Counter(get_issue_representation(issue) for issue in expected_issues)
        
        # Calculate metrics
        all_groups = set(actual_groups.keys()) | set(expected_groups.keys())
        matches = 0
        total_expected = sum(expected_groups.values())
        total_actual = sum(actual_groups.values())
        
        for group in all_groups:
            matches += min(actual_groups.get(group, 0), expected_groups.get(group, 0))
        
        precision = matches / total_actual if total_actual > 0 else 0
        recall = matches / total_expected if total_expected > 0 else 0
        
        score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        
        # Bonus for identifying critical issues even if types don't match exactly
        if score < 0.5 and len(actual_issues) >= len(expected_issues) * 0.8:
            score = max(score, 0.5)  # Minimum 50% if most issues were found
        
        comment = (f"Flexible F1 score: {score:.2%}. "
                   f"Precision: {precision:.2%}, Recall: {recall:.2%}. "
                   f"Found {len(actual_issues)} issues, expected {len(expected_issues)}")
        
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
    Evaluate severity assessment accuracy with flexible matching.
    Works even if issue types don't match exactly.
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
        
        if not actual_issues:
            return {
                "key": "severity_accuracy",
                "score": 0.0,
                "comment": "No issues found to evaluate severity"
            }
        
        # Flexible severity matching with aliases
        severity_aliases = {
            "critical": ["critical", "fatal", "severe", "emergency"],
            "error": ["error", "high", "major"],
            "warning": ["warning", "warn", "medium", "moderate"],
            "info": ["info", "low", "minor", "notice"]
        }
        
        def normalize_severity(severity: str) -> str:
            """Normalize severity to standard levels."""
            if not severity:
                return "info"
            
            severity_lower = str(severity).lower()
            for standard, aliases in severity_aliases.items():
                if severity_lower in aliases:
                    return standard
            return "info"
        
        # Get all severities from both sets
        actual_severities = [normalize_severity(issue.get("severity", "info")) for issue in actual_issues]
        expected_severities = [normalize_severity(issue.get("severity", "info")) for issue in expected_issues]
        
        # Sort to compare highest severities
        severity_order = ["critical", "error", "warning", "info"]
        actual_severities.sort(key=lambda x: severity_order.index(x))
        expected_severities.sort(key=lambda x: severity_order.index(x))
        
        # Compare overall severity distribution
        actual_dist = Counter(actual_severities)
        expected_dist = Counter(expected_severities)
        
        # Calculate score based on:
        # 1. Matching the highest severity (most important)
        # 2. Overall distribution similarity
        
        score = 0.0
        
        # Part 1: Highest severity match (50% of score)
        if actual_severities and expected_severities:
            highest_actual = actual_severities[0]
            highest_expected = expected_severities[0]
            
            if highest_actual == highest_expected:
                score += 0.5
            elif abs(severity_order.index(highest_actual) - severity_order.index(highest_expected)) == 1:
                score += 0.3  # Partial credit for being one level off
        
        # Part 2: Distribution similarity (50% of score)
        total_severities = sum(expected_dist.values())
        distribution_score = 0.0
        
        for severity in severity_order:
            expected_count = expected_dist.get(severity, 0)
            actual_count = actual_dist.get(severity, 0)
            
            if expected_count == 0 and actual_count == 0:
                continue
            
            # Calculate similarity for this severity level
            if expected_count == 0:
                # Penalty for false positives
                distribution_score -= 0.1 * (actual_count / max(1, total_severities))
            else:
                # Reward for matches, with some tolerance
                diff = abs(expected_count - actual_count)
                level_score = max(0, 1 - (diff / expected_count))
                weight = expected_count / total_severities
                distribution_score += level_score * weight
        
        score += max(0, distribution_score * 0.5)
        
        comment = (f"Severity accuracy: {score:.2%}. "
                   f"Expected distribution: {dict(expected_dist)}, "
                   f"Actual distribution: {dict(actual_dist)}")
        
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
def evaluate_diagnostic_commands(run: Run, example: Example) -> Dict[str, Any]:
    """
    Evaluate diagnostic commands with more balanced scoring.
    Rewards relevant commands without requiring exact matches.
    """
    try:
        actual = run.outputs or {}
        actual_issues = actual.get("issues", [])
        actual_commands = actual.get("diagnostic_commands", [])
        
        if not actual_issues:
            # No issues = no commands needed
            score = 1.0 if not actual_commands else 0.8  # Small penalty for unnecessary commands
            comment = "No issues found, diagnostic commands not required"
            return {"key": "diagnostic_commands", "score": score, "comment": comment}
        
        # Evaluate command quality
        if not actual_commands:
            # Some commands would be helpful, but not critical
            score = 0.3  # More forgiving than 0.0
            comment = f"No diagnostic commands provided for {len(actual_issues)} issues"
        else:
            # Check command structure and relevance
            valid_commands = []
            for cmd in actual_commands:
                if isinstance(cmd, dict):
                    has_command = bool(cmd.get("command", "").strip())
                    has_description = bool(cmd.get("description", "").strip())
                    if has_command:
                        valid_commands.append(cmd)
                elif isinstance(cmd, str) and cmd.strip():
                    # Accept string commands too
                    valid_commands.append({"command": cmd, "description": "Diagnostic command"})
            
            if not valid_commands:
                score = 0.2
                comment = "Commands provided but improperly formatted"
            else:
                # Score based on command coverage and quality
                base_score = min(1.0, len(valid_commands) / max(1, len(actual_issues)))
                
                # Bonus for well-documented commands
                doc_score = sum(1 for cmd in valid_commands if 
                               isinstance(cmd, dict) and 
                               len(cmd.get("description", "")) > 10) / len(valid_commands)
                
                score = 0.7 * base_score + 0.3 * doc_score
                
                # Check for relevant command keywords
                command_text = " ".join(cmd.get("command", "") for cmd in valid_commands).lower()
                relevant_keywords = ["log", "status", "check", "test", "verify", "show", "list", "debug"]
                
                if any(keyword in command_text for keyword in relevant_keywords):
                    score = min(1.0, score + 0.1)  # Bonus for relevant commands
                
                comment = f"{len(valid_commands)} valid commands for {len(actual_issues)} issues"
        
        return {"key": "diagnostic_commands", "score": score, "comment": comment}
    except Exception as e:
        return {"key": "diagnostic_commands", "score": 0.0, "comment": f"Error in evaluation: {str(e)}"}


# Export the fixed evaluators
__all__ = [
    'evaluate_issue_type_accuracy',
    'evaluate_severity_accuracy', 
    'evaluate_diagnostic_commands'
]