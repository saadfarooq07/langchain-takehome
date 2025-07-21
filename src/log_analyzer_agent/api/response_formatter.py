"""Response formatter for consistent UI output."""

import re
from typing import Dict, Any, List, Union


def parse_text_analysis(text: str) -> Dict[str, Any]:
    """Parse text-based analysis output into structured format."""
    
    result = {
        "executive_summary": {
            "overview": "",
            "critical_issues": []
        },
        "issues": [],
        "explanations": [],
        "suggestions": [],
        "diagnostic_commands": []
    }
    
    # Split into sections
    sections = re.split(r'\n(?=(?:Issues Found|Explanations|Recommendations|Diagnostic Commands|Executive Summary))', text)
    
    for section in sections:
        section = section.strip()
        if not section:
            continue
            
        if section.startswith("Issues Found"):
            # Parse issues
            lines = section.split('\n')[1:]  # Skip header
            current_issue = None
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                # Check if it's a severity line (e.g., "WARNING", "ERROR", "CRITICAL")
                severity_match = re.match(r'^(CRITICAL|HIGH|MEDIUM|LOW|WARNING|ERROR|INFO)\s*$', line, re.IGNORECASE)
                if severity_match:
                    # Start a new issue
                    if current_issue and current_issue.get("description"):
                        result["issues"].append(current_issue)
                    current_issue = {
                        "severity": severity_match.group(1).lower(),
                        "type": "general",
                        "description": "",
                        "root_cause": ""
                    }
                elif current_issue is not None:
                    # Add to current issue description
                    if current_issue["description"]:
                        current_issue["description"] += " "
                    current_issue["description"] += line
                else:
                    # No severity found, treat as general issue
                    result["issues"].append({
                        "severity": "medium",
                        "type": "general",
                        "description": line,
                        "root_cause": ""
                    })
            
            # Add last issue if exists
            if current_issue and current_issue.get("description"):
                result["issues"].append(current_issue)
                
        elif section.startswith("Explanations"):
            # Parse explanations
            lines = section.split('\n')[1:]  # Skip header
            current_explanation = ""
            
            for line in lines:
                line = line.strip()
                if not line:
                    if current_explanation:
                        result["explanations"].append({
                            "issue": "General",
                            "explanation": current_explanation
                        })
                        current_explanation = ""
                else:
                    if current_explanation:
                        current_explanation += " "
                    current_explanation += line
            
            # Add last explanation
            if current_explanation:
                result["explanations"].append({
                    "issue": "General",
                    "explanation": current_explanation
                })
                
        elif section.startswith("Recommendations") or section.startswith("Suggestions"):
            # Parse recommendations
            lines = section.split('\n')[1:]  # Skip header
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                # Remove bullet points or numbers
                line = re.sub(r'^[\d\-\*\•]\s*', '', line)
                if line:
                    result["suggestions"].append(line)
                    
        elif section.startswith("Diagnostic Commands"):
            # Parse diagnostic commands
            lines = section.split('\n')[1:]  # Skip header
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                # Try to parse command format
                # Format 1: "command - description"
                if ' - ' in line:
                    parts = line.split(' - ', 1)
                    result["diagnostic_commands"].append({
                        "command": parts[0].strip(),
                        "description": parts[1].strip()
                    })
                # Format 2: Just the command
                else:
                    result["diagnostic_commands"].append({
                        "command": line,
                        "description": "Run this command for diagnostics"
                    })
    
    # Generate executive summary if not present
    if not result["executive_summary"]["overview"] and result["issues"]:
        issue_count = len(result["issues"])
        critical_count = sum(1 for i in result["issues"] if i["severity"] in ["critical", "high"])
        
        if critical_count > 0:
            result["executive_summary"]["overview"] = f"Found {issue_count} issues, including {critical_count} critical/high severity issues that require immediate attention."
        else:
            result["executive_summary"]["overview"] = f"Found {issue_count} issues. No critical issues detected."
        
        # Add critical issues to summary
        result["executive_summary"]["critical_issues"] = [
            i["description"] for i in result["issues"] 
            if i["severity"] in ["critical", "high"]
        ][:3]
    
    return result


def format_analysis_result(analysis: Union[Dict[str, Any], str]) -> Dict[str, Any]:
    """Format any analysis result into the expected UI structure."""
    
    # If it's a string, parse it
    if isinstance(analysis, str):
        return parse_text_analysis(analysis)
    
    # If it's already a dict, ensure it has the right structure
    if isinstance(analysis, dict):
        # Check if it's already properly formatted
        if all(key in analysis for key in ["issues", "executive_summary"]):
            return ensure_proper_format(analysis)
        
        # Check if it has a nested analysis field
        if "analysis" in analysis:
            if isinstance(analysis["analysis"], str):
                return parse_text_analysis(analysis["analysis"])
            else:
                return format_analysis_result(analysis["analysis"])
        
        # Try to extract from other common structures
        result = {
            "executive_summary": {
                "overview": analysis.get("summary", "Analysis completed"),
                "critical_issues": []
            },
            "issues": [],
            "explanations": [],
            "suggestions": [],
            "diagnostic_commands": []
        }
        
        # Extract issues
        if "issues" in analysis:
            result["issues"] = ensure_issues_format(analysis["issues"])
        elif "issues_found" in analysis:
            result["issues"] = ensure_issues_format(analysis["issues_found"])
        
        # Extract other fields
        for field in ["explanations", "suggestions", "recommendations", "diagnostic_commands"]:
            if field in analysis:
                if field == "recommendations" and "suggestions" not in analysis:
                    result["suggestions"] = ensure_list_format(analysis[field])
                else:
                    result[field.replace("recommendations", "suggestions")] = ensure_list_format(analysis[field])
        
        return result
    
    # Fallback
    return {
        "executive_summary": {
            "overview": "Analysis completed",
            "critical_issues": []
        },
        "issues": [],
        "explanations": [],
        "suggestions": [],
        "diagnostic_commands": []
    }


def ensure_issues_format(issues: Any) -> List[Dict[str, Any]]:
    """Ensure issues are in the correct format."""
    if not isinstance(issues, list):
        return []
    
    formatted_issues = []
    for issue in issues:
        if isinstance(issue, dict):
            formatted_issues.append({
                "severity": issue.get("severity", "medium"),
                "type": issue.get("type", "general"),
                "description": issue.get("description", issue.get("message", str(issue))),
                "root_cause": issue.get("root_cause", "")
            })
        elif isinstance(issue, str):
            formatted_issues.append({
                "severity": "medium",
                "type": "general",
                "description": issue,
                "root_cause": ""
            })
    
    return formatted_issues


def ensure_list_format(items: Any) -> List[Any]:
    """Ensure items are in list format."""
    if isinstance(items, list):
        return items
    elif isinstance(items, str):
        return [items]
    elif isinstance(items, dict):
        return [f"{k}: {v}" for k, v in items.items()]
    else:
        return []


def ensure_proper_format(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure the analysis dict has all required fields properly formatted."""
    result = {
        "executive_summary": analysis.get("executive_summary", {
            "overview": "Analysis completed",
            "critical_issues": []
        }),
        "issues": ensure_issues_format(analysis.get("issues", [])),
        "explanations": [],
        "suggestions": ensure_list_format(analysis.get("suggestions", [])),
        "diagnostic_commands": []
    }
    
    # Format explanations
    explanations = analysis.get("explanations", [])
    if isinstance(explanations, list):
        formatted_explanations = []
        for exp in explanations:
            if isinstance(exp, dict) and "issue" in exp and "explanation" in exp:
                formatted_explanations.append(exp)
            elif isinstance(exp, str):
                formatted_explanations.append({
                    "issue": "General",
                    "explanation": exp
                })
        result["explanations"] = formatted_explanations
    
    # Format diagnostic commands
    commands = analysis.get("diagnostic_commands", [])
    if isinstance(commands, list):
        formatted_commands = []
        for cmd in commands:
            if isinstance(cmd, dict) and "command" in cmd:
                formatted_commands.append(cmd)
            elif isinstance(cmd, str):
                formatted_commands.append({
                    "command": cmd,
                    "description": "Run this command for diagnostics"
                })
        result["diagnostic_commands"] = formatted_commands
    
    return result