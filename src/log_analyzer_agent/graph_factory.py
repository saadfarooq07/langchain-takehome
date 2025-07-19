"""Simple factory for creating graphs with appropriate configuration."""

from typing import Optional, Set
from .graph import (
    create_graph,
    create_minimal_graph,
    create_interactive_graph,
    create_memory_graph,
    create_full_graph,
)


class GraphFactory:
    """Factory for creating log analyzer graphs with various configurations."""

    @staticmethod
    def create_graph(
        mode: str = "auto",
        features: Optional[Set[str]] = None,
    ):
        """Create a graph with the specified configuration.

        Args:
            mode: Graph mode. Options:
                - "auto": Automatically detect based on environment (default)
                - "minimal": Lightest possible graph
                - "interactive": With user interaction support
                - "memory": With full memory support (requires DB)
                - "full": All features enabled
            features: Explicit features to enable (overrides mode)

        Returns:
            Configured graph instance
        """
        # Handle explicit feature set
        if features is not None:
            return create_graph(features=features)

        # Handle modes
        if mode == "minimal":
            return create_minimal_graph()
        elif mode == "interactive":
            return create_interactive_graph()
        elif mode == "memory":
            return create_memory_graph()
        elif mode == "full":
            return create_full_graph()
        elif mode == "auto":
            # Auto-detect based on environment
            import os
            if os.getenv("DATABASE_URL"):
                # Database available, use full features
                return create_memory_graph()
            else:
                # No database, use interactive mode
                return create_interactive_graph()
        else:
            raise ValueError(f"Unknown mode: {mode}")


# Convenience function for backward compatibility
def get_graph(lightweight: bool = False):
    """Get a graph instance with backward-compatible interface.

    Args:
        lightweight: If True, create minimal graph

    Returns:
        Graph instance
    """
    if lightweight:
        return create_minimal_graph()
    else:
        return create_interactive_graph()