"""Tools for log analysis.

This module contains functions that are directly exposed to the LLM as tools.
These tools can be used for tasks such as searching documentation, 
requesting additional information, and providing analysis results.
"""

import json
from typing import Any, Dict, List, Optional, cast

import aiohttp
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg, tool
from langgraph.prebuilt import InjectedState
from typing_extensions import Annotated

from .configuration import Configuration
from .state import State
from .utils import init_model



async def search_documentation(
    query: str, *, config: Annotated[RunnableConfig, InjectedToolArg]
) -> Optional[List[Dict[str, Any]]]:
    """Search for relevant documentation based on the log analysis.
    
    This function queries the web to find documentation, guides, or forum posts
    that are relevant to the issues identified in the logs.
    
    Args:
        query: A specific query targeting documentation for the identified issue
        
    Returns:
        A list of relevant documentation sources with titles, snippets, and URLs
    """
    configuration = Configuration.from_runnable_config(config)
    wrapped = TavilySearchResults(max_results=configuration.max_search_results)
    
    try:
        result = await wrapped.ainvoke({"query": query})
        
        # Enhance results with evidence tracking
        enhanced_results = []
        for item in cast(List[Dict[str, Any]], result):
            enhanced_item = {
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "snippet": item.get("snippet", ""),
                "evidence_type": "documentation",
                "relevance_score": item.get("score", 0.0),
                "source_type": _categorize_source(item.get("url", ""))
            }
            enhanced_results.append(enhanced_item)
        
        return enhanced_results
    except Exception as e:
        # Return empty list on error rather than failing
        return []


def _categorize_source(url: str) -> str:
    """Categorize the source type based on URL patterns."""
    url_lower = url.lower()
    
    if "github.com" in url_lower:
        return "github"
    elif "stackoverflow.com" in url_lower:
        return "stackoverflow"
    elif any(doc_site in url_lower for doc_site in ["docs.", "documentation", "wiki"]):
        return "official_docs"
    elif any(forum in url_lower for forum in ["forum", "discuss", "community"]):
        return "forum"
    elif any(blog in url_lower for blog in ["blog", "medium.com", "dev.to"]):
        return "blog"
    else:
        return "other"


@tool
async def request_additional_info(
    request: Dict[str, Any],
    *,
    state: Annotated[State, InjectedState],
) -> str:
    """Request additional information from the user to complete the analysis.
    
    Use this tool when you need more details from the user to provide an accurate analysis.
    
    Args:
        request: A dictionary containing:
            - "question": The specific question you need answered
            - "reason": Why this information is needed
            - "how_to_retrieve": Instructions on how the user can retrieve this information
            
    Returns:
        A confirmation that the request was registered
    """
    # Mark that we need user input
    state.needs_user_input = True
    return f"Request for additional information: {request['question']}. Reason: {request['reason']}"



@tool
async def submit_analysis(
    analysis: Dict[str, Any],
    *,
    state: Annotated[State, InjectedState],
) -> str:
    """Submit the final analysis of the log content.
    
    Args:
        analysis: A dictionary containing:
            - "issues": List of identified issues, each with description and severity
            - "explanations": Detailed explanations of what each issue means
            - "suggestions": Recommended solutions or next steps for each issue
            - "documentation_references": Relevant documentation links for further reading
            - "diagnostic_commands": Recommended commands to run for further investigation
            
    Returns:
        A confirmation that the analysis was submitted
    """
    # Generate command suggestions if not already included
    if "diagnostic_commands" not in analysis:
        engine = CommandSuggestionEngine()
        environment_info = state.environment_info if hasattr(state, 'environment_info') else {}
        analysis["diagnostic_commands"] = engine.suggest_commands(
            environment_info=environment_info,
            issues=analysis.get("issues", [])
        )
    
    state.analysis_result = analysis
    return "Analysis completed and submitted successfully."