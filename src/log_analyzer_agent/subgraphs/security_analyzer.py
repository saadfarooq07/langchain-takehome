"""Specialized analyzer for security-related logs.

This analyzer focuses on authentication, authorization, security events,
and potential security threats in system logs.
"""

from typing import Dict, Any, List
import re
from datetime import datetime
from collections import Counter

from ..core.unified_state import UnifiedState
from ..core.circuit_breaker import circuit_breaker
from langchain_core.messages import AIMessage


# Security-specific patterns
SECURITY_PATTERNS = {
    "failed_login": r"Failed (password|login|authentication).*for.*from \d+\.\d+\.\d+\.\d+",
    "brute_force": r"(Failed password.*){3,}.*from same IP",
    "privilege_escalation": r"sudo:.*COMMAND=|su\[.*\].*Successful su|user.*added to.*group",
    "unauthorized_access": r"Permission denied|Access denied|Unauthorized access",
    "suspicious_commands": r"(wget|curl).*http.*\||sh\s+-c|/bin/bash.*-c|eval\(|exec\(",
    "port_scan": r"Connection.*refused|POSSIBLE.*SCAN|SYN.*flood",
    "malware_indicators": r"virus|malware|trojan|backdoor|rootkit|exploit",
    "data_exfiltration": r"scp.*@.*:|rsync.*@.*:|Large data transfer|Unusual outbound traffic",
    "config_changes": r"Changed.*configuration|Modified.*policy|Updated.*firewall",
    "service_manipulation": r"(Started|Stopped|Restarted).*service|systemctl.*(start|stop|restart)",
}


@circuit_breaker(name="security_analyzer", failure_threshold=3)
async def analyze_security_logs(state: UnifiedState) -> Dict[str, Any]:
    """Analyze security-specific log patterns and threats.
    
    This specialized analyzer focuses on:
    - Authentication and authorization issues
    - Potential security threats and attacks
    - Suspicious activities and commands
    - Configuration changes and service manipulation
    """
    log_content = state.log_content
    issues = []
    threat_indicators = []
    ip_addresses = Counter()
    user_activities = Counter()
    
    metrics = {
        "total_lines": len(log_content.split("\n")),
        "security_events": 0,
        "failed_logins": 0,
        "suspicious_activities": 0,
        "threat_level": "low",
    }
    
    # Extract and count IP addresses
    ip_pattern = r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
    for match in re.finditer(ip_pattern, log_content):
        ip_addresses[match.group(0)] += 1
    
    # Extract and count user activities
    user_pattern = r'(user|USER|User)\s*[=:]\s*(\w+)|for user (\w+)|by (\w+)'
    for match in re.finditer(user_pattern, log_content):
        user = match.group(2) or match.group(3) or match.group(4)
        if user:
            user_activities[user] += 1
    
    # Analyze security patterns
    for pattern_name, pattern in SECURITY_PATTERNS.items():
        matches = list(re.finditer(pattern, log_content, re.MULTILINE | re.IGNORECASE))
        
        for match in matches:
            line_num = log_content[:match.start()].count('\n') + 1
            
            issue = {
                "type": pattern_name,
                "severity": _get_security_severity(pattern_name, len(matches)),
                "message": match.group(0),
                "line": line_num,
                "context": _get_line_context(log_content, line_num),
                "timestamp": _extract_timestamp(match.group(0))
            }
            issues.append(issue)
            
            # Track specific threat indicators
            if pattern_name in ["brute_force", "suspicious_commands", "malware_indicators", "data_exfiltration"]:
                threat_indicators.append(issue)
            
            # Update metrics
            metrics["security_events"] += 1
            if pattern_name == "failed_login":
                metrics["failed_logins"] += 1
            if pattern_name in ["suspicious_commands", "malware_indicators"]:
                metrics["suspicious_activities"] += 1
    
    # Assess threat level
    threat_assessment = _assess_threat_level(issues, threat_indicators, ip_addresses)
    metrics["threat_level"] = threat_assessment["level"]
    
    # Generate security recommendations
    recommendations = _generate_security_recommendations(
        issues, threat_indicators, ip_addresses, user_activities, threat_assessment
    )
    
    # Build analysis result
    analysis_result = {
        "summary": f"Security Log Analysis: {metrics['security_events']} security events detected. Threat level: {metrics['threat_level'].upper()}",
        "log_type": "security",
        "issues": issues[:100],  # Limit to top 100 issues
        "threat_indicators": threat_indicators,
        "metrics": metrics,
        "recommendations": recommendations,
        "specialized_insights": {
            "threat_assessment": threat_assessment,
            "top_attacking_ips": ip_addresses.most_common(10),
            "suspicious_users": [u for u, c in user_activities.most_common(10) if c > 10],
            "attack_timeline": _build_attack_timeline(threat_indicators),
            "security_posture": _assess_security_posture(issues, metrics)
        }
    }
    
    # Update state
    state.analysis_result = analysis_result
    state.add_message(AIMessage(
        content=f"Security analysis complete. Threat level: {metrics['threat_level'].upper()}. "
                f"Found {metrics['security_events']} security events with {len(threat_indicators)} threat indicators."
    ))
    
    return {"analysis_result": analysis_result}


def _get_security_severity(pattern_name: str, match_count: int) -> str:
    """Determine severity based on pattern type and frequency."""
    critical_patterns = ["brute_force", "malware_indicators", "data_exfiltration", "privilege_escalation"]
    high_patterns = ["suspicious_commands", "unauthorized_access", "port_scan"]
    
    # Escalate severity based on frequency
    if pattern_name in critical_patterns or (pattern_name == "failed_login" and match_count > 10):
        return "critical"
    elif pattern_name in high_patterns or (pattern_name == "failed_login" and match_count > 5):
        return "high"
    elif pattern_name in ["config_changes", "service_manipulation"]:
        return "medium"
    return "low"


def _extract_timestamp(log_line: str) -> Optional[str]:
    """Extract timestamp from log line."""
    # Common timestamp patterns
    patterns = [
        r'\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}',
        r'\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}',
        r'\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}:\d{2}'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, log_line)
        if match:
            return match.group(0)
    return None


def _assess_threat_level(issues: List[Dict], threat_indicators: List[Dict], ip_addresses: Counter) -> Dict[str, Any]:
    """Assess overall threat level based on detected issues."""
    critical_count = len([i for i in issues if i["severity"] == "critical"])
    high_count = len([i for i in issues if i["severity"] == "high"])
    
    # Check for attack patterns
    brute_force_ips = [ip for ip, count in ip_addresses.most_common() if count > 20]
    
    if critical_count > 5 or len(threat_indicators) > 10:
        level = "critical"
        message = "Active security incident detected. Immediate response required."
    elif critical_count > 0 or high_count > 10 or len(brute_force_ips) > 0:
        level = "high"
        message = "Significant security activity detected. Investigation recommended."
    elif high_count > 5 or len(threat_indicators) > 5:
        level = "medium"
        message = "Elevated security activity. Monitor closely."
    else:
        level = "low"
        message = "Normal security activity levels."
    
    return {
        "level": level,
        "message": message,
        "critical_events": critical_count,
        "high_events": high_count,
        "threat_indicators": len(threat_indicators),
        "suspicious_ips": brute_force_ips
    }


def _generate_security_recommendations(
    issues: List[Dict],
    threat_indicators: List[Dict],
    ip_addresses: Counter,
    user_activities: Counter,
    threat_assessment: Dict
) -> List[Dict[str, Any]]:
    """Generate security-specific recommendations."""
    recommendations = []
    
    # Critical threat response
    if threat_assessment["level"] in ["critical", "high"]:
        recommendations.append({
            "category": "Incident Response",
            "priority": "critical",
            "action": "Initiate security incident response procedure",
            "steps": [
                "1. Isolate affected systems",
                "2. Preserve evidence (logs, memory dumps)",
                "3. Block suspicious IPs at firewall",
                "4. Reset compromised credentials",
                "5. Conduct forensic analysis"
            ],
            "documentation": "https://www.sans.org/white-papers/33901/"
        })
    
    # Brute force mitigation
    failed_logins = [i for i in issues if i["type"] == "failed_login"]
    if len(failed_logins) > 10:
        suspicious_ips = [ip for ip, count in ip_addresses.most_common(5) if count > 10]
        recommendations.append({
            "category": "Access Control",
            "priority": "high",
            "action": "Implement brute force protection",
            "commands": [
                f"iptables -A INPUT -s {ip} -j DROP" for ip in suspicious_ips[:3]
            ],
            "suggestions": [
                "Enable fail2ban or similar IPS",
                "Implement account lockout policies",
                "Use multi-factor authentication",
                "Deploy CAPTCHA for login forms"
            ]
        })
    
    # Malware response
    malware_indicators = [i for i in issues if i["type"] == "malware_indicators"]
    if malware_indicators:
        recommendations.append({
            "category": "Malware Response",
            "priority": "critical",
            "action": "Scan for malware and rootkits",
            "commands": [
                "clamscan -r /",
                "rkhunter --check",
                "chkrootkit",
                "aide --check"
            ],
            "documentation": "https://www.cisa.gov/malware-analysis-reports"
        })
    
    # Configuration hardening
    config_changes = [i for i in issues if i["type"] == "config_changes"]
    if config_changes:
        recommendations.append({
            "category": "Configuration Management",
            "priority": "medium",
            "action": "Review and audit configuration changes",
            "suggestions": [
                "Implement configuration management (Ansible, Puppet)",
                "Enable audit logging for all config changes",
                "Use version control for configurations",
                "Implement change approval process"
            ]
        })
    
    return recommendations


def _build_attack_timeline(threat_indicators: List[Dict]) -> List[Dict[str, Any]]:
    """Build a timeline of attack events."""
    timeline = []
    
    for indicator in sorted(threat_indicators, key=lambda x: x.get("timestamp", "")):
        if indicator.get("timestamp"):
            timeline.append({
                "timestamp": indicator["timestamp"],
                "event": indicator["type"],
                "severity": indicator["severity"],
                "details": indicator["message"][:100]
            })
    
    return timeline[:20]  # Limit to most recent 20 events


def _assess_security_posture(issues: List[Dict], metrics: Dict) -> Dict[str, Any]:
    """Assess overall security posture."""
    score = 100
    
    # Deduct points based on issues
    score -= len([i for i in issues if i["severity"] == "critical"]) * 20
    score -= len([i for i in issues if i["severity"] == "high"]) * 10
    score -= len([i for i in issues if i["severity"] == "medium"]) * 5
    
    score = max(0, score)
    
    if score >= 80:
        rating = "strong"
        message = "Security posture is strong with minimal issues."
    elif score >= 60:
        rating = "moderate"
        message = "Security posture needs improvement in key areas."
    elif score >= 40:
        rating = "weak"
        message = "Security posture has significant vulnerabilities."
    else:
        rating = "critical"
        message = "Security posture is critically compromised."
    
    return {
        "score": score,
        "rating": rating,
        "message": message,
        "recommendations_count": 5 - (score // 20)
    }


def _get_line_context(log_content: str, line_num: int, context_lines: int = 3) -> List[str]:
    """Get surrounding lines for context."""
    lines = log_content.split("\n")
    start = max(0, line_num - context_lines - 1)
    end = min(len(lines), line_num + context_lines)
    return lines[start:end]