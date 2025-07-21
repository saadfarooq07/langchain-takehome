"""Patch SSE compatibility issue with langgraph-api"""
import sse_starlette

# Monkey patch to fix the attribute name issues
# 1. Fix listen_for_exit_signal
if hasattr(sse_starlette.EventSourceResponse, '_listen_for_exit_signal'):
    # Create a wrapper that accepts the extra argument
    def listen_for_exit_signal_wrapper(self):
        if hasattr(self, '_listen_for_exit_signal'):
            return self._listen_for_exit_signal()
    sse_starlette.EventSourceResponse.listen_for_exit_signal = listen_for_exit_signal_wrapper

# 2. Add missing listen_for_disconnect method
if not hasattr(sse_starlette.EventSourceResponse, 'listen_for_disconnect'):
    async def listen_for_disconnect(self, receive):
        """Listen for client disconnect"""
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                break
    sse_starlette.EventSourceResponse.listen_for_disconnect = listen_for_disconnect

print("SSE patch applied successfully")