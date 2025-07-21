#!/usr/bin/env python3
"""
Parallel evaluation script for the log analyzer agent using LangSmith.
This script evaluates all dataset entries in parallel using async functions
for significantly improved performance.

Key improvements:
- True parallel evaluation of all dataset entries
- Configurable batch size for memory management
- Progress tracking with real-time updates
- Improved error handling and retry logic
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Set
from collections import defaultdict, Counter
from difflib import SequenceMatcher
import time
from concurrent.futures import ThreadPoolExecutor

from langsmith import Client
from langsmith.evaluation import aevaluate, run_evaluator
from langsmith.schemas import Example, Run

# Import the log analyzer agent
from log_analyzer_agent.graph import graph
from log_analyzer_agent.state import CoreWorkingState, working_to_output, create_working_state
from log_analyzer_agent.configuration import Configuration, ModelConfig


# ==================== Helper Functions ====================

def normalize_text(text: str) -> str:
    """Normalize text for comparison by lowercasing and removing extra whitespace."""
    return ' '.join(str(text).lower().split())


def calculate_text_similarity(text1: str, text2: str) -> float:
    """Calculate similarity between two texts using SequenceMatcher."""
    return SequenceMatcher(None, normalize_text(text1), normalize_text(text2)).ratio()


def extract_keywords(text: str) -> Set[str]:
    """Extract meaningful keywords from text."""
    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
                  'of', 'with', 'by', 'is', 'was', 'are', 'were', 'be', 'been', 'being',
                  'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
                  'should', 'may', 'might', 'must', 'shall', 'can', 'cannot'}
    words = set(normalize_text(text).split()) - stop_words
    return {word for word in words if len(word) > 2}


# ==================== Issue Type Matching ====================

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
# [Keep all the existing evaluator functions from the original script]
# evaluate_issue_detection_comprehensive, evaluate_severity_assessment, etc.
# (Omitted here for brevity - copy from original file)

# ==================== Copy Core Evaluators from Original Script ====================

@run_evaluator
def evaluate_issue_detection_comprehensive(run: Run, example: Example) -> Dict[str, Any]:
    """Comprehensive evaluation of issue detection including type, count, and descriptions."""
    try:
        actual = run.outputs or {}
        expected = example.outputs or {}
        
        actual_issues = actual.get("issues", [])
        expected_issues = expected.get("issues", [])
        
        if not expected_issues:
            if not actual_issues:
                return {"key": "issue_detection_comprehensive", "score": 1.0, "comment": "Correctly identified no issues present"}
            else:
                false_positive_penalty = min(0.5, len(actual_issues) * 0.1)
                return {"key": "issue_detection_comprehensive", "score": max(0, 1.0 - false_positive_penalty), "comment": f"Found {len(actual_issues)} issues when none were expected"}
        
        if not actual_issues:
            return {"key": "issue_detection_comprehensive", "score": 0.0, "comment": f"Failed to detect any of the {len(expected_issues)} expected issues"}
        
        # Match issues by semantic type
        matched_issues = []
        unmatched_expected = list(expected_issues)
        unmatched_actual = list(actual_issues)
        
        for exp_issue in expected_issues[:]:
            exp_type = match_issue_type(exp_issue.get("type", ""), exp_issue.get("description", ""))
            
            for act_issue in unmatched_actual[:]:
                act_type = match_issue_type(act_issue.get("type", ""), act_issue.get("description", ""))
                
                if exp_type == act_type:
                    matched_issues.append((exp_issue, act_issue))
                    unmatched_expected.remove(exp_issue)
                    unmatched_actual.remove(act_issue)
                    break
        
        type_match_score = len(matched_issues) / len(expected_issues) if expected_issues else 0
        
        # Evaluate description quality for matched issues
        description_scores = []
        for exp_issue, act_issue in matched_issues:
            exp_desc = exp_issue.get("description", "")
            act_desc = act_issue.get("description", "")
            
            exp_keywords = extract_keywords(exp_desc)
            act_keywords = extract_keywords(act_desc)
            
            if exp_keywords:
                keyword_overlap = len(exp_keywords & act_keywords) / len(exp_keywords)
            else:
                keyword_overlap = 1.0 if not act_keywords else 0.5
            
            description_scores.append(keyword_overlap)
        
        desc_quality_score = sum(description_scores) / len(description_scores) if description_scores else 0
        false_positive_penalty = len(unmatched_actual) * 0.1
        
        final_score = (0.6 * type_match_score + 0.3 * desc_quality_score + 0.1 * max(0, 1 - false_positive_penalty))
        
        comment_parts = [f"Detected {len(matched_issues)}/{len(expected_issues)} expected issues", f"Description quality: {desc_quality_score:.2%}"]
        if unmatched_actual:
            comment_parts.append(f"{len(unmatched_actual)} unexpected issues")
        
        return {"key": "issue_detection_comprehensive", "score": final_score, "comment": ". ".join(comment_parts)}
        
    except Exception as e:
        return {"key": "issue_detection_comprehensive", "score": 0.0, "comment": f"Error in evaluation: {str(e)}"}


@run_evaluator
def evaluate_severity_assessment(run: Run, example: Example) -> Dict[str, Any]:
    """Evaluate severity assessment accuracy with tolerance for minor differences."""
    try:
        actual = run.outputs or {}
        expected = example.outputs or {}
        
        actual_issues = actual.get("issues", [])
        expected_issues = expected.get("issues", [])
        
        if not expected_issues:
            return {"key": "severity_assessment", "score": 1.0 if not actual_issues else 0.5, "comment": "No issues to assess severity"}
        
        severity_levels = {"critical": 4, "high": 4, "error": 3, "medium": 3, "warning": 2, "low": 2, "info": 1}
        
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
        
        severity_scores = []
        
        for exp_issue in expected_issues:
            exp_type = match_issue_type(exp_issue.get("type", ""), exp_issue.get("description", ""))
            exp_severity = normalize_severity(exp_issue.get("severity", "info"))
            
            best_match = None
            for act_issue in actual_issues:
                act_type = match_issue_type(act_issue.get("type", ""), act_issue.get("description", ""))
                if exp_type == act_type:
                    best_match = act_issue
                    break
            
            if best_match:
                act_severity = normalize_severity(best_match.get("severity", "info"))
                exp_level = severity_levels.get(exp_severity, 1)
                act_level = severity_levels.get(act_severity, 1)
                
                if exp_level == act_level:
                    severity_scores.append(1.0)
                elif abs(exp_level - act_level) == 1:
                    severity_scores.append(0.7)
                else:
                    severity_scores.append(0.3)
            else:
                severity_scores.append(0.0)
        
        final_score = sum(severity_scores) / len(severity_scores) if severity_scores else 0
        
        if final_score >= 0.9:
            comment = "Excellent severity assessment"
        elif final_score >= 0.7:
            comment = "Good severity assessment with minor differences"
        elif final_score >= 0.5:
            comment = "Moderate severity assessment accuracy"
        else:
            comment = "Poor severity assessment accuracy"
        
        return {"key": "severity_assessment", "score": final_score, "comment": f"{comment} (score: {final_score:.2%})"}
        
    except Exception as e:
        return {"key": "severity_assessment", "score": 0.0, "comment": f"Error in evaluation: {str(e)}"}


@run_evaluator 
def evaluate_explanations_quality(run: Run, example: Example) -> Dict[str, Any]:
    """Evaluate the quality and relevance of explanations."""
    try:
        actual = run.outputs or {}
        expected = example.outputs or {}
        
        actual_explanations = actual.get("explanations", [])
        expected_explanations = expected.get("explanations", [])
        
        if not expected_explanations:
            return {"key": "explanations_quality", "score": 1.0 if not actual_explanations else 0.8, "comment": "No explanations expected"}
        
        if not actual_explanations:
            return {"key": "explanations_quality", "score": 0.0, "comment": f"No explanations provided, but {len(expected_explanations)} expected"}
        
        quality_scores = []
        coverage_score = min(1.0, len(actual_explanations) / len(expected_explanations))
        quality_scores.append(("coverage", coverage_score))
        
        for i, exp_explanation in enumerate(expected_explanations):
            if i < len(actual_explanations):
                act_explanation = actual_explanations[i]
                
                if len(act_explanation) < 20:
                    quality_scores.append(("length", 0.3))
                elif len(act_explanation) < 50:
                    quality_scores.append(("length", 0.7))
                else:
                    quality_scores.append(("length", 1.0))
                
                exp_keywords = extract_keywords(exp_explanation)
                act_keywords = extract_keywords(act_explanation)
                
                if exp_keywords:
                    concept_overlap = len(exp_keywords & act_keywords) / len(exp_keywords)
                    quality_scores.append(("concepts", concept_overlap))
                
                technical_terms = {"system", "error", "service", "connection", "memory", "disk", 
                                 "authentication", "configuration", "network", "process"}
                has_technical = any(term in act_explanation.lower() for term in technical_terms)
                quality_scores.append(("technical", 1.0 if has_technical else 0.5))
        
        final_score = sum(score for _, score in quality_scores) / len(quality_scores) if quality_scores else 0
        
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
        
        return {"key": "explanations_quality", "score": final_score, "comment": ". ".join(feedback_parts) if feedback_parts else "Explanation quality assessed"}
        
    except Exception as e:
        return {"key": "explanations_quality", "score": 0.0, "comment": f"Error in evaluation: {str(e)}"}


@run_evaluator
def evaluate_suggestions_relevance(run: Run, example: Example) -> Dict[str, Any]:
    """Evaluate the relevance and quality of suggestions."""
    try:
        actual = run.outputs or {}
        expected = example.outputs or {}
        
        actual_suggestions = actual.get("suggestions", [])
        expected_suggestions = expected.get("suggestions", [])
        actual_issues = actual.get("issues", [])
        
        if not expected_suggestions:
            return {"key": "suggestions_relevance", "score": 1.0 if not actual_suggestions else 0.8, "comment": "No suggestions expected"}
        
        if not actual_suggestions:
            return {"key": "suggestions_relevance", "score": 0.0, "comment": f"No suggestions provided, but {len(expected_suggestions)} expected"}
        
        quality_metrics = []
        
        coverage_ratio = min(1.0, len(actual_suggestions) / len(expected_suggestions))
        quality_metrics.append(("coverage", coverage_ratio))
        
        action_verbs = {"check", "verify", "ensure", "review", "monitor", "increase", "restart", 
                       "configure", "update", "fix", "repair", "investigate", "analyze", "test"}
        
        actionable_count = sum(1 for suggestion in actual_suggestions if any(verb in suggestion.lower() for verb in action_verbs))
        actionability_score = actionable_count / len(actual_suggestions) if actual_suggestions else 0
        quality_metrics.append(("actionability", actionability_score))
        
        specific_terms = {"service", "network", "configuration", "log", "system", "memory", 
                         "disk", "port", "firewall", "authentication", "database", "file"}
        
        specific_count = sum(1 for suggestion in actual_suggestions if any(term in suggestion.lower() for term in specific_terms))
        specificity_score = specific_count / len(actual_suggestions) if actual_suggestions else 0
        quality_metrics.append(("specificity", specificity_score))
        
        if actual_issues:
            issue_types = [match_issue_type(issue.get("type", ""), issue.get("description", "")) for issue in actual_issues]
            
            relevant_count = 0
            for suggestion in actual_suggestions:
                suggestion_lower = suggestion.lower()
                for issue_type in issue_types:
                    if any(keyword in suggestion_lower for keyword in ISSUE_TYPE_GROUPS.get(issue_type, {}).get("keywords", [])):
                        relevant_count += 1
                        break
            
            relevance_score = relevant_count / len(actual_suggestions) if actual_suggestions else 0
            quality_metrics.append(("relevance", relevance_score))
        
        final_score = sum(score for _, score in quality_metrics) / len(quality_metrics)
        
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
        
        return {"key": "suggestions_relevance", "score": final_score, "comment": ". ".join(feedback_parts)}
        
    except Exception as e:
        return {"key": "suggestions_relevance", "score": 0.0, "comment": f"Error in evaluation: {str(e)}"}


@run_evaluator
def evaluate_documentation_references(run: Run, example: Example) -> Dict[str, Any]:
    """Evaluate the quality and relevance of documentation references."""
    try:
        actual = run.outputs or {}
        expected = example.outputs or {}
        
        actual_docs = actual.get("documentation_references", [])
        expected_docs = expected.get("documentation_references", [])
        actual_issues = actual.get("issues", [])
        
        if not expected_docs:
            score = 1.0 if not actual_docs else 0.9
            return {"key": "documentation_references", "score": score, "comment": "No documentation references expected"}
        
        if not actual_docs:
            has_critical = any(issue.get("severity") in ["critical", "error"] for issue in actual_issues)
            score = 0.0 if has_critical else 0.3
            return {"key": "documentation_references", "score": score, "comment": f"No documentation provided{', but critical issues found' if has_critical else ''}"}
        
        quality_scores = []
        
        for doc in actual_docs:
            if isinstance(doc, dict):
                has_title = bool(doc.get("title", "").strip())
                has_url = bool(doc.get("url", "").strip())
                has_relevance = bool(doc.get("relevance", "").strip())
                
                structure_score = (0.4 * (1.0 if has_title else 0) + 0.4 * (1.0 if has_url else 0) + 0.2 * (1.0 if has_relevance else 0))
                quality_scores.append(structure_score)
                
                if has_url:
                    url = doc["url"]
                    if url.startswith(("http://", "https://", "/")):
                        quality_scores.append(1.0)
                    else:
                        quality_scores.append(0.5)
            else:
                quality_scores.append(0.0)
        
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
        
        valid_docs = sum(1 for doc in actual_docs if isinstance(doc, dict) and doc.get("url"))
        comment = f"{valid_docs}/{len(actual_docs)} valid documentation references"
        
        if final_score >= 0.8:
            comment += " - Well-structured and relevant"
        elif final_score >= 0.6:
            comment += " - Adequate documentation"
        else:
            comment += " - Needs improvement"
        
        return {"key": "documentation_references", "score": final_score, "comment": comment}
        
    except Exception as e:
        return {"key": "documentation_references", "score": 0.0, "comment": f"Error in evaluation: {str(e)}"}


@run_evaluator
def evaluate_diagnostic_commands_quality(run: Run, example: Example) -> Dict[str, Any]:
    """Evaluate the quality and appropriateness of diagnostic commands."""
    try:
        actual = run.outputs or {}
        expected = example.outputs or {}
        
        actual_commands = actual.get("diagnostic_commands", [])
        expected_commands = expected.get("diagnostic_commands", [])
        actual_issues = actual.get("issues", [])
        
        if not expected_commands:
            score = 1.0 if not actual_commands else 0.9
            return {"key": "diagnostic_commands_quality", "score": score, "comment": "No diagnostic commands expected"}
        
        if not actual_commands:
            score = 0.0 if actual_issues else 0.5
            return {"key": "diagnostic_commands_quality", "score": score, "comment": f"No commands provided{', but issues were found' if actual_issues else ''}"}
        
        quality_metrics = []
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
                valid_commands.append({"command": cmd, "description": ""})
                quality_metrics.append(("structure", 0.6))
        
        diagnostic_keywords = {
            "system": ["ps", "top", "uptime", "systemctl", "service", "dmesg"],
            "network": ["netstat", "ss", "ping", "traceroute", "nslookup", "tcpdump", "ifconfig", "ip"],
            "disk": ["df", "du", "iostat", "fdisk", "mount", "lsblk"],
            "memory": ["free", "vmstat", "pmap", "smem"],
            "logs": ["tail", "grep", "journalctl", "cat", "less", "awk"],
            "process": ["ps", "pgrep", "lsof", "strace"],
            "performance": ["iotop", "htop", "sar", "mpstat"]
        }
        
        all_diagnostic_keywords = set()
        for keywords in diagnostic_keywords.values():
            all_diagnostic_keywords.update(keywords)
        
        relevant_commands = sum(1 for cmd in valid_commands if any(keyword in cmd.get("command", "").lower() for keyword in all_diagnostic_keywords))
        relevance_score = relevant_commands / len(valid_commands) if valid_commands else 0
        quality_metrics.append(("relevance", relevance_score))
        
        coverage_score = min(1.0, len(valid_commands) / max(1, len(expected_commands)))
        quality_metrics.append(("coverage", coverage_score))
        
        if actual_issues:
            issue_types = [match_issue_type(issue.get("type", ""), issue.get("description", "")) for issue in actual_issues]
            
            appropriate_commands = 0
            for cmd in valid_commands:
                command_text = cmd.get("command", "").lower()
                description = cmd.get("description", "").lower()
                
                for issue_type in issue_types:
                    if issue_type in diagnostic_keywords:
                        if any(keyword in command_text for keyword in diagnostic_keywords[issue_type]):
                            appropriate_commands += 1
                            break
            
            appropriateness_score = appropriate_commands / len(valid_commands) if valid_commands else 0
            quality_metrics.append(("appropriateness", appropriateness_score))
        
        final_score = sum(score for _, score in quality_metrics) / len(quality_metrics) if quality_metrics else 0
        
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
        
        return {"key": "diagnostic_commands_quality", "score": final_score, "comment": ". ".join(feedback_parts)}
        
    except Exception as e:
        return {"key": "diagnostic_commands_quality", "score": 0.0, "comment": f"Error in evaluation: {str(e)}"}


@run_evaluator
def evaluate_overall_completeness(run: Run, example: Example) -> Dict[str, Any]:
    """Evaluate the overall completeness and structure of the response."""
    try:
        actual = run.outputs or {}
        expected = example.outputs or {}
        
        required_fields = ["issues", "explanations", "suggestions", "documentation_references", "diagnostic_commands"]
        
        present_fields = [field for field in required_fields if field in actual]
        completeness_score = len(present_fields) / len(required_fields)
        
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
        
        consistency_score = 1.0
        issues = actual.get("issues", [])
        
        if issues:
            if not actual.get("explanations"):
                consistency_score -= 0.2
            if not actual.get("suggestions"):
                consistency_score -= 0.2
            
            has_critical = any(issue.get("severity") in ["critical", "error"] for issue in issues)
            if has_critical:
                if not actual.get("documentation_references"):
                    consistency_score -= 0.1
                if not actual.get("diagnostic_commands"):
                    consistency_score -= 0.1
        else:
            if len(actual.get("explanations", [])) > 1:
                consistency_score -= 0.1
            if len(actual.get("suggestions", [])) > 1:
                consistency_score -= 0.1
        
        consistency_score = max(0, consistency_score)
        
        final_score = (0.4 * completeness_score + 0.3 * population_score + 0.3 * consistency_score)
        
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
        
        return {"key": "overall_completeness", "score": final_score, "comment": ". ".join(feedback_parts)}
        
    except Exception as e:
        return {"key": "overall_completeness", "score": 0.0, "comment": f"Error in evaluation: {str(e)}"}


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
        
        actual_types = Counter(match_issue_type(issue.get("type", ""), issue.get("description", "")) for issue in actual_issues)
        expected_types = Counter(match_issue_type(issue.get("type", ""), issue.get("description", "")) for issue in expected_issues)
        
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
    
    for run in runs:
        if run.error or not hasattr(run, 'feedback'):
            continue
            
        for feedback in run.feedback:
            if hasattr(feedback, 'key') and hasattr(feedback, 'score'):
                metric_scores[feedback.key].append(feedback.score)
    
    metric_averages = {}
    for metric, scores in metric_scores.items():
        if scores:
            metric_averages[metric] = sum(scores) / len(scores)
    
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
    
    breakdown = []
    for metric, avg in sorted(metric_averages.items()):
        breakdown.append(f"{metric}: {avg:.2%}")
    
    return {
        "key": "response_quality_overall",
        "score": final_score,
        "comment": f"Overall quality: {final_score:.2%}. " + "; ".join(breakdown[:3]) + "..."
    }


def transform_output_fields(analysis_result: Dict[str, Any]) -> Dict[str, Any]:
    """Transform agent output fields to match expected evaluation format."""
    if not analysis_result:
        return {}
    
    transformed = analysis_result.copy()
    
    if "root_cause" in transformed and "explanations" not in transformed:
        root_cause = transformed.get("root_cause", "")
        if root_cause and isinstance(root_cause, str):
            transformed["explanations"] = [root_cause]
        else:
            transformed["explanations"] = []
    
    if "recommendations" in transformed and "suggestions" not in transformed:
        transformed["suggestions"] = transformed.get("recommendations", [])
    
    return transformed


# ==================== Parallel Agent Runner ====================

class ParallelEvaluationRunner:
    """Manages parallel evaluation of log analyzer agent."""
    
    def __init__(self, config: Configuration, batch_size: int = 10, max_retries: int = 3):
        self.config = config
        self.batch_size = batch_size
        self.max_retries = max_retries
        self.semaphore = asyncio.Semaphore(batch_size)
        self.progress_lock = asyncio.Lock()
        self.completed = 0
        self.total = 0
        self.errors = []
        
    async def run_single_evaluation(self, example_id: str, inputs: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """Run agent on a single input with retry logic and rate limiting."""
        async with self.semaphore:
            for attempt in range(self.max_retries):
                try:
                    # Add small delay to prevent rate limiting
                    await asyncio.sleep(0.5 * (attempt + 1))
                    
                    # Initialize state
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
                    
                    # Create runnable config
                    runnable_config = {
                        "configurable": {
                            "model": self.config.primary_model.get_model_string(),
                            "orchestration_model": self.config.orchestration_model.get_model_string(),
                            "max_analysis_iterations": self.config.max_analysis_iterations,
                            "max_tool_calls": self.config.max_tool_calls,
                        }
                    }
                    
                    # Run the agent
                    result = await graph.ainvoke(initial_state, config=runnable_config)
                    
                    # Extract and transform analysis result
                    analysis_result = result.get("analysis_result", {})
                    
                    # Handle different output formats
                    if not analysis_result:
                        messages = result.get("messages", [])
                        for message in reversed(messages):
                            if hasattr(message, "tool_calls") and message.tool_calls:
                                for tool_call in message.tool_calls:
                                    if tool_call.get("name") == "submit_analysis":
                                        analysis_result = tool_call.get("args", {})
                                        break
                            if analysis_result:
                                break
                    
                    # Transform output fields
                    analysis_result = transform_output_fields(analysis_result)
                    
                    # Update progress
                    async with self.progress_lock:
                        self.completed += 1
                        print(f"\rProgress: {self.completed}/{self.total} ({self.completed/self.total*100:.1f}%)", end="", flush=True)
                    
                    # Return successful result
                    return example_id, {
                        "issues": analysis_result.get("issues", []),
                        "explanations": analysis_result.get("explanations", []),
                        "suggestions": analysis_result.get("suggestions", []),
                        "documentation_references": analysis_result.get("documentation_references", []),
                        "diagnostic_commands": analysis_result.get("diagnostic_commands", [])
                    }
                    
                except Exception as e:
                    if attempt == self.max_retries - 1:
                        # Final attempt failed
                        async with self.progress_lock:
                            self.completed += 1
                            self.errors.append((example_id, str(e)))
                            print(f"\rProgress: {self.completed}/{self.total} ({self.completed/self.total*100:.1f}%) - Error on {example_id}", end="", flush=True)
                        
                        return example_id, {
                            "issues": [{"type": "execution_error", "description": str(e), "severity": "critical"}],
                            "explanations": [f"Agent execution failed after {self.max_retries} attempts: {e}"],
                            "suggestions": ["Check agent configuration and retry"],
                            "documentation_references": [],
                            "diagnostic_commands": []
                        }
                    else:
                        # Retry with exponential backoff
                        await asyncio.sleep(2 ** attempt)
    
    async def evaluate_dataset(self, dataset_name: str, max_examples: Optional[int] = None) -> Dict[str, Any]:
        """Evaluate all examples in the dataset in parallel."""
        print(f"\nLoading dataset: {dataset_name}")
        
        # Load dataset
        client = Client()
        examples = []
        
        for example in client.list_examples(dataset_name=dataset_name):
            examples.append(example)
            if max_examples and len(examples) >= max_examples:
                break
        
        self.total = len(examples)
        print(f"Loaded {self.total} examples from dataset")
        
        if self.total == 0:
            return {"error": "No examples found in dataset"}
        
        # Create evaluation tasks
        print(f"\nStarting parallel evaluation with batch size: {self.batch_size}")
        start_time = time.time()
        
        tasks = [
            self.run_single_evaluation(str(example.id), example.inputs)
            for example in examples
        ]
        
        # Run all evaluations in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        evaluation_results = {}
        for result in results:
            if isinstance(result, Exception):
                self.errors.append(("unknown", str(result)))
            else:
                example_id, output = result
                evaluation_results[example_id] = output
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"\n\nCompleted {self.total} evaluations in {duration:.1f} seconds")
        print(f"Average time per evaluation: {duration/self.total:.2f} seconds")
        print(f"Errors encountered: {len(self.errors)}")
        
        return {
            "results": evaluation_results,
            "examples": examples,
            "duration": duration,
            "errors": self.errors
        }


# ==================== Main Parallel Evaluation Function ====================

async def run_parallel_evaluation(
    dataset_name: str = "log-analyzer-evaluation",
    max_examples: Optional[int] = None,
    experiment_prefix: Optional[str] = None,
    primary_model: Optional[str] = None,
    orchestration_model: Optional[str] = None,
    batch_size: int = 10,
):
    """Run comprehensive evaluation on the LangSmith dataset in parallel."""
    
    # Create configuration
    config = Configuration()
    
    # Parse and set models
    if primary_model and ":" in primary_model:
        provider, model_name = primary_model.split(":", 1)
        config.primary_model = ModelConfig(
            provider=provider,
            model_name=model_name,
            temperature=0.0
        )
    
    if orchestration_model and ":" in orchestration_model:
        provider, model_name = orchestration_model.split(":", 1)
        config.orchestration_model = ModelConfig(
            provider=provider,
            model_name=model_name,
            temperature=0.3
        )
    
    print("="*80)
    print("PARALLEL LOG ANALYZER EVALUATION")
    print("="*80)
    print(f"Dataset: {dataset_name}")
    print(f"Primary model: {config.primary_model.get_model_string()}")
    print(f"Orchestration model: {config.orchestration_model.get_model_string()}")
    print(f"Batch size: {batch_size}")
    if max_examples:
        print(f"Max examples: {max_examples}")
    
    # Create parallel runner
    runner = ParallelEvaluationRunner(config, batch_size=batch_size)
    
    # Run evaluations in parallel
    eval_data = await runner.evaluate_dataset(dataset_name, max_examples)
    
    if "error" in eval_data:
        print(f"Error: {eval_data['error']}")
        return
    
    # Now run the evaluators on the results
    print("\nRunning quality evaluators...")
    
    # Create mock runs and examples for evaluation
    runs = []
    examples = eval_data["examples"]
    results = eval_data["results"]
    
    for example in examples:
        example_id = str(example.id)
        if example_id in results:
            # Create a mock Run object
            class MockRun:
                def __init__(self):
                    self.outputs = results[example_id]
                    self.error = None
                    self.feedback = []
                    self.id = example_id
                    
            run = MockRun()
            runs.append(run)
    
    # Run individual evaluators
    evaluator_results = defaultdict(list)
    
    for i, (run, example) in enumerate(zip(runs, examples)):
        # Run each evaluator
        for evaluator in [
            evaluate_issue_detection_comprehensive,
            evaluate_severity_assessment,
            evaluate_explanations_quality,
            evaluate_suggestions_relevance,
            evaluate_documentation_references,
            evaluate_diagnostic_commands_quality,
            evaluate_overall_completeness,
        ]:
            result = evaluator(run, example)
            evaluator_results[result["key"]].append(result["score"])
            # Add feedback to run for summary evaluators
            feedback = type('Feedback', (), {
                'key': result["key"],
                'score': result["score"],
                'comment': result["comment"]
            })()
            run.feedback.append(feedback)
    
    # Run summary evaluators
    f1_summary = precision_recall_f1_summary(runs, examples)
    quality_summary = response_quality_summary(runs, examples)
    
    # Display results
    print("\n" + "="*80)
    print("EVALUATION RESULTS")
    print("="*80)
    
    print(f"\nTotal examples evaluated: {len(examples)}")
    print(f"Successful evaluations: {len(runs)}")
    print(f"Errors encountered: {len(eval_data['errors'])}")
    print(f"Success rate: {(len(runs) / len(examples) * 100):.1f}%")
    print(f"Total duration: {eval_data['duration']:.1f} seconds")
    print(f"Throughput: {len(examples) / eval_data['duration']:.1f} evaluations/second")
    
    # Display individual metrics
    print("\nIndividual Metric Scores:")
    print("-" * 60)
    for metric_name, scores in sorted(evaluator_results.items()):
        if scores:
            avg_score = sum(scores) / len(scores)
            min_score = min(scores)
            max_score = max(scores)
            print(f"{metric_name:.<40} {avg_score:.2%} (min: {min_score:.2%}, max: {max_score:.2%})")
    
    # Display summary metrics
    print("\nSummary Metrics:")
    print("-" * 60)
    print(f"{f1_summary['key']:.<40} {f1_summary['score']:.2%}")
    print(f"  {f1_summary['comment']}")
    print(f"{quality_summary['key']:.<40} {quality_summary['score']:.2%}")
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = Path(f"evaluation_results_parallel_{timestamp}.json")
    
    detailed_results = {
        "dataset": dataset_name,
        "experiment_prefix": experiment_prefix or f"parallel-eval-{timestamp}",
        "timestamp": timestamp,
        "batch_size": batch_size,
        "total_examples": len(examples),
        "successful_evaluations": len(runs),
        "errors": eval_data['errors'],
        "duration_seconds": eval_data['duration'],
        "throughput_per_second": len(examples) / eval_data['duration'],
        "models": {
            "primary": config.primary_model.get_model_string(),
            "orchestration": config.orchestration_model.get_model_string()
        },
        "metrics": {
            name: {
                "average": sum(scores)/len(scores) if scores else 0,
                "min": min(scores) if scores else 0,
                "max": max(scores) if scores else 0,
                "count": len(scores)
            }
            for name, scores in evaluator_results.items()
        },
        "summary_metrics": {
            f1_summary['key']: {
                "score": f1_summary['score'],
                "comment": f1_summary['comment']
            },
            quality_summary['key']: {
                "score": quality_summary['score'],
                "comment": quality_summary['comment']
            }
        }
    }
    
    with open(results_file, 'w') as f:
        json.dump(detailed_results, f, indent=2)
    
    print(f"\nDetailed results saved to: {results_file}")
    print("\nParallel evaluation complete! 🚀")
    
    # Display errors if any
    if eval_data['errors']:
        print("\nErrors encountered during evaluation:")
        for example_id, error in eval_data['errors'][:5]:  # Show first 5 errors
            print(f"  - {example_id}: {error}")
        if len(eval_data['errors']) > 5:
            print(f"  ... and {len(eval_data['errors']) - 5} more errors")


# ==================== CLI Interface ====================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Run parallel evaluation for log analyzer agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with default settings (batch size 10)
  %(prog)s
  
  # Run with larger batch size for faster evaluation
  %(prog)s --batch-size 20
  
  # Evaluate specific number of examples
  %(prog)s --max-examples 100 --batch-size 25
  
  # Use custom models
  %(prog)s --primary-model gemini:gemini-2.0-flash-exp --orchestration-model groq:deepseek-r1-distill-llama-70b
        """
    )
    
    parser.add_argument("--dataset", default="log-analyzer-evaluation", help="Dataset name in LangSmith")
    parser.add_argument("--max-examples", type=int, help="Maximum number of examples to evaluate")
    parser.add_argument("--experiment-prefix", help="Custom experiment prefix")
    parser.add_argument("--batch-size", type=int, default=10, help="Number of evaluations to run in parallel (default: 10)")
    parser.add_argument("--primary-model", help="Primary model in provider:model format")
    parser.add_argument("--orchestration-model", help="Orchestration model in provider:model format")
    
    args = parser.parse_args()
    
    # Check if running in asyncio environment
    try:
        asyncio.run(run_parallel_evaluation(
            dataset_name=args.dataset,
            max_examples=args.max_examples,
            experiment_prefix=args.experiment_prefix,
            primary_model=args.primary_model,
            orchestration_model=args.orchestration_model,
            batch_size=args.batch_size
        ))
    except KeyboardInterrupt:
        print("\n\nEvaluation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nError during evaluation: {e}")
        sys.exit(1)