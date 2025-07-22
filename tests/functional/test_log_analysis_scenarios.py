"""
Functional tests for various log analysis scenarios in the Log Analyzer Agent.
"""

import pytest
import asyncio
import json
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

from src.log_analyzer_agent.graph import create_graph
from src.log_analyzer_agent.core.improved_graph import create_improved_graph


class TestDatabaseIssueScenarios:
    """Test scenarios involving database-related issues."""
    
    @pytest.fixture
    def database_timeout_log(self):
        """Database connection timeout log scenario."""
        return """
2024-01-15 10:30:15 ERROR [DatabaseConnection] Connection failed: timeout after 30s
2024-01-15 10:30:16 INFO [RetryManager] Retrying connection attempt 1/3
2024-01-15 10:30:20 ERROR [DatabaseConnection] Connection failed: timeout after 30s
2024-01-15 10:30:21 INFO [RetryManager] Retrying connection attempt 2/3
2024-01-15 10:30:25 ERROR [DatabaseConnection] Connection failed: timeout after 30s
2024-01-15 10:30:26 ERROR [RetryManager] Max retries exceeded, giving up
2024-01-15 10:30:27 CRITICAL [Application] Database unavailable, shutting down
        """
    
    @pytest.fixture
    def database_deadlock_log(self):
        """Database deadlock scenario."""
        return """
2024-01-15 10:30:15 INFO [TransactionManager] Starting transaction TX-12345
2024-01-15 10:30:16 INFO [TransactionManager] Starting transaction TX-12346
2024-01-15 10:30:17 WARN [DatabaseConnection] Lock wait timeout exceeded for TX-12345
2024-01-15 10:30:18 WARN [DatabaseConnection] Lock wait timeout exceeded for TX-12346
2024-01-15 10:30:19 ERROR [TransactionManager] Deadlock detected between TX-12345 and TX-12346
2024-01-15 10:30:20 ERROR [TransactionManager] Rolling back transaction TX-12345
2024-01-15 10:30:21 ERROR [TransactionManager] Rolling back transaction TX-12346
2024-01-15 10:30:22 CRITICAL [Application] Database deadlock caused transaction failures
        """
    
    @pytest.mark.functional
    @pytest.mark.asyncio
    async def test_database_timeout_analysis(self, database_timeout_log, mock_runnable_config):
        """Test analysis of database timeout issues."""
        graph = create_graph()
        compiled_graph = graph.compile()
        
        initial_state = {
            "log_content": database_timeout_log,
            "messages": [],
            "iteration_count": 0,
            "analysis_complete": False
        }
        
        with patch('src.log_analyzer_agent.nodes.analysis.get_model') as mock_analysis_model, \
             patch('src.log_analyzer_agent.nodes.validation.get_orchestration_model') as mock_validation_model:
            
            # Expected analysis for database timeout scenario
            mock_analysis_model.return_value.generate_content.return_value.text = """
            {
                "summary": "Database connection timeout issues causing application shutdown",
                "issues": [
                    {
                        "severity": "critical",
                        "category": "connectivity",
                        "description": "Repeated database connection timeouts leading to application shutdown",
                        "affected_components": ["DatabaseConnection", "RetryManager", "Application"],
                        "first_occurrence": "2024-01-15 10:30:15",
                        "frequency": 3,
                        "pattern": "Connection timeout after 30s, retry attempts exhausted"
                    }
                ],
                "suggestions": [
                    {
                        "priority": "critical",
                        "category": "configuration",
                        "description": "Increase database connection timeout",
                        "implementation": "Update connection timeout from 30s to 60s or higher",
                        "estimated_impact": "Reduce timeout-related connection failures"
                    },
                    {
                        "priority": "high",
                        "category": "resilience",
                        "description": "Implement exponential backoff for retries",
                        "implementation": "Add exponential backoff between retry attempts",
                        "estimated_impact": "Better handling of temporary database unavailability"
                    },
                    {
                        "priority": "medium",
                        "category": "monitoring",
                        "description": "Add database health monitoring",
                        "implementation": "Implement proactive database health checks",
                        "estimated_impact": "Early detection of database issues"
                    }
                ]
            }
            """
            
            mock_validation_model.return_value.chat.completions.create.return_value.choices[0].message.content = """
            {
                "is_valid": true,
                "completeness_score": 0.95,
                "accuracy_score": 0.9,
                "feedback": "Excellent analysis of database timeout scenario with comprehensive suggestions"
            }
            """
            
            result = await compiled_graph.ainvoke(initial_state, config=mock_runnable_config)
            
            # Verify analysis results
            assert result is not None
            assert result.get("analysis_complete") is True
            
            analysis = result["analysis_result"]
            assert "database" in analysis["summary"].lower()
            assert "timeout" in analysis["summary"].lower()
            
            # Verify critical issues identified
            issues = analysis["issues"]
            assert len(issues) > 0
            critical_issues = [issue for issue in issues if issue["severity"] == "critical"]
            assert len(critical_issues) > 0
            
            # Verify actionable suggestions
            suggestions = analysis["suggestions"]
            assert len(suggestions) >= 2
            critical_suggestions = [s for s in suggestions if s["priority"] == "critical"]
            assert len(critical_suggestions) > 0
    
    @pytest.mark.functional
    @pytest.mark.asyncio
    async def test_database_deadlock_analysis(self, database_deadlock_log, mock_runnable_config):
        """Test analysis of database deadlock issues."""
        graph = create_graph()
        compiled_graph = graph.compile()
        
        initial_state = {
            "log_content": database_deadlock_log,
            "messages": [],
            "iteration_count": 0,
            "analysis_complete": False
        }
        
        with patch('src.log_analyzer_agent.nodes.analysis.get_model') as mock_analysis_model, \
             patch('src.log_analyzer_agent.nodes.validation.get_orchestration_model') as mock_validation_model:
            
            mock_analysis_model.return_value.generate_content.return_value.text = """
            {
                "summary": "Database deadlock detected causing transaction failures",
                "issues": [
                    {
                        "severity": "high",
                        "category": "concurrency",
                        "description": "Database deadlock between concurrent transactions",
                        "affected_components": ["TransactionManager", "DatabaseConnection"],
                        "first_occurrence": "2024-01-15 10:30:19",
                        "frequency": 1,
                        "transactions_involved": ["TX-12345", "TX-12346"]
                    }
                ],
                "suggestions": [
                    {
                        "priority": "high",
                        "category": "design",
                        "description": "Implement consistent lock ordering",
                        "implementation": "Ensure all transactions acquire locks in the same order",
                        "estimated_impact": "Prevent deadlock scenarios"
                    },
                    {
                        "priority": "medium",
                        "category": "configuration",
                        "description": "Tune deadlock detection timeout",
                        "implementation": "Adjust database deadlock detection settings",
                        "estimated_impact": "Faster deadlock resolution"
                    }
                ]
            }
            """
            
            mock_validation_model.return_value.chat.completions.create.return_value.choices[0].message.content = """
            {
                "is_valid": true,
                "completeness_score": 0.85,
                "accuracy_score": 0.9,
                "feedback": "Good analysis of deadlock scenario with appropriate suggestions"
            }
            """
            
            result = await compiled_graph.ainvoke(initial_state, config=mock_runnable_config)
            
            # Verify deadlock-specific analysis
            assert result is not None
            analysis = result["analysis_result"]
            assert "deadlock" in analysis["summary"].lower()
            
            issues = analysis["issues"]
            assert any("deadlock" in issue["description"].lower() for issue in issues)
            assert any("concurrency" in issue["category"].lower() for issue in issues)


class TestSecurityIncidentScenarios:
    """Test scenarios involving security incidents."""
    
    @pytest.fixture
    def brute_force_attack_log(self):
        """Brute force attack scenario."""
        return """
2024-01-15 10:30:15 INFO [AuthService] User login attempt: admin from IP 192.168.1.100
2024-01-15 10:30:16 WARN [AuthService] Failed login attempt: admin from IP 192.168.1.100 - invalid password
2024-01-15 10:30:17 WARN [AuthService] Failed login attempt: admin from IP 192.168.1.100 - invalid password
2024-01-15 10:30:18 WARN [AuthService] Failed login attempt: admin from IP 192.168.1.100 - invalid password
2024-01-15 10:30:19 WARN [AuthService] Failed login attempt: admin from IP 192.168.1.100 - invalid password
2024-01-15 10:30:20 WARN [AuthService] Failed login attempt: admin from IP 192.168.1.100 - invalid password
2024-01-15 10:30:21 ERROR [SecurityMonitor] Multiple failed login attempts detected for admin from IP 192.168.1.100
2024-01-15 10:30:22 CRITICAL [SecurityMonitor] IP 192.168.1.100 blocked due to suspicious activity
        """
    
    @pytest.fixture
    def sql_injection_log(self):
        """SQL injection attempt scenario."""
        return """
2024-01-15 10:30:15 INFO [WebServer] GET /search?q=products from IP 192.168.1.200
2024-01-15 10:30:16 WARN [DatabaseQuery] Suspicious query detected: SELECT * FROM products WHERE name = 'products' OR '1'='1'
2024-01-15 10:30:17 ERROR [SecurityFilter] SQL injection attempt blocked from IP 192.168.1.200
2024-01-15 10:30:18 CRITICAL [SecurityMonitor] Potential SQL injection attack from IP 192.168.1.200
2024-01-15 10:30:19 INFO [SecurityMonitor] IP 192.168.1.200 added to security watchlist
        """
    
    @pytest.mark.functional
    @pytest.mark.asyncio
    async def test_brute_force_attack_analysis(self, brute_force_attack_log, mock_runnable_config):
        """Test analysis of brute force attack scenario."""
        graph = create_graph()
        compiled_graph = graph.compile()
        
        initial_state = {
            "log_content": brute_force_attack_log,
            "messages": [],
            "iteration_count": 0,
            "analysis_complete": False
        }
        
        with patch('src.log_analyzer_agent.nodes.analysis.get_model') as mock_analysis_model, \
             patch('src.log_analyzer_agent.nodes.validation.get_orchestration_model') as mock_validation_model:
            
            mock_analysis_model.return_value.generate_content.return_value.text = """
            {
                "summary": "Brute force attack detected and blocked by security systems",
                "issues": [
                    {
                        "severity": "critical",
                        "category": "security",
                        "description": "Brute force login attack against admin account",
                        "affected_components": ["AuthService", "SecurityMonitor"],
                        "first_occurrence": "2024-01-15 10:30:16",
                        "frequency": 5,
                        "attack_source": "192.168.1.100",
                        "target_account": "admin"
                    }
                ],
                "suggestions": [
                    {
                        "priority": "critical",
                        "category": "security",
                        "description": "Implement account lockout policy",
                        "implementation": "Lock accounts after 3 failed attempts for 15 minutes",
                        "estimated_impact": "Prevent brute force attacks"
                    },
                    {
                        "priority": "high",
                        "category": "monitoring",
                        "description": "Enhance security monitoring",
                        "implementation": "Add real-time alerts for failed login patterns",
                        "estimated_impact": "Faster detection of security incidents"
                    },
                    {
                        "priority": "medium",
                        "category": "authentication",
                        "description": "Implement multi-factor authentication",
                        "implementation": "Require MFA for admin accounts",
                        "estimated_impact": "Additional security layer"
                    }
                ]
            }
            """
            
            mock_validation_model.return_value.chat.completions.create.return_value.choices[0].message.content = """
            {
                "is_valid": true,
                "completeness_score": 0.9,
                "accuracy_score": 0.95,
                "feedback": "Excellent security analysis with appropriate incident response suggestions"
            }
            """
            
            result = await compiled_graph.ainvoke(initial_state, config=mock_runnable_config)
            
            # Verify security analysis
            assert result is not None
            analysis = result["analysis_result"]
            assert "brute force" in analysis["summary"].lower() or "attack" in analysis["summary"].lower()
            
            issues = analysis["issues"]
            security_issues = [issue for issue in issues if issue["category"] == "security"]
            assert len(security_issues) > 0
            assert any(issue["severity"] == "critical" for issue in security_issues)
    
    @pytest.mark.functional
    @pytest.mark.asyncio
    async def test_sql_injection_analysis(self, sql_injection_log, mock_runnable_config):
        """Test analysis of SQL injection attempt scenario."""
        graph = create_graph()
        compiled_graph = graph.compile()
        
        initial_state = {
            "log_content": sql_injection_log,
            "messages": [],
            "iteration_count": 0,
            "analysis_complete": False
        }
        
        with patch('src.log_analyzer_agent.nodes.analysis.get_model') as mock_analysis_model, \
             patch('src.log_analyzer_agent.nodes.validation.get_orchestration_model') as mock_validation_model:
            
            mock_analysis_model.return_value.generate_content.return_value.text = """
            {
                "summary": "SQL injection attack attempt detected and blocked",
                "issues": [
                    {
                        "severity": "critical",
                        "category": "security",
                        "description": "SQL injection attack attempt blocked by security filters",
                        "affected_components": ["WebServer", "DatabaseQuery", "SecurityFilter"],
                        "first_occurrence": "2024-01-15 10:30:16",
                        "frequency": 1,
                        "attack_source": "192.168.1.200",
                        "attack_vector": "Query parameter manipulation"
                    }
                ],
                "suggestions": [
                    {
                        "priority": "critical",
                        "category": "security",
                        "description": "Review and strengthen input validation",
                        "implementation": "Implement parameterized queries and input sanitization",
                        "estimated_impact": "Prevent SQL injection vulnerabilities"
                    },
                    {
                        "priority": "high",
                        "category": "monitoring",
                        "description": "Enhance web application firewall rules",
                        "implementation": "Update WAF rules to detect and block injection attempts",
                        "estimated_impact": "Better protection against web attacks"
                    }
                ]
            }
            """
            
            mock_validation_model.return_value.chat.completions.create.return_value.choices[0].message.content = """
            {
                "is_valid": true,
                "completeness_score": 0.85,
                "accuracy_score": 0.9,
                "feedback": "Good analysis of SQL injection attempt with security-focused recommendations"
            }
            """
            
            result = await compiled_graph.ainvoke(initial_state, config=mock_runnable_config)
            
            # Verify SQL injection analysis
            assert result is not None
            analysis = result["analysis_result"]
            assert "sql injection" in analysis["summary"].lower() or "injection" in analysis["summary"].lower()


class TestPerformanceIssueScenarios:
    """Test scenarios involving performance issues."""
    
    @pytest.fixture
    def memory_leak_log(self):
        """Memory leak scenario."""
        return """
2024-01-15 10:30:15 INFO [MemoryMonitor] Current memory usage: 512MB
2024-01-15 10:35:15 INFO [MemoryMonitor] Current memory usage: 768MB
2024-01-15 10:40:15 WARN [MemoryMonitor] Current memory usage: 1024MB - threshold exceeded
2024-01-15 10:45:15 WARN [MemoryMonitor] Current memory usage: 1280MB - significant increase
2024-01-15 10:50:15 ERROR [MemoryMonitor] Current memory usage: 1536MB - critical level
2024-01-15 10:55:15 CRITICAL [Application] Out of memory error - application unstable
2024-01-15 10:56:15 ERROR [Application] Garbage collection taking too long
2024-01-15 10:57:15 CRITICAL [Application] Application crashed due to memory exhaustion
        """
    
    @pytest.fixture
    def high_cpu_log(self):
        """High CPU usage scenario."""
        return """
2024-01-15 10:30:15 INFO [CPUMonitor] Current CPU usage: 45%
2024-01-15 10:30:30 WARN [CPUMonitor] Current CPU usage: 75% - elevated
2024-01-15 10:30:45 WARN [CPUMonitor] Current CPU usage: 85% - high
2024-01-15 10:31:00 ERROR [CPUMonitor] Current CPU usage: 95% - critical
2024-01-15 10:31:15 CRITICAL [CPUMonitor] CPU usage sustained at 98% for 60 seconds
2024-01-15 10:31:30 ERROR [ThreadPool] Thread pool exhausted - 200 active threads
2024-01-15 10:31:45 CRITICAL [Application] System unresponsive due to high CPU load
        """
    
    @pytest.mark.functional
    @pytest.mark.asyncio
    async def test_memory_leak_analysis(self, memory_leak_log, mock_runnable_config):
        """Test analysis of memory leak scenario."""
        graph = create_graph()
        compiled_graph = graph.compile()
        
        initial_state = {
            "log_content": memory_leak_log,
            "messages": [],
            "iteration_count": 0,
            "analysis_complete": False
        }
        
        with patch('src.log_analyzer_agent.nodes.analysis.get_model') as mock_analysis_model, \
             patch('src.log_analyzer_agent.nodes.validation.get_orchestration_model') as mock_validation_model:
            
            mock_analysis_model.return_value.generate_content.return_value.text = """
            {
                "summary": "Memory leak detected causing application crash",
                "issues": [
                    {
                        "severity": "critical",
                        "category": "performance",
                        "description": "Progressive memory leak leading to out of memory error",
                        "affected_components": ["MemoryMonitor", "Application"],
                        "first_occurrence": "2024-01-15 10:40:15",
                        "frequency": 1,
                        "memory_growth_pattern": "512MB -> 1536MB over 25 minutes"
                    }
                ],
                "suggestions": [
                    {
                        "priority": "critical",
                        "category": "debugging",
                        "description": "Perform memory profiling to identify leak source",
                        "implementation": "Use memory profiling tools to track object allocation",
                        "estimated_impact": "Identify root cause of memory leak"
                    },
                    {
                        "priority": "high",
                        "category": "monitoring",
                        "description": "Implement memory usage alerts",
                        "implementation": "Set up alerts for memory usage thresholds",
                        "estimated_impact": "Early detection of memory issues"
                    },
                    {
                        "priority": "medium",
                        "category": "configuration",
                        "description": "Tune garbage collection settings",
                        "implementation": "Optimize GC parameters for application workload",
                        "estimated_impact": "Better memory management"
                    }
                ]
            }
            """
            
            mock_validation_model.return_value.chat.completions.create.return_value.choices[0].message.content = """
            {
                "is_valid": true,
                "completeness_score": 0.9,
                "accuracy_score": 0.85,
                "feedback": "Comprehensive analysis of memory leak with actionable debugging suggestions"
            }
            """
            
            result = await compiled_graph.ainvoke(initial_state, config=mock_runnable_config)
            
            # Verify memory leak analysis
            assert result is not None
            analysis = result["analysis_result"]
            assert "memory" in analysis["summary"].lower()
            
            issues = analysis["issues"]
            performance_issues = [issue for issue in issues if issue["category"] == "performance"]
            assert len(performance_issues) > 0
    
    @pytest.mark.functional
    @pytest.mark.asyncio
    async def test_high_cpu_analysis(self, high_cpu_log, mock_runnable_config):
        """Test analysis of high CPU usage scenario."""
        graph = create_graph()
        compiled_graph = graph.compile()
        
        initial_state = {
            "log_content": high_cpu_log,
            "messages": [],
            "iteration_count": 0,
            "analysis_complete": False
        }
        
        with patch('src.log_analyzer_agent.nodes.analysis.get_model') as mock_analysis_model, \
             patch('src.log_analyzer_agent.nodes.validation.get_orchestration_model') as mock_validation_model:
            
            mock_analysis_model.return_value.generate_content.return_value.text = """
            {
                "summary": "Critical CPU usage causing system unresponsiveness",
                "issues": [
                    {
                        "severity": "critical",
                        "category": "performance",
                        "description": "Sustained high CPU usage leading to system unresponsiveness",
                        "affected_components": ["CPUMonitor", "ThreadPool", "Application"],
                        "first_occurrence": "2024-01-15 10:30:30",
                        "frequency": 1,
                        "cpu_pattern": "45% -> 98% sustained"
                    }
                ],
                "suggestions": [
                    {
                        "priority": "critical",
                        "category": "investigation",
                        "description": "Identify CPU-intensive processes",
                        "implementation": "Use profiling tools to identify hot spots",
                        "estimated_impact": "Find root cause of high CPU usage"
                    },
                    {
                        "priority": "high",
                        "category": "configuration",
                        "description": "Optimize thread pool configuration",
                        "implementation": "Tune thread pool size and queue limits",
                        "estimated_impact": "Better resource utilization"
                    }
                ]
            }
            """
            
            mock_validation_model.return_value.chat.completions.create.return_value.choices[0].message.content = """
            {
                "is_valid": true,
                "completeness_score": 0.8,
                "accuracy_score": 0.85,
                "feedback": "Good analysis of CPU performance issue"
            }
            """
            
            result = await compiled_graph.ainvoke(initial_state, config=mock_runnable_config)
            
            # Verify CPU analysis
            assert result is not None
            analysis = result["analysis_result"]
            assert "cpu" in analysis["summary"].lower()


class TestComplexScenarios:
    """Test complex scenarios with multiple interrelated issues."""
    
    @pytest.fixture
    def cascading_failure_log(self):
        """Cascading failure scenario."""
        return """
2024-01-15 10:30:15 WARN [LoadBalancer] Backend server 192.168.1.10 response time: 2500ms
2024-01-15 10:30:20 ERROR [LoadBalancer] Backend server 192.168.1.10 health check failed
2024-01-15 10:30:25 INFO [LoadBalancer] Removing server 192.168.1.10 from pool
2024-01-15 10:30:30 WARN [LoadBalancer] Increased load on remaining servers
2024-01-15 10:30:35 ERROR [LoadBalancer] Backend server 192.168.1.11 response time: 3000ms
2024-01-15 10:30:40 ERROR [LoadBalancer] Backend server 192.168.1.11 health check failed
2024-01-15 10:30:45 CRITICAL [LoadBalancer] Only 1 server remaining in pool
2024-01-15 10:30:50 ERROR [Application] Database connection pool exhausted
2024-01-15 10:30:55 CRITICAL [Application] Service unavailable - all backends down
        """
    
    @pytest.mark.functional
    @pytest.mark.asyncio
    async def test_cascading_failure_analysis(self, cascading_failure_log, mock_runnable_config):
        """Test analysis of cascading failure scenario."""
        graph = create_graph()
        compiled_graph = graph.compile()
        
        initial_state = {
            "log_content": cascading_failure_log,
            "messages": [],
            "iteration_count": 0,
            "analysis_complete": False
        }
        
        with patch('src.log_analyzer_agent.nodes.analysis.get_model') as mock_analysis_model, \
             patch('src.log_analyzer_agent.nodes.validation.get_orchestration_model') as mock_validation_model:
            
            mock_analysis_model.return_value.generate_content.return_value.text = """
            {
                "summary": "Cascading failure from backend server issues to complete service outage",
                "issues": [
                    {
                        "severity": "critical",
                        "category": "availability",
                        "description": "Cascading failure starting with backend server performance degradation",
                        "affected_components": ["LoadBalancer", "Backend Servers", "Database", "Application"],
                        "first_occurrence": "2024-01-15 10:30:15",
                        "frequency": 1,
                        "failure_chain": "Server performance -> Health check failures -> Load redistribution -> Database exhaustion -> Service outage"
                    }
                ],
                "suggestions": [
                    {
                        "priority": "critical",
                        "category": "resilience",
                        "description": "Implement circuit breaker pattern",
                        "implementation": "Add circuit breakers to prevent cascading failures",
                        "estimated_impact": "Isolate failures and prevent cascade"
                    },
                    {
                        "priority": "high",
                        "category": "capacity",
                        "description": "Increase backend server capacity",
                        "implementation": "Add more backend servers and improve auto-scaling",
                        "estimated_impact": "Better fault tolerance"
                    },
                    {
                        "priority": "high",
                        "category": "monitoring",
                        "description": "Implement comprehensive health monitoring",
                        "implementation": "Add detailed health checks and early warning systems",
                        "estimated_impact": "Earlier detection of potential failures"
                    }
                ]
            }
            """
            
            mock_validation_model.return_value.chat.completions.create.return_value.choices[0].message.content = """
            {
                "is_valid": true,
                "completeness_score": 0.95,
                "accuracy_score": 0.9,
                "feedback": "Excellent analysis of complex cascading failure with comprehensive suggestions"
            }
            """
            
            result = await compiled_graph.ainvoke(initial_state, config=mock_runnable_config)
            
            # Verify cascading failure analysis
            assert result is not None
            analysis = result["analysis_result"]
            assert "cascading" in analysis["summary"].lower() or "failure" in analysis["summary"].lower()
            
            issues = analysis["issues"]
            assert len(issues) > 0
            assert any(issue["severity"] == "critical" for issue in issues)
            
            suggestions = analysis["suggestions"]
            assert len(suggestions) >= 2
            assert any("resilience" in s["category"] for s in suggestions)