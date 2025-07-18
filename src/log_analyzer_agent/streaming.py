"""Streaming support for the log analyzer agent.

This module provides streaming capabilities for real-time analysis feedback.
"""

import asyncio
from typing import AsyncIterator, Dict, Any, Optional, Union
from langchain_core.messages import BaseMessage, AIMessage, ToolMessage
from langgraph.graph import StateGraph
from langgraph.constants import Send

from .state import CoreState
from .graph import create_graph


class StreamingLogAnalyzer:
    """Provides streaming capabilities for the log analyzer agent."""

    def __init__(self, graph: Optional[StateGraph] = None):
        """Initialize the streaming analyzer.

        Args:
            graph: Optional pre-compiled graph. If not provided, creates a default one.
        """
        self.graph = graph or create_graph()

    async def stream_analysis(
        self,
        log_content: str,
        config: Optional[Dict[str, Any]] = None,
        stream_mode: str = "updates",
    ) -> AsyncIterator[Dict[str, Any]]:
        """Stream the log analysis process.

        Args:
            log_content: The log content to analyze
            config: Optional configuration for the graph
            stream_mode: How to stream results. Options:
                - "updates": Stream state updates (default)
                - "messages": Stream only messages
                - "events": Stream all events (v2 API)

        Yields:
            Dictionaries containing streamed updates
        """
        initial_state = {
            "log_content": log_content,
            "messages": [],
            "analysis_result": None,
            "needs_user_input": False,
        }

        if stream_mode == "events":
            # Use v2 streaming API for detailed events
            async for event in self.graph.astream_events(
                initial_state, config=config, version="v2"
            ):
                yield self._process_event(event)

        elif stream_mode == "messages":
            # Stream only message updates
            async for chunk in self.graph.astream(
                initial_state, config=config, stream_mode="messages"
            ):
                yield self._process_message_chunk(chunk)

        else:
            # Default: stream state updates
            async for chunk in self.graph.astream(
                initial_state, config=config, stream_mode="updates"
            ):
                yield self._process_update_chunk(chunk)

    def _process_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Process a streaming event from v2 API.

        Args:
            event: The event dictionary

        Returns:
            Processed event for client consumption
        """
        event_type = event.get("event", "")

        if event_type == "on_chat_model_stream":
            # Streaming tokens from the model
            return {
                "type": "token",
                "content": event["data"]["chunk"].content,
                "node": event.get("name", "unknown"),
            }

        elif event_type == "on_tool_start":
            # Tool execution started
            return {
                "type": "tool_start",
                "tool": event["name"],
                "inputs": event.get("data", {}).get("input", {}),
            }

        elif event_type == "on_tool_end":
            # Tool execution completed
            return {
                "type": "tool_end",
                "tool": event["name"],
                "output": event.get("data", {}).get("output"),
            }

        elif event_type == "on_chain_start":
            # Node execution started
            return {"type": "node_start", "node": event["name"]}

        elif event_type == "on_chain_end":
            # Node execution completed
            return {
                "type": "node_end",
                "node": event["name"],
                "output": event.get("data", {}).get("output"),
            }

        else:
            # Other events
            return {
                "type": "event",
                "event_type": event_type,
                "data": event.get("data", {}),
            }

    def _process_message_chunk(
        self, chunk: Union[BaseMessage, tuple]
    ) -> Dict[str, Any]:
        """Process a message chunk.

        Args:
            chunk: The message or tuple of (message, metadata)

        Returns:
            Processed message for client consumption
        """
        if isinstance(chunk, tuple):
            message, metadata = chunk
        else:
            message = chunk
            metadata = {}

        if isinstance(message, AIMessage):
            return {
                "type": "ai_message",
                "content": message.content,
                "tool_calls": (
                    message.tool_calls if hasattr(message, "tool_calls") else []
                ),
                "metadata": metadata,
            }

        elif isinstance(message, ToolMessage):
            return {
                "type": "tool_message",
                "content": message.content,
                "tool_name": message.name if hasattr(message, "name") else "unknown",
                "status": message.status if hasattr(message, "status") else "success",
                "metadata": metadata,
            }

        else:
            return {"type": "message", "content": str(message), "metadata": metadata}

    def _process_update_chunk(self, chunk: Dict[str, Any]) -> Dict[str, Any]:
        """Process a state update chunk.

        Args:
            chunk: The state update dictionary

        Returns:
            Processed update for client consumption
        """
        # Extract the node that produced this update
        node = list(chunk.keys())[0] if chunk else "unknown"
        update = chunk.get(node, {})

        processed = {"type": "state_update", "node": node, "updates": {}}

        # Process specific updates
        if "messages" in update:
            # Extract the latest message
            messages = update["messages"]
            if messages:
                latest_message = (
                    messages[-1] if isinstance(messages, list) else messages
                )
                processed["updates"]["latest_message"] = self._process_message_chunk(
                    latest_message
                )

        if "analysis_result" in update and update["analysis_result"]:
            processed["updates"]["analysis_complete"] = True
            processed["updates"]["analysis_result"] = update["analysis_result"]

        if "needs_user_input" in update:
            processed["updates"]["needs_user_input"] = update["needs_user_input"]

        # Include any other state updates
        for key, value in update.items():
            if key not in ["messages", "analysis_result", "needs_user_input"]:
                processed["updates"][key] = value

        return processed

    async def stream_with_callback(
        self,
        log_content: str,
        on_token: Optional[callable] = None,
        on_tool_start: Optional[callable] = None,
        on_tool_end: Optional[callable] = None,
        on_complete: Optional[callable] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        """Stream analysis with callbacks for different events.

        Args:
            log_content: The log content to analyze
            on_token: Callback for streaming tokens
            on_tool_start: Callback when a tool starts
            on_tool_end: Callback when a tool completes
            on_complete: Callback when analysis is complete
            config: Optional configuration
        """
        async for event in self.stream_analysis(
            log_content, config, stream_mode="events"
        ):
            event_type = event.get("type", "")

            if event_type == "token" and on_token:
                await on_token(event["content"])

            elif event_type == "tool_start" and on_tool_start:
                await on_tool_start(event["tool"], event.get("inputs", {}))

            elif event_type == "tool_end" and on_tool_end:
                await on_tool_end(event["tool"], event.get("output"))

            elif event_type == "state_update":
                updates = event.get("updates", {})
                if updates.get("analysis_complete") and on_complete:
                    await on_complete(updates.get("analysis_result"))


# Example usage functions
async def example_streaming_usage():
    """Example of how to use the streaming analyzer."""
    analyzer = StreamingLogAnalyzer()

    # Example 1: Stream tokens as they're generated
    print("=== Streaming Tokens ===")
    async for event in analyzer.stream_analysis(
        "ERROR: Connection timeout to database server", stream_mode="events"
    ):
        if event["type"] == "token":
            print(event["content"], end="", flush=True)

    print("\n\n=== Streaming State Updates ===")
    # Example 2: Stream state updates
    async for update in analyzer.stream_analysis(
        "ERROR: Connection timeout to database server", stream_mode="updates"
    ):
        print(f"Update from {update['node']}: {update['updates']}")

    print("\n\n=== Using Callbacks ===")

    # Example 3: Use callbacks
    async def on_token(token: str):
        print(f"Token: {token}", end="")

    async def on_tool_start(tool: str, inputs: Dict):
        print(f"\n🔧 Starting tool: {tool}")

    async def on_tool_end(tool: str, output: Any):
        print(f"\n✅ Tool completed: {tool}")

    async def on_complete(result: Dict):
        print(f"\n🎉 Analysis complete! Found {len(result.get('issues', []))} issues")

    await analyzer.stream_with_callback(
        "ERROR: Connection timeout to database server",
        on_token=on_token,
        on_tool_start=on_tool_start,
        on_tool_end=on_tool_end,
        on_complete=on_complete,
    )


if __name__ == "__main__":
    # Run the examples
    asyncio.run(example_streaming_usage())
