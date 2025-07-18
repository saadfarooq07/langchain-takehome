"""Refactored node implementations using focused components.

This module provides clean node implementations that delegate to
focused analyzer components instead of being monolithic functions.
"""

from typing import Dict, Any, Optional

from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq

from ..core.states import WorkingState, InputState
from ..core.config import Config
from ..core.logging import get_logger, log_execution_time
from ..core.analyzers import LogPreprocessor, MemoryAnalyzer, LogAnalyzer
from ..services.memory_service import MemoryService
from ..tools import create_tools


logger = get_logger("log_analyzer.nodes")


@log_execution_time("log_analyzer.nodes.analyze")
async def analyze_logs_node(state: WorkingState, config: Config) -> Dict[str, Any]:
    """Analyze log content using focused components.
    
    This is a refactored version that breaks down the analysis into:
    1. Preprocessing
    2. Memory search (if enabled)
    3. Analysis
    4. Result handling
    
    Args:
        state: Working state
        config: Configuration
        
    Returns:
        State updates
    """
    logger.info("Starting log analysis")
    
    # Get input from messages or state
    log_content = None
    environment_details = None
    
    if state.messages:
        last_message = state.messages[-1]
        if isinstance(last_message, HumanMessage):
            # Try to parse structured input
            try:
                content = last_message.content
                if isinstance(content, dict):
                    log_content = content.get("log_content")
                    environment_details = content.get("environment_details")
                else:
                    log_content = content
            except:
                log_content = str(last_message.content)
    
    if not log_content:
        logger.error("No log content found in state")
        return {
            "current_analysis": {
                "error": "No log content provided",
                "issues": [],
                "root_cause": "Unable to analyze - no logs provided",
                "recommendations": ["Please provide log content to analyze"]
            }
        }
    
    try:
        # 1. Preprocess logs
        preprocessor = LogPreprocessor()
        processed_content, metadata = preprocessor.preprocess(
            log_content,
            max_lines=config.execution_limits.max_log_size_mb * 1000  # Rough estimate
        )
        
        # 2. Search memory if enabled
        similar_issues = []
        if state.has_feature("memory"):
            try:
                memory_service = MemoryService(config.database.url)
                memory_analyzer = MemoryAnalyzer(memory_service)
                similar_issues = await memory_analyzer.find_similar_issues(
                    log_content,
                    metadata,
                    limit=5
                )
                state.similar_issues = similar_issues
            except Exception as e:
                logger.warning(f"Memory search failed: {e}")
        
        # 3. Get additional context if available
        additional_context = None
        if state.user_response and state.pending_request:
            additional_context = state.user_response
        
        # 4. Perform analysis
        model = _create_model(config.primary_model)
        analyzer = LogAnalyzer(model, config)
        
        analysis_result = await analyzer.analyze(
            processed_content,
            metadata,
            environment_details=environment_details,
            similar_issues=similar_issues,
            additional_context=additional_context
        )
        
        # 5. Check if we need more information
        needs_info = _check_needs_more_info(analysis_result, metadata)
        
        # 6. Prepare response message
        response_parts = [
            f"# Log Analysis Results\n",
            f"## Issues Identified ({len(analysis_result['issues'])})\n"
        ]
        
        for i, issue in enumerate(analysis_result['issues'], 1):
            response_parts.append(f"{i}. {issue}")
        
        response_parts.extend([
            f"\n## Root Cause Analysis\n{analysis_result['root_cause']}",
            f"\n## Recommendations\n"
        ])
        
        for i, rec in enumerate(analysis_result['recommendations'], 1):
            response_parts.append(f"{i}. {rec}")
        
        response_message = '\n'.join(response_parts)
        
        # 7. Create tool calls if needed
        tool_calls = []
        if needs_info and state.has_feature("interactive"):
            tool_calls.append({
                "name": "request_additional_info",
                "args": {
                    "question": "Could you provide more context about when this issue started or any recent changes to the system?"
                }
            })
        
        # Update state
        updates = {
            "messages": [AIMessage(content=response_message, tool_calls=tool_calls)],
            "current_analysis": analysis_result,
            "needs_user_input": bool(tool_calls),
            "token_count": state.token_count + _estimate_tokens(response_message)
        }
        
        if tool_calls:
            updates["pending_request"] = tool_calls[0]
        
        logger.info("Analysis complete", extra={
            "issues_found": len(analysis_result['issues']),
            "has_root_cause": bool(analysis_result.get('root_cause')),
            "needs_more_info": needs_info
        })
        
        return updates
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
        return {
            "current_analysis": {
                "error": str(e),
                "issues": ["Analysis failed due to an error"],
                "root_cause": "Unable to complete analysis",
                "recommendations": ["Please check the logs and try again"]
            },
            "messages": [AIMessage(content=f"Analysis failed: {str(e)}")]
        }


@log_execution_time("log_analyzer.nodes.validate")
async def validate_analysis_node(state: WorkingState, config: Config) -> Dict[str, Any]:
    """Validate analysis quality.
    
    Args:
        state: Working state
        config: Configuration
        
    Returns:
        State updates
    """
    logger.info("Validating analysis")
    
    analysis = state.current_analysis
    if not analysis:
        logger.error("No analysis to validate")
        return {}
    
    # Simple validation for now
    is_valid = (
        len(analysis.get('issues', [])) > 0 and
        analysis.get('root_cause') and
        len(analysis.get('recommendations', [])) > 0
    )
    
    if not is_valid:
        logger.warning("Analysis validation failed", extra={
            "has_issues": len(analysis.get('issues', [])) > 0,
            "has_root_cause": bool(analysis.get('root_cause')),
            "has_recommendations": len(analysis.get('recommendations', [])) > 0
        })
        
        # Could trigger re-analysis here
        return {
            "messages": [AIMessage(content="Analysis incomplete - missing required components")]
        }
    
    logger.info("Analysis validated successfully")
    
    # Store in memory if enabled
    if state.has_feature("memory") and config.database.is_configured:
        try:
            memory_service = MemoryService(config.database.url)
            await memory_service.store_analysis(
                thread_id=state.thread_id,
                analysis=analysis,
                metadata={
                    "session_id": state.session_id,
                    "timestamp": state.start_time
                }
            )
            logger.info("Analysis stored in memory")
        except Exception as e:
            logger.error(f"Failed to store analysis: {e}")
    
    return {
        "messages": [AIMessage(content="Analysis complete and validated")]
    }


@log_execution_time("log_analyzer.nodes.user_input")
async def handle_user_input_node(state: WorkingState, config: Config) -> Dict[str, Any]:
    """Handle user input responses.
    
    Args:
        state: Working state
        config: Configuration
        
    Returns:
        State updates
    """
    logger.info("Handling user input")
    
    if not state.user_response:
        logger.warning("No user response to handle")
        return {}
    
    # Clear the input request state
    updates = {
        "needs_user_input": False,
        "pending_request": None,
        "messages": [HumanMessage(content=state.user_response)]
    }
    
    logger.info("User input processed", extra={
        "response_length": len(state.user_response)
    })
    
    return updates


@log_execution_time("log_analyzer.nodes.tools")
async def execute_tools_node(state: WorkingState, config: Config) -> Dict[str, Any]:
    """Execute tool calls.
    
    Args:
        state: Working state
        config: Configuration
        
    Returns:
        State updates
    """
    logger.info("Executing tools")
    
    if not state.messages:
        return {}
    
    last_message = state.messages[-1]
    if not isinstance(last_message, AIMessage) or not last_message.tool_calls:
        logger.warning("No tool calls to execute")
        return {}
    
    # Create tools
    tools_dict = {tool.name: tool for tool in create_tools(config)}
    
    results = []
    for tool_call in last_message.tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call.get("args", {})
        
        state.increment_tool_call(tool_name)
        
        logger.info(f"Executing tool: {tool_name}", extra={
            "tool": tool_name,
            "args": tool_args
        })
        
        if tool_name in tools_dict:
            try:
                tool = tools_dict[tool_name]
                result = await tool.ainvoke(tool_args)
                
                results.append(ToolMessage(
                    content=str(result),
                    tool_call_id=tool_call.get("id", tool_name)
                ))
                
                # Handle special tools
                if tool_name == "request_additional_info":
                    return {
                        "messages": results,
                        "needs_user_input": True,
                        "pending_request": tool_call
                    }
                
            except Exception as e:
                logger.error(f"Tool execution failed: {e}", extra={
                    "tool": tool_name,
                    "error": str(e)
                })
                results.append(ToolMessage(
                    content=f"Error: {str(e)}",
                    tool_call_id=tool_call.get("id", tool_name)
                ))
        else:
            logger.warning(f"Unknown tool: {tool_name}")
            results.append(ToolMessage(
                content=f"Unknown tool: {tool_name}",
                tool_call_id=tool_call.get("id", tool_name)
            ))
    
    return {"messages": results}


def _create_model(model_config):
    """Create a language model from config."""
    if model_config.provider.value == "google":
        return ChatGoogleGenerativeAI(
            model=model_config.model_name,
            temperature=model_config.temperature,
            google_api_key=model_config.get_api_key()
        )
    elif model_config.provider.value == "groq":
        return ChatGroq(
            model=model_config.model_name,
            temperature=model_config.temperature,
            groq_api_key=model_config.get_api_key()
        )
    else:
        raise ValueError(f"Unsupported model provider: {model_config.provider}")


def _check_needs_more_info(analysis: Dict[str, Any], metadata) -> bool:
    """Check if we need more information for better analysis."""
    # Simple heuristics
    if len(analysis.get('issues', [])) == 0:
        return True
    
    if "Unable to determine" in analysis.get('root_cause', ''):
        return True
    
    if metadata.severity_counts.get('error', 0) > 100:
        return True
    
    return False


def _estimate_tokens(text: str) -> int:
    """Rough token estimation."""
    # Approximate: 1 token per 4 characters
    return len(text) // 4