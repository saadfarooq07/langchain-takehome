"""Enhanced analysis node with comprehensive fixes integrated.

This module demonstrates how to integrate all the reliability and security fixes
into the existing analysis nodes.
"""

import asyncio
from typing import Dict, Any, Optional
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig

# Import our enhanced systems
from ..core.circuit_breaker import get_execution_controller, ExecutionLimits
from ..core.api_manager import get_api_manager, APIProvider, rate_limited_api_call
from ..core.resource_manager import get_resource_manager, ResourceType
from ..core.error_handling import (
    get_error_recovery_manager, error_boundary, safe_operation,
    APIError, ValidationError, ResourceExhaustionError
)
from ..state import CoreState
from ..configuration import Configuration
from ..validation import LogValidator


@error_boundary("log_analysis", max_retries=3, timeout_seconds=120)
async def enhanced_analyze_logs(
    state: CoreState,
    *,
    config: Optional[RunnableConfig] = None,
    store=None,
) -> Dict[str, Any]:
    """Enhanced log analysis with comprehensive reliability fixes.
    
    This version integrates:
    - Circuit breaker protection
    - API rate limiting 
    - Resource management
    - Enhanced error handling
    """
    # Get configuration
    configuration = Configuration.from_runnable_config(config)
    
    # Get enhanced systems
    execution_controller = get_execution_controller()
    api_manager = get_api_manager()
    resource_manager = get_resource_manager()
    
    # Execute within controlled environment
    async with execution_controller.execute_operation("analyze_logs") as metrics:
        
        # 1. Enhanced Input Validation
        async with safe_operation("input_validation"):
            log_content = getattr(state, "log_content", "")
            if not log_content:
                raise ValidationError(
                    "No log content provided",
                    field_name="log_content",
                    validation_rule="required"
                )
            
            # Validate with enhanced validator
            is_valid, error_msg, sanitized_info = LogValidator.validate_log_content(log_content)
            if not is_valid:
                raise ValidationError(
                    f"Log validation failed: {error_msg}",
                    field_name="log_content",
                    validation_rule="size_and_format"
                )
        
        # 2. Resource Usage Check
        resource_stats = resource_manager.get_resource_stats()
        memory_usage_percent = resource_stats["memory"]["usage_percent"]
        
        if memory_usage_percent > 80:
            raise ResourceExhaustionError(
                f"Memory usage too high: {memory_usage_percent}%",
                resource_type="memory",
                current_usage=memory_usage_percent,
                limit=100
            )
        
        # 3. Enhanced API Call with Rate Limiting
        async with safe_operation("api_call_preparation"):
            # Estimate token usage based on log size
            estimated_tokens = min(len(log_content) // 4, 8000)  # Rough estimate
            
            # Prepare prompt
            prompt_content = f"""
            Analyze the following log content and identify:
            1. Issues and errors with severity levels
            2. Root cause analysis
            3. Specific recommendations for resolution
            4. Relevant documentation references
            
            Environment: {getattr(state, 'environment_details', {})}
            
            Log content:
            {log_content[:4000]}  # Truncate for safety
            """
        
        # 4. Rate-Limited API Call
        @rate_limited_api_call(APIProvider.GEMINI, estimated_tokens)
        async def make_analysis_call():
            # Initialize model with resource tracking
            from ..utils import init_model_async
            model = await init_model_async(config)
            
                         # Track this as a managed resource
             model_resource = await resource_manager.register_resource(
                 f"model_{asyncio.current_task()}",
                 model,
                 resource_type=ResourceType.HTTP_SESSION,
                 cleanup_func=lambda m: None  # Models typically don't need cleanup
             )
             
             try:
                 # Create messages
                 messages = [HumanMessage(content=prompt_content)]
                 if hasattr(state, "messages") and state.messages:
                     # Only include HumanMessage and AIMessage types for safety
                     recent_messages = [msg for msg in state.messages[-3:] if isinstance(msg, (HumanMessage, AIMessage))]
                     messages.extend(recent_messages)
                
                # Make the API call
                response = await model.ainvoke(messages)
                
                return response
                
            finally:
                # Cleanup model resource
                await resource_manager.unregister_resource(f"model_{asyncio.current_task()}")
        
        # Execute the API call
        async with safe_operation("llm_api_call"):
            try:
                response = await make_analysis_call()
                metrics.increment_tool_call()
                
            except Exception as e:
                # Convert to our enhanced error type
                raise APIError(
                    f"LLM API call failed: {str(e)}",
                    api_provider="gemini",
                    status_code=getattr(e, 'status_code', None)
                )
        
        # 5. Enhanced Response Processing
        async with safe_operation("response_processing"):
            if not isinstance(response, AIMessage):
                raise ValidationError(
                    "Invalid response type from LLM",
                    field_name="response",
                    validation_rule="must_be_ai_message"
                )
            
            # Parse response content
            try:
                analysis_result = _parse_analysis_response(response.content)
            except Exception as e:
                raise ValidationError(
                    f"Failed to parse LLM response: {str(e)}",
                    field_name="response_content",
                    validation_rule="valid_json_structure"
                )
        
        # 6. Enhanced Result Validation
        async with safe_operation("result_validation"):
            if not _validate_analysis_quality(analysis_result):
                # Log the issue but don't fail - return best effort result
                analysis_result = _create_fallback_analysis(log_content, sanitized_info)
        
        # 7. Update execution metrics
        execution_status = execution_controller.get_status()
        analysis_result["execution_metadata"] = {
            "iterations": execution_status["total_iterations"],
            "tool_calls": execution_status["tool_calls"],
            "elapsed_time": execution_status["elapsed_time"],
            "memory_usage_mb": resource_stats["memory"]["current_mb"],
            "circuit_state": execution_status["circuit_state"]
        }
        
        return {
            "messages": [response] if isinstance(response, AIMessage) else [],
            "analysis_result": analysis_result,
            "needs_user_input": False,
        }


def _parse_analysis_response(content: str) -> Dict[str, Any]:
    """Parse and structure the analysis response with fallback handling."""
    try:
        # Try to parse as JSON first
        import json
        if content.strip().startswith("{"):
            return json.loads(content)
    except:
        pass
    
    # Fallback: Extract structured information from text
    lines = content.split('\n')
    
    issues = []
    recommendations = []
    current_section = None
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Detect sections
        if any(keyword in line.lower() for keyword in ['issue', 'error', 'problem']):
            current_section = 'issues'
            if line not in ['Issues:', 'Errors:', 'Problems:']:
                issues.append({
                    "type": "error",
                    "description": line,
                    "severity": "medium"
                })
        elif any(keyword in line.lower() for keyword in ['recommend', 'suggest', 'solution']):
            current_section = 'recommendations'
            if line not in ['Recommendations:', 'Suggestions:', 'Solutions:']:
                recommendations.append(line)
        elif current_section == 'issues' and line.startswith(('-', '*', '•')):
            issues.append({
                "type": "error",
                "description": line[1:].strip(),
                "severity": "medium"
            })
        elif current_section == 'recommendations' and line.startswith(('-', '*', '•')):
            recommendations.append(line[1:].strip())
    
    return {
        "issues": issues or [{"type": "analysis", "description": "Log analysis completed", "severity": "info"}],
        "explanations": [content[:500] + "..." if len(content) > 500 else content],
        "suggestions": recommendations or ["Review the analysis above"],
        "documentation_references": [],
        "diagnostic_commands": []
    }


def _validate_analysis_quality(analysis_result: Dict[str, Any]) -> bool:
    """Validate that the analysis result meets quality standards."""
    required_fields = ["issues", "explanations", "suggestions"]
    
    # Check required fields exist
    for field in required_fields:
        if field not in analysis_result:
            return False
        if not analysis_result[field]:
            return False
    
    # Check issues have proper structure
    for issue in analysis_result.get("issues", []):
        if not isinstance(issue, dict):
            return False
        if "description" not in issue or not issue["description"]:
            return False
    
    return True


def _create_fallback_analysis(log_content: str, sanitized_info: Dict[str, Any]) -> Dict[str, Any]:
    """Create a fallback analysis when LLM response is inadequate."""
    
    # Simple pattern-based analysis
    lines = log_content.split('\n')
    error_lines = [line for line in lines if any(keyword in line.lower() for keyword in ['error', 'fail', 'exception', 'fatal'])]
    warning_lines = [line for line in lines if any(keyword in line.lower() for keyword in ['warn', 'warning'])]
    
    issues = []
    
    # Detect common patterns
    if error_lines:
        issues.append({
            "type": "error_detected",
            "description": f"Found {len(error_lines)} error lines in logs",
            "severity": "high"
        })
    
    if len(lines) > sanitized_info.get("line_count", 0) * 0.1:  # More than 10% warnings
        issues.append({
            "type": "high_warning_rate",
            "description": f"Found {len(warning_lines)} warning lines, indicating potential issues",
            "severity": "medium"
        })
    
    return {
        "issues": issues or [{"type": "no_issues", "description": "No obvious issues detected", "severity": "info"}],
        "explanations": [
            f"Automatic analysis of {sanitized_info.get('line_count', 0)} log lines",
            f"Found {len(error_lines)} errors and {len(warning_lines)} warnings"
        ],
        "suggestions": [
            "Review error lines for specific failure patterns",
            "Check system resources and connectivity",
            "Consult application documentation for error codes"
        ],
        "documentation_references": [],
        "diagnostic_commands": [
            {"command": "tail -n 50 /var/log/syslog", "description": "Check recent system logs"},
            {"command": "systemctl status <service>", "description": "Check service status"}
        ]
    }


# Enhanced routing with circuit breaker integration
async def enhanced_route_after_analysis(state: CoreState) -> str:
    """Enhanced routing with circuit breaker protection."""
    execution_controller = get_execution_controller()
    status = execution_controller.get_status()
    
    # Check circuit breaker state
    if status["circuit_state"] == "open":
        return "__end__"  # Stop execution if circuit is open
    
    # Check iteration limits
    if status["total_iterations"] >= status["limits"]["max_total_iterations"]:
        return "__end__"
    
    # Normal routing logic
    messages = getattr(state, "messages", [])
    last_message = messages[-1] if messages else None
    
    if hasattr(state, "analysis_result") and state.analysis_result:
        return "validate_analysis"
    
    return "analyze_logs"


# Enhanced tools execution with rate limiting
@error_boundary("tools_execution", max_retries=2)
async def enhanced_execute_tools(state: CoreState, *, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    """Enhanced tools execution with rate limiting and error handling."""
    
    execution_controller = get_execution_controller()
    
    async with execution_controller.execute_operation("execute_tools") as metrics:
        messages = getattr(state, "messages", [])
        last_message = messages[-1] if messages else None
        
        if not isinstance(last_message, AIMessage) or not last_message.tool_calls:
            return {"messages": []}
        
        results = []
        
        for tool_call in last_message.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call.get("args", {})
            
            try:
                if tool_name == "search_documentation":
                    # Rate-limited documentation search
                    @rate_limited_api_call(APIProvider.TAVILY, estimated_tokens=100)
                    async def search_docs():
                        from ..tools import search_documentation
                        return await search_documentation.ainvoke(tool_args)
                    
                    result = await search_docs()
                    metrics.increment_tool_call()
                    
                else:
                    # Handle other tools normally
                    from ..tools import create_tools
                    tools = create_tools()
                    tools_dict = {tool.name: tool for tool in tools}
                    
                    if tool_name in tools_dict:
                        result = await tools_dict[tool_name].ainvoke(tool_args)
                        metrics.increment_tool_call()
                    else:
                        result = f"Unknown tool: {tool_name}"
                
                results.append({
                    "tool": tool_name,
                    "result": str(result),
                    "success": True
                })
                
            except Exception as e:
                error_msg = f"Tool {tool_name} failed: {str(e)}"
                results.append({
                    "tool": tool_name,
                    "result": error_msg,
                    "success": False
                })
                
                # Log the error
                recovery_manager = get_error_recovery_manager()
                from ..core.error_handling import ErrorContext, ErrorCategory, ErrorSeverity, RecoveryStrategy
                
                error_context = ErrorContext(
                    error_type="ToolExecutionError",
                    error_message=error_msg,
                    severity=ErrorSeverity.MEDIUM,
                    category=ErrorCategory.API_COMMUNICATION,
                    operation_name=f"tool_{tool_name}",
                    recovery_strategy=RecoveryStrategy.NO_RECOVERY,
                    metadata={"tool_name": tool_name, "tool_args": tool_args}
                )
                recovery_manager.record_error(error_context)
        
        return {
            "messages": [],
            "tool_results": results
        } 