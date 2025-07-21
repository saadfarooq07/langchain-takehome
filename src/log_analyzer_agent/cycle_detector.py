"""Intelligent cycle detection for preventing infinite loops in graph execution.

This module provides sophisticated cycle detection that goes beyond simple
counter-based limits. It detects actual patterns in execution, identifies
unproductive loops, and provides intelligent backoff strategies.

Key features:
- Pattern-based cycle detection
- State fingerprinting for accurate loop detection
- Configurable detection sensitivity
- Detailed cycle analysis and reporting
- Suggested remediation actions
"""

import hashlib
import json
from typing import Dict, List, Optional, Tuple, Set, Any
from datetime import datetime
from collections import defaultdict, deque
from dataclasses import dataclass
from enum import Enum


class CycleType(str, Enum):
    """Types of cycles that can be detected."""
    SIMPLE_LOOP = "simple_loop"  # A→B→A
    COMPLEX_LOOP = "complex_loop"  # A→B→C→A
    OSCILLATION = "oscillation"  # A→B→A→B→A
    SPIRAL = "spiral"  # Similar states with minor variations
    DEADLOCK = "deadlock"  # No progress being made


@dataclass
class StateTransition:
    """Represents a transition between states."""
    from_node: str
    to_node: str
    state_fingerprint: str
    timestamp: datetime
    metadata: Dict[str, Any]


@dataclass
class DetectedCycle:
    """Information about a detected cycle."""
    cycle_type: CycleType
    pattern: List[str]
    frequency: int
    first_occurrence: datetime
    last_occurrence: datetime
    confidence: float
    suggested_action: str


class CycleDetector:
    """Intelligent cycle detector for graph execution."""
    
    def __init__(
        self,
        max_history: int = 100,
        min_pattern_length: int = 2,
        max_pattern_length: int = 10,
        detection_threshold: int = 2,
        spiral_similarity_threshold: float = 0.85
    ):
        """Initialize the cycle detector.
        
        Args:
            max_history: Maximum number of transitions to keep in history
            min_pattern_length: Minimum length of pattern to detect
            max_pattern_length: Maximum length of pattern to detect
            detection_threshold: Number of repetitions before flagging a cycle
            spiral_similarity_threshold: Similarity threshold for spiral detection
        """
        self.max_history = max_history
        self.min_pattern_length = min_pattern_length
        self.max_pattern_length = max_pattern_length
        self.detection_threshold = detection_threshold
        self.spiral_similarity_threshold = spiral_similarity_threshold
        
        # State tracking
        self.transition_history: deque[StateTransition] = deque(maxlen=max_history)
        self.node_visit_counts: Dict[str, int] = defaultdict(int)
        self.pattern_counts: Dict[Tuple[str, ...], int] = defaultdict(int)
        self.state_fingerprints: Dict[str, List[datetime]] = defaultdict(list)
        self.detected_cycles: List[DetectedCycle] = []
        
        # Performance tracking
        self.total_transitions = 0
        self.cycles_detected = 0
        
    def add_transition(
        self,
        from_node: str,
        to_node: str,
        state: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[DetectedCycle]:
        """Add a state transition and check for cycles.
        
        Args:
            from_node: Source node name
            to_node: Destination node name
            state: Current state dictionary
            metadata: Optional metadata about the transition
            
        Returns:
            DetectedCycle if a cycle is detected, None otherwise
        """
        # Create state fingerprint
        fingerprint = self._create_state_fingerprint(state)
        
        # Record transition
        transition = StateTransition(
            from_node=from_node,
            to_node=to_node,
            state_fingerprint=fingerprint,
            timestamp=datetime.now(),
            metadata=metadata or {}
        )
        
        self.transition_history.append(transition)
        self.total_transitions += 1
        self.node_visit_counts[to_node] += 1
        self.state_fingerprints[fingerprint].append(transition.timestamp)
        
        # Check for various cycle types
        detected_cycle = None
        
        # Check for simple and complex loops
        loop_cycle = self._detect_loop_patterns()
        if loop_cycle:
            detected_cycle = loop_cycle
            
        # Check for oscillations
        oscillation_cycle = self._detect_oscillations()
        if oscillation_cycle and (not detected_cycle or oscillation_cycle.confidence > detected_cycle.confidence):
            detected_cycle = oscillation_cycle
            
        # Check for spirals (similar but not identical states)
        spiral_cycle = self._detect_spirals()
        if spiral_cycle and (not detected_cycle or spiral_cycle.confidence > detected_cycle.confidence):
            detected_cycle = spiral_cycle
            
        # Check for deadlocks (no progress)
        deadlock_cycle = self._detect_deadlock()
        if deadlock_cycle and (not detected_cycle or deadlock_cycle.confidence > detected_cycle.confidence):
            detected_cycle = deadlock_cycle
            
        if detected_cycle:
            self.detected_cycles.append(detected_cycle)
            self.cycles_detected += 1
            
        return detected_cycle
        
    def _create_state_fingerprint(self, state: Dict[str, Any]) -> str:
        """Create a fingerprint of the current state.
        
        This creates a hash of the important parts of the state
        to detect when we're in the same or similar state again.
        """
        # Extract key state elements (customize based on your state structure)
        key_elements = {
            "node_visits": state.get("node_visits", {}),
            "validation_status": state.get("validation_status"),
            "analysis_result_exists": bool(state.get("analysis_result")),
            "tool_calls_count": len(state.get("tool_calls", [])),
            "last_message_type": self._get_last_message_type(state.get("messages", []))
        }
        
        # Create deterministic string representation
        fingerprint_str = json.dumps(key_elements, sort_keys=True)
        
        # Return hash
        return hashlib.sha256(fingerprint_str.encode()).hexdigest()[:16]
        
    def _get_last_message_type(self, messages: List[Any]) -> str:
        """Get the type of the last message."""
        if not messages:
            return "none"
            
        last_message = messages[-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tool_call"
        elif hasattr(last_message, "content"):
            content = str(last_message.content)
            if "error" in content.lower():
                return "error"
            elif "retry" in content.lower():
                return "retry"
            else:
                return "content"
        return "unknown"
        
    def _detect_loop_patterns(self) -> Optional[DetectedCycle]:
        """Detect simple and complex loop patterns."""
        if len(self.transition_history) < self.min_pattern_length * 2:
            return None
            
        # Convert recent history to node sequence
        recent_nodes = [t.to_node for t in self.transition_history]
        
        # Look for repeating patterns
        for pattern_len in range(self.min_pattern_length, 
                               min(self.max_pattern_length + 1, len(recent_nodes) // 2)):
            # Check if the last pattern_len nodes repeat
            pattern = tuple(recent_nodes[-pattern_len:])
            
            # Count occurrences of this pattern
            count = 0
            for i in range(len(recent_nodes) - pattern_len + 1):
                if tuple(recent_nodes[i:i+pattern_len]) == pattern:
                    count += 1
                    
            if count >= self.detection_threshold:
                # Determine cycle type
                cycle_type = CycleType.SIMPLE_LOOP if pattern_len == 2 else CycleType.COMPLEX_LOOP
                
                return DetectedCycle(
                    cycle_type=cycle_type,
                    pattern=list(pattern),
                    frequency=count,
                    first_occurrence=self.transition_history[0].timestamp,
                    last_occurrence=self.transition_history[-1].timestamp,
                    confidence=min(0.9, count / self.detection_threshold * 0.3),
                    suggested_action=f"Break {cycle_type} by adding termination condition or state modification"
                )
                
        return None
        
    def _detect_oscillations(self) -> Optional[DetectedCycle]:
        """Detect oscillation patterns (A→B→A→B→A)."""
        if len(self.transition_history) < 5:
            return None
            
        # Look for alternating patterns
        recent_nodes = [t.to_node for t in list(self.transition_history)[-10:]]
        
        # Check for A-B-A-B pattern
        for i in range(len(recent_nodes) - 4):
            if (recent_nodes[i] == recent_nodes[i+2] == recent_nodes[i+4] and
                recent_nodes[i+1] == recent_nodes[i+3] and
                recent_nodes[i] != recent_nodes[i+1]):
                
                pattern = [recent_nodes[i], recent_nodes[i+1]]
                
                # Count full oscillations
                oscillation_count = sum(1 for j in range(0, len(recent_nodes)-1, 2)
                                      if j+1 < len(recent_nodes) and
                                      recent_nodes[j] == pattern[0] and
                                      recent_nodes[j+1] == pattern[1])
                
                if oscillation_count >= self.detection_threshold:
                    return DetectedCycle(
                        cycle_type=CycleType.OSCILLATION,
                        pattern=pattern,
                        frequency=oscillation_count,
                        first_occurrence=self.transition_history[0].timestamp,
                        last_occurrence=self.transition_history[-1].timestamp,
                        confidence=min(0.85, oscillation_count / self.detection_threshold * 0.4),
                        suggested_action="Add state memory or decision logic to prevent oscillation"
                    )
                    
        return None
        
    def _detect_spirals(self) -> Optional[DetectedCycle]:
        """Detect spiral patterns (similar but evolving states)."""
        if len(self.state_fingerprints) < 3:
            return None
            
        # Group similar fingerprints
        fingerprint_groups = self._group_similar_fingerprints()
        
        # Look for groups with multiple similar states
        for group in fingerprint_groups:
            if len(group) >= self.detection_threshold:
                # Check if states are evolving (timestamps increasing)
                timestamps = []
                for fp in group:
                    timestamps.extend(self.state_fingerprints[fp])
                    
                timestamps.sort()
                
                # If we're repeatedly visiting similar states
                if len(timestamps) >= self.detection_threshold * 2:
                    return DetectedCycle(
                        cycle_type=CycleType.SPIRAL,
                        pattern=[f"similar_state_{i}" for i in range(len(group))],
                        frequency=len(timestamps),
                        first_occurrence=timestamps[0],
                        last_occurrence=timestamps[-1],
                        confidence=0.7,
                        suggested_action="Add convergence criteria or limit iterations with similar states"
                    )
                    
        return None
        
    def _detect_deadlock(self) -> Optional[DetectedCycle]:
        """Detect deadlock (no progress being made)."""
        if len(self.transition_history) < 10:
            return None
            
        # Check if we're stuck in the same few nodes
        recent_nodes = [t.to_node for t in list(self.transition_history)[-10:]]
        unique_nodes = set(recent_nodes)
        
        # If we've been cycling through very few nodes
        if len(unique_nodes) <= 2:
            # Check if state is not changing
            recent_fingerprints = [t.state_fingerprint for t in list(self.transition_history)[-10:]]
            unique_fingerprints = set(recent_fingerprints)
            
            if len(unique_fingerprints) <= 2:
                return DetectedCycle(
                    cycle_type=CycleType.DEADLOCK,
                    pattern=list(unique_nodes),
                    frequency=10,
                    first_occurrence=self.transition_history[-10].timestamp,
                    last_occurrence=self.transition_history[-1].timestamp,
                    confidence=0.8,
                    suggested_action="Add timeout or force progress with state modification"
                )
                
        return None
        
    def _group_similar_fingerprints(self) -> List[List[str]]:
        """Group similar state fingerprints together."""
        groups = []
        processed = set()
        
        for fp1 in self.state_fingerprints:
            if fp1 in processed:
                continue
                
            group = [fp1]
            processed.add(fp1)
            
            for fp2 in self.state_fingerprints:
                if fp2 not in processed:
                    similarity = self._calculate_fingerprint_similarity(fp1, fp2)
                    if similarity >= self.spiral_similarity_threshold:
                        group.append(fp2)
                        processed.add(fp2)
                        
            if len(group) > 1:
                groups.append(group)
                
        return groups
        
    def _calculate_fingerprint_similarity(self, fp1: str, fp2: str) -> float:
        """Calculate similarity between two fingerprints."""
        # Simple character-based similarity
        matches = sum(c1 == c2 for c1, c2 in zip(fp1, fp2))
        return matches / max(len(fp1), len(fp2))
        
    def get_analytics(self) -> Dict[str, Any]:
        """Get analytics about cycle detection."""
        return {
            "total_transitions": self.total_transitions,
            "cycles_detected": self.cycles_detected,
            "node_visit_counts": dict(self.node_visit_counts),
            "unique_states": len(self.state_fingerprints),
            "detection_rate": self.cycles_detected / self.total_transitions if self.total_transitions > 0 else 0,
            "most_visited_node": max(self.node_visit_counts.items(), key=lambda x: x[1])[0] if self.node_visit_counts else None,
            "recent_cycles": [
                {
                    "type": cycle.cycle_type.value,
                    "pattern": cycle.pattern,
                    "confidence": cycle.confidence,
                    "action": cycle.suggested_action
                }
                for cycle in self.detected_cycles[-5:]  # Last 5 cycles
            ]
        }
        
    def reset(self):
        """Reset the cycle detector state."""
        self.transition_history.clear()
        self.node_visit_counts.clear()
        self.pattern_counts.clear()
        self.state_fingerprints.clear()
        self.detected_cycles.clear()
        self.total_transitions = 0
        self.cycles_detected = 0
        
    def should_terminate(self, cycle: Optional[DetectedCycle] = None) -> bool:
        """Determine if execution should terminate based on detected cycles.
        
        Args:
            cycle: The detected cycle (if any)
            
        Returns:
            True if execution should terminate
        """
        if not cycle:
            return False
            
        # High confidence cycles should terminate
        if cycle.confidence >= 0.8:
            return True
            
        # Multiple cycles of any type should terminate
        if self.cycles_detected >= 3:
            return True
            
        # Deadlocks should always terminate
        if cycle.cycle_type == CycleType.DEADLOCK:
            return True
            
        # Long-running spirals should terminate
        if cycle.cycle_type == CycleType.SPIRAL and cycle.frequency >= 20:
            return True
            
        return False