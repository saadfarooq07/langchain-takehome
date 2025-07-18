"""Compatibility layer for migrating from old state to new state structure."""

from typing import Any, Dict, Optional, Set, Type, Union
from .state import State as LegacyState
from .state import (
    CoreState,
    InteractiveState,
    MemoryState,
    create_state_class,
    get_state_features,
)


class StateAdapter:
    """Adapter to help transition between legacy and new state systems."""

    @staticmethod
    def from_legacy(legacy_state: Union[LegacyState, Dict[str, Any]]) -> Dict[str, Any]:
        """Convert legacy state to new state structure.

        Args:
            legacy_state: Legacy state object or dictionary

        Returns:
            Dictionary compatible with new state structure
        """
        # Convert to dict if it's a dataclass
        if hasattr(legacy_state, "__dataclass_fields__"):
            state_dict = {
                field: getattr(legacy_state, field)
                for field in legacy_state.__dataclass_fields__
            }
        else:
            state_dict = legacy_state

        # Detect which features are being used
        features = get_state_features(state_dict)

        # Get appropriate state class
        target_class = create_state_class(features)

        # Get valid fields for target class
        valid_fields = {f.name for f in target_class.__dataclass_fields__.values()}

        # Filter to only valid fields
        new_state = {
            key: value for key, value in state_dict.items() if key in valid_fields
        }

        return new_state

    @staticmethod
    def to_legacy(new_state: Union[CoreState, Dict[str, Any]]) -> Dict[str, Any]:
        """Convert new state to legacy state structure.

        Args:
            new_state: New state object or dictionary

        Returns:
            Dictionary compatible with legacy state structure
        """
        # Convert to dict if it's a dataclass
        if hasattr(new_state, "__dataclass_fields__"):
            state_dict = {
                field: getattr(new_state, field)
                for field in new_state.__dataclass_fields__
            }
        else:
            state_dict = new_state.copy()

        # Add any missing legacy fields with defaults
        legacy_defaults = {
            "follow_up_requests": [],
            "needs_user_input": False,
            "user_response": "",
            "pending_request": None,
            "additional_context": None,
            "loop_step": 0,
            "thread_id": "",
            "user_id": None,
            "session_id": "",
            "application_name": None,
            "application_version": None,
            "environment_type": None,
            "start_time": 0.0,
            "memory_search_count": 0,
            "similar_issues": [],
            "previous_solutions": [],
            "user_preferences": {},
        }

        for field, default in legacy_defaults.items():
            if field not in state_dict:
                state_dict[field] = default

        return state_dict

    @staticmethod
    def detect_features(state: Union[Any, Dict[str, Any]]) -> Set[str]:
        """Detect which features are needed based on state content.

        Args:
            state: State object or dictionary to analyze

        Returns:
            Set of required features
        """
        # Convert to dict if needed
        if hasattr(state, "__dataclass_fields__"):
            state_dict = {
                field: getattr(state, field) for field in state.__dataclass_fields__
            }
        else:
            state_dict = state

        return get_state_features(state_dict)

    @staticmethod
    def create_minimal_state(
        log_content: str, environment_details: Optional[Dict[str, Any]] = None
    ) -> CoreState:
        """Create a minimal state for simple log analysis.

        Args:
            log_content: The log content to analyze
            environment_details: Optional environment context

        Returns:
            Minimal CoreState instance
        """
        return CoreState(
            log_content=log_content, environment_details=environment_details
        )

    @staticmethod
    def upgrade_state(
        state: CoreState, features: Set[str]
    ) -> Union[CoreState, InteractiveState, MemoryState]:
        """Upgrade a state instance to support additional features.

        Args:
            state: Current state instance
            features: Features to enable

        Returns:
            Upgraded state instance
        """
        # Get target class
        target_class = create_state_class(features)

        # If already the right class, return as-is
        if isinstance(state, target_class):
            return state

        # Convert to dict
        state_dict = {
            field: getattr(state, field)
            for field in state.__dataclass_fields__
            if hasattr(state, field)
        }

        # Create new instance
        return target_class(**state_dict)
