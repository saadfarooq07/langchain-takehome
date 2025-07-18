"""Single graph builder with configuration-driven construction.

This module provides a clean, configuration-driven approach to building
the LangGraph workflow with proper separation of concerns.
"""

from typing import Dict, Any, Optional, Callable, List, Set
from dataclasses import dataclass
from functools import lru_cache

from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph
from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.memory import InMemoryStore

from .states import WorkingState, StateValidator
from .config import Config, get_config
from .logging import get_logger, log_execution_time


logger = get_logger("log_analyzer.graph_builder")


@dataclass
class NodeDefinition:
    """Definition of a graph node."""
    name: str
    function: Callable
    description: str
    required_features: Set[str] = None
    
    def __post_init__(self):
        if self.required_features is None:
            self.required_features = set()
    
    def is_enabled(self, features: Set[str]) -> bool:
        """Check if this node should be enabled based on features."""
        return self.required_features.issubset(features)


@dataclass
class EdgeDefinition:
    """Definition of a graph edge."""
    source: str
    target: str
    condition: Optional[Callable] = None
    description: str = ""
    required_features: Set[str] = None
    
    def __post_init__(self):
        if self.required_features is None:
            self.required_features = set()
    
    def is_enabled(self, features: Set[str]) -> bool:
        """Check if this edge should be enabled based on features."""
        return self.required_features.issubset(features)


class GraphBuilder:
    """Builder for constructing LangGraph workflows."""
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize the graph builder.
        
        Args:
            config: Configuration to use. If None, uses global config.
        """
        self.config = config or get_config()
        self.nodes: List[NodeDefinition] = []
        self.edges: List[EdgeDefinition] = []
        self._compiled_graph: Optional[CompiledStateGraph] = None
        
        logger.info("Initialized GraphBuilder", extra={
            "features": list(self.config.feature_flags.to_set()),
            "primary_model": self.config.primary_model.model_name,
            "orchestration_model": self.config.orchestration_model.model_name,
        })
    
    def add_node(
        self,
        name: str,
        function: Callable,
        description: str,
        required_features: Optional[Set[str]] = None
    ) -> 'GraphBuilder':
        """Add a node to the graph.
        
        Args:
            name: Node name
            function: Node function
            description: Human-readable description
            required_features: Features required for this node
        
        Returns:
            Self for chaining
        """
        node = NodeDefinition(
            name=name,
            function=function,
            description=description,
            required_features=required_features or set()
        )
        self.nodes.append(node)
        
        logger.debug(f"Added node: {name}", extra={
            "node_name": name,
            "required_features": list(node.required_features)
        })
        
        return self
    
    def add_edge(
        self,
        source: str,
        target: str,
        condition: Optional[Callable] = None,
        description: str = "",
        required_features: Optional[Set[str]] = None
    ) -> 'GraphBuilder':
        """Add an edge to the graph.
        
        Args:
            source: Source node
            target: Target node or END
            condition: Optional condition function
            description: Human-readable description
            required_features: Features required for this edge
        
        Returns:
            Self for chaining
        """
        edge = EdgeDefinition(
            source=source,
            target=target,
            condition=condition,
            description=description,
            required_features=required_features or set()
        )
        self.edges.append(edge)
        
        logger.debug(f"Added edge: {source} -> {target}", extra={
            "source": source,
            "target": target,
            "conditional": condition is not None,
            "required_features": list(edge.required_features)
        })
        
        return self
    
    @log_execution_time("log_analyzer.graph_builder")
    def build(self) -> CompiledStateGraph:
        """Build the graph based on configuration.
        
        Returns:
            Compiled state graph
        """
        if self._compiled_graph is not None:
            logger.debug("Returning cached compiled graph")
            return self._compiled_graph
        
        features = self.config.feature_flags.to_set()
        logger.info("Building graph", extra={"enabled_features": list(features)})
        
        # Create state graph
        graph = StateGraph(WorkingState)
        
        # Add enabled nodes
        enabled_nodes = []
        for node in self.nodes:
            if node.is_enabled(features):
                # Wrap node function with logging
                wrapped_function = self._wrap_node_function(node)
                graph.add_node(node.name, wrapped_function)
                enabled_nodes.append(node.name)
                logger.debug(f"Added node to graph: {node.name}")
        
        # Add enabled edges
        for edge in self.edges:
            if edge.is_enabled(features):
                # Check if both nodes exist
                if edge.source in enabled_nodes or edge.source == START:
                    if edge.target in enabled_nodes or edge.target == END:
                        if edge.condition:
                            # Conditional edge
                            graph.add_conditional_edges(
                                edge.source,
                                edge.condition,
                                # Condition should return dict mapping to targets
                            )
                        else:
                            # Direct edge
                            graph.add_edge(edge.source, edge.target)
                        logger.debug(f"Added edge to graph: {edge.source} -> {edge.target}")
        
        # Set entry point
        if enabled_nodes:
            graph.set_entry_point(enabled_nodes[0])
        
        # Compile based on features
        compile_kwargs = {}
        
        if "memory" in features and self.config.database.is_configured:
            # Add checkpointing for memory feature
            compile_kwargs["checkpointer"] = MemorySaver()
            logger.info("Enabled checkpointing for memory feature")
        
        self._compiled_graph = graph.compile(**compile_kwargs)
        
        logger.info("Graph compilation complete", extra={
            "node_count": len(enabled_nodes),
            "edge_count": len([e for e in self.edges if e.is_enabled(features)]),
            "has_checkpointer": "checkpointer" in compile_kwargs
        })
        
        return self._compiled_graph
    
    def _wrap_node_function(self, node: NodeDefinition) -> Callable:
        """Wrap a node function with logging and error handling.
        
        Args:
            node: Node definition
        
        Returns:
            Wrapped function
        """
        async def wrapped(state: WorkingState) -> Dict[str, Any]:
            """Wrapped node function with logging."""
            node_logger = get_logger(f"log_analyzer.nodes.{node.name}")
            
            # Track node visit
            state.increment_node_visit(node.name)
            
            # Validate state
            try:
                StateValidator.validate_feature_requirements(state)
                StateValidator.validate_limits(state, self.config.to_dict())
            except Exception as e:
                node_logger.error(f"State validation failed", extra={
                    "node": node.name,
                    "error": str(e)
                })
                raise
            
            node_logger.info(f"Executing node", extra={
                "node": node.name,
                "iteration": state.iteration_count,
                "total_tool_calls": state.get_total_tool_calls()
            })
            
            try:
                # Execute node function
                result = await node.function(state, self.config)
                
                node_logger.info(f"Node execution complete", extra={
                    "node": node.name,
                    "has_updates": bool(result)
                })
                
                return result or {}
                
            except Exception as e:
                node_logger.error(f"Node execution failed", extra={
                    "node": node.name,
                    "error_type": type(e).__name__,
                    "error_message": str(e)
                }, exc_info=True)
                
                # Re-raise with context
                raise RuntimeError(f"Node '{node.name}' failed: {str(e)}") from e
        
        # Preserve function metadata
        wrapped.__name__ = node.function.__name__
        wrapped.__doc__ = node.function.__doc__
        
        return wrapped
    
    def visualize(self) -> str:
        """Generate a visual representation of the graph.
        
        Returns:
            Mermaid diagram of the graph
        """
        features = self.config.feature_flags.to_set()
        
        lines = ["graph TD"]
        
        # Add nodes
        for node in self.nodes:
            if node.is_enabled(features):
                lines.append(f"    {node.name}[{node.name}]")
        
        # Add edges
        for edge in self.edges:
            if edge.is_enabled(features):
                if edge.condition:
                    lines.append(f"    {edge.source} -->|conditional| {edge.target}")
                else:
                    lines.append(f"    {edge.source} --> {edge.target}")
        
        return "\n".join(lines)
    
    @lru_cache(maxsize=1)
    def get_node_descriptions(self) -> Dict[str, str]:
        """Get descriptions of all nodes.
        
        Returns:
            Mapping of node names to descriptions
        """
        features = self.config.feature_flags.to_set()
        return {
            node.name: node.description
            for node in self.nodes
            if node.is_enabled(features)
        }


class RouterBuilder:
    """Builder for creating routing functions."""
    
    def __init__(self, config: Config):
        """Initialize router builder.
        
        Args:
            config: Configuration to use
        """
        self.config = config
        self.routes: Dict[str, Callable] = {}
        self.logger = get_logger("log_analyzer.router")
    
    def add_route(
        self,
        condition: str,
        target: str,
        predicate: Callable[[WorkingState], bool]
    ) -> 'RouterBuilder':
        """Add a route condition.
        
        Args:
            condition: Condition name
            target: Target node
            predicate: Function to check if condition is met
        
        Returns:
            Self for chaining
        """
        self.routes[condition] = (target, predicate)
        return self
    
    def build(self) -> Callable[[WorkingState], str]:
        """Build the routing function.
        
        Returns:
            Routing function
        """
        def router(state: WorkingState) -> str:
            """Route based on state."""
            self.logger.debug("Evaluating routing conditions", extra={
                "iteration": state.iteration_count,
                "needs_user_input": state.needs_user_input,
                "has_analysis": state.current_analysis is not None
            })
            
            # Check each condition in order
            for condition, (target, predicate) in self.routes.items():
                try:
                    if predicate(state):
                        self.logger.info(f"Routing to {target}", extra={
                            "condition": condition,
                            "target": target
                        })
                        return target
                except Exception as e:
                    self.logger.error(f"Error evaluating route condition", extra={
                        "condition": condition,
                        "error": str(e)
                    })
            
            # Default route
            self.logger.warning("No routing condition matched, using END")
            return END
        
        return router


# Factory function for creating standard graph configurations
def create_standard_graph(config: Optional[Config] = None) -> CompiledStateGraph:
    """Create a standard log analyzer graph.
    
    Args:
        config: Optional configuration override
    
    Returns:
        Compiled graph
    """
    from ..nodes import analyze_logs_node, validate_analysis_node, handle_user_input_node, execute_tools_node
    
    builder = GraphBuilder(config)
    
    # Add core nodes
    builder.add_node(
        "analyze_logs",
        analyze_logs_node,
        "Analyze log content and identify issues"
    )
    
    builder.add_node(
        "validate_analysis",
        validate_analysis_node,
        "Validate analysis quality"
    )
    
    builder.add_node(
        "execute_tools",
        execute_tools_node,
        "Execute tool calls"
    )
    
    # Add interactive nodes
    builder.add_node(
        "handle_user_input",
        handle_user_input_node,
        "Handle user responses",
        required_features={"interactive"}
    )
    
    # Create router for after analysis
    router = RouterBuilder(builder.config)
    router.add_route(
        "needs_user_input",
        "handle_user_input",
        lambda s: s.needs_user_input and s.has_feature("interactive")
    )
    router.add_route(
        "has_tool_calls",
        "execute_tools",
        lambda s: s.current_analysis and s.current_analysis.get("tool_calls")
    )
    router.add_route(
        "complete",
        "validate_analysis",
        lambda s: s.current_analysis is not None
    )
    
    # Add edges
    builder.add_edge(START, "analyze_logs")
    builder.add_edge("analyze_logs", "router", condition=router.build())
    builder.add_edge("execute_tools", "analyze_logs")
    builder.add_edge("handle_user_input", "analyze_logs", required_features={"interactive"})
    builder.add_edge("validate_analysis", END)
    
    return builder.build()