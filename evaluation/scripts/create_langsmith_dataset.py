#!/usr/bin/env python3
"""
Create a LangSmith-compatible evaluation dataset from LogHub logs.
Consolidated version with all features from v1, v2, and v3.
"""

import json
import random
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import defaultdict
from langsmith import Client
from langsmith.schemas import DataType


# ==================== Configuration ====================

DATASET_NAME = "log-analyzer-evaluation"
DATASET_DESCRIPTION = """
Curated evaluation dataset for the LangGraph log analyzer agent.
Contains diverse log entries with comprehensive expected outputs including
issues, explanations, suggestions, documentation references, and diagnostic commands.
"""

# Target samples per system
SYSTEM_DISTRIBUTION = {
    "Apache": 10,
    "HDFS": 10,
    "BGL": 8,
    "OpenStack": 8,
    "Hadoop": 8,
    "Linux": 7,
    "Windows": 7,
    "Spark": 6,
    "OpenSSH": 6,
    "Android": 5,
    "HPC": 5,
    "Mac": 5,
    "Thunderbird": 5,
    "Zookeeper": 4,
    "HealthApp": 3,
    "Proxifier": 3,
}

ERROR_RATIO = 0.7


# ==================== Issue Detection ====================

class IssueDetector:
    """Detect and categorize issues in log entries."""
    
    def __init__(self):
        self.patterns = {
            "connection_failure": {
                "keywords": ["connection", "connect", "refused", "timeout", "unreachable"],
                "severity": "error",
                "explanation": "A connection error indicates that the system was unable to establish communication with a remote service or host.",
                "suggestions": [
                    "Check network connectivity to the target service",
                    "Verify firewall rules and port accessibility",
                    "Ensure the target service is running and accepting connections"
                ],
                "commands": [
                    {"command": "netstat -tuln", "description": "Show listening ports"},
                    {"command": "ss -s", "description": "Socket statistics summary"},
                    {"command": "ping -c 4 <hostname>", "description": "Test network connectivity"}
                ]
            },
            "authentication_failure": {
                "keywords": ["authentication", "auth", "login", "password", "credential", "denied", "unauthorized"],
                "severity": "error",
                "explanation": "Authentication failures occur when invalid credentials are provided or when authentication mechanisms fail.",
                "suggestions": [
                    "Verify credentials are correct",
                    "Check authentication service availability",
                    "Review authentication logs for more details"
                ],
                "commands": [
                    {"command": "grep 'auth' /var/log/syslog | tail -50", "description": "Check authentication logs"},
                    {"command": "id", "description": "Show current user and groups"},
                    {"command": "sudo -l", "description": "List sudo permissions"}
                ]
            },
            "memory_error": {
                "keywords": ["memory", "heap", "oom", "out of memory", "allocation"],
                "severity": "critical",
                "explanation": "Memory errors suggest that the system or application has exhausted available memory resources.",
                "suggestions": [
                    "Increase heap size or memory allocation",
                    "Check for memory leaks in the application",
                    "Monitor memory usage patterns"
                ],
                "commands": [
                    {"command": "free -h", "description": "Check current memory usage"},
                    {"command": "ps aux --sort=-%mem | head -20", "description": "Show top memory-consuming processes"},
                    {"command": "dmesg | grep -i memory", "description": "Check kernel memory messages"}
                ]
            },
            "disk_error": {
                "keywords": ["disk", "space", "storage", "filesystem", "full"],
                "severity": "error",
                "explanation": "Disk-related errors indicate problems with storage capacity or filesystem operations.",
                "suggestions": [
                    "Check available disk space",
                    "Clean up old logs or temporary files",
                    "Verify disk health and filesystem integrity"
                ],
                "commands": [
                    {"command": "df -h", "description": "Check disk space usage"},
                    {"command": "du -sh /* 2>/dev/null | sort -h", "description": "Find large directories"},
                    {"command": "iostat -x 1 5", "description": "Monitor disk I/O statistics"}
                ]
            },
            "service_failure": {
                "keywords": ["failed", "failure", "error", "exception", "crash"],
                "severity": "error",
                "explanation": "Service failures indicate that a system component or application has encountered an error condition.",
                "suggestions": [
                    "Check service logs for detailed error messages",
                    "Verify service configuration",
                    "Restart the affected service if appropriate"
                ],
                "commands": [
                    {"command": "systemctl status", "description": "Check system service status"},
                    {"command": "journalctl -xe --since '1 hour ago'", "description": "Recent system logs"},
                    {"command": "top -b -n 1", "description": "Show system resource usage"}
                ]
            },
            "performance_issue": {
                "keywords": ["slow", "timeout", "latency", "performance", "delayed"],
                "severity": "warning",
                "explanation": "Performance issues suggest that the system is experiencing delays or resource constraints.",
                "suggestions": [
                    "Monitor system resources (CPU, memory, I/O)",
                    "Check for bottlenecks in the application",
                    "Optimize configurations for better performance"
                ],
                "commands": [
                    {"command": "vmstat 1 5", "description": "Monitor system performance"},
                    {"command": "iotop -b -n 1", "description": "Show I/O usage by process"},
                    {"command": "netstat -i", "description": "Network interface statistics"}
                ]
            }
        }
    
    def detect_and_analyze(self, log_entry: Dict[str, Any]) -> Dict[str, Any]:
        """Detect issues and generate complete analysis."""
        if not log_entry.get('expected_analysis', {}).get('is_error', False):
            # No error expected - return empty analysis
            return {
                "issues": [],
                "explanations": [],
                "root_cause": "",
                "suggestions": [],
                "recommendations": [],
                "documentation_references": [],
                "diagnostic_commands": []
            }
        
        raw_log = log_entry.get('raw_log', '').lower()
        log_source = log_entry.get('log_source', 'system')
        
        # Detect primary issue
        detected_issue = None
        for issue_type, pattern in self.patterns.items():
            if any(keyword in raw_log for keyword in pattern['keywords']):
                detected_issue = (issue_type, pattern)
                break
        
        # Default to general error if no specific pattern matched
        if not detected_issue and log_entry.get('expected_analysis', {}).get('is_error', False):
            detected_issue = ("general_error", {
                "severity": log_entry.get('severity', 'error'),
                "explanation": "An error condition was detected in the system logs that requires investigation.",
                "suggestions": [
                    "Review the full error context in logs",
                    "Check system resources (CPU, memory, disk)",
                    "Verify service dependencies are healthy"
                ],
                "commands": [
                    {"command": "tail -50 /var/log/syslog", "description": "Recent system logs"},
                    {"command": "uptime", "description": "Show system uptime and load"},
                    {"command": "systemctl status", "description": "Check service status"}
                ]
            })
        
        if not detected_issue:
            return {
                "issues": [],
                "explanations": [],
                "root_cause": "",
                "suggestions": [],
                "recommendations": [],
                "documentation_references": [],
                "diagnostic_commands": []
            }
        
        issue_type, pattern = detected_issue
        
        # Build the analysis result
        issues = [{
            "type": issue_type,
            "description": f"{issue_type.replace('_', ' ').title()} detected in {log_source} logs",
            "severity": pattern.get('severity', 'error')
        }]
        
        # Support both field names for compatibility
        explanations = [pattern.get('explanation', f"An issue of type '{issue_type}' was detected.")]
        root_cause = pattern.get('explanation', f"An issue of type '{issue_type}' was detected.")
        
        suggestions = pattern.get('suggestions', [])[:3]  # Limit to 3
        recommendations = pattern.get('suggestions', [])[:3]  # Also store as recommendations
        
        # Add system-specific suggestions
        if log_source == "HDFS" and 'block' in raw_log:
            suggestions.append("Run HDFS fsck to check filesystem integrity")
        elif log_source == "Apache":
            suggestions.append("Check Apache error logs for more details")
        elif log_source == "OpenSSH" and issue_type == "authentication_failure":
            suggestions.append("Review SSH configuration in /etc/ssh/sshd_config")
        
        # Limit suggestions to 5 total
        suggestions = suggestions[:5]
        
        # Generate documentation references based on issue type and system
        documentation_references = self._generate_doc_references(issue_type, log_source)
        
        # Get diagnostic commands
        diagnostic_commands = pattern.get('commands', [])[:3]
        
        # Add system-specific commands
        if log_source == "HDFS":
            diagnostic_commands.append({
                "command": "hdfs dfsadmin -report",
                "description": "HDFS cluster health report"
            })
        elif log_source == "Apache":
            diagnostic_commands.append({
                "command": "apachectl -S",
                "description": "Apache virtual host configuration"
            })
        
        # Limit to 5 commands total
        diagnostic_commands = diagnostic_commands[:5]
        
        return {
            "issues": issues,
            "explanations": explanations,
            "root_cause": root_cause,  # Include for compatibility
            "suggestions": suggestions,
            "recommendations": recommendations,  # Include for compatibility
            "documentation_references": documentation_references,
            "diagnostic_commands": diagnostic_commands
        }
    
    def _generate_doc_references(self, issue_type: str, log_source: str) -> List[Dict[str, str]]:
        """Generate relevant documentation references."""
        references = []
        
        # Issue-specific documentation
        issue_docs = {
            "connection_failure": [
                {
                    "title": "Troubleshooting Network Connectivity Issues",
                    "url": "https://docs.example.com/network-troubleshooting",
                    "relevance": "Primary reference for connection issues"
                }
            ],
            "authentication_failure": [
                {
                    "title": "Authentication and Access Control Guide",
                    "url": "https://docs.example.com/auth-guide",
                    "relevance": "Comprehensive authentication troubleshooting"
                }
            ],
            "memory_error": [
                {
                    "title": "Memory Management and Optimization",
                    "url": "https://docs.example.com/memory-management",
                    "relevance": "Guide for diagnosing and fixing memory issues"
                }
            ]
        }
        
        # System-specific documentation
        system_docs = {
            "HDFS": [
                {
                    "title": "HDFS Administration Guide",
                    "url": "https://hadoop.apache.org/docs/stable/hadoop-project-dist/hadoop-hdfs/HdfsUserGuide.html",
                    "relevance": "Official HDFS documentation"
                }
            ],
            "Apache": [
                {
                    "title": "Apache HTTP Server Documentation",
                    "url": "https://httpd.apache.org/docs/",
                    "relevance": "Official Apache documentation"
                }
            ]
        }
        
        # Add issue-specific docs
        if issue_type in issue_docs:
            references.extend(issue_docs[issue_type])
        
        # Add system-specific docs
        if log_source in system_docs:
            references.extend(system_docs[log_source])
        
        return references[:3]  # Limit to 3 references


# ==================== Dataset Processing ====================

def load_loghub_dataset(file_path: Path) -> List[Dict[str, Any]]:
    """Load LogHub evaluation dataset."""
    with open(file_path, 'r') as f:
        return json.load(f)


def sample_entries(entries: List[Dict[str, Any]], 
                  system_distribution: Dict[str, int],
                  error_ratio: float) -> List[Dict[str, Any]]:
    """Sample entries according to distribution and error ratio."""
    sampled = []
    
    # Group by system
    by_system = defaultdict(list)
    for entry in entries:
        by_system[entry['log_source']].append(entry)
    
    # Sample from each system
    for system, count in system_distribution.items():
        if system not in by_system:
            print(f"Warning: No entries found for system {system}")
            continue
        
        system_entries = by_system[system]
        error_entries = [e for e in system_entries if e['expected_analysis']['is_error']]
        normal_entries = [e for e in system_entries if not e['expected_analysis']['is_error']]
        
        # Calculate samples needed
        n_errors = min(len(error_entries), int(count * error_ratio))
        n_normal = count - n_errors
        
        # Sample
        if error_entries:
            sampled.extend(random.sample(error_entries, min(n_errors, len(error_entries))))
        if normal_entries and n_normal > 0:
            sampled.extend(random.sample(normal_entries, min(n_normal, len(normal_entries))))
    
    return sampled


def transform_entry(entry: Dict[str, Any], detector: IssueDetector) -> Dict[str, Any]:
    """Transform a log entry to match agent's expected format."""
    # Generate analysis
    analysis = detector.detect_and_analyze(entry)
    
    # Create the example in LangSmith format
    return {
        "inputs": {
            "log_content": entry['raw_log']
        },
        "outputs": analysis,  # Direct analysis dict, not nested
        "metadata": {
            "log_source": entry['log_source'],
            "original_id": entry.get('id', ''),
            "is_error": entry['expected_analysis']['is_error'],
            "category": entry['expected_analysis'].get('category', 'general'),
            "severity": entry.get('severity', 'info')
        }
    }


def calculate_statistics(examples: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate dataset statistics."""
    stats = {
        "total_examples": len(examples),
        "by_system": defaultdict(int),
        "by_severity": defaultdict(int),
        "error_count": 0,
        "issues_distribution": defaultdict(int)
    }
    
    for ex in examples:
        meta = ex["metadata"]
        stats["by_system"][meta["log_source"]] += 1
        stats["by_severity"][meta["severity"]] += 1
        if meta["is_error"]:
            stats["error_count"] += 1
        
        for issue in ex["outputs"]["issues"]:
            stats["issues_distribution"][issue["type"]] += 1
    
    return dict(stats)


# ==================== Main Execution ====================

def main(
    dataset_name: Optional[str] = None,
    dataset_description: Optional[str] = None,
    system_distribution: Optional[Dict[str, int]] = None,
    error_ratio: Optional[float] = None,
    source_file: Optional[str] = None,
    version_tag: Optional[str] = None
):
    """Create and upload the dataset to LangSmith."""
    # Use defaults if not provided
    dataset_name = dataset_name or DATASET_NAME
    dataset_description = dataset_description or DATASET_DESCRIPTION
    system_distribution = system_distribution or SYSTEM_DISTRIBUTION
    error_ratio = error_ratio if error_ratio is not None else ERROR_RATIO
    
    print(f"=== LangSmith Dataset Creator ===")
    print(f"Creating dataset: {dataset_name}")
    
    # Initialize components
    client = Client()
    detector = IssueDetector()
    
    # Load source data
    if source_file:
        source_path = Path(source_file)
    else:
        source_path = Path("loghub/loghub_evaluation_dataset/train_dataset.json")
    
    if not source_path.exists():
        raise FileNotFoundError(f"Source dataset not found: {source_path}")
    
    print(f"\nLoading source dataset from: {source_path}")
    all_entries = load_loghub_dataset(source_path)
    print(f"Loaded {len(all_entries)} total entries")
    
    # Sample entries
    print("\nSampling entries according to distribution...")
    sampled_entries = sample_entries(all_entries, system_distribution, error_ratio)
    print(f"Sampled {len(sampled_entries)} entries")
    
    # Transform entries
    print("\nTransforming entries to agent format...")
    examples = []
    for entry in sampled_entries:
        try:
            example = transform_entry(entry, detector)
            examples.append(example)
        except Exception as e:
            print(f"Error transforming entry {entry.get('id', 'unknown')}: {e}")
    
    print(f"Successfully transformed {len(examples)} entries")
    
    # Check if dataset exists and delete if so
    existing_datasets = list(client.list_datasets())
    for dataset in existing_datasets:
        if dataset.name == dataset_name:
            print(f"\nDataset '{dataset_name}' exists. Deleting...")
            client.delete_dataset(dataset_id=dataset.id)
            print("Old dataset deleted.")
            break
    
    # Create new dataset
    dataset = client.create_dataset(
        dataset_name=dataset_name,
        description=dataset_description,
        data_type=DataType.kv
    )
    print(f"\nCreated new dataset: {dataset.name} (ID: {dataset.id})")
    
    # Upload examples using the bulk method
    print(f"\nUploading {len(examples)} examples to LangSmith...")
    
    # Prepare for bulk upload
    inputs = [ex["inputs"] for ex in examples]
    outputs = [ex["outputs"] for ex in examples]
    metadata = [ex["metadata"] for ex in examples]
    
    # Bulk create examples
    client.create_examples(
        dataset_id=dataset.id,
        inputs=inputs,
        outputs=outputs,
        metadata=metadata
    )
    
    print(f"Successfully uploaded all {len(examples)} examples!")
    
    # Create version tag if specified
    if version_tag:
        try:
            client.create_dataset_version(
                dataset_id=dataset.id,
                tag=version_tag,
                description=f"Version {version_tag} - {datetime.now().isoformat()}"
            )
            print(f"Created version tag: {version_tag}")
        except Exception as e:
            print(f"Warning: Could not create version tag: {e}")
    
    # Save backup
    backup_file = Path(f"langsmith_dataset_backup_{dataset_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    backup_data = {
        "dataset_name": dataset_name,
        "dataset_id": str(dataset.id),
        "description": dataset_description,
        "created_at": datetime.now().isoformat(),
        "num_examples": len(examples),
        "examples": examples[:5],  # Save first 5 as samples
        "statistics": calculate_statistics(examples)
    }
    
    with open(backup_file, 'w') as f:
        json.dump(backup_data, f, indent=2)
    
    print(f"\nLocal backup saved to: {backup_file}")
    print("\n✅ Dataset creation complete!")
    
    # Print statistics
    stats = backup_data["statistics"]
    print("\nDataset Statistics:")
    print(f"  Total examples: {stats['total_examples']}")
    print(f"  Error examples: {stats['error_count']} ({stats['error_count']/stats['total_examples']*100:.1f}%)")
    print(f"  Systems covered: {len(stats['by_system'])}")
    print(f"  Issue types: {len(stats['issues_distribution'])}")
    
    return dataset.id


if __name__ == "__main__":
    # Run with default configuration
    main()