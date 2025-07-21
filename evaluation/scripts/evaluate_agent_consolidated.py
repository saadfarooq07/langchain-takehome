#!/usr/bin/env python3
"""
Consolidated evaluation script for the log analyzer agent using LangSmith.
This script provides comprehensive evaluation aligned with the dataset structure
and expected outputs from create_langsmith_dataset.py.

Features:
- Semantic matching for issue types
- Flexible severity assessment
- Quality evaluation for all components
- Support for both original and improved implementations
- Proper integration with the agent's actual output structure
- Modular evaluator support
"""

import asyncio
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Set
from collections import defaultdict, Counter
from difflib import SequenceMatcher

from langsmith import Client
from langsmith.evaluation import aevaluate, run_evaluator
from langsmith.schemas import Example, Run

# Import the log analyzer agent
from log_analyzer_agent.graph import graph
from log_analyzer_agent.state import CoreWorkingState, working_to_output, create_working_state
from log_analyzer_agent.configuration import Configuration, ModelConfig

# The "improved" implementation has been merged into the main implementation
# No need for separate imports or switching logic
print("Using log analyzer implementation")


# ==================== Helper Functions ====================

def normalize_text(text: str) -> str:
    """Normalize text for comparison by lowercasing and removing extra whitespace."""
    return ' '.join(str(text).lower().split())


def calculate_text_similarity(text1: str, text2: str) -> float:
    """Calculate similarity between two texts using SequenceMatcher."""
    return SequenceMatcher(None, normalize_text(text1), normalize_text(text2)).ratio()


def extract_keywords(text: str) -> Set[str]:
    """Extract meaningful keywords from text."""
    # Remove common words and split
    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
                  'of', 'with', 'by', 'is', 'was', 'are', 'were', 'be', 'been', 'being',
                  'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
                  'should', 'may', 'might', 'must', 'shall', 'can', 'cannot'}
    words = set(normalize_text(text).split()) - stop_words
    return {word for word in words if len(word) > 2}


# ==================== Issue Type Matching ====================

# Define semantic groups based on the IssueDetector patterns from dataset creation
ISSUE_TYPE_GROUPS = {
    "connection": {
        "keywords": ["connection", "connect", "refused", "timeout", "unreachable", 
                     "network", "socket", "port", "connectivity"],
        "aliases": ["connection_failure", "network_error", "connectivity_issue"]
    },
    "authentication": {
        "keywords": ["authentication", "auth", "login", "password", "credential", 
                     "denied", "unauthorized", "forbidden", "permission", "access"],
        "aliases": ["authentication_failure", "auth_error", "access_denied"]
    },
    "memory": {
        "keywords": ["memory", "heap", "oom", "allocation", "ram", "swap", 
                     "out of memory", "outofmemory", "heap space"],
        "aliases": ["memory_error", "oom_error", "heap_error", "memory_issue"]
    },
    "disk": {
        "keywords": ["disk", "space", "storage", "filesystem", "full", "volume", 
                     "mount", "capacity", "inode"],
        "aliases": ["disk_error", "storage_error", "filesystem_error", "disk_full"]
    },
    "service": {
        "keywords": ["service", "failure", "crash", "error", "exception", "failed", 
                     "stopped", "terminated", "killed", "died"],
        "aliases": ["service_failure", "application_error", "process_error", "crash"]
    },
    "performance": {
        "keywords": ["slow", "timeout", "latency", "performance", "delayed", 
                     "bottleneck", "lag", "response time", "throughput"],
        "aliases": ["performance_issue", "slowness", "high_latency", "performance_degradation"]
    },
    "general": {
        "keywords": ["error", "warning", "issue", "problem", "alert", "fault", "failure"],
        "aliases": ["general_error", "unknown_error", "unspecified_error"]
    }
}


def match_issue_type(issue_type: str, issue_description: str = "") -> str:
    """Match an issue type to a semantic group."""
    combined_text = f"{issue_type} {issue_description}".lower()
    
    # First check for exact alias matches
    for group_name, group_info in ISSUE_TYPE_GROUPS.items():
        if issue_type.lower() in [alias.lower() for alias in group_info["aliases"]]:
            return group_name
    
    # Then check for keyword matches
    best_match = "general"
    best_score = 0
    
    for group_name, group_info in ISSUE_TYPE_GROUPS.items():
        score = sum(1 for keyword in group_info["keywords"] if keyword in combined_text)
        if score > best_score:
            best_score = score
            best_match = group_name
    
    return best_match


# ==================== Core Evaluators ====================

@run_evaluator
def evaluate_issue_detection_comprehensive(run: Run, example: Example) -> Dict[str, Any]:
    """
    Comprehensive evaluation of issue detection including type, count, and descriptions.
    Uses semantic matching for issue types.
    """
    try:
        actual = run.outputs or {}
        expected = example.outputs or {}
        
        actual_issues = actual.get("issues", [])
        expected_issues = expected.get("issues", [])
        
        # Handle case where no issues are expected
        if not expected_issues:
            if not actual_issues:
                return {
                    "key": "issue_detection_comprehensive",
                    "score": 1.0,
                    "comment": "Correctly identified no issues present"
                }
            else:
                # Penalize false positives, but not too harshly
                false_positive_penalty = min(0.5, len(actual_issues) * 0.1)
                return {
                    "key": "issue_detection_comprehensive",
                    "score": max(0, 1.0 - false_positive_penalty),
                    "comment": f"Found {len(actual_issues)} issues when none were expected"
                }
        
        if not actual_issues:
            return {
                "key": "issue_detection_comprehensive",
                "score": 0.0,
                "comment": f"Failed to detect any of the {len(expected_issues)} expected issues"
            }
        
        # Match issues by semantic type
        matched_issues = []
        unmatched_expected = list(expected_issues)
        unmatched_actual = list(actual_issues)
        
        # First pass: match by semantic type
        for exp_issue in expected_issues[:]:
            exp_type = match_issue_type(
                exp_issue.get("type", ""), 
                exp_issue.get("description", "")
            )
            
            for act_issue in unmatched_actual[:]:
                act_type = match_issue_type(
                    act_issue.get("type", ""), 
                    act_issue.get("description", "")
                )
                
                if exp_type == act_type:
                    matched_issues.append((exp_issue, act_issue))
                    unmatched_expected.remove(exp_issue)
                    unmatched_actual.remove(act_issue)
                    break
        
        # Calculate scores
        type_match_score = len(matched_issues) / len(expected_issues) if expected_issues else 0
        
        # Evaluate description quality for matched issues
        description_scores = []
        for exp_issue, act_issue in matched_issues:
            exp_desc = exp_issue.get("description", "")
            act_desc = act_issue.get("description", "")
            
            # Check if key concepts are preserved
            exp_keywords = extract_keywords(exp_desc)
            act_keywords = extract_keywords(act_desc)
            
            if exp_keywords:
                keyword_overlap = len(exp_keywords & act_keywords) / len(exp_keywords)
            else:
                keyword_overlap = 1.0 if not act_keywords else 0.5
            
            description_scores.append(keyword_overlap)
        
        desc_quality_score = sum(description_scores) / len(description_scores) if description_scores else 0
        
        # Penalize false positives
        false_positive_penalty = len(unmatched_actual) * 0.1
        
        # Combined score
        final_score = (
            0.6 * type_match_score +  # Issue type detection is most important
            0.3 * desc_quality_score + # Description quality
            0.1 * max(0, 1 - false_positive_penalty)  # False positive penalty
        )
        
        comment_parts = [
            f"Detected {len(matched_issues)}/{len(expected_issues)} expected issues",
            f"Description quality: {desc_quality_score:.2%}",
        ]
        if unmatched_actual:
            comment_parts.append(f"{len(unmatched_actual)} unexpected issues")
        
        return {
            "key": "issue_detection_comprehensive",
            "score": final_score,
            "comment": ". ".join(comment_parts)
        }
        
    except Exception as e:
        return {
            "key": "issue_detection_comprehensive",
            "score": 0.0,
            "comment": f"Error in evaluation: {str(e)}"
        }


@run_evaluator
def evaluate_severity_assessment(run: Run, example: Example) -> Dict[str, Any]:
    """
    Evaluate severity assessment accuracy with tolerance for minor differences.
    """
    try:
        actual = run.outputs or {}
        expected = example.outputs or {}
        
        actual_issues = actual.get("issues", [])
        expected_issues = expected.get("issues", [])
        
        if not expected_issues:
            return {
                "key": "severity_assessment",
                "score": 1.0 if not actual_issues else 0.5,
                "comment": "No issues to assess severity"
            }
        
        # Define severity levels and scoring
        severity_levels = {
            "critical": 4,
            "high": 4,      # Some systems use "high" instead of "critical"
            "error": 3,
            "medium": 3,    # Some systems use "medium" instead of "error"
            "warning": 2,
            "low": 2,       # Some systems use "low" instead of "warning"
            "info": 1
        }
        
        # Normalize severities
        def normalize_severity(sev: str) -> str:
            sev_lower = str(sev).lower()
            if "critical" in sev_lower or "fatal" in sev_lower:
                return "critical"
            elif "error" in sev_lower or "high" in sev_lower:
                return "error"
            elif "warning" in sev_lower or "warn" in sev_lower or "medium" in sev_lower:
                return "warning"
            else:
                return "info"
        
        # Match issues by type first
        severity_scores = []
        
        for exp_issue in expected_issues:
            exp_type = match_issue_type(exp_issue.get("type", ""), exp_issue.get("description", ""))
            exp_severity = normalize_severity(exp_issue.get("severity", "info"))
            
            # Find matching actual issue
            best_match = None
            for act_issue in actual_issues:
                act_type = match_issue_type(act_issue.get("type", ""), act_issue.get("description", ""))
                if exp_type == act_type:
                    best_match = act_issue
                    break
            
            if best_match:
                act_severity = normalize_severity(best_match.get("severity", "info"))
                
                # Calculate severity score
                exp_level = severity_levels.get(exp_severity, 1)
                act_level = severity_levels.get(act_severity, 1)
                
                if exp_level == act_level:
                    severity_scores.append(1.0)
                elif abs(exp_level - act_level) == 1:
                    severity_scores.append(0.7)  # Partial credit for being one level off
                else:
                    severity_scores.append(0.3)  # Some credit for attempting
            else:
                severity_scores.append(0.0)  # No matching issue found
        
        final_score = sum(severity_scores) / len(severity_scores) if severity_scores else 0
        
        # Provide detailed feedback
        if final_score >= 0.9:
            comment = "Excellent severity assessment"
        elif final_score >= 0.7:
            comment = "Good severity assessment with minor differences"
        elif final_score >= 0.5:
            comment = "Moderate severity assessment accuracy"
        else:
            comment = "Poor severity assessment accuracy"
        
        return {
            "key": "severity_assessment",
            "score": final_score,
            "comment": f"{comment} (score: {final_score:.2%})"
        }
        
    except Exception as e:
        return {
            "key": "severity_assessment",
            "score": 0.0,
            "comment": f"Error in evaluation: {str(e)}"
        }


@run_evaluator
def evaluate_explanations_quality(run: Run, example: Example) -> Dict[str, Any]:
    """
    Evaluate the quality and relevance of explanations.
    """
    try:
        actual = run.outputs or {}
        expected = example.outputs or {}
        
        actual_issues = actual.get("issues", [])
        actual_explanations = actual.get("explanations", [])
        expected_explanations = expected.get("explanations", [])
        
        if not expected_explanations:
            # If no explanations expected, check that none are provided unnecessarily
            return {
                "key": "explanations_quality",
                "score": 1.0 if not actual_explanations else 0.8,
                "comment": "No explanations expected"
            }
        
        if not actual_explanations:
            return {
                "key": "explanations_quality",
                "score": 0.0,
                "comment": f"No explanations provided, but {len(expected_explanations)} expected"
            }
        
        # Evaluate explanation quality
        quality_scores = []
        
        # Check coverage (do we have enough explanations?)
        coverage_score = min(1.0, len(actual_explanations) / len(expected_explanations))
        quality_scores.append(("coverage", coverage_score))
        
        # Check content quality
        for i, exp_explanation in enumerate(expected_explanations):
            if i < len(actual_explanations):
                act_explanation = actual_explanations[i]
                
                # Check length (explanations should be substantive)
                if len(act_explanation) < 20:
                    quality_scores.append(("length", 0.3))
                elif len(act_explanation) < 50:
                    quality_scores.append(("length", 0.7))
                else:
                    quality_scores.append(("length", 1.0))
                
                # Check for key concepts
                exp_keywords = extract_keywords(exp_explanation)
                act_keywords = extract_keywords(act_explanation)
                
                if exp_keywords:
                    concept_overlap = len(exp_keywords & act_keywords) / len(exp_keywords)
                    quality_scores.append(("concepts", concept_overlap))
                
                # Check for technical accuracy indicators
                technical_terms = {"system", "error", "service", "connection", "memory", "disk", 
                                 "authentication", "configuration", "network", "process"}
                has_technical = any(term in act_explanation.lower() for term in technical_terms)
                quality_scores.append(("technical", 1.0 if has_technical else 0.5))
        
        # Calculate final score
        if quality_scores:
            final_score = sum(score for _, score in quality_scores) / len(quality_scores)
        else:
            final_score = 0.0
        
        # Generate detailed feedback
        score_by_type = defaultdict(list)
        for score_type, score in quality_scores:
            score_by_type[score_type].append(score)
        
        feedback_parts = []
        for score_type, scores in score_by_type.items():
            avg_score = sum(scores) / len(scores)
            if score_type == "coverage":
                feedback_parts.append(f"Coverage: {avg_score:.2%}")
            elif score_type == "length":
                feedback_parts.append(f"Length adequacy: {avg_score:.2%}")
            elif score_type == "concepts":
                feedback_parts.append(f"Concept matching: {avg_score:.2%}")
        
        return {
            "key": "explanations_quality",
            "score": final_score,
            "comment": ". ".join(feedback_parts) if feedback_parts else "Explanation quality assessed"
        }
        
    except Exception as e:
        return {
            "key": "explanations_quality",
            "score": 0.0,
            "comment": f"Error in evaluation: {str(e)}"
        }


@run_evaluator
def evaluate_suggestions_relevance(run: Run, example: Example) -> Dict[str, Any]:
    """
    Evaluate the relevance and quality of suggestions.
    """
    try:
        actual = run.outputs or {}
        expected = example.outputs or {}
        
        actual_suggestions = actual.get("suggestions", [])
        expected_suggestions = expected.get("suggestions", [])
        actual_issues = actual.get("issues", [])
        
        if not expected_suggestions:
            # No suggestions expected
            return {
                "key": "suggestions_relevance",
                "score": 1.0 if not actual_suggestions else 0.8,
                "comment": "No suggestions expected"
            }
        
        if not actual_suggestions:
            # Suggestions expected but none provided
            return {
                "key": "suggestions_relevance",
                "score": 0.0,
                "comment": f"No suggestions provided, but {len(expected_suggestions)} expected"
            }
        
        # Evaluate suggestion quality
        quality_metrics = []
        
        # 1. Coverage - do we have enough suggestions?
        coverage_ratio = min(1.0, len(actual_suggestions) / len(expected_suggestions))
        quality_metrics.append(("coverage", coverage_ratio))
        
        # 2. Actionability - do suggestions contain action verbs?
        action_verbs = {"check", "verify", "ensure", "review", "monitor", "increase", "restart", 
                       "configure", "update", "fix", "repair", "investigate", "analyze", "test"}
        
        actionable_count = 0
        for suggestion in actual_suggestions:
            if any(verb in suggestion.lower() for verb in action_verbs):
                actionable_count += 1
        
        actionability_score = actionable_count / len(actual_suggestions) if actual_suggestions else 0
        quality_metrics.append(("actionability", actionability_score))
        
        # 3. Specificity - are suggestions specific rather than generic?
        specific_terms = {"service", "network", "configuration", "log", "system", "memory", 
                         "disk", "port", "firewall", "authentication", "database", "file"}
        
        specific_count = 0
        for suggestion in actual_suggestions:
            if any(term in suggestion.lower() for term in specific_terms):
                specific_count += 1
        
        specificity_score = specific_count / len(actual_suggestions) if actual_suggestions else 0
        quality_metrics.append(("specificity", specificity_score))
        
        # 4. Relevance to issues - do suggestions address the identified issues?
        if actual_issues:
            issue_types = [match_issue_type(issue.get("type", ""), issue.get("description", "")) 
                          for issue in actual_issues]
            
            relevant_count = 0
            for suggestion in actual_suggestions:
                suggestion_lower = suggestion.lower()
                # Check if suggestion relates to any identified issue type
                for issue_type in issue_types:
                    if any(keyword in suggestion_lower 
                          for keyword in ISSUE_TYPE_GROUPS.get(issue_type, {}).get("keywords", [])):
                        relevant_count += 1
                        break
            
            relevance_score = relevant_count / len(actual_suggestions) if actual_suggestions else 0
            quality_metrics.append(("relevance", relevance_score))
        
        # Calculate final score
        final_score = sum(score for _, score in quality_metrics) / len(quality_metrics)
        
        # Generate feedback
        feedback_parts = []
        for metric_name, score in quality_metrics:
            if metric_name == "coverage":
                feedback_parts.append(f"{len(actual_suggestions)}/{len(expected_suggestions)} suggestions")
            elif metric_name == "actionability":
                feedback_parts.append(f"{int(score * 100)}% actionable")
            elif metric_name == "specificity":
                feedback_parts.append(f"{int(score * 100)}% specific")
            elif metric_name == "relevance":
                feedback_parts.append(f"{int(score * 100)}% relevant to issues")
        
        return {
            "key": "suggestions_relevance",
            "score": final_score,
            "comment": ". ".join(feedback_parts)
        }
        
    except Exception as e:
        return {
            "key": "suggestions_relevance",
            "score": 0.0,
            "comment": f"Error in evaluation: {str(e)}"
        }


@run_evaluator
def evaluate_documentation_references(run: Run, example: Example) -> Dict[str, Any]:
    """
    Evaluate the quality and relevance of documentation references.
    """
    try:
        actual = run.outputs or {}
        expected = example.outputs or {}
        
        actual_docs = actual.get("documentation_references", [])
        expected_docs = expected.get("documentation_references", [])
        actual_issues = actual.get("issues", [])
        
        if not expected_docs:
            # No documentation expected
            score = 1.0 if not actual_docs else 0.9  # Small penalty for unnecessary docs
            return {
                "key": "documentation_references",
                "score": score,
                "comment": "No documentation references expected"
            }
        
        if not actual_docs:
            # Check if documentation is critical (for errors/critical issues)
            has_critical = any(issue.get("severity") in ["critical", "error"] for issue in actual_issues)
            score = 0.0 if has_critical else 0.3  # More forgiving if no critical issues
            return {
                "key": "documentation_references",
                "score": score,
                "comment": f"No documentation provided{', but critical issues found' if has_critical else ''}"
            }
        
        # Evaluate documentation quality
        quality_scores = []
        
        # Check structure
        for doc in actual_docs:
            if isinstance(doc, dict):
                has_title = bool(doc.get("title", "").strip())
                has_url = bool(doc.get("url", "").strip())
                has_relevance = bool(doc.get("relevance", "").strip())
                
                # Calculate structure score
                structure_score = (
                    0.4 * (1.0 if has_title else 0) +
                    0.4 * (1.0 if has_url else 0) +
                    0.2 * (1.0 if has_relevance else 0)
                )
                quality_scores.append(structure_score)
                
                # Check URL validity (basic check)
                if has_url:
                    url = doc["url"]
                    if url.startswith(("http://", "https://", "/")):
                        quality_scores.append(1.0)
                    else:
                        quality_scores.append(0.5)
            else:
                quality_scores.append(0.0)  # Invalid format
        
        # Check relevance to issues
        if actual_issues:
            issue_keywords = set()
            for issue in actual_issues:
                issue_type = match_issue_type(issue.get("type", ""), issue.get("description", ""))
                issue_keywords.update(ISSUE_TYPE_GROUPS.get(issue_type, {}).get("keywords", []))
            
            relevance_scores = []
            for doc in actual_docs:
                if isinstance(doc, dict):
                    doc_text = f"{doc.get('title', '')} {doc.get('relevance', '')}".lower()
                    if any(keyword in doc_text for keyword in issue_keywords):
                        relevance_scores.append(1.0)
                    else:
                        relevance_scores.append(0.5)
            
            if relevance_scores:
                quality_scores.extend(relevance_scores)
        
        final_score = sum(quality_scores) / len(quality_scores) if quality_scores else 0
        
        # Generate feedback
        valid_docs = sum(1 for doc in actual_docs if isinstance(doc, dict) and doc.get("url"))
        comment = f"{valid_docs}/{len(actual_docs)} valid documentation references"
        
        if final_score >= 0.8:
            comment += " - Well-structured and relevant"
        elif final_score >= 0.6:
            comment += " - Adequate documentation"
        else:
            comment += " - Needs improvement"
        
        return {
            "key": "documentation_references",
            "score": final_score,
            "comment": comment
        }
        
    except Exception as e:
        return {
            "key": "documentation_references",
            "score": 0.0,
            "comment": f"Error in evaluation: {str(e)}"
        }


@run_evaluator
def evaluate_diagnostic_commands_quality(run: Run, example: Example) -> Dict[str, Any]:
    """
    Evaluate the quality and appropriateness of diagnostic commands.
    """
    try:
        actual = run.outputs or {}
        expected = example.outputs or {}
        
        actual_commands = actual.get("diagnostic_commands", [])
        expected_commands = expected.get("diagnostic_commands", [])
        actual_issues = actual.get("issues", [])
        
        if not expected_commands:
            # No commands expected
            score = 1.0 if not actual_commands else 0.9
            return {
                "key": "diagnostic_commands_quality",
                "score": score,
                "comment": "No diagnostic commands expected"
            }
        
        if not actual_commands:
            # Commands expected but none provided
            score = 0.0 if actual_issues else 0.5  # More forgiving if no issues found
            return {
                "key": "diagnostic_commands_quality",
                "score": score,
                "comment": f"No commands provided{', but issues were found' if actual_issues else ''}"
            }
        
        # Evaluate command quality
        quality_metrics = []
        
        # 1. Structure validation
        valid_commands = []
        for cmd in actual_commands:
            if isinstance(cmd, dict):
                has_command = bool(cmd.get("command", "").strip())
                has_description = bool(cmd.get("description", "").strip())
                if has_command:
                    valid_commands.append(cmd)
                    structure_score = 0.7 if has_command else 0
                    structure_score += 0.3 if has_description else 0
                    quality_metrics.append(("structure", structure_score))
            elif isinstance(cmd, str) and cmd.strip():
                # Accept string commands but with lower score
                valid_commands.append({"command": cmd, "description": ""})
                quality_metrics.append(("structure", 0.6))
        
        # 2. Command relevance to common diagnostic tools
        diagnostic_keywords = {
            "system": ["ps", "top", "uptime", "systemctl", "service", "dmesg"],
            "network": ["netstat", "ss", "ping", "traceroute", "nslookup", "tcpdump", "ifconfig", "ip"],
            "disk": ["df", "du", "iostat", "fdisk", "mount", "lsblk"],
            "memory": ["free", "vmstat", "pmap", "smem"],
            "logs": ["tail", "grep", "journalctl", "cat", "less", "awk"],
            "process": ["ps", "pgrep", "lsof", "strace"],
            "performance": ["iotop", "htop", "sar", "mpstat"]
        }
        
        # Flatten all keywords
        all_diagnostic_keywords = set()
        for keywords in diagnostic_keywords.values():
            all_diagnostic_keywords.update(keywords)
        
        relevant_commands = 0
        for cmd in valid_commands:
            command_text = cmd.get("command", "").lower()
            if any(keyword in command_text for keyword in all_diagnostic_keywords):
                relevant_commands += 1
        
        relevance_score = relevant_commands / len(valid_commands) if valid_commands else 0
        quality_metrics.append(("relevance", relevance_score))
        
        # 3. Coverage - do we have enough commands?
        coverage_score = min(1.0, len(valid_commands) / max(1, len(expected_commands)))
        quality_metrics.append(("coverage", coverage_score))
        
        # 4. Appropriateness to issues
        if actual_issues:
            issue_types = [match_issue_type(issue.get("type", ""), issue.get("description", "")) 
                          for issue in actual_issues]
            
            appropriate_commands = 0
            for cmd in valid_commands:
                command_text = cmd.get("command", "").lower()
                description = cmd.get("description", "").lower()
                combined_text = f"{command_text} {description}"
                
                # Check if command is appropriate for any issue type
                for issue_type in issue_types:
                    if issue_type in diagnostic_keywords:
                        if any(keyword in command_text for keyword in diagnostic_keywords[issue_type]):
                            appropriate_commands += 1
                            break
            
            appropriateness_score = appropriate_commands / len(valid_commands) if valid_commands else 0
            quality_metrics.append(("appropriateness", appropriateness_score))
        
        # Calculate final score
        final_score = sum(score for _, score in quality_metrics) / len(quality_metrics) if quality_metrics else 0
        
        # Generate detailed feedback
        feedback_parts = [f"{len(valid_commands)} commands provided"]
        
        metric_scores = defaultdict(list)
        for metric_name, score in quality_metrics:
            metric_scores[metric_name].append(score)
        
        for metric_name, scores in metric_scores.items():
            avg_score = sum(scores) / len(scores)
            if metric_name == "relevance":
                feedback_parts.append(f"{int(avg_score * 100)}% use standard tools")
            elif metric_name == "appropriateness" and "appropriateness" in metric_scores:
                feedback_parts.append(f"{int(avg_score * 100)}% match issues")
        
        return {
            "key": "diagnostic_commands_quality",
            "score": final_score,
            "comment": ". ".join(feedback_parts)
        }
        
    except Exception as e:
        return {
            "key": "diagnostic_commands_quality",
            "score": 0.0,
            "comment": f"Error in evaluation: {str(e)}"
        }


@run_evaluator
def evaluate_overall_completeness(run: Run, example: Example) -> Dict[str, Any]:
    """
    Evaluate the overall completeness and structure of the response.
    """
    try:
        actual = run.outputs or {}
        expected = example.outputs or {}
        
        required_fields = ["issues", "explanations", "suggestions", "documentation_references", "diagnostic_commands"]
        
        # Check field presence
        present_fields = [field for field in required_fields if field in actual]
        completeness_score = len(present_fields) / len(required_fields)
        
        # Check field population (not just present but has content)
        populated_fields = []
        for field in present_fields:
            value = actual[field]
            if isinstance(value, list) and len(value) > 0:
                populated_fields.append(field)
            elif isinstance(value, dict) and len(value) > 0:
                populated_fields.append(field)
            elif isinstance(value, str) and value.strip():
                populated_fields.append(field)
        
        population_score = len(populated_fields) / len(required_fields)
        
        # Check consistency between fields
        consistency_score = 1.0
        issues = actual.get("issues", [])
        
        if issues:
            # If issues exist, we expect other fields to be populated
            if not actual.get("explanations"):
                consistency_score -= 0.2
            if not actual.get("suggestions"):
                consistency_score -= 0.2
            
            # For critical issues, we expect documentation and commands
            has_critical = any(issue.get("severity") in ["critical", "error"] for issue in issues)
            if has_critical:
                if not actual.get("documentation_references"):
                    consistency_score -= 0.1
                if not actual.get("diagnostic_commands"):
                    consistency_score -= 0.1
        else:
            # If no issues, other fields should be minimal or empty
            if len(actual.get("explanations", [])) > 1:
                consistency_score -= 0.1
            if len(actual.get("suggestions", [])) > 1:
                consistency_score -= 0.1
        
        consistency_score = max(0, consistency_score)
        
        # Calculate final score
        final_score = (
            0.4 * completeness_score +
            0.3 * population_score +
            0.3 * consistency_score
        )
        
        # Generate feedback
        missing_fields = [f for f in required_fields if f not in present_fields]
        unpopulated_fields = [f for f in present_fields if f not in populated_fields]
        
        feedback_parts = []
        if missing_fields:
            feedback_parts.append(f"Missing: {', '.join(missing_fields)}")
        if unpopulated_fields:
            feedback_parts.append(f"Empty: {', '.join(unpopulated_fields)}")
        if consistency_score < 1.0:
            feedback_parts.append("Inconsistent field population")
        
        if not feedback_parts:
            feedback_parts.append("All fields present and properly populated")
        
        return {
            "key": "overall_completeness",
            "score": final_score,
            "comment": ". ".join(feedback_parts)
        }
        
    except Exception as e:
        return {
            "key": "overall_completeness",
            "score": 0.0,
            "comment": f"Error in evaluation: {str(e)}"
        }


# ==================== Summary Evaluators ====================

def precision_recall_f1_summary(runs: List[Run], examples: List[Example]) -> Dict[str, Any]:
    """Calculate precision, recall, and F1 score for issue detection across all examples."""
    total_tp, total_fp, total_fn = 0, 0, 0
    
    for run, example in zip(runs, examples):
        if run.error:
            continue
            
        actual = run.outputs or {}
        expected = example.outputs or {}
        
        actual_issues = actual.get("issues", [])
        expected_issues = expected.get("issues", [])
        
        # Match issues by semantic type
        actual_types = Counter(
            match_issue_type(issue.get("type", ""), issue.get("description", ""))
            for issue in actual_issues
        )
        expected_types = Counter(
            match_issue_type(issue.get("type", ""), issue.get("description", ""))
            for issue in expected_issues
        )
        
        # Calculate true positives, false positives, and false negatives
        for issue_type in set(actual_types.keys()) | set(expected_types.keys()):
            actual_count = actual_types.get(issue_type, 0)
            expected_count = expected_types.get(issue_type, 0)
            
            tp = min(actual_count, expected_count)
            fp = max(0, actual_count - expected_count)
            fn = max(0, expected_count - actual_count)
            
            total_tp += tp
            total_fp += fp
            total_fn += fn
    
    precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0
    recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    
    return {
        "key": "issue_detection_f1",
        "score": f1,
        "comment": f"F1: {f1:.2%} (Precision: {precision:.2%}, Recall: {recall:.2%}, TP: {total_tp}, FP: {total_fp}, FN: {total_fn})"
    }


def response_quality_summary(runs: List[Run], examples: List[Example]) -> Dict[str, Any]:
    """Calculate average response quality across all evaluation metrics."""
    metric_scores = defaultdict(list)
    
    # Collect all individual scores
    for run in runs:
        if run.error or not hasattr(run, 'feedback'):
            continue
            
        for feedback in run.feedback:
            if hasattr(feedback, 'key') and hasattr(feedback, 'score'):
                metric_scores[feedback.key].append(feedback.score)
    
    # Calculate averages
    metric_averages = {}
    for metric, scores in metric_scores.items():
        if scores:
            metric_averages[metric] = sum(scores) / len(scores)
    
    # Calculate overall quality score (weighted average)
    weights = {
        "issue_detection_comprehensive": 0.3,
        "severity_assessment": 0.15,
        "explanations_quality": 0.15,
        "suggestions_relevance": 0.15,
        "documentation_references": 0.1,
        "diagnostic_commands_quality": 0.1,
        "overall_completeness": 0.05
    }
    
    weighted_score = 0
    total_weight = 0
    
    for metric, weight in weights.items():
        if metric in metric_averages:
            weighted_score += metric_averages[metric] * weight
            total_weight += weight
    
    final_score = weighted_score / total_weight if total_weight > 0 else 0
    
    # Format detailed breakdown
    breakdown = []
    for metric, avg in sorted(metric_averages.items()):
        breakdown.append(f"{metric}: {avg:.2%}")
    
    return {
        "key": "response_quality_overall",
        "score": final_score,
        "comment": f"Overall quality: {final_score:.2%}. " + "; ".join(breakdown[:3]) + "..."
    }


# ==================== Agent Runner ====================

def transform_output_fields(analysis_result: Dict[str, Any]) -> Dict[str, Any]:
    """Transform agent output fields to match expected evaluation format.
    
    The agent outputs:
    - root_cause (string) -> explanations (list of strings)
    - recommendations (list) -> suggestions (list)
    
    The evaluation expects:
    - explanations (list)
    - suggestions (list)
    """
    if not analysis_result:
        return {}
    
    transformed = analysis_result.copy()
    
    # Transform root_cause to explanations
    if "root_cause" in transformed and "explanations" not in transformed:
        root_cause = transformed.get("root_cause", "")
        if root_cause and isinstance(root_cause, str):
            transformed["explanations"] = [root_cause]
        else:
            transformed["explanations"] = []
    
    # Transform recommendations to suggestions
    if "recommendations" in transformed and "suggestions" not in transformed:
        transformed["suggestions"] = transformed.get("recommendations", [])
    
    return transformed


async def run_agent_on_input(inputs: Dict[str, Any], config: Optional[Configuration] = None) -> Dict[str, Any]:
    """Run the log analyzer agent on a single input with robust error handling."""
    try:
        # Rate limiting
        await asyncio.sleep(1)
        
        # Initialize state using the proper state structure
        initial_state = {
            "log_content": inputs["log_content"],
            "messages": [],
            "analysis_result": None,
            "validation_status": None,
            "log_metadata": {},
            "node_visits": {},
            "tool_calls": [],
            "token_count": 0,
            "start_time": datetime.now().timestamp(),
            "enabled_features": set()
        }
        
        # Create runnable config with model settings if provided
        runnable_config = None
        if config:
            runnable_config = {
                "configurable": {
                    "model": config.primary_model.get_model_string(),
                    "orchestration_model": config.orchestration_model.get_model_string(),
                    "max_analysis_iterations": config.max_analysis_iterations,
                    "max_tool_calls": config.max_tool_calls,
                }
            }
        
        # Run the agent
        result = await graph.ainvoke(initial_state, config=runnable_config)
        
        # Extract analysis result - handle both old and new formats
        analysis_result = result.get("analysis_result", {})
        
        # If analysis_result is None or empty, try to extract from final analysis
        if not analysis_result:
            # Look for the last submit_analysis tool call in messages
            messages = result.get("messages", [])
            for message in reversed(messages):
                if hasattr(message, "tool_calls") and message.tool_calls:
                    for tool_call in message.tool_calls:
                        if tool_call.get("name") == "submit_analysis":
                            analysis_result = tool_call.get("args", {})
                            break
                if analysis_result:
                    break
        
        # Ensure we have the expected structure
        if not isinstance(analysis_result, dict):
            analysis_result = {}
        
        # Transform output fields to match expected format
        analysis_result = transform_output_fields(analysis_result)
        
        # Return with all required fields
        return {
            "issues": analysis_result.get("issues", []),
            "explanations": analysis_result.get("explanations", []),
            "suggestions": analysis_result.get("suggestions", []),
            "documentation_references": analysis_result.get("documentation_references", []),
            "diagnostic_commands": analysis_result.get("diagnostic_commands", [])
        }
        
    except Exception as e:
        print(f"Error running agent: {e}")
        return {
            "issues": [{"type": "execution_error", "description": str(e), "severity": "critical"}],
            "explanations": [f"Agent execution failed: {e}"],
            "suggestions": ["Check agent configuration and retry"],
            "documentation_references": [],
            "diagnostic_commands": []
        }


# ==================== Main Evaluation Function ====================

async def run_evaluation(
    dataset_name: str = "log-analyzer-evaluation",
    max_examples: Optional[int] = None,
    experiment_prefix: Optional[str] = None,
    primary_model: Optional[str] = None,
    orchestration_model: Optional[str] = None,
):
    """Run the comprehensive evaluation on the LangSmith dataset."""
    
    # The improved implementation has been merged into the main implementation
    # No need for switching logic
    
    # Create configuration with model settings
    config = Configuration()
    
    # Parse and set primary model if provided
    if primary_model:
        if ":" in primary_model:
            provider, model_name = primary_model.split(":", 1)
            config.primary_model = ModelConfig(
                provider=provider,
                model_name=model_name,
                temperature=0.0
            )
        else:
            print(f"Warning: Invalid primary model format '{primary_model}'. Using default.")
    
    # Parse and set orchestration model if provided
    if orchestration_model:
        if ":" in orchestration_model:
            provider, model_name = orchestration_model.split(":", 1)
            config.orchestration_model = ModelConfig(
                provider=provider,
                model_name=model_name,
                temperature=0.3
            )
        else:
            print(f"Warning: Invalid orchestration model format '{orchestration_model}'. Using default.")
    
    print(f"Starting consolidated evaluation for dataset: {dataset_name}")
    print(f"Using log analyzer implementation")
    print(f"Primary model: {config.primary_model.get_model_string()}")
    print(f"Orchestration model: {config.orchestration_model.get_model_string()}")
    if max_examples:
        print(f"Limiting to {max_examples} examples")
    
    # Define evaluators
    evaluators = [
        evaluate_issue_detection_comprehensive,
        evaluate_severity_assessment,
        evaluate_explanations_quality,
        evaluate_suggestions_relevance,
        evaluate_documentation_references,
        evaluate_diagnostic_commands_quality,
        evaluate_overall_completeness,
    ]
    
    # Define summary evaluators
    summary_evaluators = [
        precision_recall_f1_summary,
        response_quality_summary,
    ]
    
    # Generate experiment name with model info
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    primary_short = config.primary_model.provider[:4]  # e.g., "gemi" for gemini
    orch_short = config.orchestration_model.provider[:4]  # e.g., "groq" for groq
    
    if not experiment_prefix:
        experiment_prefix = f"log-analyzer-{primary_short}-{orch_short}-{timestamp}"
    
    print("\nRunning evaluation...")
    print(f"Experiment: {experiment_prefix}")
    
    # Create a wrapper function that includes the config
    async def run_agent_wrapper(inputs: Dict[str, Any]) -> Dict[str, Any]:
        return await run_agent_on_input(inputs, config)
    
    # Run evaluation
    results = await aevaluate(
        run_agent_wrapper,
        data=dataset_name,
        evaluators=evaluators,
        summary_evaluators=summary_evaluators,
        experiment_prefix=experiment_prefix,
        max_concurrency=2,
        metadata={
            "evaluation_version": "consolidated_v1",
            "timestamp": timestamp,
            "evaluator_count": len(evaluators),
            "implementation": "main",
            "primary_model": config.primary_model.get_model_string(),
            "orchestration_model": config.orchestration_model.get_model_string(),
        },
    )
    
    # Process results
    print("\n" + "="*80)
    print("EVALUATION RESULTS")
    print("="*80)
    
    results_list = [res async for res in results]
    total_examples = len(results_list)
    errors = sum(1 for res in results_list if (hasattr(res, 'error') and res.error))
    
    print(f"\nTotal examples evaluated: {total_examples}")
    print(f"Errors encountered: {errors}")
    print(f"Success rate: {((total_examples - errors) / total_examples * 100):.1f}%")
    
    # Collect individual metrics
    metrics = defaultdict(list)
    for result in results_list:
        if hasattr(result, 'error') and result.error:
            continue
        
        if hasattr(result, 'feedback'):
            for feedback in result.feedback:
                if hasattr(feedback, 'key') and hasattr(feedback, 'score'):
                    metrics[feedback.key].append(feedback.score)
    
    # Display individual metrics
    print("\nIndividual Metric Scores:")
    print("-" * 60)
    for metric_name, scores in sorted(metrics.items()):
        if scores:
            avg_score = sum(scores) / len(scores)
            min_score = min(scores)
            max_score = max(scores)
            print(f"{metric_name:.<40} {avg_score:.2%} (min: {min_score:.2%}, max: {max_score:.2%})")
    
    # Save results
    results_file = Path(f"evaluation_results_consolidated_{timestamp}.json")
    detailed_results = {
        "dataset": dataset_name,
        "experiment_prefix": experiment_prefix,
        "timestamp": timestamp,
        "implementation": "main",
        "total_examples": total_examples,
        "errors": errors,
        "metrics": {
            name: {
                "average": sum(scores)/len(scores) if scores else 0,
                "min": min(scores) if scores else 0,
                "max": max(scores) if scores else 0,
                "count": len(scores)
            }
            for name, scores in metrics.items()
        }
    }
    
    with open(results_file, 'w') as f:
        json.dump(detailed_results, f, indent=2)
    
    print(f"\nDetailed results saved to: {results_file}")
    print(f"\nView full results in LangSmith: https://smith.langchain.com/")
    print("\nEvaluation complete! ✨")


# ==================== CLI Interface ====================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run consolidated evaluation for log analyzer agent")
    parser.add_argument("--dataset", default="log-analyzer-evaluation", help="Dataset name in LangSmith")
    parser.add_argument("--max-examples", type=int, help="Maximum number of examples to evaluate")
    parser.add_argument("--experiment-prefix", help="Custom experiment prefix")
    parser.add_argument("--primary-model", help="Primary model in provider:model format (e.g., gemini:gemini-2.0-flash-exp)")
    parser.add_argument("--orchestration-model", help="Orchestration model in provider:model format (e.g., groq:deepseek-r1-distill-llama-70b)")
    
    args = parser.parse_args()
    
    asyncio.run(run_evaluation(
        dataset_name=args.dataset,
        max_examples=args.max_examples,
        experiment_prefix=args.experiment_prefix,
        primary_model=args.primary_model,
        orchestration_model=args.orchestration_model
    ))