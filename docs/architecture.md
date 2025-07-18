# Architecture Guide

This document explains the architecture of the Log Analyzer Agent, including its graph system, state management, and core components.

## Graph Architecture

The agent is built on LangGraph's StateGraph system with three distinct operation modes:

### 1. Minimal Graph

![Minimal Graph](./images/minimal_graph_diagram.png)

The Minimal Graph offers:
- Core analysis functionality only
- Lowest memory overhead
- Fastest execution time
- No user interaction or memory persistence

Core flow:
1. Input validation
2. Log analysis
3. Result validation
4. Output formatting

### 2. Interactive Graph

![Interactive Graph](./images/interactive_graph_diagram.png)

The Interactive Graph extends the Minimal Graph with:
- User interaction node
- Tool-calling capabilities
- Interactive follow-up questions
- Documentation search functionality

Core flow:
1. Input validation
2. Log analysis
3. Result validation
4. (Optional) Request additional information from user
5. (Optional) Search documentation
6. Output formatting

### 3. Memory Graph

![Memory Graph](./images/memory_graph_diagram.png)

The Memory Graph is the most feature-rich with:
- Database persistence
- User and application context
- Historical issue tracking
- Pattern recognition across analyses
- Similar issue search
- Suggested solutions based on past successes

Core flow:
1. Input validation
2. Retrieve context from memory
3. Log analysis with context
4. Result validation
5. (Optional) Interactive features
6. Store results in memory
7. Output formatting with historical context

## State Management

The system uses a progressive enhancement approach with typed state classes:

### CoreState

Base state for all graph modes:

```python
class CoreState:
    log_content: str
    environment_details: Optional[Dict[str, Any]] = None
    analysis_result: Optional[Dict[str, Any]] = None
    validation_result: Optional[Dict[str, Any]] = None
    system_prompt: Optional[str] = None
```

### InteractiveState

Extends CoreState with interactive features:

```python
class InteractiveState(CoreState):
    user_input: Optional[str] = None
    pending_questions: Optional[List[str]] = None
    documentation_results: Optional[List[Dict[str, Any]]] = None
    user_interaction_required: bool = False
```

### MemoryState

Extends InteractiveState with memory features:

```python
class MemoryState(InteractiveState):
    user_id: str = "demo_user"
    application_name: str = "demo_app"
    memory_matches: Optional[List[Dict[str, Any]]] = None
    application_context: Optional[Dict[str, Any]] = None
    performance_metrics: Optional[Dict[str, Any]] = None
```

## Core Components

### Analysis Node

The central component that performs log analysis:

```python
async def analyze_logs(
    state: CoreState, 
    *, 
    config: Optional[RunnableConfig] = None
) -> CoreState:
    # Initialize model
    model = await init_model(config)
    
    # Prepare context and prompt
    system_prompt = state.system_prompt or ANALYSIS_SYSTEM_PROMPT
    
    # Run analysis
    response = await model.invoke({
        "role": "system", 
        "content": system_prompt,
        "log_content": state.log_content,
        "environment_details": state.environment_details or {}
    })
    
    # Process response
    state.analysis_result = response
    
    return state
```

### Validation Node

Ensures analysis quality:

```python
async def validate_analysis(
    state: CoreState, 
    *, 
    config: Optional[RunnableConfig] = None
) -> CoreState:
    # Check if analysis meets quality criteria
    quality_checks = AnalysisQualityCheck(state.analysis_result)
    validation_result = quality_checks.validate()
    
    state.validation_result = validation_result
    
    return state
```

### User Input Node

Handles interactive requests:

```python
async def handle_user_input(
    state: InteractiveState, 
    *, 
    config: Optional[RunnableConfig] = None
) -> InteractiveState:
    # Process user input if available
    if state.user_input:
        # Update analysis based on new information
        state = await update_analysis_with_user_input(state, config)
        
    # Check if we need more information
    if state.pending_questions:
        state.user_interaction_required = True
        
    return state
```

### Memory Integration

For the Memory mode:

```python
async def retrieve_context(
    state: MemoryState, 
    *, 
    config: Optional[RunnableConfig] = None
) -> MemoryState:
    # Get memory service
    memory_service = get_memory_service()
    
    # Retrieve application context
    state.application_context = await memory_service.get_application_context(
        state.user_id, 
        state.application_name
    )
    
    # Find similar issues
    state.memory_matches = await memory_service.search_similar_issues(
        state.user_id,
        state.application_name,
        state.log_content
    )
    
    return state
```

## Tool Integration

The agent uses LangChain tools for external integrations:

```python
@tool
async def search_documentation(
    query: str, 
    *, 
    config: Annotated[RunnableConfig, InjectedToolArg]
) -> str:
    """Search for documentation related to the issue."""
    search_client = get_search_client()
    results = await search_client.search(query)
    return format_search_results(results)
```

## Dual Model Architecture

The agent uses two different models:

1. **Primary Analysis Model** (Gemini 2.5 Flash):
   - Processes large log files
   - Handles the core analysis work
   - Extracts patterns and issues from logs

2. **Orchestration Model** (Kimi K2):
   - Manages the agent workflow
   - Handles tool calling decisions
   - Processes user interactions
   - Generally faster and more efficient for agent orchestration

This dual-model approach optimizes for both analysis quality and agent responsiveness.

## Data Flow

1. **Input**: Log content and environment details
2. **Preprocessing**: Log sanitization and format detection
3. **Analysis**: Issue detection and classification
4. **Validation**: Quality checking of analysis results
5. **Enhancement**: User interaction or memory retrieval
6. **Formatting**: Output standardization
7. **Persistence**: (Memory mode only) Storing results

## Dependency Graph

Key dependencies:

- **LangGraph**: Core state machine implementation
- **LangChain**: Model integration and tools
- **PostgreSQL**: Database for Memory mode
- **Gemini API**: Primary analysis model
- **Groq API**: Orchestration model
- **Tavily API**: Documentation search

## Extensibility Points

The architecture provides several extension points:

1. **Graph Nodes**: Add new nodes to the graph
2. **Tools**: Add new tools for additional capabilities
3. **State Additions**: Extend state classes with new fields
4. **Models**: Replace models with different providers
5. **Memory Providers**: Change persistence layer implementation