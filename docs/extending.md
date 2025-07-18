# Extension Guide

This guide explains how to extend and customize the Log Analyzer Agent for your specific needs.

## Adding New Tools

Tools allow the agent to interact with external systems or perform specialized tasks. Here's how to add a new tool:

### 1. Define the Tool

Create a new function in `src/log_analyzer_agent/tools.py`:

```python
from langchain.tools import tool
from typing import Dict, Any, Annotated
from langchain.schema.runnable import RunnableConfig
from langchain_core.agents import AgentAction
from langchain_core.agents.agent import InjectedToolArg, InjectedState

@tool
async def custom_api_lookup(
    system_name: str,
    error_code: str,
    *,
    state: Annotated[State, InjectedState],
    config: Annotated[RunnableConfig, InjectedToolArg]
) -> str:
    """Look up error codes in a custom API system.
    
    Args:
        system_name: The name of the system to look up
        error_code: The specific error code to search for
        
    Returns:
        Detailed information about the error code
    """
    # Implementation
    # Example: call an external API, database, or service
    api_client = get_api_client(config.get("api_key"))
    result = await api_client.lookup_error(system_name, error_code)
    
    return format_api_result(result)
```

### 2. Register the Tool in the Graph

Update the graph definition in `src/log_analyzer_agent/graph.py`:

```python
from src.log_analyzer_agent.tools import search_documentation, custom_api_lookup

# In the graph creation function
def create_graph(features=None):
    # ... existing code ...
    
    # Register tools with the model
    model = raw_model.bind_tools(
        [search_documentation, request_additional_info, submit_analysis, custom_api_lookup], 
        tool_choice="any"
    )
    
    # ... rest of the function ...
```

### 3. Update Prompts (Optional)

You may want to update the system prompt to inform the agent about the new tool in `src/log_analyzer_agent/prompts.py`:

```python
ANALYSIS_SYSTEM_PROMPT = """You are a log analysis expert...

You have access to the following tools:
1. search_documentation - Search for relevant documentation
2. request_additional_info - Ask the user for more information
3. custom_api_lookup - Look up error codes in a custom API system
...
"""
```

## Customizing Prompts

The agent's behavior is largely determined by its prompts. Here's how to customize them:

### 1. Locate Prompt Templates

Prompts are defined in `src/log_analyzer_agent/prompts.py`:

```python
# Example of editing the existing system prompt
ANALYSIS_SYSTEM_PROMPT = """You are a log analysis expert specializing in identifying issues in application logs.

When analyzing logs, focus on:
1. Critical errors and exceptions
2. Performance bottlenecks
3. Security issues
4. Configuration problems
5. [Your custom focus area]

Format your response as a structured JSON with the following fields:
...
"""
```

### 2. Adjust the Level of Detail

You can customize how detailed the analysis should be:

```python
# For more detailed analysis
DETAILED_ANALYSIS_PROMPT = """Perform an exhaustive analysis of the provided logs.
Identify ALL issues, no matter how minor.
For each issue, provide:
1. Detailed technical explanation
2. Potential root causes (list at least 3)
3. Step-by-step troubleshooting procedures
4. References to relevant documentation
...
"""

# For concise analysis
CONCISE_ANALYSIS_PROMPT = """Analyze the logs and identify only the most critical issues.
Focus on problems that:
1. Cause system failure
2. Lead to data loss
3. Present security vulnerabilities
Provide brief, actionable suggestions for each issue.
...
"""
```

## Adding New Graph Nodes

For more complex extensions, you can add new nodes to the agent's graph:

### 1. Create a New Node Function

In `src/log_analyzer_agent/nodes/custom_nodes.py`:

```python
from src.log_analyzer_agent.state import CoreState
from typing import Optional
from langchain.schema.runnable import RunnableConfig

async def prioritize_issues(
    state: CoreState, 
    *, 
    config: Optional[RunnableConfig] = None
) -> CoreState:
    """Node that prioritizes issues based on severity and impact."""
    # Implementation
    if not state.analysis_result or "issues" not in state.analysis_result:
        return state
        
    # Sort issues by severity
    issues = state.analysis_result["issues"]
    prioritized_issues = sorted(
        issues,
        key=lambda x: severity_score(x.get("severity", "low"))
    )
    
    # Update state
    state.analysis_result["issues"] = prioritized_issues
    state.analysis_result["prioritized"] = True
    
    return state

def severity_score(severity: str) -> int:
    """Helper function to convert severity to numeric score."""
    scores = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}
    return scores.get(severity.lower(), 0)
```

### 2. Integrate the Node in the Graph

Update `src/log_analyzer_agent/graph.py`:

```python
from src.log_analyzer_agent.nodes.custom_nodes import prioritize_issues

def create_graph(features=None):
    # ... existing code ...
    
    # Add the new node to the graph
    graph.add_node("prioritize_issues", prioritize_issues)
    
    # Update edges to include the new node
    graph.add_edge("analyze_logs", "prioritize_issues")
    graph.add_edge("prioritize_issues", "validate_analysis")
    
    # ... rest of the function ...
```

## Creating a Custom Graph Configuration

You can create an entirely new graph configuration for specialized use cases:

### 1. Create a Configuration Class

In `src/log_analyzer_agent/configurations/custom_config.py`:

```python
from src.log_analyzer_agent.state import CoreState
from langchain.schema.runnable import RunnableConfig
from langgraph.graph import StateGraph

class SpecializedGraphConfiguration:
    """A graph configuration for specialized log analysis."""
    
    def __init__(self):
        """Initialize the configuration."""
        pass
        
    def get_name(self):
        """Get the name of this configuration."""
        return "specialized"
        
    def get_description(self):
        """Get a description of this configuration."""
        return "Specialized graph for security-focused log analysis"
        
    def supports_memory(self):
        """Whether this configuration supports memory."""
        return True
        
    def create_graph(self):
        """Create the specialized graph."""
        from src.log_analyzer_agent.nodes.analysis import analyze_logs
        from src.log_analyzer_agent.nodes.validation import validate_analysis
        from src.log_analyzer_agent.nodes.custom_nodes import security_scan
        
        # Create the graph
        graph = StateGraph(CoreState)
        
        # Add nodes
        graph.add_node("analyze_logs", analyze_logs)
        graph.add_node("security_scan", security_scan)
        graph.add_node("validate_analysis", validate_analysis)
        
        # Define edges
        graph.add_edge("analyze_logs", "security_scan")
        graph.add_edge("security_scan", "validate_analysis")
        graph.set_entry_point("analyze_logs")
        
        # Compile the graph
        return graph.compile()
```

### 2. Register the Configuration

Update `src/log_analyzer_agent/graph_factory.py`:

```python
from src.log_analyzer_agent.configurations.custom_config import SpecializedGraphConfiguration

class GraphFactory:
    # ... existing code ...
    
    @classmethod
    def create_graph(cls, mode="auto", features=None, use_legacy=False):
        """Create a graph based on the specified mode."""
        # ... existing code ...
        
        # Add your custom configuration
        if mode == "specialized":
            config = SpecializedGraphConfiguration()
            return config.create_graph()
            
        # ... rest of the method ...
```

## Customizing State Classes

You can extend the state to include additional fields:

### 1. Define a Custom State Class

In `src/log_analyzer_agent/custom_state.py`:

```python
from src.log_analyzer_agent.state import CoreState
from typing import List, Dict, Any, Optional

class SecurityState(CoreState):
    """State class with additional security-focused fields."""
    
    vulnerability_scan: Optional[Dict[str, Any]] = None
    compliance_check: Optional[Dict[str, Any]] = None
    threat_indicators: Optional[List[Dict[str, Any]]] = None
    security_score: Optional[float] = None
```

### 2. Use the Custom State in Your Graph

```python
from src.log_analyzer_agent.custom_state import SecurityState
from langgraph.graph import StateGraph

# Create graph with custom state
graph = StateGraph(SecurityState)

# ... rest of the graph definition ...
```

## Adding a New Model Provider

To use a different LLM provider:

### 1. Add the Provider Integration

In `src/log_analyzer_agent/utils.py`:

```python
async def init_custom_model(config: Optional[RunnableConfig] = None):
    """Initialize a custom model."""
    from langchain_custom_provider import CustomChatModel
    
    # Get API key
    api_key = os.environ.get("CUSTOM_API_KEY")
    if not api_key:
        raise ValueError("CUSTOM_API_KEY environment variable not set")
    
    # Initialize the model
    model = CustomChatModel(
        api_key=api_key,
        model_name="custom-model-name",
        max_tokens=8192,
        temperature=0.1
    )
    
    return model
```

### 2. Update the Model Initialization Logic

```python
async def init_model(config: Optional[RunnableConfig] = None):
    """Initialize the appropriate model based on configuration."""
    # Get model provider from config
    if config and "configurable" in config:
        provider = config["configurable"].get("model_provider", "gemini")
    else:
        provider = "gemini"
    
    # Select the appropriate model
    if provider == "gemini":
        return await _init_gemini_model(config)
    elif provider == "groq":
        return await _init_groq_model(config)
    elif provider == "custom":
        return await init_custom_model(config)
    else:
        raise ValueError(f"Unsupported model provider: {provider}")
```

## Creating Custom Evaluators

If you want to evaluate your agent's performance:

### 1. Define a Custom Evaluator

In `src/evaluation/evaluators/custom_evaluator.py`:

```python
from src.evaluation.core.interfaces import EvaluationMetric, SystemType
from typing import Dict, Any

class SecurityComplianceEvaluator(EvaluationMetric):
    """Evaluates whether the analysis meets security compliance standards."""
    
    def __init__(self, compliance_standards=None):
        """Initialize the evaluator."""
        self.compliance_standards = compliance_standards or {
            "pci_dss": ["credit_card", "payment", "pci"],
            "hipaa": ["health", "patient", "medical", "phi"],
            "gdpr": ["personal_data", "consent", "privacy"]
        }
    
    def get_name(self):
        """Get the name of this evaluator."""
        return "security_compliance"
        
    def get_description(self):
        """Get a description of this evaluator."""
        return "Evaluates whether the analysis correctly identifies compliance-related issues"
        
    def applies_to(self, system_type: SystemType):
        """Determine if this evaluator applies to the given system type."""
        return True  # Applies to all system types
        
    def evaluate(self, outputs: Dict[str, Any], reference: Dict[str, Any]):
        """Evaluate the outputs against the reference."""
        # Implementation
        compliance_score = self._evaluate_compliance_coverage(
            outputs.get("analysis_result", {}).get("issues", []),
            reference.get("log_content", "")
        )
        
        return {
            "score": compliance_score,
            "max_score": 1.0,
            "comments": f"Compliance coverage: {compliance_score * 100:.1f}%"
        }
        
    def _evaluate_compliance_coverage(self, issues, log_content):
        """Calculate compliance coverage score."""
        # Implementation details
        # ...
        return score  # 0.0 to 1.0
```

### 2. Register the Evaluator

In your evaluation code:

```python
from src.evaluation.evaluators.custom_evaluator import SecurityComplianceEvaluator

# Create and use the evaluator
evaluator = SecurityComplianceEvaluator()
results = evaluator.evaluate(agent_output, reference_data)
print(f"Compliance score: {results['score']}")
```

## Best Practices for Extensions

1. **Maintain Compatibility**: Ensure your extensions work with the existing system
2. **Test Thoroughly**: Create unit tests for your extensions
3. **Document Changes**: Update documentation to reflect new capabilities
4. **Follow Design Patterns**: Match the existing code style and patterns
5. **Versioning**: Consider how your extensions will be maintained across versions