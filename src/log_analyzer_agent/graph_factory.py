"""Factory for creating graphs with appropriate configuration."""

import os
from typing import Optional, Set, Union
from .graph import (
    create_graph,
    create_minimal_graph,
    create_interactive_graph,
    create_full_graph,
    create_graph_with_memory,
)
from .state_compat import StateAdapter

# Import improved implementation if enabled
USE_IMPROVED_IMPLEMENTATION = os.getenv("USE_IMPROVED_LOG_ANALYZER", "false").lower() == "true"
if USE_IMPROVED_IMPLEMENTATION:
    try:
        from .core.improved_graph import create_improved_graph
    except ImportError:
        USE_IMPROVED_IMPLEMENTATION = False


class GraphFactory:
    """Factory for creating log analyzer graphs with various configurations."""

    @staticmethod
    def create_graph(
        mode: str = "auto",
        features: Optional[Set[str]] = None,
        use_legacy: bool = False,
        use_improved: Optional[bool] = None,
    ):
        """Create a graph with the specified configuration.

        Args:
            mode: Graph mode. Options:
                - "auto": Automatically detect based on environment (default)
                - "minimal": Lightest possible graph
                - "interactive": With user interaction support
                - "memory": With full memory support (requires DB)
                - "legacy": Use the old state system
                - "improved": Use the improved implementation
            features: Explicit features to enable (overrides mode)
            use_legacy: Force use of legacy state system
            use_improved: Force use of improved implementation (overrides env var)

        Returns:
            Configured graph instance
        """
        # Check if we should use improved implementation
        should_use_improved = use_improved if use_improved is not None else USE_IMPROVED_IMPLEMENTATION
        
        if should_use_improved or mode == "improved":
            if not USE_IMPROVED_IMPLEMENTATION and use_improved is None:
                raise ValueError(
                    "Improved implementation not available. "
                    "Set USE_IMPROVED_LOG_ANALYZER=true or ensure core modules are installed."
                )
            return create_improved_graph(features=features)
        
        # Handle explicit feature set
        if features is not None:
            return create_graph(features=features)

        # Handle modes
        if mode == "minimal":
            return create_minimal_graph()
        elif mode == "interactive":
            return create_interactive_graph()
        elif mode == "memory":
            return create_full_graph()
        elif mode == "auto":
            # Auto-detect based on environment
            if os.getenv("DATABASE_URL"):
                # Database available, use full features
                return create_full_graph()
            else:
                # No database, use interactive mode
                return create_interactive_graph()
        else:
            raise ValueError(f"Unknown mode: {mode}")

    @staticmethod
    async def create_graph_async(
        mode: str = "auto",
        features: Optional[Set[str]] = None,
        db_uri: Optional[str] = None,
    ):
        """Create a graph asynchronously (needed for memory features).

        Args:
            mode: Graph mode (same as create_graph)
            features: Explicit features to enable
            db_uri: Database URI for memory features

        Returns:
            For memory mode: (graph, store, checkpointer)
            For other modes: graph
        """
        # Handle memory mode specially
        if mode == "memory" or (features and "memory" in features):
            return await create_graph_with_memory(db_uri=db_uri, features=features)

        # For non-memory modes, use sync creation
        return GraphFactory.create_graph(mode=mode, features=features)

    @staticmethod
    def detect_required_mode(state_dict: dict) -> str:
        """Detect the required mode based on state content.

        Args:
            state_dict: State dictionary to analyze

        Returns:
            Recommended mode
        """
        features = StateAdapter.detect_features(state_dict)

        if "memory" in features:
            return "memory"
        elif "interactive" in features:
            return "interactive"
        else:
            return "minimal"


# Convenience function for backward compatibility
def get_graph(lightweight: bool = False, use_legacy: bool = False):
    """Get a graph instance with backward-compatible interface.

    Args:
        lightweight: If True, create minimal graph
        use_legacy: Ignored (kept for backward compatibility)

    Returns:
        Graph instance
    """
    if lightweight:
        return create_minimal_graph()
    else:
        return create_interactive_graph()


# Convenience function for creating improved graph
def create_improved_analyzer(features: Optional[Set[str]] = None):
    """Create an improved log analyzer graph.
    
    Args:
        features: Set of features to enable (e.g., {"streaming", "memory"})
        
    Returns:
        Improved graph instance
    """
    return GraphFactory.create_graph(mode="improved", features=features)
