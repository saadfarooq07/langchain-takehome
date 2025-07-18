# API Reference

This document provides a comprehensive reference for the Log Analyzer Agent's API.

## REST API

When running in API mode, the agent exposes a RESTful API that can be used to analyze logs and manage user data.

### Starting the API Server

```bash
python main.py --mode api
```

By default, the server runs on `http://localhost:8000`. You can change the port with the `--port` option.

### API Endpoints

#### Authentication

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/auth/register` | POST | Register a new user |
| `/api/v1/auth/login` | POST | Login and get access token |
| `/api/v1/auth/logout` | POST | Logout (invalidate token) |

#### Log Analysis

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/analyze` | POST | Analyze log content |
| `/api/v1/history` | GET | Get analysis history |
| `/api/v1/history/{id}` | GET | Get specific analysis result |

#### Memory

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/memory/search` | POST | Search for similar issues |
| `/api/v1/applications` | GET | List user applications |
| `/api/v1/applications/{name}/context` | GET | Get application context |
| `/api/v1/applications/{name}/context` | PUT | Update application context |

#### Utilities

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/health` | GET | Health check endpoint |
| `/api/v1/preferences` | GET | Get user preferences |
| `/api/v1/preferences` | PUT | Update user preferences |

### API Models

#### Log Analysis

**LogAnalysisRequest**
```json
{
  "log_content": "string",
  "environment_details": {
    "software": "string",
    "runtime": "string",
    "database": "string",
    "additional": {}
  },
  "user_id": "string",  // Optional
  "application_name": "string",  // Optional
  "mode": "string"  // Optional: minimal, interactive, memory
}
```

**LogAnalysisResponse**
```json
{
  "analysis_id": "string",
  "analysis_result": {
    "issues": [
      {
        "id": "string",
        "description": "string",
        "severity": "string",
        "location": "string",
        "suggestion": "string",
        "diagnostic_commands": ["string"]
      }
    ],
    "summary": "string",
    "documentation_references": ["string"],
    "performance_metrics": {},
    "memory_matches": []  // Only when using memory mode
  },
  "timestamp": "string"
}
```

#### Authentication

**UserRegistration**
```json
{
  "email": "string",
  "password": "string",
  "full_name": "string"
}
```

**AuthResponse**
```json
{
  "access_token": "string",
  "token_type": "string",
  "user": {
    "id": "string",
    "email": "string",
    "full_name": "string"
  }
}
```

### Example API Usage

#### Analyzing Logs

```bash
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "log_content": "2023-08-15T14:25:12.345Z ERROR [app.main] Failed to connect to database: Connection refused",
    "environment_details": {
      "software": "MyApp v1.2.3",
      "database": "PostgreSQL 14.5"
    }
  }'
```

#### Authentication and Memory Search

```bash
# Login
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "password123"
  }' | jq -r '.access_token')

# Search memory with authentication
curl -X POST http://localhost:8000/api/v1/memory/search \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "application_name": "myapp",
    "query": "database connection"
  }'
```

## Python API

The Log Analyzer Agent can also be used programmatically through its Python API.

### Core Classes

#### GraphFactory

The `GraphFactory` class provides methods to create different types of graphs:

```python
from src.log_analyzer_agent.graph_factory import GraphFactory

# Create a graph with the specified mode
graph = GraphFactory.create_graph(mode="interactive")

# Create a graph with specific features
graph = GraphFactory.create_graph(mode="minimal", features={"documentation_search"})

# Create a memory-enabled graph with database connection
graph = GraphFactory.create_graph(mode="memory")
```

#### StreamingLogAnalyzer

The `StreamingLogAnalyzer` class provides streaming functionality:

```python
from src.log_analyzer_agent.streaming import StreamingLogAnalyzer

analyzer = StreamingLogAnalyzer()

# Stream with callbacks
analyzer.stream_with_callback(
    log_content="log content here",
    on_token=lambda token: print(token, end=""),
    on_tool_start=lambda tool, inputs: print(f"\nTool: {tool}"),
    on_tool_end=lambda tool, output: print(f"\nResult: {output}"),
    on_complete=lambda result: print("\nDone!")
)

# Stream with updates
for update in analyzer.stream_analysis(
    log_content="log content here",
    stream_mode="updates"
):
    print(f"Update: {update}")
```

#### MemoryService

The `MemoryService` class provides memory functionality:

```python
from src.log_analyzer_agent.services.memory_service import MemoryService
from langchain.memory import PostgresChatMessageHistory

# Create memory service
memory_service = MemoryService(PostgresChatMessageHistory("postgres://..."))

# Store analysis result
memory_service.store_analysis_result(
    user_id="user123",
    application_name="myapp",
    log_content="log content",
    analysis_result={...},
    performance_metrics={...}
)

# Search for similar issues
similar_issues = memory_service.search_similar_issues(
    user_id="user123",
    application_name="myapp",
    current_log_content="log content",
    limit=5
)
```

### State Classes

The agent uses typed state classes:

```python
from src.log_analyzer_agent.state import CoreState, InteractiveState, MemoryState

# Create a state object
state = CoreState(
    log_content="log content here",
    environment_details={"software": "MyApp v1.2.3"}
)

# Create an interactive state
interactive_state = InteractiveState(
    log_content="log content here",
    environment_details={"software": "MyApp v1.2.3"},
    user_input="Additional context: This happened after server restart"
)

# Create a memory state
memory_state = MemoryState(
    log_content="log content here",
    environment_details={"software": "MyApp v1.2.3"},
    user_id="user123",
    application_name="myapp"
)
```

### API Integration

To use the Log Analyzer Agent with the FastAPI server:

```python
from fastapi import FastAPI, Depends, HTTPException
from src.log_analyzer_agent.api.models import LogAnalysisRequest, LogAnalysisResponse
from src.log_analyzer_agent.graph_factory import GraphFactory

app = FastAPI()

@app.post("/analyze", response_model=LogAnalysisResponse)
async def analyze_logs(request: LogAnalysisRequest):
    # Create appropriate graph based on request
    mode = request.mode or "minimal"
    graph = GraphFactory.create_graph(mode=mode)
    
    # Prepare state
    state = {
        "log_content": request.log_content,
        "environment_details": request.environment_details
    }
    
    # Add memory fields if needed
    if mode == "memory" and request.user_id:
        state["user_id"] = request.user_id
        state["application_name"] = request.application_name or "default"
    
    # Run analysis
    try:
        result = graph.invoke(state)
        return LogAnalysisResponse(
            analysis_id=generate_id(),
            analysis_result=result["analysis_result"],
            timestamp=get_timestamp()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

## WebSocket API

For real-time streaming of analysis results, the agent provides a WebSocket API:

```python
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from src.log_analyzer_agent.streaming import StreamingLogAnalyzer

app = FastAPI()

@app.websocket("/ws/analyze")
async def websocket_analyze(websocket: WebSocket):
    await websocket.accept()
    
    try:
        # Receive request
        data = await websocket.receive_json()
        log_content = data.get("log_content")
        
        if not log_content:
            await websocket.send_json({"error": "Log content is required"})
            await websocket.close()
            return
        
        # Create streaming analyzer
        analyzer = StreamingLogAnalyzer()
        
        # Define callbacks
        async def on_token(token):
            await websocket.send_json({"type": "token", "content": token})
            
        async def on_tool_start(tool, inputs):
            await websocket.send_json({"type": "tool_start", "tool": tool, "inputs": inputs})
            
        async def on_tool_end(tool, output):
            await websocket.send_json({"type": "tool_end", "tool": tool, "output": output})
            
        async def on_complete(result):
            await websocket.send_json({"type": "complete", "result": result})
        
        # Run analysis with streaming
        await analyzer.stream_with_callback(
            log_content=log_content,
            on_token=on_token,
            on_tool_start=on_tool_start,
            on_tool_end=on_tool_end,
            on_complete=on_complete
        )
        
    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        await websocket.send_json({"type": "error", "message": str(e)})
        await websocket.close()
```

## API Security

The API includes security features:

1. **Authentication**: JWT-based authentication for protected endpoints
2. **Rate Limiting**: Prevents abuse of the API
3. **Input Validation**: Validates all inputs to prevent injection attacks
4. **CORS**: Configurable CORS settings for frontend integration

Example securing an endpoint:

```python
from fastapi import Depends, HTTPException
from src.log_analyzer_agent.api.auth import get_current_user
from src.log_analyzer_agent.api.models import UserResponse

@app.get("/api/v1/protected-endpoint")
async def protected_endpoint(current_user: UserResponse = Depends(get_current_user)):
    # Only authenticated users can access this endpoint
    return {"message": f"Hello, {current_user.full_name}"}
```