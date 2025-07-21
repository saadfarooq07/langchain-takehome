#!/usr/bin/env python3
"""
Enhanced LangSmith-compatible evaluation dataset creator from LogHub logs.
Fixes reference output generation and adds dataset splitting functionality.
"""

import json
import random
import hashlib
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict
from langsmith import Client
from langsmith.schemas import DataType


# ==================== Configuration ====================

DATASET_BASE_NAME = "log-analyzer-evaluation"
DATASET_DESCRIPTION = """
Enhanced evaluation dataset for the LangGraph log analyzer agent.
Contains diverse log entries with comprehensive expected outputs including
issues, explanations, suggestions, documentation references, and diagnostic commands.
Properly handles both error and non-error cases with meaningful reference outputs.
"""

# Target samples per system
SYSTEM_DISTRIBUTION = {
    "Apache": 15,
    "HDFS": 15,
    "BGL": 12,
    "OpenStack": 12,
    "Hadoop": 12,
    "Linux": 10,
    "Windows": 10,
    "Spark": 8,
    "OpenSSH": 8,
    "Android": 6,
    "HPC": 6,
    "Mac": 6,
    "Thunderbird": 6,
    "Zookeeper": 5,
    "HealthApp": 4,
    "Proxifier": 4,
}

ERROR_RATIO = 0.6  # 60% error, 40% normal
DATASET_SPLITS = {
    "train": 0.7,
    "validation": 0.15,
    "test": 0.15
}


# ==================== Enhanced Issue Detection ====================

class EnhancedIssueDetector:
    """Enhanced issue detection and analysis generation."""
    
    def __init__(self):
        self.error_patterns = {
            "connection_failure": {
                "keywords": ["connection", "connect", "refused", "timeout", "unreachable", "network", "socket"],
                "severity": "error",
                "explanation": "A connection error indicates that the system was unable to establish communication with a remote service or host.",
                "suggestions": [
                    "Check network connectivity to the target service",
                    "Verify firewall rules and port accessibility",
                    "Ensure the target service is running and accepting connections",
                    "Check DNS resolution for the target hostname"
                ],
                "commands": [
                    {"command": "netstat -tuln", "description": "Show listening ports"},
                    {"command": "ss -s", "description": "Socket statistics summary"},
                    {"command": "ping -c 4 <hostname>", "description": "Test network connectivity"},
                    {"command": "nslookup <hostname>", "description": "Check DNS resolution"}
                ]
            },
            "authentication_failure": {
                "keywords": ["authentication", "auth", "login", "password", "credential", "denied", "unauthorized", "invalid user", "preauth"],
                "severity": "error",
                "explanation": "Authentication failures occur when invalid credentials are provided or when authentication mechanisms fail.",
                "suggestions": [
                    "Verify credentials are correct and not expired",
                    "Check authentication service availability",
                    "Review authentication logs for more details",
                    "Ensure user account is not locked or disabled"
                ],
                "commands": [
                    {"command": "grep 'auth' /var/log/syslog | tail -50", "description": "Check authentication logs"},
                    {"command": "id <username>", "description": "Check user account status"},
                    {"command": "sudo -l", "description": "List sudo permissions"},
                    {"command": "lastlog", "description": "Show recent login attempts"}
                ]
            },
            "memory_error": {
                "keywords": ["memory", "heap", "oom", "out of memory", "allocation", "malloc", "virtual memory"],
                "severity": "critical",
                "explanation": "Memory errors suggest that the system or application has exhausted available memory resources.",
                "suggestions": [
                    "Increase heap size or memory allocation",
                    "Check for memory leaks in the application",
                    "Monitor memory usage patterns",
                    "Review memory-intensive processes"
                ],
                "commands": [
                    {"command": "free -h", "description": "Check current memory usage"},
                    {"command": "ps aux --sort=-%mem | head -20", "description": "Show top memory-consuming processes"},
                    {"command": "dmesg | grep -i memory", "description": "Check kernel memory messages"},
                    {"command": "cat /proc/meminfo", "description": "Detailed memory information"}
                ]
            },
            "disk_error": {
                "keywords": ["disk", "space", "storage", "filesystem", "full", "quota", "no space", "io error"],
                "severity": "error",
                "explanation": "Disk-related errors indicate problems with storage capacity, filesystem operations, or I/O failures.",
                "suggestions": [
                    "Check available disk space",
                    "Clean up old logs or temporary files",
                    "Verify disk health and filesystem integrity",
                    "Check for disk quota limits"
                ],
                "commands": [
                    {"command": "df -h", "description": "Check disk space usage"},
                    {"command": "du -sh /* 2>/dev/null | sort -h", "description": "Find large directories"},
                    {"command": "iostat -x 1 5", "description": "Monitor disk I/O statistics"},
                    {"command": "fsck -n /dev/<device>", "description": "Check filesystem integrity"}
                ]
            },
            "service_failure": {
                "keywords": ["failed", "failure", "error", "exception", "crash", "terminated", "killed", "exit"],
                "severity": "error",
                "explanation": "Service failures indicate that a system component or application has encountered an error condition.",
                "suggestions": [
                    "Check service logs for detailed error messages",
                    "Verify service configuration files",
                    "Restart the affected service if appropriate",
                    "Check system resources and dependencies"
                ],
                "commands": [
                    {"command": "systemctl status <service>", "description": "Check specific service status"},
                    {"command": "journalctl -xe --since '1 hour ago'", "description": "Recent system logs"},
                    {"command": "top -b -n 1", "description": "Show system resource usage"},
                    {"command": "systemctl list-failed", "description": "List failed services"}
                ]
            },
            "performance_issue": {
                "keywords": ["slow", "timeout", "latency", "performance", "delayed", "bottleneck", "response time"],
                "severity": "warning",
                "explanation": "Performance issues suggest that the system is experiencing delays or resource constraints.",
                "suggestions": [
                    "Monitor system resources (CPU, memory, I/O)",
                    "Check for bottlenecks in the application",
                    "Optimize configurations for better performance",
                    "Review application logs for slow operations"
                ],
                "commands": [
                    {"command": "vmstat 1 5", "description": "Monitor system performance"},
                    {"command": "iotop -b -n 1", "description": "Show I/O usage by process"},
                    {"command": "netstat -i", "description": "Network interface statistics"},
                    {"command": "sar -u 1 5", "description": "CPU utilization statistics"}
                ]
            }
        }
        
        # Patterns for normal/informational logs
        self.normal_patterns = {
            "initialization": {
                "keywords": ["starting", "started", "initialized", "loading", "boot", "init"],
                "category": "system_startup"
            },
            "status_update": {
                "keywords": ["status", "update", "progress", "completed", "finished"],
                "category": "monitoring"
            },
            "configuration": {
                "keywords": ["config", "setting", "parameter", "option"],
                "category": "configuration"
            },
            "user_activity": {
                "keywords": ["user", "session", "login", "logout", "access"],
                "category": "user_activity"
            },
            "data_processing": {
                "keywords": ["processing", "data", "records", "batch", "job"],
                "category": "data_processing"
            }
        }
    
    def detect_and_analyze(self, log_entry: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive analysis for both error and normal log entries."""
        raw_log = log_entry.get('raw_log', '').lower()
        log_source = log_entry.get('log_source', 'system')
        is_error = log_entry.get('expected_analysis', {}).get('is_error', False)
        severity = log_entry.get('severity', 'info')
        category = log_entry.get('expected_analysis', {}).get('category', 'general')
        
        if is_error:
            return self._analyze_error_log(raw_log, log_source, severity, category)
        else:
            return self._analyze_normal_log(raw_log, log_source, severity, category)
    
    def _analyze_error_log(self, raw_log: str, log_source: str, severity: str, category: str) -> Dict[str, Any]:
        """Analyze error logs and generate comprehensive output."""
        # Detect primary issue type
        detected_issue = None
        for issue_type, pattern in self.error_patterns.items():
            if any(keyword in raw_log for keyword in pattern['keywords']):
                detected_issue = (issue_type, pattern)
                break
        
        # Default to general error if no specific pattern matched
        if not detected_issue:
            detected_issue = ("general_error", {
                "severity": severity,
                "explanation": "An error condition was detected in the system logs that requires investigation.",
                "suggestions": [
                    "Review the full error context in logs",
                    "Check system resources (CPU, memory, disk)",
                    "Verify service dependencies are healthy",
                    "Check for recent configuration changes"
                ],
                "commands": [
                    {"command": "tail -50 /var/log/syslog", "description": "Recent system logs"},
                    {"command": "uptime", "description": "Show system uptime and load"},
                    {"command": "systemctl status", "description": "Check service status"},
                    {"command": "dmesg | tail -20", "description": "Recent kernel messages"}
                ]
            })
        
        issue_type, pattern = detected_issue
        
        # Build comprehensive analysis
        issues = [{
            "type": issue_type,
            "description": f"{issue_type.replace('_', ' ').title()} detected in {log_source} logs",
            "severity": pattern.get('severity', severity)
        }]
        
        explanations = [pattern.get('explanation', f"An issue of type '{issue_type}' was detected.")]
        suggestions = list(pattern.get('suggestions', []))[:4]  # Limit to 4
        
        # Add system-specific suggestions
        if log_source == "HDFS" and 'block' in raw_log:
            suggestions.append("Run HDFS fsck to check filesystem integrity")
        elif log_source == "Apache" and issue_type == "connection_failure":
            suggestions.append("Check Apache error logs and virtual host configuration")
        elif log_source == "OpenSSH" and issue_type == "authentication_failure":
            suggestions.append("Review SSH configuration in /etc/ssh/sshd_config")
        elif log_source == "Spark" and issue_type == "memory_error":
            suggestions.append("Adjust Spark executor memory settings")
        
        # Limit suggestions to 5 total
        suggestions = suggestions[:5]
        
        # Generate documentation references
        documentation_references = self._generate_doc_references(issue_type, log_source)
        
        # Get diagnostic commands with system-specific additions
        diagnostic_commands = list(pattern.get('commands', []))[:3]
        
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
        elif log_source == "Spark":
            diagnostic_commands.append({
                "command": "spark-submit --help", 
                "description": "Spark configuration options"
            })
        
        # Limit to 4 commands total
        diagnostic_commands = diagnostic_commands[:4]
        
        return {
            "issues": issues,
            "explanations": explanations,
            "suggestions": suggestions,
            "documentation_references": documentation_references,
            "diagnostic_commands": diagnostic_commands
        }
    
    def _analyze_normal_log(self, raw_log: str, log_source: str, severity: str, category: str) -> Dict[str, Any]:
        """Analyze normal/informational logs and generate meaningful output."""
        # Detect log pattern for better categorization
        detected_pattern = None
        for pattern_type, pattern in self.normal_patterns.items():
            if any(keyword in raw_log for keyword in pattern['keywords']):
                detected_pattern = (pattern_type, pattern)
                break
        
        if detected_pattern:
            pattern_type, pattern = detected_pattern
            detected_category = pattern['category']
        else:
            pattern_type = "general"
            detected_category = category
        
        # Generate analysis for normal logs
        issues = []  # Normal logs typically don't have issues
        
        # Generate helpful explanations even for normal logs
        explanations = self._generate_normal_explanation(raw_log, log_source, detected_category, pattern_type)
        
        # Generate monitoring suggestions for normal logs
        suggestions = self._generate_normal_suggestions(log_source, detected_category, pattern_type)
        
        # Generate relevant documentation
        documentation_references = self._generate_normal_doc_references(log_source, detected_category)
        
        # Generate monitoring/diagnostic commands
        diagnostic_commands = self._generate_normal_commands(log_source, detected_category)
        
        return {
            "issues": issues,
            "explanations": explanations,
            "suggestions": suggestions,
            "documentation_references": documentation_references,
            "diagnostic_commands": diagnostic_commands
        }
    
    def _generate_normal_explanation(self, raw_log: str, log_source: str, category: str, pattern_type: str) -> List[str]:
        """Generate explanations for normal log entries."""
        explanations = []
        
        if pattern_type == "initialization":
            explanations.append(f"This is a normal {log_source} initialization message indicating the system is starting up properly.")
        elif pattern_type == "status_update":
            explanations.append(f"This status update from {log_source} indicates normal operational progress.")
        elif pattern_type == "configuration":
            explanations.append(f"This configuration message shows {log_source} is loading or applying settings.")
        elif pattern_type == "user_activity":
            explanations.append(f"This log indicates normal user activity within the {log_source} system.")
        elif pattern_type == "data_processing":
            explanations.append(f"This message shows {log_source} is processing data as part of normal operations.")
        else:
            explanations.append(f"This is a normal operational message from {log_source} indicating healthy system activity.")
        
        # Add context-specific explanation
        if "time" in raw_log.lower():
            explanations.append("The timing information can be useful for performance monitoring and troubleshooting.")
        
        return explanations
    
    def _generate_normal_suggestions(self, log_source: str, category: str, pattern_type: str) -> List[str]:
        """Generate monitoring/maintenance suggestions for normal logs."""
        suggestions = []
        
        if pattern_type == "initialization":
            suggestions.extend([
                "Monitor startup times for performance trends",
                "Ensure all expected services start successfully",
                "Check for any initialization warnings or errors"
            ])
        elif pattern_type == "status_update":
            suggestions.extend([
                "Set up monitoring for regular status updates",
                "Alert on missing status updates that indicate issues",
                "Track trends in operational metrics"
            ])
        elif category == "configuration":
            suggestions.extend([
                "Document configuration changes for audit trail",
                "Validate configuration settings are as expected",
                "Monitor for configuration drift over time"
            ])
        else:
            suggestions.extend([
                f"Continue monitoring {log_source} for any unusual patterns",
                "Set up log aggregation for better visibility",
                "Establish baseline metrics for normal operations"
            ])
        
        # Add system-specific suggestions
        if log_source == "HDFS":
            suggestions.append("Monitor HDFS cluster health metrics regularly")
        elif log_source == "Apache":
            suggestions.append("Track Apache access patterns and response times")
        elif log_source == "Spark":
            suggestions.append("Monitor Spark job execution metrics")
        
        return suggestions[:4]  # Limit to 4 suggestions
    
    def _generate_normal_doc_references(self, log_source: str, category: str) -> List[Dict[str, str]]:
        """Generate documentation references for normal logs."""
        references = []
        
        # System-specific documentation
        system_docs = {
            "HDFS": {
                "title": "HDFS Monitoring and Maintenance Guide",
                "url": "https://hadoop.apache.org/docs/stable/hadoop-project-dist/hadoop-hdfs/HdfsUserGuide.html",
                "relevance": "Comprehensive guide for HDFS operations and monitoring"
            },
            "Apache": {
                "title": "Apache HTTP Server Log Files",
                "url": "https://httpd.apache.org/docs/2.4/logs.html",
                "relevance": "Official documentation on Apache logging"
            },
            "Spark": {
                "title": "Spark Monitoring and Instrumentation",
                "url": "https://spark.apache.org/docs/latest/monitoring.html",
                "relevance": "Guide for monitoring Spark applications"
            },
            "OpenSSH": {
                "title": "OpenSSH Server Configuration",
                "url": "https://man.openbsd.org/sshd_config",
                "relevance": "SSH server configuration reference"
            }
        }
        
        if log_source in system_docs:
            references.append(system_docs[log_source])
        
        # Category-specific documentation
        if category == "monitoring":
            references.append({
                "title": "System Monitoring Best Practices",
                "url": "https://docs.example.com/monitoring-guide",
                "relevance": "Best practices for system monitoring and alerting"
            })
        
        return references[:2]  # Limit to 2 references
    
    def _generate_normal_commands(self, log_source: str, category: str) -> List[Dict[str, str]]:
        """Generate diagnostic commands for normal logs."""
        commands = []
        
        # Basic monitoring commands
        commands.extend([
            {"command": "systemctl status", "description": "Check overall system service status"},
            {"command": "uptime", "description": "Show system uptime and load averages"}
        ])
        
        # System-specific commands
        if log_source == "HDFS":
            commands.append({
                "command": "hdfs dfsadmin -report", 
                "description": "Check HDFS cluster status and health"
            })
        elif log_source == "Apache":
            commands.append({
                "command": "apachectl status", 
                "description": "Check Apache server status"
            })
        elif log_source == "Spark":
            commands.append({
                "command": "spark-shell --version", 
                "description": "Verify Spark installation"
            })
        
        return commands[:3]  # Limit to 3 commands
    
    def _generate_doc_references(self, issue_type: str, log_source: str) -> List[Dict[str, str]]:
        """Generate relevant documentation references for errors."""
        references = []
        
        # Issue-specific documentation
        issue_docs = {
            "connection_failure": {
                "title": "Network Troubleshooting Guide",
                "url": "https://docs.example.com/network-troubleshooting",
                "relevance": "Comprehensive guide for diagnosing connection issues"
            },
            "authentication_failure": {
                "title": "Authentication and Access Control",
                "url": "https://docs.example.com/auth-guide",
                "relevance": "Guide for troubleshooting authentication problems"
            },
            "memory_error": {
                "title": "Memory Management and Optimization",
                "url": "https://docs.example.com/memory-management",
                "relevance": "Best practices for memory troubleshooting"
            },
            "disk_error": {
                "title": "Storage and Filesystem Troubleshooting",
                "url": "https://docs.example.com/storage-guide",
                "relevance": "Guide for resolving disk and filesystem issues"
            }
        }
        
        # System-specific documentation
        system_docs = {
            "HDFS": {
                "title": "HDFS Troubleshooting Guide",
                "url": "https://hadoop.apache.org/docs/stable/hadoop-project-dist/hadoop-hdfs/HdfsTroubleshooting.html",
                "relevance": "Official HDFS troubleshooting documentation"
            },
            "Apache": {
                "title": "Apache HTTP Server Troubleshooting",
                "url": "https://httpd.apache.org/docs/2.4/misc/troubleshooting.html",
                "relevance": "Official Apache troubleshooting guide"
            },
            "OpenSSH": {
                "title": "SSH Troubleshooting Guide",
                "url": "https://www.ssh.com/academy/ssh/troubleshoot",
                "relevance": "Comprehensive SSH troubleshooting resource"
            }
        }
        
        # Add issue-specific docs
        if issue_type in issue_docs:
            references.append(issue_docs[issue_type])
        
        # Add system-specific docs
        if log_source in system_docs:
            references.append(system_docs[log_source])
        
        return references[:2]  # Limit to 2 references


# ==================== Dataset Splitting ====================

def create_deterministic_splits(entries: List[Dict[str, Any]], 
                               splits: Dict[str, float]) -> Dict[str, List[Dict[str, Any]]]:
    """Create deterministic dataset splits based on entry hash."""
    # Sort entries by ID for deterministic ordering  
    sorted_entries = sorted(entries, key=lambda x: x.get('metadata', {}).get('original_id', x.get('id', '')))
    
    # Split based on hash for reproducibility
    split_data = {split_name: [] for split_name in splits.keys()}
    
    for entry in sorted_entries:
        # Create deterministic hash based on entry ID
        entry_id = entry.get('metadata', {}).get('original_id', entry.get('id', ''))
        entry_hash = hashlib.md5(entry_id.encode()).hexdigest()
        hash_value = int(entry_hash[:8], 16) / (2**32)  # Normalize to [0, 1)
        
        # Determine split
        cumulative = 0
        for split_name, ratio in splits.items():
            cumulative += ratio
            if hash_value < cumulative:
                split_data[split_name].append(entry)
                break
    
    return split_data


# ==================== Enhanced Dataset Processing ====================

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
        
        # Sample with random seed for reproducibility
        random.seed(42)
        if error_entries and n_errors > 0:
            sampled.extend(random.sample(error_entries, min(n_errors, len(error_entries))))
        if normal_entries and n_normal > 0:
            sampled.extend(random.sample(normal_entries, min(n_normal, len(normal_entries))))
    
    return sampled


def transform_entry(entry: Dict[str, Any], detector: EnhancedIssueDetector) -> Dict[str, Any]:
    """Transform a log entry to match agent's expected format."""
    # Generate enhanced analysis
    analysis = detector.detect_and_analyze(entry)
    
    # Create the example in LangSmith format
    return {
        "inputs": {
            "log_content": entry['raw_log']
        },
        "outputs": analysis,
        "metadata": {
            "log_source": entry['log_source'],
            "original_id": entry.get('id', ''),
            "is_error": entry['expected_analysis']['is_error'],
            "category": entry['expected_analysis'].get('category', 'general'),
            "severity": entry.get('severity', 'info'),
            "event_id": entry.get('event_id', ''),
            "parsed_template": entry.get('parsed_template', '')
        }
    }


def calculate_statistics(examples: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate comprehensive dataset statistics."""
    stats = {
        "total_examples": len(examples),
        "by_system": defaultdict(int),
        "by_severity": defaultdict(int),
        "by_category": defaultdict(int),
        "error_count": 0,
        "normal_count": 0,
        "issues_distribution": defaultdict(int),
        "avg_suggestions_per_example": 0,
        "avg_commands_per_example": 0,
        "examples_with_docs": 0
    }
    
    total_suggestions = 0
    total_commands = 0
    
    for ex in examples:
        meta = ex["metadata"]
        outputs = ex["outputs"]
        
        stats["by_system"][meta["log_source"]] += 1
        stats["by_severity"][meta["severity"]] += 1
        stats["by_category"][meta["category"]] += 1
        
        if meta["is_error"]:
            stats["error_count"] += 1
        else:
            stats["normal_count"] += 1
        
        # Count issues
        for issue in outputs.get("issues", []):
            stats["issues_distribution"][issue.get("type", "unknown")] += 1
        
        # Count suggestions and commands
        total_suggestions += len(outputs.get("suggestions", []))
        total_commands += len(outputs.get("diagnostic_commands", []))
        
        # Count examples with documentation
        if outputs.get("documentation_references"):
            stats["examples_with_docs"] += 1
    
    # Calculate averages
    if len(examples) > 0:
        stats["avg_suggestions_per_example"] = round(total_suggestions / len(examples), 2)
        stats["avg_commands_per_example"] = round(total_commands / len(examples), 2)
    
    return dict(stats)


# ==================== Main Execution ====================

def main(
    dataset_name: Optional[str] = None,
    dataset_description: Optional[str] = None,
    system_distribution: Optional[Dict[str, int]] = None,
    error_ratio: Optional[float] = None,
    source_file: Optional[str] = None,
    create_splits: bool = True,
    version_tag: Optional[str] = None
):
    """Create and upload enhanced datasets to LangSmith with optional splitting."""
    # Use defaults if not provided
    base_name = dataset_name or DATASET_BASE_NAME
    dataset_description = dataset_description or DATASET_DESCRIPTION
    system_distribution = system_distribution or SYSTEM_DISTRIBUTION
    error_ratio = error_ratio if error_ratio is not None else ERROR_RATIO
    
    print(f"=== Enhanced LangSmith Dataset Creator ===")
    print(f"Creating dataset: {base_name}")
    print(f"Dataset splitting: {'enabled' if create_splits else 'disabled'}")
    
    # Initialize components
    client = Client()
    detector = EnhancedIssueDetector()
    
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
    
    # Create dataset splits if requested
    if create_splits:
        print("\nCreating dataset splits...")
        split_data = create_deterministic_splits(examples, DATASET_SPLITS)
        
        dataset_ids = {}
        for split_name, split_examples in split_data.items():
            if not split_examples:
                print(f"Warning: No examples for {split_name} split")
                continue
                
            split_dataset_name = f"{base_name}-{split_name}"
            split_description = f"{dataset_description}\nSplit: {split_name} ({len(split_examples)} examples)"
            
            dataset_id = create_single_dataset(
                client, split_dataset_name, split_description, 
                split_examples, version_tag
            )
            dataset_ids[split_name] = dataset_id
            
            print(f"Created {split_name} dataset: {split_dataset_name} ({len(split_examples)} examples)")
        
        # Create backup with split information
        backup_data = create_backup_data(base_name, dataset_ids, dataset_description, split_data)
        
    else:
        # Create single dataset
        dataset_id = create_single_dataset(
            client, base_name, dataset_description, 
            examples, version_tag
        )
        dataset_ids = {"full": dataset_id}
        
        # Create backup
        backup_data = create_backup_data(base_name, dataset_ids, dataset_description, {"full": examples})
    
    # Save backup
    backup_file = Path(f"langsmith_dataset_backup_{base_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(backup_file, 'w') as f:
        json.dump(backup_data, f, indent=2)
    
    print(f"\nLocal backup saved to: {backup_file}")
    print("\n✅ Enhanced dataset creation complete!")
    
    # Print comprehensive statistics
    total_examples = sum(len(examples) for examples in backup_data["splits"].values())
    print(f"\nOverall Statistics:")
    print(f"  Total examples across all datasets: {total_examples}")
    
    for split_name, split_examples in backup_data["splits"].items():
        if split_examples:
            stats = calculate_statistics(split_examples)
            print(f"\n{split_name.title()} Split Statistics:")
            print(f"  Examples: {stats['total_examples']}")
            print(f"  Error ratio: {stats['error_count']}/{stats['total_examples']} ({stats['error_count']/stats['total_examples']*100:.1f}%)")
            print(f"  Systems: {len(stats['by_system'])}")
            print(f"  Avg suggestions/example: {stats['avg_suggestions_per_example']}")
            print(f"  Examples with documentation: {stats['examples_with_docs']}")
    
    return dataset_ids


def create_single_dataset(client: Client, name: str, description: str, 
                         examples: List[Dict[str, Any]], version_tag: Optional[str] = None) -> str:
    """Create a single dataset in LangSmith."""
    # Check if dataset exists and delete if so
    existing_datasets = list(client.list_datasets())
    for dataset in existing_datasets:
        if dataset.name == name:
            print(f"Dataset '{name}' exists. Deleting...")
            client.delete_dataset(dataset_id=dataset.id)
            print("Old dataset deleted.")
            break
    
    # Create new dataset
    dataset = client.create_dataset(
        dataset_name=name,
        description=description,
        data_type=DataType.kv
    )
    
    # Upload examples
    print(f"Uploading {len(examples)} examples to {name}...")
    
    inputs = [ex["inputs"] for ex in examples]
    outputs = [ex["outputs"] for ex in examples]
    metadata = [ex["metadata"] for ex in examples]
    
    client.create_examples(
        dataset_id=dataset.id,
        inputs=inputs,
        outputs=outputs,
        metadata=metadata
    )
    
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
    
    return str(dataset.id)


def create_backup_data(base_name: str, dataset_ids: Dict[str, str], 
                      description: str, split_data: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
    """Create backup data structure."""
    return {
        "dataset_base_name": base_name,
        "dataset_ids": dataset_ids,
        "description": description,
        "created_at": datetime.now().isoformat(),
        "total_examples": sum(len(examples) for examples in split_data.values()),
        "splits": {
            split_name: examples for split_name, examples in split_data.items()
        },
        "split_statistics": {
            split_name: calculate_statistics(examples) 
            for split_name, examples in split_data.items() if examples
        },
        "sample_examples": {
            split_name: examples[:3] if examples else []
            for split_name, examples in split_data.items()
        }
    }


if __name__ == "__main__":
    # Run with enhanced configuration
    main(
        create_splits=True,  # Enable dataset splitting
        version_tag="v2.0"   # Tag this version
    )
