"""Utility modules for the log analyzer agent."""

from .cache import get_cache

# We don't need to import init_model from parent module, since it will be imported directly
# from the parent utils.py file when needed

__all__ = ["get_cache"]