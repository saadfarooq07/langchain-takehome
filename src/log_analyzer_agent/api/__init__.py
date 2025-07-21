"""API module for log analyzer agent."""

# Import fixed streaming router
try:
    from .streaming_routes_fixed import router as fixed_streaming_router
    __all__ = ["fixed_streaming_router"]
except ImportError:
    # Fall back to enhanced streaming if available
    try:
        from .streaming_routes_enhanced import router as enhanced_streaming_router
        __all__ = ["enhanced_streaming_router"]
    except ImportError:
        __all__ = []
