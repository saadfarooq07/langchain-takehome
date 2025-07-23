#!/usr/bin/env python3
"""Check for common LangGraph pitfalls in the codebase."""

import os
import re
from pathlib import Path
from typing import List, Tuple, Dict, Set
from dataclasses import dataclass


@dataclass
class Issue:
    file_path: str
    line_number: int
    issue_type: str
    description: str
    code_snippet: str
    severity: str  # "critical", "warning", "info"


def find_python_files(directory: str) -> List[Path]:
    """Find all Python files in the project."""
    return list(Path(directory).rglob("*.py"))


def check_side_effects_outside_nodes(file_path: Path) -> List[Issue]:
    """Check for side effects that should be encapsulated in nodes/tasks."""
    issues = []
    
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    # Patterns for side effects
    side_effect_patterns = [
        (r'with\s+open\s*\(.*[\'"]w[\'"]', "File write operation"),
        (r'\.write\s*\(', "Write operation"),
        (r'\.save\s*\(', "Save operation"),
        (r'requests\.(get|post|put|delete)\s*\(', "HTTP request"),
        (r'smtp\.send', "Email sending"),
        (r'subprocess\.(run|call|Popen)', "Subprocess execution"),
        (r'os\.(remove|unlink|rmdir)', "File deletion"),
        (r'shutil\.(copy|move|rmtree)', "File system operation"),
    ]
    
    # Check if we're inside a node/task function
    in_node = False
    node_patterns = [
        r'async\s+def\s+\w+_node\s*\(',
        r'def\s+\w+_node\s*\(',
        r'@node',
        r'@task',
        r'async\s+def\s+(analyze_logs|validate_analysis|handle_user_input|tools)',
    ]
    
    for i, line in enumerate(lines):
        # Check if we're entering a node
        for pattern in node_patterns:
            if re.search(pattern, line):
                in_node = True
                break
        
        # Check if we're exiting a function (rough heuristic)
        if in_node and re.match(r'^(def|class|async\s+def)', line):
            in_node = False
        
        # Look for side effects outside nodes
        if not in_node:
            for pattern, desc in side_effect_patterns:
                if re.search(pattern, line):
                    # Skip if it's in a test file
                    if 'test' in str(file_path):
                        continue
                        
                    issues.append(Issue(
                        file_path=str(file_path),
                        line_number=i + 1,
                        issue_type="side_effect_outside_node",
                        description=f"{desc} outside of node/task - may execute multiple times on resume",
                        code_snippet=line.strip(),
                        severity="critical"
                    ))
    
    return issues


def check_non_deterministic_operations(file_path: Path) -> List[Issue]:
    """Check for non-deterministic operations that should be in tasks."""
    issues = []
    
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    # Patterns for non-deterministic operations
    non_det_patterns = [
        (r'random\.\w+\s*\(', "Random number generation"),
        (r'uuid\.uuid[14]\s*\(', "UUID generation"),
        (r'time\.time\s*\(', "Current time access"),
        (r'datetime\.now\s*\(', "Current datetime access"),
        (r'secrets\.\w+\s*\(', "Cryptographic random generation"),
    ]
    
    # Check context
    in_node = False
    in_state_default = False
    
    for i, line in enumerate(lines):
        # Check if we're in a node
        if re.search(r'(async\s+)?def\s+\w+_(node|task)\s*\(|@(node|task)', line):
            in_node = True
        elif re.match(r'^(def|class|async\s+def)', line) and in_node:
            in_node = False
            
        # Check if we're in a state field default
        if re.search(r'field\s*\(\s*default_factory', line):
            in_state_default = True
        elif ';' in line or '\n' in line:
            in_state_default = False
        
        # Look for non-deterministic operations
        for pattern, desc in non_det_patterns:
            if re.search(pattern, line):
                # Skip if it's in a test or example
                if 'test' in str(file_path) or 'example' in str(file_path):
                    continue
                
                # Skip if it's for logging/metrics
                if 'log' in line.lower() or 'metric' in line.lower():
                    continue
                    
                # Skip if it's in state defaults (those are OK)
                if in_state_default:
                    continue
                
                # Check if it's used for control flow
                if i > 0 and re.search(r'if|while|for', lines[i-1]):
                    severity = "critical"
                    desc = f"{desc} used in control flow - will differ on resume"
                else:
                    severity = "warning"
                
                issues.append(Issue(
                    file_path=str(file_path),
                    line_number=i + 1,
                    issue_type="non_deterministic_operation",
                    description=desc,
                    code_snippet=line.strip(),
                    severity=severity
                ))
    
    return issues


def check_interrupt_usage(file_path: Path) -> List[Issue]:
    """Check for proper interrupt usage patterns."""
    issues = []
    
    with open(file_path, 'r') as f:
        content = f.read()
        lines = content.split('\n')
    
    # Look for interrupt calls
    interrupt_pattern = r'interrupt\s*\('
    
    for i, line in enumerate(lines):
        if re.search(interrupt_pattern, line):
            # Check if it's in an entrypoint or properly structured
            # Look backwards for function definition
            func_found = False
            for j in range(max(0, i-10), i):
                if re.search(r'@entrypoint|def\s+\w+.*checkpointer', lines[j]):
                    func_found = True
                    break
            
            if not func_found:
                issues.append(Issue(
                    file_path=str(file_path),
                    line_number=i + 1,
                    issue_type="interrupt_without_entrypoint",
                    description="interrupt() call without proper @entrypoint or checkpointer",
                    code_snippet=line.strip(),
                    severity="critical"
                ))
    
    return issues


def check_state_mutations(file_path: Path) -> List[Issue]:
    """Check for direct state mutations outside of proper channels."""
    issues = []
    
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    # Patterns for state mutations
    mutation_patterns = [
        (r'state\.\w+\s*=(?!=)', "Direct state assignment"),
        (r'state\[[\'"]\w+[\'"]]\s*=(?!=)', "Direct state dict assignment"),
        (r'state\.\w+\.append\s*\(', "Direct state list mutation"),
        (r'state\.\w+\.extend\s*\(', "Direct state list mutation"),
        (r'state\.\w+\.update\s*\(', "Direct state dict mutation"),
    ]
    
    for i, line in enumerate(lines):
        for pattern, desc in mutation_patterns:
            if re.search(pattern, line):
                # Skip if it's in a return statement
                if 'return' in line:
                    continue
                    
                issues.append(Issue(
                    file_path=str(file_path),
                    line_number=i + 1,
                    issue_type="direct_state_mutation",
                    description=f"{desc} - should return new state dict instead",
                    code_snippet=line.strip(),
                    severity="warning"
                ))
    
    return issues


def analyze_project(project_dir: str) -> Dict[str, List[Issue]]:
    """Analyze the entire project for LangGraph pitfalls."""
    all_issues = {
        "side_effects": [],
        "non_deterministic": [],
        "interrupts": [],
        "state_mutations": []
    }
    
    # Focus on source files, not test files
    src_dir = os.path.join(project_dir, "src", "log_analyzer_agent")
    
    for py_file in find_python_files(src_dir):
        # Skip __pycache__ and test files
        if '__pycache__' in str(py_file) or 'test_' in py_file.name:
            continue
            
        all_issues["side_effects"].extend(check_side_effects_outside_nodes(py_file))
        all_issues["non_deterministic"].extend(check_non_deterministic_operations(py_file))
        all_issues["interrupts"].extend(check_interrupt_usage(py_file))
        all_issues["state_mutations"].extend(check_state_mutations(py_file))
    
    return all_issues


def print_report(issues: Dict[str, List[Issue]]):
    """Print a formatted report of issues found."""
    print("=" * 80)
    print("LangGraph Pitfall Analysis Report")
    print("=" * 80)
    
    total_issues = sum(len(issue_list) for issue_list in issues.values())
    critical_count = sum(1 for issue_list in issues.values() for issue in issue_list if issue.severity == "critical")
    
    print(f"\nTotal issues found: {total_issues}")
    print(f"Critical issues: {critical_count}")
    print()
    
    for category, issue_list in issues.items():
        if not issue_list:
            continue
            
        print(f"\n{category.upper().replace('_', ' ')} ({len(issue_list)} issues)")
        print("-" * 60)
        
        # Group by file
        by_file = {}
        for issue in issue_list:
            if issue.file_path not in by_file:
                by_file[issue.file_path] = []
            by_file[issue.file_path].append(issue)
        
        for file_path, file_issues in by_file.items():
            rel_path = file_path.replace("/home/shl0th/Documents/langchain-takehome/", "")
            print(f"\n  {rel_path}:")
            
            for issue in sorted(file_issues, key=lambda x: x.line_number):
                severity_marker = "❗" if issue.severity == "critical" else "⚠️" if issue.severity == "warning" else "ℹ️"
                print(f"    {severity_marker} Line {issue.line_number}: {issue.description}")
                print(f"       Code: {issue.code_snippet}")


if __name__ == "__main__":
    project_dir = "/home/shl0th/Documents/langchain-takehome"
    issues = analyze_project(project_dir)
    print_report(issues)
    
    # Return exit code based on critical issues
    critical_count = sum(1 for issue_list in issues.values() for issue in issue_list if issue.severity == "critical")
    exit(1 if critical_count > 0 else 0)