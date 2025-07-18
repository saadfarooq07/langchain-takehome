"""Input validation and sanitization for log analyzer."""

import re
from typing import Dict, Any, Tuple


class LogValidator:
    """Validates and sanitizes log input."""

    # Size limits
    MAX_LOG_SIZE_MB = 100  # Maximum log file size in MB
    MAX_LOG_SIZE_BYTES = MAX_LOG_SIZE_MB * 1024 * 1024
    MAX_LINE_LENGTH = 10000  # Maximum characters per line
    MAX_LINES = 100000  # Maximum number of lines

    # Patterns for detecting potentially malicious content
    SUSPICIOUS_PATTERNS = [
        re.compile(r"<script[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL),
        re.compile(r"javascript:", re.IGNORECASE),
        re.compile(r"data:.*base64", re.IGNORECASE),
        re.compile(r"(\x00|\x1a|\x1b\[)", re.IGNORECASE),  # Null bytes and ANSI escape
    ]

    @classmethod
    def validate_log_content(cls, content: str) -> Tuple[bool, str, Dict[str, Any]]:
        """Validate log content for size, format, and safety.

        Args:
            content: The log content to validate

        Returns:
            Tuple of (is_valid, error_message, sanitized_info)
        """
        # Check size
        content_size = len(content.encode("utf-8"))
        if content_size > cls.MAX_LOG_SIZE_BYTES:
            return (
                False,
                f"Log size exceeds maximum allowed size of {cls.MAX_LOG_SIZE_MB}MB",
                {},
            )

        # Check line count and length
        lines = content.split("\n")
        if len(lines) > cls.MAX_LINES:
            return False, f"Log contains too many lines (max: {cls.MAX_LINES})", {}

        # Check for excessively long lines
        for i, line in enumerate(lines[:1000]):  # Check first 1000 lines
            if len(line) > cls.MAX_LINE_LENGTH:
                return (
                    False,
                    f"Line {i+1} exceeds maximum length of {cls.MAX_LINE_LENGTH} characters",
                    {},
                )

        # Check for suspicious patterns
        for pattern in cls.SUSPICIOUS_PATTERNS:
            if pattern.search(content):
                return False, "Log content contains potentially malicious patterns", {}

        # Calculate sanitized info
        sanitized_info = {
            "total_lines": len(lines),
            "size_bytes": content_size,
            "size_mb": round(content_size / (1024 * 1024), 2),
            "truncated": False,
            "sanitized": False,
        }

        return True, "", sanitized_info

    @classmethod
    def sanitize_log_content(cls, content: str) -> str:
        """Sanitize log content by removing potentially harmful elements.

        Args:
            content: The log content to sanitize

        Returns:
            Sanitized log content
        """
        # Remove any HTML/script tags
        content = re.sub(r"<[^>]+>", "", content)

        # Remove ANSI escape sequences
        content = re.sub(r"\x1b\[[0-9;]*m", "", content)

        # Remove null bytes
        content = content.replace("\x00", "")

        # Limit line length
        lines = content.split("\n")
        sanitized_lines = []
        for line in lines:
            if len(line) > cls.MAX_LINE_LENGTH:
                line = line[: cls.MAX_LINE_LENGTH] + "... [truncated]"
            sanitized_lines.append(line)

        return "\n".join(sanitized_lines)


class APIKeyValidator:
    """Validates API keys format and basic security."""

    @staticmethod
    def validate_gemini_api_key(key: str) -> Tuple[bool, str]:
        """Validate Gemini API key format."""
        if not key:
            return False, "Gemini API key is required"

        # Basic format check (Gemini API keys are typically 39 characters)
        if not re.match(r"^[A-Za-z0-9\-_]{30,50}$", key):
            return False, "Invalid Gemini API key format"

        return True, ""

    @staticmethod
    def validate_groq_api_key(key: str) -> Tuple[bool, str]:
        """Validate Groq API key format."""
        if not key:
            return False, "Groq API key is required"

        # Groq keys typically start with 'gsk_'
        if not key.startswith("gsk_"):
            return False, "Groq API key should start with 'gsk_'"

        if len(key) < 20:
            return False, "Groq API key appears to be too short"

        return True, ""

    @staticmethod
    def validate_tavily_api_key(key: str) -> Tuple[bool, str]:
        """Validate Tavily API key format."""
        if not key:
            return False, "Tavily API key is required"

        # Tavily keys typically start with 'tvly-'
        if not key.startswith("tvly-"):
            return False, "Tavily API key should start with 'tvly-'"

        if len(key) < 20:
            return False, "Tavily API key appears to be too short"

        return True, ""

    @classmethod
    def validate_all_keys(cls, config: Dict[str, Any]) -> Tuple[bool, list[str]]:
        """Validate all API keys in configuration.

        Args:
            config: Configuration dictionary containing API keys

        Returns:
            Tuple of (all_valid, list_of_errors)
        """
        errors = []

        # Validate Gemini API key
        gemini_key = config.get("configurable", {}).get("gemini_api_key", "")
        valid, error = cls.validate_gemini_api_key(gemini_key)
        if not valid:
            errors.append(error)

        # Validate Groq API key
        groq_key = config.get("configurable", {}).get("groq_api_key", "")
        valid, error = cls.validate_groq_api_key(groq_key)
        if not valid:
            errors.append(error)

        # Validate Tavily API key
        tavily_key = config.get("configurable", {}).get("tavily_api_key", "")
        valid, error = cls.validate_tavily_api_key(tavily_key)
        if not valid:
            errors.append(error)

        return len(errors) == 0, errors
