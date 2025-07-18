"""Refactored graph module integrating all improved components.

This module provides the main entry point for the refactored log analyzer
agent, demonstrating how all the new components work together.
"""

import asyncio
from typing import Dict, Any, Optional

from langgraph.graph.state import CompiledStateGraph

from .core.states import InputState, WorkingState, OutputState, StateTransition
from .core.config import Config, ConfigBuilder, get_config
from .core.logging import get_logger, log_manager
from .core.graph_builder import GraphBuilder, RouterBuilder
from .core.context_managers import (
    timeout_context, model_context, performance_monitor,
    graceful_shutdown, ExecutionContext
)
from .core.caching import get_state_cache
from .core.streaming import create_streaming_node
from .nodes.refactored_nodes import (
    analyze_logs_node,
    validate_analysis_node,
    handle_user_input_node,
    execute_tools_node
)


logger = get_logger("log_analyzer.refactored_graph")


class RefactoredLogAnalyzer:
    """Main class for the refactored log analyzer agent."""
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize the analyzer.
        
        Args:
            config: Configuration (uses global if not provided)
        """
        self.config = config or get_config()
        self._graph: Optional[CompiledStateGraph] = None
        self._execution_context: Optional[ExecutionContext] = None
        
        # Configure logging
        log_manager.configure(self.config.logging)
        
        # Initialize cache
        self.cache = get_state_cache(self.config)
        
        logger.info("Initialized RefactoredLogAnalyzer", extra={
            "features": list(self.config.feature_flags.to_set()),
            "primary_model": self.config.primary_model.model_name
        })
    
    def build_graph(self) -> CompiledStateGraph:
        """Build the analysis graph.
        
        Returns:
            Compiled graph
        """
        if self._graph is not None:
            return self._graph
        
        builder = GraphBuilder(self.config)
        
        # Add nodes based on features
        builder.add_node(
            "analyze_logs",
            analyze_logs_node,
            "Analyze log content and identify issues"
        )
        
        builder.add_node(
            "validate_analysis",
            validate_analysis_node,
            "Validate and store analysis results"
        )
        
        builder.add_node(
            "execute_tools",
            execute_tools_node,
            "Execute tool calls for additional information"
        )
        
        # Add conditional nodes
        if self.config.feature_flags.enable_interactive:
            builder.add_node(
                "handle_user_input",
                handle_user_input_node,
                "Handle user responses to questions",
                required_features={"interactive"}
            )
        
        if self.config.feature_flags.enable_streaming:
            builder.add_node(
                "stream_analysis",
                create_streaming_node(),
                "Stream analysis for large logs",
                required_features={"streaming"}
            )
        
        # Build router for post-analysis routing
        router = RouterBuilder(self.config)
        
        # Check if streaming should be used
        router.add_route(
            "needs_streaming",
            "stream_analysis",
            lambda s: (
                s.has_feature("streaming") and
                not s.current_analysis and
                len(s.messages[0].content if s.messages else "") > 5_000_000  # 5MB
            )
        )
        
        # Check if user input is needed
        router.add_route(
            "needs_user_input",
            "handle_user_input",
            lambda s: s.needs_user_input and s.has_feature("interactive")
        )
        
        # Check if tools need to be executed
        router.add_route(
            "has_tool_calls",
            "execute_tools",
            lambda s: (
                s.messages and
                hasattr(s.messages[-1], 'tool_calls') and
                s.messages[-1].tool_calls
            )
        )
        
        # Check if analysis is complete
        router.add_route(
            "analysis_complete",
            "validate_analysis",
            lambda s: s.current_analysis is not None
        )
        
        # Add edges
        from langgraph.graph import START, END
        
        builder.add_edge(START, "analyze_logs")
        builder.add_edge("analyze_logs", "router", condition=router.build())
        builder.add_edge("stream_analysis", "validate_analysis", required_features={"streaming"})
        builder.add_edge("execute_tools", "analyze_logs")
        builder.add_edge("handle_user_input", "analyze_logs", required_features={"interactive"})
        builder.add_edge("validate_analysis", END)
        
        self._graph = builder.build()
        return self._graph
    
    async def analyze(
        self,
        log_content: str,
        environment_details: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None
    ) -> OutputState:
        """Analyze log content.
        
        Args:
            log_content: Log content to analyze
            environment_details: Optional environment information
            timeout: Optional timeout in seconds
            
        Returns:
            Analysis output state
        """
        # Create input state
        input_state = InputState(
            log_content=log_content,
            environment_details=environment_details
        )
        
        # Check cache
        cached_result = await self.cache.get_analysis(
            log_content,
            environment_details
        )
        
        if cached_result:
            logger.info("Returning cached analysis")
            return OutputState(
                analysis_result=cached_result,
                execution_metadata={"cached": True}
            )
        
        # Create execution context
        self._execution_context = ExecutionContext(
            timeout=timeout or self.config.execution_limits.max_execution_time_seconds
        )
        
        async with performance_monitor("log_analysis") as metrics:
            try:
                # Create working state
                working_state = StateTransition.create_working_state(
                    input_state,
                    self.config.feature_flags.to_set()
                )
                
                # Get graph
                graph = self.build_graph()
                
                # Execute analysis
                async with model_context(self.config) as models:
                    # Store models in context for nodes to use
                    log_manager.set_context(models=models)
                    
                    # Run graph
                    result = await self._execution_context.run(
                        graph.ainvoke({
                            "log_content": log_content,
                            "environment_details": environment_details,
                            "messages": [],
                            "analysis_result": None,
                            "needs_user_input": False,
                            "features": working_state.features
                        })
                    )
                
                metrics.checkpoint("analysis_complete")
                
                # Extract analysis result
                analysis_result = result.get("current_analysis") or result.get("analysis_result")
                
                if not analysis_result:
                    raise ValueError("No analysis result produced")
                
                # Cache result
                await self.cache.put_analysis(
                    log_content,
                    analysis_result,
                    environment_details,
                    ttl=3600  # 1 hour
                )
                
                # Create output state
                output_state = StateTransition.create_output_state(
                    working_state,
                    analysis_result
                )
                
                return output_state
                
            except asyncio.TimeoutError:
                logger.error(f"Analysis timed out after {timeout}s")
                raise
            except Exception as e:
                logger.error(f"Analysis failed: {e}", exc_info=True)
                raise
            finally:
                # Clear context
                log_manager.clear_context()
    
    async def analyze_interactive(
        self,
        log_content: str,
        environment_details: Optional[Dict[str, Any]] = None
    ):
        """Run interactive analysis with user input support.
        
        Args:
            log_content: Log content
            environment_details: Environment details
            
        Yields:
            Analysis updates
        """
        if not self.config.feature_flags.enable_interactive:
            raise ValueError("Interactive mode not enabled")
        
        # Create input state
        input_state = InputState(
            log_content=log_content,
            environment_details=environment_details
        )
        
        # Create working state
        working_state = StateTransition.create_working_state(
            input_state,
            self.config.feature_flags.to_set()
        )
        
        # Get graph
        graph = self.build_graph()
        
        async with model_context(self.config) as models:
            log_manager.set_context(models=models)
            
            state = {
                "log_content": log_content,
                "environment_details": environment_details,
                "messages": [],
                "analysis_result": None,
                "needs_user_input": False,
                "features": working_state.features
            }
            
            # Stream updates
            async for update in graph.astream(state):
                if "needs_user_input" in update and update["needs_user_input"]:
                    # Yield request for user input
                    yield {
                        "type": "user_input_request",
                        "request": update.get("pending_request")
                    }
                    
                    # Wait for user response
                    user_response = yield
                    
                    # Continue with user response
                    state["user_response"] = user_response
                    state["needs_user_input"] = False
                
                elif "current_analysis" in update:
                    # Yield analysis result
                    yield {
                        "type": "analysis_complete",
                        "result": update["current_analysis"]
                    }
    
    def stop(self):
        """Stop any ongoing analysis."""
        if self._execution_context:
            self._execution_context.cancel()
            logger.info("Analysis cancelled")


async def main():
    """Example usage of the refactored analyzer."""
    # Load configuration
    config = ConfigBuilder.from_environment()
    
    # Create analyzer
    analyzer = RefactoredLogAnalyzer(config)
    
    # Example log content
    log_content = """
    2024-01-20 10:15:32 ERROR ConnectionPool: Failed to connect to database
    2024-01-20 10:15:33 ERROR ConnectionPool: Connection refused: localhost:5432
    2024-01-20 10:15:34 ERROR AppService: Database connection unavailable
    2024-01-20 10:15:35 ERROR AppService: Failed to process user request
    2024-01-20 10:15:36 WARN  HealthCheck: Service degraded - database offline
    """
    
    try:
        # Run analysis
        result = await analyzer.analyze(
            log_content,
            environment_details={
                "service": "user-api",
                "environment": "production",
                "version": "2.1.0"
            },
            timeout=60
        )
        
        # Print results
        print("Analysis Result:")
        print(f"Issues: {result.analysis_result['issues']}")
        print(f"Root Cause: {result.analysis_result['root_cause']}")
        print(f"Recommendations: {result.analysis_result['recommendations']}")
        print(f"\nExecution Time: {result.execution_metadata['execution_time_seconds']}s")
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())