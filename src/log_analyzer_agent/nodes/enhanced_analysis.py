"""Enhanced log analysis node with improved output quality."""

import json
import re
from typing import Any, Dict, Optional, List, cast
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.store.base import BaseStore

from ..configuration import Configuration
from ..state import CoreState
from ..tools import search_documentation, submit_analysis
from ..improved_prompts import (
    enhanced_main_prompt_template,
    specialized_templates,
    ENHANCED_MAIN_PROMPT
)
from ..utils import format_environment_context, preprocess_log, init_model_async
from ..model_pool import pooled_model
from ..validation import LogValidator


def detect_log_type(log_content: str) -> str:
    """Detect the type of log based on content patterns."""
    log_lower = log_content.lower()
    
    # Security patterns
    if any(pattern in log_lower for pattern in [
        "authentication", "unauthorized", "permission denied", "access denied",
        "security", "audit", "login failed", "intrusion", "firewall"
    ]):
        return "security"
    
    # Database patterns
    elif any(pattern in log_lower for pattern in [
        "sql", "query", "database", "mysql", "postgres", "mongodb",
        "deadlock", "transaction", "connection pool", "replication"
    ]):
        return "database"
    
    # Infrastructure patterns
    elif any(pattern in log_lower for pattern in [
        "cpu", "memory", "disk", "network", "kernel", "hardware",
        "systemd", "docker", "kubernetes", "load average"
    ]):
        return "infrastructure"
    
    # Default to application logs
    else:
        return "application"


def structure_analysis_output(raw_analysis: str) -> Dict[str, Any]:
    """Structure the raw analysis output into a well-formatted response."""
    
    # Initialize structured output
    structured = {
        "executive_summary": {
            "overview": "",
            "health_assessment": "unknown",
            "critical_issues": []
        },
        "issues": [],
        "recommendations": [],
        "diagnostic_commands": [],
        "documentation_references": [],
        "pattern_analysis": {
            "recurring_patterns": [],
            "time_correlations": [],
            "insights": []
        }
    }
    
    # Extract executive summary
    exec_match = re.search(r"## Executive Summary\s*\n(.*?)(?=##|\Z)", raw_analysis, re.DOTALL)
    if exec_match:
        summary_text = exec_match.group(1).strip()
        summary_lines = summary_text.split('\n')
        
        for line in summary_lines:
            line = line.strip('- ').strip()
            if line:
                if not structured["executive_summary"]["overview"]:
                    structured["executive_summary"]["overview"] = line
                elif "health" in line.lower() or "status" in line.lower():
                    structured["executive_summary"]["health_assessment"] = line
                elif "critical" in line.lower() or "immediate" in line.lower():
                    structured["executive_summary"]["critical_issues"].append(line)
    
    # Extract detailed issues
    issues_match = re.search(r"## Detailed Issues Analysis\s*\n(.*?)(?=##|\Z)", raw_analysis, re.DOTALL)
    if issues_match:
        issues_text = issues_match.group(1).strip()
        
        # Split by issue markers
        issue_blocks = re.split(r'\n(?=\*\*Issue Type\*\*:|Issue \d+:)', issues_text)
        
        for block in issue_blocks:
            if not block.strip():
                continue
                
            issue = {
                "type": "unknown",
                "severity": "medium",
                "description": "",
                "root_cause": "",
                "impact": "",
                "evidence": []
            }
            
            # Extract issue fields
            type_match = re.search(r"\*\*Issue Type\*\*:\s*\[?(.*?)\]?(?:\n|$)", block)
            if type_match:
                issue["type"] = type_match.group(1).strip()
            
            severity_match = re.search(r"\*\*Severity\*\*:\s*\[?(.*?)\]?(?:\n|$)", block)
            if severity_match:
                issue["severity"] = severity_match.group(1).strip()
            
            desc_match = re.search(r"\*\*Description\*\*:\s*(.*?)(?=\*\*|$)", block, re.DOTALL)
            if desc_match:
                issue["description"] = desc_match.group(1).strip()
            
            root_match = re.search(r"\*\*Root Cause\*\*:\s*(.*?)(?=\*\*|$)", block, re.DOTALL)
            if root_match:
                issue["root_cause"] = root_match.group(1).strip()
            
            impact_match = re.search(r"\*\*Impact\*\*:\s*(.*?)(?=\*\*|$)", block, re.DOTALL)
            if impact_match:
                issue["impact"] = impact_match.group(1).strip()
            
            evidence_match = re.search(r"\*\*Evidence\*\*:\s*(.*?)(?=\*\*|$)", block, re.DOTALL)
            if evidence_match:
                evidence_text = evidence_match.group(1).strip()
                issue["evidence"] = [line.strip('- ').strip() for line in evidence_text.split('\n') if line.strip()]
            
            if issue["description"]:  # Only add if we found actual content
                structured["issues"].append(issue)
    
    # Extract recommendations
    rec_match = re.search(r"## Recommendations\s*\n(.*?)(?=##|\Z)", raw_analysis, re.DOTALL)
    if rec_match:
        rec_text = rec_match.group(1).strip()
        
        current_rec = {}
        for line in rec_text.split('\n'):
            line = line.strip()
            if not line:
                if current_rec:
                    structured["recommendations"].append(current_rec)
                    current_rec = {}
                continue
            
            if line.startswith("**Immediate Actions**:"):
                current_rec["immediate_actions"] = []
            elif line.startswith("**Long-term Solutions**:"):
                current_rec["long_term_solutions"] = []
            elif line.startswith("**Prevention**:"):
                current_rec["prevention"] = []
            elif line.startswith("- ") or line.startswith("* "):
                action = line[2:].strip()
                if "immediate_actions" in current_rec and not current_rec.get("long_term_solutions") and not current_rec.get("prevention"):
                    current_rec["immediate_actions"].append(action)
                elif "long_term_solutions" in current_rec and not current_rec.get("prevention"):
                    current_rec["long_term_solutions"].append(action)
                elif "prevention" in current_rec:
                    current_rec["prevention"].append(action)
        
        if current_rec:
            structured["recommendations"].append(current_rec)
    
    # Extract diagnostic commands
    diag_match = re.search(r"## Diagnostic Commands\s*\n(.*?)(?=##|\Z)", raw_analysis, re.DOTALL)
    if diag_match:
        diag_text = diag_match.group(1).strip()
        
        # Match patterns like `command` - description
        cmd_pattern = r'`([^`]+)`\s*[-–]\s*(.+?)(?=\n|$)'
        for match in re.finditer(cmd_pattern, diag_text):
            structured["diagnostic_commands"].append({
                "command": match.group(1),
                "description": match.group(2).strip()
            })
    
    # Extract documentation references
    doc_match = re.search(r"## Documentation References\s*\n(.*?)(?=##|\Z)", raw_analysis, re.DOTALL)
    if doc_match:
        doc_text = doc_match.group(1).strip()
        
        for line in doc_text.split('\n'):
            line = line.strip('- ').strip()
            if line and ('http' in line or 'www' in line):
                # Try to extract URL and description
                url_match = re.search(r'(https?://[^\s]+)', line)
                if url_match:
                    url = url_match.group(1)
                    desc = line.replace(url, '').strip(' -:')
                    structured["documentation_references"].append({
                        "url": url,
                        "title": desc if desc else "Documentation"
                    })
    
    # Extract pattern analysis
    pattern_match = re.search(r"## Pattern Analysis\s*\n(.*?)(?=##|\Z)", raw_analysis, re.DOTALL)
    if pattern_match:
        pattern_text = pattern_match.group(1).strip()
        
        current_section = None
        for line in pattern_text.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            if "recurring" in line.lower() or "pattern" in line.lower():
                current_section = "recurring_patterns"
            elif "time" in line.lower() or "correlation" in line.lower():
                current_section = "time_correlations"
            elif "insight" in line.lower() or "behavior" in line.lower():
                current_section = "insights"
            elif line.startswith("- ") or line.startswith("* "):
                item = line[2:].strip()
                if current_section and current_section in structured["pattern_analysis"]:
                    structured["pattern_analysis"][current_section].append(item)
    
    return structured


async def enhanced_analyze_logs(
    state: CoreState,
    *,
    config: Optional[RunnableConfig] = None,
    store: BaseStore = None,
) -> Dict[str, Any]:
    """Enhanced log analysis with improved output quality."""
    
    configuration = Configuration.from_runnable_config(config)
    
    # Validate log content
    is_valid, error_msg, sanitized_info = LogValidator.validate_log_content(
        state.log_content
    )
    if not is_valid:
        return {
            "messages": [AIMessage(content=f"Error: {error_msg}")],
            "analysis_result": {
                "error": error_msg,
                "issues": [{
                    "type": "validation_error",
                    "description": error_msg,
                    "severity": "critical"
                }],
                "suggestions": ["Please provide a valid log file"],
                "documentation_references": []
            },
            "needs_user_input": False
        }
    
    # Preprocess log
    processed_log = preprocess_log(state.log_content)
    
    # Detect log type
    log_type = detect_log_type(processed_log)
    
    # Always use the enhanced main template for consistent structured output
    prompt_template = enhanced_main_prompt_template
    
    # Add log type context to environment
    log_type_context = f"\nLog Type Detected: {log_type.upper()} logs\n"
    if log_type == "database":
        log_type_context += "Focus on: connection issues, query performance, deadlocks, replication, and availability.\n"
    elif log_type == "security":
        log_type_context += "Focus on: authentication failures, unauthorized access, security violations, and potential threats.\n"
    elif log_type == "application":
        log_type_context += "Focus on: exceptions, errors, performance issues, and business logic failures.\n"
    
    # Format environment context
    environment_context = ""
    if getattr(state, "environment_details", None):
        environment_context = format_environment_context(state.environment_details)
    
    # Add log type context
    environment_context += log_type_context
    
    # Create prompt
    # Check if template needs log_type
    if "{log_type}" in prompt_template:
        prompt_content = prompt_template.format(
            log_content=processed_log,
            environment_context=environment_context,
            log_type=log_type
        )
    else:
        prompt_content = prompt_template.format(
            log_content=processed_log,
            environment_context=environment_context
        )
    
    # Debug logging
    print(f"[DEBUG] Prompt length: {len(prompt_content)} chars")
    print(f"[DEBUG] Using template for: {log_type}")
    
    # Use pooled model without tools first to get the analysis
    async with pooled_model(config) as raw_model:
        # Get analysis without tools
        messages = [HumanMessage(content=prompt_content)]
        response = cast(AIMessage, await raw_model.ainvoke(messages))
    
    # Debug logging
    print(f"[DEBUG] Response content: {response.content[:200] if response.content else 'None'}")
    print(f"[DEBUG] Tool calls: {len(response.tool_calls) if response.tool_calls else 0}")
    if response.tool_calls:
        for tc in response.tool_calls:
            print(f"[DEBUG] Tool call: {tc['name']} with args keys: {list(tc['args'].keys())}")
    
    # Structure the output
    if response.content:
        structured_analysis = structure_analysis_output(response.content)
    else:
        structured_analysis = {
            "error": "No analysis generated",
            "issues": [],
            "suggestions": []
        }
    
    # Check for tool calls
    analysis_result = None
    if response.tool_calls:
        for tool_call in response.tool_calls:
            if tool_call["name"] == "submit_analysis":
                # Merge tool call results with structured analysis
                tool_result = tool_call["args"]
                
                # Merge issues
                if "issues" in tool_result:
                    for issue in tool_result["issues"]:
                        # Check if issue already exists
                        exists = any(
                            i["description"] == issue.get("description", "")
                            for i in structured_analysis["issues"]
                        )
                        if not exists:
                            structured_analysis["issues"].append(issue)
                
                # Merge other fields
                for key in ["suggestions", "documentation_references", "diagnostic_commands"]:
                    if key in tool_result:
                        if key not in structured_analysis:
                            structured_analysis[key] = []
                        structured_analysis[key].extend(tool_result[key])
    
    # Ensure we have the required structure
    if "issues" not in structured_analysis:
        structured_analysis["issues"] = []
    if "suggestions" not in structured_analysis:
        structured_analysis["suggestions"] = []
    if "documentation_references" not in structured_analysis:
        structured_analysis["documentation_references"] = []
    if "diagnostic_commands" not in structured_analysis:
        structured_analysis["diagnostic_commands"] = []
    
    # Convert recommendations to suggestions if needed
    if "recommendations" in structured_analysis and structured_analysis["recommendations"]:
        for rec in structured_analysis["recommendations"]:
            if "immediate_actions" in rec:
                structured_analysis["suggestions"].extend(rec["immediate_actions"])
            if "long_term_solutions" in rec:
                structured_analysis["suggestions"].extend(rec["long_term_solutions"])
    
    # Create final response
    return {
        "messages": [response],
        "analysis_result": structured_analysis,
        "needs_user_input": False,
        "log_type_detected": log_type
    }