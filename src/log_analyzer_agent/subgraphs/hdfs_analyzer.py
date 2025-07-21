"""Specialized analyzer for HDFS (Hadoop Distributed File System) logs.

This analyzer understands HDFS-specific patterns, errors, and provides
targeted recommendations for HDFS issues.
"""

from typing import Dict, Any, List
import re
from datetime import datetime

from ..core.unified_state import UnifiedState
from ..core.circuit_breaker import circuit_breaker
from ..configuration import Configuration
from langchain_core.messages import AIMessage


# HDFS-specific patterns
HDFS_PATTERNS = {
    "block_corruption": r"Corrupt block.*blk_[\d\-]+",
    "replication_issues": r"Under-replicated.*Target Replicas is \d+.*Current Replica\(s\) is \d+",
    "namenode_errors": r"NameNode.*ERROR|FATAL.*NameNode",
    "datanode_errors": r"DataNode.*ERROR|FATAL.*DataNode",
    "disk_failure": r"DataNode.*Disk.*failure|IOException.*No space left on device",
    "network_issues": r"Network.*unreachable|Connection.*refused|Timeout.*waiting",
    "gc_pauses": r"Total time for which application threads were stopped:.*seconds",
    "heap_issues": r"java\.lang\.OutOfMemoryError|GC overhead limit exceeded",
}


@circuit_breaker(name="hdfs_analyzer", failure_threshold=3)
async def analyze_hdfs_logs(state: UnifiedState) -> Dict[str, Any]:
    """Analyze HDFS-specific log patterns and issues.
    
    This specialized analyzer focuses on:
    - Block corruption and replication issues
    - NameNode and DataNode health
    - Disk and network failures
    - Performance issues (GC, heap)
    """
    log_content = state.log_content
    issues = []
    recommendations = []
    metrics = {
        "total_lines": len(log_content.split("\n")),
        "error_count": 0,
        "warning_count": 0,
        "block_issues": 0,
        "node_issues": 0,
    }
    
    # Analyze each pattern
    for pattern_name, pattern in HDFS_PATTERNS.items():
        matches = re.finditer(pattern, log_content, re.MULTILINE | re.IGNORECASE)
        for match in matches:
            line_num = log_content[:match.start()].count('\n') + 1
            
            issue = {
                "type": pattern_name,
                "severity": _get_severity(pattern_name),
                "message": match.group(0),
                "line": line_num,
                "context": _get_line_context(log_content, line_num)
            }
            issues.append(issue)
            
            # Update metrics
            if "block" in pattern_name:
                metrics["block_issues"] += 1
            if "node" in pattern_name:
                metrics["node_issues"] += 1
            if issue["severity"] == "error":
                metrics["error_count"] += 1
            elif issue["severity"] == "warning":
                metrics["warning_count"] += 1
    
    # Generate HDFS-specific recommendations
    if metrics["block_issues"] > 0:
        recommendations.append({
            "category": "Data Integrity",
            "priority": "high",
            "action": "Run HDFS fsck to identify and repair corrupt blocks",
            "command": "hdfs fsck / -files -blocks -locations | grep 'CORRUPT'",
            "documentation": "https://hadoop.apache.org/docs/stable/hadoop-project-dist/hadoop-hdfs/HdfsUserGuide.html#fsck"
        })
    
    if metrics["node_issues"] > 0:
        recommendations.append({
            "category": "Cluster Health",
            "priority": "high",
            "action": "Check NameNode and DataNode status",
            "commands": [
                "hdfs dfsadmin -report",
                "hdfs haadmin -getServiceState nn1",
                "yarn node -list"
            ],
            "documentation": "https://hadoop.apache.org/docs/stable/hadoop-project-dist/hadoop-hdfs/HDFSCommands.html"
        })
    
    # Check for replication issues
    replication_issues = [i for i in issues if i["type"] == "replication_issues"]
    if replication_issues:
        recommendations.append({
            "category": "Data Availability",
            "priority": "medium",
            "action": "Rebalance HDFS cluster to fix under-replicated blocks",
            "command": "hdfs balancer -threshold 5",
            "documentation": "https://hadoop.apache.org/docs/stable/hadoop-project-dist/hadoop-hdfs/HdfsUserGuide.html#Balancer"
        })
    
    # Performance recommendations
    gc_issues = [i for i in issues if i["type"] in ["gc_pauses", "heap_issues"]]
    if gc_issues:
        recommendations.append({
            "category": "Performance",
            "priority": "medium",
            "action": "Tune JVM settings for NameNode/DataNode",
            "suggestions": [
                "Increase heap size: -Xmx8g",
                "Use G1GC: -XX:+UseG1GC",
                "Set GC logging: -XX:+PrintGCDetails"
            ],
            "documentation": "https://hadoop.apache.org/docs/stable/hadoop-project-dist/hadoop-common/ClusterSetup.html"
        })
    
    # Build analysis result
    analysis_result = {
        "summary": f"HDFS Log Analysis: Found {len(issues)} issues ({metrics['error_count']} errors, {metrics['warning_count']} warnings)",
        "log_type": "hdfs",
        "issues": issues[:50],  # Limit to top 50 issues
        "patterns": list(HDFS_PATTERNS.keys()),
        "metrics": metrics,
        "recommendations": recommendations,
        "specialized_insights": {
            "cluster_health": _assess_cluster_health(issues, metrics),
            "data_integrity": _assess_data_integrity(issues, metrics),
            "performance_status": _assess_performance(issues, metrics)
        }
    }
    
    # Update state
    state.analysis_result = analysis_result
    state.add_message(AIMessage(
        content=f"HDFS specialized analysis complete. Found {len(issues)} issues with {len(recommendations)} recommendations."
    ))
    
    return {"analysis_result": analysis_result}


def _get_severity(pattern_name: str) -> str:
    """Determine severity based on pattern type."""
    high_severity = ["block_corruption", "namenode_errors", "disk_failure", "heap_issues"]
    medium_severity = ["replication_issues", "datanode_errors", "gc_pauses"]
    
    if pattern_name in high_severity:
        return "error"
    elif pattern_name in medium_severity:
        return "warning"
    return "info"


def _get_line_context(log_content: str, line_num: int, context_lines: int = 2) -> List[str]:
    """Get surrounding lines for context."""
    lines = log_content.split("\n")
    start = max(0, line_num - context_lines - 1)
    end = min(len(lines), line_num + context_lines)
    return lines[start:end]


def _assess_cluster_health(issues: List[Dict], metrics: Dict) -> Dict[str, Any]:
    """Assess overall cluster health based on issues."""
    namenode_issues = len([i for i in issues if "namenode" in i["type"]])
    datanode_issues = len([i for i in issues if "datanode" in i["type"]])
    
    if namenode_issues > 5:
        status = "critical"
        message = "Multiple NameNode errors detected. Immediate attention required."
    elif namenode_issues > 0 or datanode_issues > 10:
        status = "degraded"
        message = "Cluster experiencing issues. Investigation recommended."
    else:
        status = "healthy"
        message = "Cluster appears to be functioning normally."
    
    return {
        "status": status,
        "message": message,
        "namenode_issues": namenode_issues,
        "datanode_issues": datanode_issues
    }


def _assess_data_integrity(issues: List[Dict], metrics: Dict) -> Dict[str, Any]:
    """Assess data integrity status."""
    corruption_count = metrics.get("block_issues", 0)
    replication_issues = len([i for i in issues if i["type"] == "replication_issues"])
    
    if corruption_count > 0:
        status = "at_risk"
        message = f"Found {corruption_count} corrupt blocks. Data loss risk."
    elif replication_issues > 10:
        status = "degraded"
        message = "Multiple under-replicated blocks. Reduced redundancy."
    else:
        status = "healthy"
        message = "Data integrity appears intact."
    
    return {
        "status": status,
        "message": message,
        "corrupt_blocks": corruption_count,
        "under_replicated_blocks": replication_issues
    }


def _assess_performance(issues: List[Dict], metrics: Dict) -> Dict[str, Any]:
    """Assess performance status."""
    gc_issues = len([i for i in issues if i["type"] == "gc_pauses"])
    heap_issues = len([i for i in issues if i["type"] == "heap_issues"])
    
    if heap_issues > 0:
        status = "critical"
        message = "Out of memory errors detected. Performance severely impacted."
    elif gc_issues > 5:
        status = "degraded"
        message = "Frequent GC pauses detected. Performance may be impacted."
    else:
        status = "normal"
        message = "No significant performance issues detected."
    
    return {
        "status": status,
        "message": message,
        "gc_pause_count": gc_issues,
        "oom_errors": heap_issues
    }