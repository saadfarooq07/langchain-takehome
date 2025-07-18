"""Focused analyzer components for log analysis.

This module breaks down the monolithic analyze_logs function into
focused, testable components with single responsibilities.
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import re
from datetime import datetime
import hashlib

from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.language_models import BaseChatModel

from .logging import get_logger, log_execution_time
from .config import Config


logger = get_logger("log_analyzer.analyzers")


@dataclass
class LogMetadata:
    """Extracted metadata from log content."""
    line_count: int
    size_bytes: int
    time_range: Optional[Tuple[datetime, datetime]]
    log_format: str
    severity_counts: Dict[str, int]
    unique_components: List[str]
    patterns_detected: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for prompts."""
        return {
            "line_count": self.line_count,
            "size_bytes": self.size_bytes,
            "time_range": {
                "start": self.time_range[0].isoformat() if self.time_range else None,
                "end": self.time_range[1].isoformat() if self.time_range else None
            },
            "log_format": self.log_format,
            "severity_counts": self.severity_counts,
            "unique_components": self.unique_components,
            "patterns_detected": self.patterns_detected
        }


class LogPreprocessor:
    """Preprocesses log content for analysis."""
    
    # Common log formats
    LOG_FORMATS = {
        "syslog": re.compile(r'^\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}'),
        "apache_common": re.compile(r'^\S+\s+\S+\s+\S+\s+\[\d{2}/\w{3}/\d{4}'),
        "json": re.compile(r'^\s*\{.*\}\s*$'),
        "logfmt": re.compile(r'^\w+='),
        "iso8601": re.compile(r'^\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}'),
    }
    
    # Severity patterns
    SEVERITY_PATTERNS = {
        "critical": re.compile(r'\b(CRITICAL|FATAL|EMERGENCY|EMERG)\b', re.I),
        "error": re.compile(r'\b(ERROR|ERR|FAILURE|FAILED)\b', re.I),
        "warning": re.compile(r'\b(WARNING|WARN|ALERT)\b', re.I),
        "info": re.compile(r'\b(INFO|INFORMATION|NOTICE)\b', re.I),
        "debug": re.compile(r'\b(DEBUG|TRACE|VERBOSE)\b', re.I),
    }
    
    @log_execution_time("log_analyzer.preprocessor")
    def preprocess(self, log_content: str, max_lines: int = 10000) -> Tuple[str, LogMetadata]:
        """Preprocess log content and extract metadata.
        
        Args:
            log_content: Raw log content
            max_lines: Maximum lines to process
            
        Returns:
            Tuple of (processed_content, metadata)
        """
        lines = log_content.strip().split('\n')
        total_lines = len(lines)
        
        # Truncate if necessary
        if total_lines > max_lines:
            logger.warning(f"Truncating log from {total_lines} to {max_lines} lines")
            lines = lines[:max_lines]
            truncated = True
        else:
            truncated = False
        
        # Detect log format
        log_format = self._detect_format(lines[:100])  # Sample first 100 lines
        
        # Extract time range
        time_range = self._extract_time_range(lines[:100], lines[-100:])
        
        # Count severities
        severity_counts = self._count_severities(lines)
        
        # Extract unique components
        components = self._extract_components(lines)
        
        # Detect patterns
        patterns = self._detect_patterns(lines)
        
        # Create metadata
        metadata = LogMetadata(
            line_count=total_lines,
            size_bytes=len(log_content.encode('utf-8')),
            time_range=time_range,
            log_format=log_format,
            severity_counts=severity_counts,
            unique_components=components[:20],  # Top 20 components
            patterns_detected=patterns
        )
        
        # Process content
        processed_content = '\n'.join(lines)
        if truncated:
            processed_content += f"\n\n[TRUNCATED: Showing first {max_lines} of {total_lines} lines]"
        
        logger.info("Log preprocessing complete", extra={
            "line_count": metadata.line_count,
            "format": metadata.log_format,
            "severities": metadata.severity_counts
        })
        
        return processed_content, metadata
    
    def _detect_format(self, sample_lines: List[str]) -> str:
        """Detect the log format from sample lines."""
        format_scores = {fmt: 0 for fmt in self.LOG_FORMATS}
        
        for line in sample_lines:
            if not line.strip():
                continue
            for fmt_name, pattern in self.LOG_FORMATS.items():
                if pattern.match(line):
                    format_scores[fmt_name] += 1
        
        if max(format_scores.values()) > len(sample_lines) * 0.5:
            return max(format_scores, key=format_scores.get)
        return "unknown"
    
    def _extract_time_range(
        self,
        start_lines: List[str],
        end_lines: List[str]
    ) -> Optional[Tuple[datetime, datetime]]:
        """Extract time range from log lines."""
        # Common timestamp patterns
        timestamp_patterns = [
            (r'(\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2})', '%Y-%m-%dT%H:%M:%S'),
            (r'(\d{2}/\w{3}/\d{4}:\d{2}:\d{2}:\d{2})', '%d/%b/%Y:%H:%M:%S'),
            (r'(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})', '%b %d %H:%M:%S'),
        ]
        
        start_time = None
        end_time = None
        
        # Find first timestamp
        for line in start_lines:
            for pattern, fmt in timestamp_patterns:
                match = re.search(pattern, line)
                if match:
                    try:
                        start_time = datetime.strptime(match.group(1), fmt)
                        break
                    except ValueError:
                        continue
            if start_time:
                break
        
        # Find last timestamp
        for line in reversed(end_lines):
            for pattern, fmt in timestamp_patterns:
                match = re.search(pattern, line)
                if match:
                    try:
                        end_time = datetime.strptime(match.group(1), fmt)
                        break
                    except ValueError:
                        continue
            if end_time:
                break
        
        if start_time and end_time:
            return (start_time, end_time)
        return None
    
    def _count_severities(self, lines: List[str]) -> Dict[str, int]:
        """Count severity levels in log lines."""
        counts = {level: 0 for level in self.SEVERITY_PATTERNS}
        
        for line in lines:
            for level, pattern in self.SEVERITY_PATTERNS.items():
                if pattern.search(line):
                    counts[level] += 1
                    break  # Count each line only once
        
        return counts
    
    def _extract_components(self, lines: List[str]) -> List[str]:
        """Extract unique component/service names."""
        # Common component patterns
        component_patterns = [
            re.compile(r'\[([A-Za-z0-9_.-]+)\]'),  # [component]
            re.compile(r'^(\w+):'),  # component:
            re.compile(r'service=(\w+)'),  # service=name
            re.compile(r'component=(\w+)'),  # component=name
        ]
        
        components = {}
        for line in lines:
            for pattern in component_patterns:
                matches = pattern.findall(line)
                for match in matches:
                    components[match] = components.get(match, 0) + 1
        
        # Sort by frequency
        return [comp for comp, _ in sorted(components.items(), key=lambda x: x[1], reverse=True)]
    
    def _detect_patterns(self, lines: List[str]) -> List[str]:
        """Detect common patterns in logs."""
        patterns = []
        
        # Check for stack traces
        stack_trace_count = sum(1 for line in lines if line.strip().startswith('at '))
        if stack_trace_count > 10:
            patterns.append("stack_traces")
        
        # Check for repeated errors
        error_lines = [line for line in lines if self.SEVERITY_PATTERNS['error'].search(line)]
        if len(error_lines) > len(lines) * 0.1:  # More than 10% errors
            patterns.append("high_error_rate")
        
        # Check for connection issues
        connection_pattern = re.compile(r'(connection|timeout|refused|closed)', re.I)
        connection_count = sum(1 for line in lines if connection_pattern.search(line))
        if connection_count > 10:
            patterns.append("connection_issues")
        
        # Check for performance issues
        perf_pattern = re.compile(r'(slow|latency|performance|lag)', re.I)
        perf_count = sum(1 for line in lines if perf_pattern.search(line))
        if perf_count > 5:
            patterns.append("performance_issues")
        
        return patterns


class MemoryAnalyzer:
    """Analyzes similar issues from memory."""
    
    def __init__(self, memory_service):
        """Initialize with memory service."""
        self.memory_service = memory_service
        self.logger = get_logger("log_analyzer.memory_analyzer")
    
    @log_execution_time("log_analyzer.memory_analyzer")
    async def find_similar_issues(
        self,
        log_content: str,
        metadata: LogMetadata,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Find similar issues from memory.
        
        Args:
            log_content: Log content
            metadata: Log metadata
            limit: Maximum results
            
        Returns:
            List of similar issues with solutions
        """
        if not self.memory_service:
            return []
        
        try:
            # Create search query from metadata
            search_terms = []
            
            # Add error messages
            error_lines = [
                line for line in log_content.split('\n')
                if LogPreprocessor.SEVERITY_PATTERNS['error'].search(line)
            ][:5]  # Top 5 errors
            search_terms.extend(error_lines)
            
            # Add detected patterns
            search_terms.extend(metadata.patterns_detected)
            
            # Add components with errors
            if metadata.unique_components:
                search_terms.extend(metadata.unique_components[:3])
            
            # Search memory
            similar_issues = await self.memory_service.search_similar_issues(
                ' '.join(search_terms),
                limit=limit
            )
            
            self.logger.info(f"Found {len(similar_issues)} similar issues")
            return similar_issues
            
        except Exception as e:
            self.logger.error(f"Error searching memory: {e}")
            return []


class LogAnalyzer:
    """Main log analyzer component."""
    
    def __init__(self, model: BaseChatModel, config: Config):
        """Initialize analyzer.
        
        Args:
            model: Language model to use
            config: Configuration
        """
        self.model = model
        self.config = config
        self.logger = get_logger("log_analyzer.analyzer")
    
    @log_execution_time("log_analyzer.analyzer")
    async def analyze(
        self,
        processed_content: str,
        metadata: LogMetadata,
        environment_details: Optional[Dict[str, Any]] = None,
        similar_issues: Optional[List[Dict[str, Any]]] = None,
        additional_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """Analyze log content.
        
        Args:
            processed_content: Preprocessed log content
            metadata: Log metadata
            environment_details: Environment information
            similar_issues: Similar issues from memory
            additional_context: Additional context from user
            
        Returns:
            Analysis result
        """
        # Build prompt
        prompt_parts = [
            "You are an expert system administrator and log analyst.",
            f"\nLog Metadata:\n{self._format_metadata(metadata)}",
            f"\nLog Content:\n{processed_content}"
        ]
        
        if environment_details:
            prompt_parts.append(f"\nEnvironment Details:\n{self._format_dict(environment_details)}")
        
        if similar_issues:
            prompt_parts.append(f"\nSimilar Issues Found:\n{self._format_similar_issues(similar_issues)}")
        
        if additional_context:
            prompt_parts.append(f"\nAdditional Context:\n{additional_context}")
        
        prompt_parts.append(
            "\nAnalyze the logs and provide:\n"
            "1. Issues identified (with severity)\n"
            "2. Root cause analysis\n"
            "3. Specific recommendations\n"
            "4. Relevant documentation or commands"
        )
        
        prompt = '\n'.join(prompt_parts)
        
        # Call model
        self.logger.debug("Calling language model for analysis")
        response = await self.model.ainvoke([HumanMessage(content=prompt)])
        
        # Parse response
        analysis = self._parse_analysis_response(response.content)
        
        # Add metadata
        analysis['metadata'] = {
            'analyzed_lines': metadata.line_count,
            'log_format': metadata.log_format,
            'severity_distribution': metadata.severity_counts,
            'patterns_detected': metadata.patterns_detected
        }
        
        return analysis
    
    def _format_metadata(self, metadata: LogMetadata) -> str:
        """Format metadata for prompt."""
        parts = [
            f"- Lines: {metadata.line_count}",
            f"- Format: {metadata.log_format}",
            f"- Severities: {metadata.severity_counts}",
        ]
        if metadata.time_range:
            parts.append(f"- Time Range: {metadata.time_range[0]} to {metadata.time_range[1]}")
        if metadata.patterns_detected:
            parts.append(f"- Patterns: {', '.join(metadata.patterns_detected)}")
        return '\n'.join(parts)
    
    def _format_dict(self, d: Dict[str, Any]) -> str:
        """Format dictionary for prompt."""
        return '\n'.join(f"- {k}: {v}" for k, v in d.items())
    
    def _format_similar_issues(self, issues: List[Dict[str, Any]]) -> str:
        """Format similar issues for prompt."""
        formatted = []
        for i, issue in enumerate(issues, 1):
            formatted.append(
                f"{i}. {issue.get('title', 'Unknown Issue')}\n"
                f"   Solution: {issue.get('solution', 'No solution recorded')}\n"
                f"   Similarity: {issue.get('similarity_score', 0):.2%}"
            )
        return '\n'.join(formatted)
    
    def _parse_analysis_response(self, response: str) -> Dict[str, Any]:
        """Parse the model's analysis response."""
        # Default structure
        analysis = {
            "issues": [],
            "root_cause": "Unable to determine root cause",
            "recommendations": [],
            "documentation_links": [],
            "suggested_commands": []
        }
        
        # Simple parsing - in production, use structured output
        sections = response.split('\n\n')
        current_section = None
        
        for section in sections:
            lower_section = section.lower()
            if 'issue' in lower_section:
                current_section = 'issues'
            elif 'root cause' in lower_section:
                current_section = 'root_cause'
            elif 'recommend' in lower_section:
                current_section = 'recommendations'
            elif 'document' in lower_section:
                current_section = 'documentation'
            elif 'command' in lower_section:
                current_section = 'commands'
            
            # Extract content based on section
            if current_section == 'issues':
                # Extract bullet points
                for line in section.split('\n'):
                    if line.strip().startswith(('-', '*', '•')):
                        analysis['issues'].append(line.strip()[1:].strip())
            elif current_section == 'root_cause':
                analysis['root_cause'] = section.strip()
            elif current_section == 'recommendations':
                for line in section.split('\n'):
                    if line.strip().startswith(('-', '*', '•', '1', '2', '3')):
                        analysis['recommendations'].append(line.strip()[1:].strip())
        
        return analysis