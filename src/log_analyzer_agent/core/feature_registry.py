"""Feature registry for managing and configuring log analyzer features.

This module provides a centralized way to manage features, their dependencies,
and configurations across the improved log analyzer implementation.
"""

from typing import Dict, Set, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import os
import logging

logger = logging.getLogger(__name__)


class FeatureStatus(str, Enum):
    """Status of a feature."""
    ENABLED = "enabled"
    DISABLED = "disabled"
    EXPERIMENTAL = "experimental"
    DEPRECATED = "deprecated"


@dataclass
class Feature:
    """Definition of a feature."""
    name: str
    description: str
    status: FeatureStatus = FeatureStatus.DISABLED
    dependencies: Set[str] = field(default_factory=set)
    conflicts: Set[str] = field(default_factory=set)
    config: Dict[str, Any] = field(default_factory=dict)
    validator: Optional[Callable[[], bool]] = None
    
    def is_available(self) -> bool:
        """Check if the feature can be enabled."""
        if self.status == FeatureStatus.DEPRECATED:
            return False
        
        if self.validator:
            try:
                return self.validator()
            except Exception as e:
                logger.warning(f"Feature {self.name} validation failed: {e}")
                return False
        
        return True


class FeatureRegistry:
    """Central registry for all log analyzer features."""
    
    def __init__(self):
        self._features: Dict[str, Feature] = {}
        self._enabled_features: Set[str] = set()
        self._initialize_features()
    
    def _initialize_features(self):
        """Initialize all available features."""
        
        # Core features
        self.register(Feature(
            name="streaming",
            description="Enable streaming for large log files (>10MB)",
            status=FeatureStatus.ENABLED,
            config={
                "chunk_size_mb": 10,
                "max_concurrent_chunks": 3,
                "overlap_lines": 100
            }
        ))
        
        self.register(Feature(
            name="interactive",
            description="Enable interactive user prompts for clarification",
            status=FeatureStatus.ENABLED,
            dependencies=set(),
            config={
                "max_questions": 3,
                "timeout_seconds": 300
            }
        ))
        
        self.register(Feature(
            name="memory",
            description="Enable memory/persistence with checkpointing",
            status=FeatureStatus.ENABLED,
            dependencies=set(),
            validator=self._validate_memory_feature,
            config={
                "checkpoint_interval": 5,
                "max_checkpoints": 10
            }
        ))
        
        self.register(Feature(
            name="caching",
            description="Enable result caching for repeated analyses",
            status=FeatureStatus.ENABLED,
            config={
                "cache_ttl_seconds": 300,
                "max_cache_size": 100
            }
        ))
        
        self.register(Feature(
            name="specialized",
            description="Enable specialized analyzers for specific log types",
            status=FeatureStatus.ENABLED,
            config={
                "auto_detect": True,
                "analyzers": ["hdfs", "security", "application"]
            }
        ))
        
        # Advanced features
        self.register(Feature(
            name="circuit_breaker",
            description="Enable circuit breaker for fault tolerance",
            status=FeatureStatus.ENABLED,
            config={
                "failure_threshold": 5,
                "recovery_timeout": 60,
                "half_open_max_calls": 3
            }
        ))
        
        self.register(Feature(
            name="rate_limiting",
            description="Enable API rate limiting",
            status=FeatureStatus.ENABLED,
            config={
                "gemini_rpm": 60,
                "groq_rpm": 30,
                "tavily_rpm": 60
            }
        ))
        
        self.register(Feature(
            name="metrics",
            description="Enable detailed metrics and monitoring",
            status=FeatureStatus.EXPERIMENTAL,
            config={
                "export_interval": 60,
                "metrics_port": 9090
            }
        ))
        
        self.register(Feature(
            name="distributed",
            description="Enable distributed processing for very large logs",
            status=FeatureStatus.EXPERIMENTAL,
            dependencies={"streaming"},
            config={
                "worker_count": 4,
                "queue_size": 100
            }
        ))
        
        # Deprecated features (for backward compatibility)
        self.register(Feature(
            name="legacy_state",
            description="Use legacy state management (deprecated)",
            status=FeatureStatus.DEPRECATED,
            conflicts={"streaming", "specialized"}
        ))
    
    def _validate_memory_feature(self) -> bool:
        """Validate if memory feature can be enabled."""
        # Check if database URL is configured for persistence
        db_url = os.getenv("DATABASE_URL")
        if db_url:
            return True
        
        # Memory feature can work without DB (in-memory only)
        logger.info("Memory feature will use in-memory storage (no DATABASE_URL configured)")
        return True
    
    def register(self, feature: Feature) -> None:
        """Register a new feature."""
        if feature.name in self._features:
            logger.warning(f"Feature {feature.name} already registered, overwriting")
        
        self._features[feature.name] = feature
        
        # Auto-enable if status is ENABLED and available
        if feature.status == FeatureStatus.ENABLED and feature.is_available():
            self._enabled_features.add(feature.name)
    
    def enable(self, feature_name: str) -> bool:
        """Enable a feature."""
        if feature_name not in self._features:
            logger.error(f"Unknown feature: {feature_name}")
            return False
        
        feature = self._features[feature_name]
        
        # Check if available
        if not feature.is_available():
            logger.error(f"Feature {feature_name} is not available")
            return False
        
        # Check for conflicts
        for conflict in feature.conflicts:
            if conflict in self._enabled_features:
                logger.error(f"Feature {feature_name} conflicts with {conflict}")
                return False
        
        # Enable dependencies
        for dep in feature.dependencies:
            if dep not in self._enabled_features:
                logger.info(f"Enabling dependency {dep} for {feature_name}")
                if not self.enable(dep):
                    logger.error(f"Failed to enable dependency {dep}")
                    return False
        
        self._enabled_features.add(feature_name)
        logger.info(f"Enabled feature: {feature_name}")
        return True
    
    def disable(self, feature_name: str) -> bool:
        """Disable a feature."""
        if feature_name not in self._features:
            logger.error(f"Unknown feature: {feature_name}")
            return False
        
        # Check for dependent features
        dependent_features = []
        for fname, feature in self._features.items():
            if feature_name in feature.dependencies and fname in self._enabled_features:
                dependent_features.append(fname)
        
        if dependent_features:
            logger.warning(f"Disabling {feature_name} will also disable: {dependent_features}")
            for dep in dependent_features:
                self.disable(dep)
        
        self._enabled_features.discard(feature_name)
        logger.info(f"Disabled feature: {feature_name}")
        return True
    
    def is_enabled(self, feature_name: str) -> bool:
        """Check if a feature is enabled."""
        return feature_name in self._enabled_features
    
    def get_enabled_features(self) -> Set[str]:
        """Get all enabled features."""
        return self._enabled_features.copy()
    
    def get_feature_config(self, feature_name: str) -> Dict[str, Any]:
        """Get configuration for a feature."""
        if feature_name not in self._features:
            return {}
        
        feature = self._features[feature_name]
        
        # Override with environment variables
        config = feature.config.copy()
        for key, value in feature.config.items():
            env_key = f"FEATURE_{feature_name.upper()}_{key.upper()}"
            env_value = os.getenv(env_key)
            if env_value:
                # Try to parse as appropriate type
                if isinstance(value, bool):
                    config[key] = env_value.lower() in ("true", "1", "yes")
                elif isinstance(value, int):
                    try:
                        config[key] = int(env_value)
                    except ValueError:
                        logger.warning(f"Invalid int value for {env_key}: {env_value}")
                elif isinstance(value, float):
                    try:
                        config[key] = float(env_value)
                    except ValueError:
                        logger.warning(f"Invalid float value for {env_key}: {env_value}")
                else:
                    config[key] = env_value
        
        return config
    
    def get_all_features(self) -> Dict[str, Feature]:
        """Get all registered features."""
        return self._features.copy()
    
    def enable_feature_set(self, feature_set: str) -> bool:
        """Enable a predefined set of features."""
        feature_sets = {
            "minimal": set(),
            "standard": {"streaming", "caching"},
            "interactive": {"streaming", "caching", "interactive"},
            "memory": {"streaming", "caching", "memory"},
            "improved": {"streaming", "caching", "specialized", "circuit_breaker", "rate_limiting"},
            "full": {"streaming", "caching", "specialized", "interactive", "memory", 
                    "circuit_breaker", "rate_limiting", "metrics"},
            "experimental": {"streaming", "caching", "specialized", "interactive", "memory",
                           "circuit_breaker", "rate_limiting", "metrics", "distributed"}
        }
        
        if feature_set not in feature_sets:
            logger.error(f"Unknown feature set: {feature_set}")
            return False
        
        # Disable all features first
        for feature_name in list(self._enabled_features):
            self.disable(feature_name)
        
        # Enable features in the set
        success = True
        for feature_name in feature_sets[feature_set]:
            if not self.enable(feature_name):
                logger.error(f"Failed to enable feature {feature_name} in set {feature_set}")
                success = False
        
        return success
    
    def get_feature_report(self) -> str:
        """Generate a report of all features and their status."""
        lines = ["Feature Registry Report", "=" * 50]
        
        for name, feature in sorted(self._features.items()):
            status_symbol = "✓" if name in self._enabled_features else "✗"
            status_text = "Enabled" if name in self._enabled_features else "Disabled"
            
            lines.append(f"\n{status_symbol} {name} ({feature.status.value})")
            lines.append(f"  Description: {feature.description}")
            
            if name in self._enabled_features:
                config = self.get_feature_config(name)
                if config:
                    lines.append(f"  Config: {config}")
            
            if feature.dependencies:
                lines.append(f"  Dependencies: {', '.join(feature.dependencies)}")
            
            if feature.conflicts:
                lines.append(f"  Conflicts: {', '.join(feature.conflicts)}")
        
        lines.append("\n" + "=" * 50)
        lines.append(f"Total features: {len(self._features)}")
        lines.append(f"Enabled features: {len(self._enabled_features)}")
        
        return "\n".join(lines)


# Global feature registry instance
_feature_registry: Optional[FeatureRegistry] = None


def get_feature_registry() -> FeatureRegistry:
    """Get the global feature registry instance."""
    global _feature_registry
    if _feature_registry is None:
        _feature_registry = FeatureRegistry()
    return _feature_registry


def configure_features_from_env() -> None:
    """Configure features based on environment variables."""
    registry = get_feature_registry()
    
    # Check for feature set
    feature_set = os.getenv("LOG_ANALYZER_FEATURE_SET")
    if feature_set:
        logger.info(f"Configuring features from set: {feature_set}")
        registry.enable_feature_set(feature_set)
        return
    
    # Check for individual feature flags
    for feature_name in registry.get_all_features():
        env_key = f"FEATURE_{feature_name.upper()}_ENABLED"
        env_value = os.getenv(env_key)
        
        if env_value is not None:
            if env_value.lower() in ("true", "1", "yes"):
                registry.enable(feature_name)
            else:
                registry.disable(feature_name)