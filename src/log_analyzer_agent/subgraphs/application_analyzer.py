"""Specialized analyzer for application logs.

This analyzer focuses on application-specific patterns, errors, performance issues,
and provides recommendations for web applications, APIs, and services.
"""

from typing import Dict, Any, List, Optional
import re
from collections import Counter, defaultdict
from datetime import datetime

from ..core.unified_state import UnifiedState
from ..core.circuit_breaker import circuit_breaker
from langchain_core.messages import AIMessage


# Application-specific patterns
APPLICATION_PATTERNS = {
    "http_errors": r"HTTP/\d\.\d\"\s+[45]\d{2}|Status:\s*[45]\d{2}",
    "exceptions": r"Exception|Error|Traceback|at\s+\w+\.\w+\(.*:\d+\)|caused by:",
    "null_pointer": r"NullPointerException|null reference|undefined.*null",
    "database_errors": r"SQLException|Database.*error|Connection.*failed|Query.*failed",
    "timeout_errors": r"Timeout|timed out|deadline exceeded|connection reset",
    "memory_issues": r"OutOfMemoryError|heap.*space|memory.*exhausted|allocation.*failed",
    "thread_issues": r"deadlock|thread.*blocked|thread.*waiting|ThreadDeath",
    "api_errors": r"API.*error|endpoint.*failed|request.*failed|response.*error",
    "validation_errors": r"validation.*failed|invalid.*input|constraint.*violation",
    "startup_errors": r"Failed to start|startup.*failed|initialization.*error|bootstrap.*error",
}

# HTTP status code categories
HTTP_STATUS_CATEGORIES = {
    "client_errors": range(400, 500),
    "server_errors": range(500, 600),
    "success": range(200, 300),
    "redirects": range(300, 400)
}


@circuit_breaker(name="application_analyzer", failure_threshold=3)
async def analyze_application_logs(state: UnifiedState) -> Dict[str, Any]:
    """Analyze application-specific log patterns and issues.
    
    This specialized analyzer focuses on:
    - HTTP errors and status codes
    - Application exceptions and stack traces
    - Performance and resource issues
    - API and service health
    """
    log_content = state.log_content
    issues = []
    error_traces = []
    endpoint_stats = defaultdict(lambda: {"total": 0, "errors": 0, "avg_time": 0})
    http_status_counts = Counter()
    
    metrics = {
        "total_lines": len(log_content.split("\n")),
        "total_errors": 0,
        "total_exceptions": 0,
        "http_4xx": 0,
        "http_5xx": 0,
        "performance_issues": 0,
        "availability": 100.0,
    }
    
    # Extract HTTP status codes and response times
    http_pattern = r'(\S+)\s+"([A-Z]+)\s+([^"]+)"\s+(\d{3})\s+(\d+)(?:\s+(\d+)ms)?'
    for match in re.finditer(http_pattern, log_content):
        ip, method, endpoint, status, size, response_time = match.groups()
        status_code = int(status)
        
        http_status_counts[status_code] += 1
        endpoint_stats[endpoint]["total"] += 1
        
        if status_code >= 400:
            endpoint_stats[endpoint]["errors"] += 1
            if 400 <= status_code < 500:
                metrics["http_4xx"] += 1
            elif status_code >= 500:
                metrics["http_5xx"] += 1
        
        if response_time:
            # Track response time for performance analysis
            endpoint_stats[endpoint]["avg_time"] = int(response_time)
    
    # Analyze application patterns
    for pattern_name, pattern in APPLICATION_PATTERNS.items():
        matches = list(re.finditer(pattern, log_content, re.MULTILINE | re.IGNORECASE))
        
        for match in matches:
            line_num = log_content[:match.start()].count('\n') + 1
            
            # Extract stack trace if it's an exception
            stack_trace = None
            if pattern_name in ["exceptions", "null_pointer"]:
                stack_trace = _extract_stack_trace(log_content, match.start())
                if stack_trace:
                    error_traces.append(stack_trace)
            
            issue = {
                "type": pattern_name,
                "severity": _get_app_severity(pattern_name, len(matches)),
                "message": match.group(0),
                "line": line_num,
                "context": _get_line_context(log_content, line_num),
                "stack_trace": stack_trace
            }
            issues.append(issue)
            
            # Update metrics
            metrics["total_errors"] += 1
            if pattern_name in ["exceptions", "null_pointer", "database_errors"]:
                metrics["total_exceptions"] += 1
            if pattern_name in ["memory_issues", "thread_issues", "timeout_errors"]:
                metrics["performance_issues"] += 1
    
    # Calculate availability
    total_requests = sum(endpoint_stats[e]["total"] for e in endpoint_stats)
    total_errors = sum(endpoint_stats[e]["errors"] for e in endpoint_stats)
    if total_requests > 0:
        metrics["availability"] = ((total_requests - total_errors) / total_requests) * 100
    
    # Analyze error patterns and generate insights
    error_analysis = _analyze_error_patterns(error_traces, issues)
    performance_analysis = _analyze_performance(endpoint_stats, issues)
    
    # Generate application-specific recommendations
    recommendations = _generate_app_recommendations(
        issues, error_analysis, performance_analysis, endpoint_stats, metrics
    )
    
    # Build analysis result
    analysis_result = {
        "summary": f"Application Log Analysis: {metrics['total_errors']} errors detected. "
                   f"Availability: {metrics['availability']:.1f}%. "
                   f"{metrics['total_exceptions']} exceptions found.",
        "log_type": "application",
        "issues": issues[:100],  # Limit to top 100 issues
        "metrics": metrics,
        "recommendations": recommendations,
        "specialized_insights": {
            "error_analysis": error_analysis,
            "performance_analysis": performance_analysis,
            "endpoint_health": _get_endpoint_health(endpoint_stats),
            "http_status_distribution": dict(http_status_counts.most_common(10)),
            "critical_errors": [i for i in issues if i["severity"] == "critical"][:10],
            "service_health": _assess_service_health(metrics, issues)
        }
    }
    
    # Update state
    state.analysis_result = analysis_result
    state.add_message(AIMessage(
        content=f"Application analysis complete. Found {metrics['total_errors']} errors "
                f"with {metrics['availability']:.1f}% availability. "
                f"{len(recommendations)} recommendations provided."
    ))
    
    return {"analysis_result": analysis_result}


def _get_app_severity(pattern_name: str, match_count: int) -> str:
    """Determine severity based on pattern type and frequency."""
    critical_patterns = ["database_errors", "startup_errors", "memory_issues"]
    high_patterns = ["exceptions", "null_pointer", "thread_issues", "timeout_errors"]
    
    if pattern_name in critical_patterns or (pattern_name == "http_errors" and match_count > 50):
        return "critical"
    elif pattern_name in high_patterns or (pattern_name == "http_errors" and match_count > 20):
        return "high"
    elif pattern_name in ["api_errors", "validation_errors"]:
        return "medium"
    return "low"


def _extract_stack_trace(log_content: str, start_pos: int, max_lines: int = 20) -> Optional[str]:
    """Extract stack trace from exception."""
    lines = log_content[start_pos:].split('\n')[:max_lines]
    stack_trace_lines = []
    
    for line in lines:
        # Common stack trace patterns
        if re.match(r'^\s*(at|Caused by:|\.{3})', line):
            stack_trace_lines.append(line)
        elif stack_trace_lines and not line.strip():
            break  # Empty line ends stack trace
        elif stack_trace_lines:
            stack_trace_lines.append(line)
    
    return '\n'.join(stack_trace_lines) if stack_trace_lines else None


def _analyze_error_patterns(error_traces: List[str], issues: List[Dict]) -> Dict[str, Any]:
    """Analyze error patterns and identify root causes."""
    error_types = Counter()
    root_causes = []
    
    # Count error types
    for issue in issues:
        error_types[issue["type"]] += 1
    
    # Analyze stack traces for common patterns
    common_exceptions = Counter()
    for trace in error_traces:
        # Extract exception class names
        exception_match = re.search(r'(\w+Exception|\w+Error):', trace)
        if exception_match:
            common_exceptions[exception_match.group(1)] += 1
    
    # Identify potential root causes
    if common_exceptions:
        most_common = common_exceptions.most_common(3)
        for exc, count in most_common:
            if "NullPointer" in exc:
                root_causes.append({
                    "type": "null_reference",
                    "description": "Frequent null reference errors indicate missing validation",
                    "count": count
                })
            elif "Database" in exc or "SQL" in exc:
                root_causes.append({
                    "type": "database",
                    "description": "Database connectivity or query issues",
                    "count": count
                })
            elif "OutOfMemory" in exc:
                root_causes.append({
                    "type": "memory",
                    "description": "Memory leaks or insufficient heap size",
                    "count": count
                })
    
    return {
        "error_distribution": dict(error_types.most_common()),
        "common_exceptions": dict(common_exceptions.most_common(5)),
        "root_causes": root_causes,
        "total_unique_errors": len(error_types)
    }


def _analyze_performance(endpoint_stats: Dict, issues: List[Dict]) -> Dict[str, Any]:
    """Analyze application performance metrics."""
    slow_endpoints = []
    error_prone_endpoints = []
    
    for endpoint, stats in endpoint_stats.items():
        error_rate = (stats["errors"] / stats["total"] * 100) if stats["total"] > 0 else 0
        
        # Identify slow endpoints (>1000ms avg response time)
        if stats.get("avg_time", 0) > 1000:
            slow_endpoints.append({
                "endpoint": endpoint,
                "avg_response_time": stats["avg_time"],
                "requests": stats["total"]
            })
        
        # Identify error-prone endpoints (>10% error rate)
        if error_rate > 10:
            error_prone_endpoints.append({
                "endpoint": endpoint,
                "error_rate": error_rate,
                "errors": stats["errors"],
                "total": stats["total"]
            })
    
    # Sort by severity
    slow_endpoints.sort(key=lambda x: x["avg_response_time"], reverse=True)
    error_prone_endpoints.sort(key=lambda x: x["error_rate"], reverse=True)
    
    return {
        "slow_endpoints": slow_endpoints[:10],
        "error_prone_endpoints": error_prone_endpoints[:10],
        "performance_issues_count": len([i for i in issues if i["type"] in ["timeout_errors", "memory_issues"]])
    }


def _get_endpoint_health(endpoint_stats: Dict) -> List[Dict[str, Any]]:
    """Calculate health score for each endpoint."""
    endpoint_health = []
    
    for endpoint, stats in endpoint_stats.items():
        if stats["total"] == 0:
            continue
            
        error_rate = (stats["errors"] / stats["total"]) * 100
        
        # Calculate health score (0-100)
        health_score = 100
        health_score -= min(error_rate * 2, 50)  # Errors can reduce score by up to 50
        health_score -= min(stats.get("avg_time", 0) / 100, 30)  # Slow response reduces by up to 30
        
        health_score = max(0, health_score)
        
        endpoint_health.append({
            "endpoint": endpoint,
            "health_score": round(health_score, 1),
            "total_requests": stats["total"],
            "error_rate": round(error_rate, 1),
            "avg_response_time": stats.get("avg_time", 0)
        })
    
    # Sort by health score
    endpoint_health.sort(key=lambda x: x["health_score"])
    
    return endpoint_health[:20]  # Top 20 unhealthiest endpoints


def _generate_app_recommendations(
    issues: List[Dict],
    error_analysis: Dict,
    performance_analysis: Dict,
    endpoint_stats: Dict,
    metrics: Dict
) -> List[Dict[str, Any]]:
    """Generate application-specific recommendations."""
    recommendations = []
    
    # Error handling recommendations
    if metrics["total_exceptions"] > 10:
        recommendations.append({
            "category": "Error Handling",
            "priority": "high",
            "action": "Improve error handling and validation",
            "suggestions": [
                "Add input validation for all API endpoints",
                "Implement global exception handlers",
                "Add null checks before object access",
                "Use try-catch blocks for external service calls"
            ],
            "code_example": """
// Example: Global error handler
app.use((err, req, res, next) => {
    logger.error('Unhandled error:', err);
    res.status(500).json({ error: 'Internal server error' });
});
"""
        })
    
    # Performance recommendations
    if performance_analysis["slow_endpoints"]:
        recommendations.append({
            "category": "Performance Optimization",
            "priority": "high",
            "action": "Optimize slow endpoints",
            "slow_endpoints": performance_analysis["slow_endpoints"][:5],
            "suggestions": [
                "Add caching for frequently accessed data",
                "Optimize database queries (add indexes)",
                "Implement pagination for large datasets",
                "Use connection pooling for database",
                "Consider async processing for heavy operations"
            ]
        })
    
    # Memory optimization
    memory_issues = [i for i in issues if i["type"] == "memory_issues"]
    if memory_issues:
        recommendations.append({
            "category": "Memory Management",
            "priority": "critical",
            "action": "Address memory leaks and optimize heap usage",
            "commands": [
                "jmap -heap <pid>  # Check heap usage",
                "jstat -gcutil <pid> 1000  # Monitor GC",
                "mat analyzer  # Use Memory Analyzer Tool"
            ],
            "jvm_options": [
                "-Xmx4g  # Increase max heap",
                "-XX:+UseG1GC  # Use G1 garbage collector",
                "-XX:+HeapDumpOnOutOfMemoryError"
            ]
        })
    
    # Database optimization
    db_errors = [i for i in issues if i["type"] == "database_errors"]
    if db_errors:
        recommendations.append({
            "category": "Database Optimization",
            "priority": "high",
            "action": "Improve database reliability",
            "suggestions": [
                "Implement connection pooling",
                "Add retry logic for transient failures",
                "Optimize slow queries",
                "Add database monitoring",
                "Consider read replicas for scaling"
            ],
            "monitoring_queries": [
                "SHOW PROCESSLIST;  # MySQL",
                "SELECT * FROM pg_stat_activity;  # PostgreSQL"
            ]
        })
    
    # Monitoring recommendations
    if metrics["availability"] < 99:
        recommendations.append({
            "category": "Monitoring & Alerting",
            "priority": "medium",
            "action": "Enhance monitoring and alerting",
            "suggestions": [
                "Set up APM (Application Performance Monitoring)",
                "Configure alerts for error rates > 1%",
                "Add health check endpoints",
                "Implement distributed tracing",
                "Set up centralized logging (ELK stack)"
            ],
            "tools": ["Datadog", "New Relic", "Prometheus + Grafana", "ELK Stack"]
        })
    
    return recommendations


def _assess_service_health(metrics: Dict, issues: List[Dict]) -> Dict[str, Any]:
    """Assess overall service health."""
    health_score = 100
    
    # Deduct points based on issues
    health_score -= min(metrics.get("http_5xx", 0) * 0.5, 30)
    health_score -= min(metrics.get("total_exceptions", 0) * 0.3, 20)
    health_score -= min((100 - metrics.get("availability", 100)) * 2, 40)
    
    health_score = max(0, health_score)
    
    if health_score >= 90:
        status = "healthy"
        message = "Service is operating normally"
    elif health_score >= 70:
        status = "degraded"
        message = "Service experiencing minor issues"
    elif health_score >= 50:
        status = "impaired"
        message = "Service has significant problems"
    else:
        status = "critical"
        message = "Service is severely impacted"
    
    return {
        "score": round(health_score, 1),
        "status": status,
        "message": message,
        "availability": round(metrics.get("availability", 0), 2),
        "error_rate": round((metrics.get("http_4xx", 0) + metrics.get("http_5xx", 0)) / max(metrics.get("total_lines", 1), 1) * 100, 2)
    }


def _get_line_context(log_content: str, line_num: int, context_lines: int = 2) -> List[str]:
    """Get surrounding lines for context."""
    lines = log_content.split("\n")
    start = max(0, line_num - context_lines - 1)
    end = min(len(lines), line_num + context_lines)
    return lines[start:end]