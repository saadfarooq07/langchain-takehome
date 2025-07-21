"""API routes for log analyzer agent."""

import os
import time
import uuid
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status

from ..services.auth_service import AuthService
from ..services.memory_service import MemoryService
from ..graph import create_graph
from ..state import State
from .auth import get_auth_service, get_current_user, get_current_user_optional
from .models import (
    UserRegistration,
    UserLogin,
    AuthResponse,
    UserResponse,
    LogAnalysisRequest,
    LogAnalysisResponse,
    AnalysisResult,
    AnalysisIssue,
    UserPreferences,
    MemorySearchRequest,
    MemorySearchResponse,
    AnalysisHistoryResponse,
    ApplicationContext,
    ErrorResponse,
)

router = APIRouter()


@router.post("/auth/register", response_model=AuthResponse)
async def register_user(
    user_data: UserRegistration, auth_service: AuthService = Depends(get_auth_service)
):
    """Register a new user."""
    success, message, user_info = await auth_service.create_user(
        email=user_data.email,
        password=user_data.password,
        full_name=user_data.full_name,
    )

    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)

    # Authenticate the user immediately after registration
    success, message, auth_info = await auth_service.authenticate_user(
        email=user_data.email, password=user_data.password
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User created but authentication failed",
        )

    return AuthResponse(
        user=UserResponse(
            id=auth_info["id"],
            email=auth_info["email"],
            full_name=auth_info.get("full_name"),
            is_active=True,
            created_at=user_info["created_at"],
        ),
        access_token=auth_info["access_token"],
        token_type=auth_info["token_type"],
    )


@router.post("/auth/login", response_model=AuthResponse)
async def login_user(
    user_data: UserLogin, auth_service: AuthService = Depends(get_auth_service)
):
    """Authenticate user and return access token."""
    success, message, auth_info = await auth_service.authenticate_user(
        email=user_data.email, password=user_data.password
    )

    if not success:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=message)

    return AuthResponse(
        user=UserResponse(
            id=auth_info["id"],
            email=auth_info["email"],
            full_name=auth_info.get("full_name"),
            is_active=True,
            created_at="",
        ),
        access_token=auth_info["access_token"],
        token_type=auth_info["token_type"],
    )


@router.post("/auth/logout")
async def logout_user(
    current_user: UserResponse = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Logout user and invalidate token."""
    # Note: In a real implementation, we'd need to get the token from the request
    # For now, we'll just return success
    return {"message": "Logout successful"}


@router.post("/analyze", response_model=LogAnalysisResponse)
async def analyze_logs(
    request: LogAnalysisRequest,
    current_user: Optional[UserResponse] = Depends(get_current_user_optional),
):
    """Analyze log content."""
    start_time = time.time()
    print(f"[DEBUG] Starting log analysis at {start_time}")

    # Create enhanced graph with memory if user is authenticated
    print(f"[DEBUG] User authenticated: {current_user is not None}, enable_memory: {request.enable_memory}")
    
    # Check if enhanced analysis is requested
    use_enhanced = os.getenv("USE_ENHANCED_ANALYSIS", "").lower() == "true" or request.enable_enhanced_analysis
    
    if use_enhanced:
        from ..enhanced_graph import create_enhanced_graph
        if current_user and request.enable_memory:
            graph = create_enhanced_graph(features={"memory", "interactive"})
        else:
            graph = create_enhanced_graph(features=set())  # Explicitly no features
        
        # Create basic state for enhanced graph
        from ..state import InputState, create_working_state
        
        input_state = InputState(
            log_content=request.log_content,
            environment_details=request.environment_details or {},
            user_id=str(current_user.id) if current_user else None,
            application_name=request.application_name,
            requested_features=set()
        )
        
        state = create_working_state(input_state)
        
        config = {
            "configurable": {
                "model": "gemini:gemini-1.5-flash",
                "max_search_results": 3,
            }
        }
        
        # Convert state to dict for graph processing
        state_dict = {
            "messages": [],
            "log_content": state.log_content,
            "log_metadata": state.log_metadata
        }
        
        # Run enhanced analysis
        result = None
        similar_issues_count = 0
        print(f"[DEBUG] Starting enhanced graph stream...")
        async for event in graph.astream(state_dict, config, stream_mode="values"):
            if "analysis_result" in event and event["analysis_result"]:
                result = event["analysis_result"]
                
    elif current_user and request.enable_memory:
        from ..state import InputState, StateFeature, create_working_state
        
        graph = create_graph(features={"memory", "interactive"})

        # Create input state first
        input_state = InputState(
            log_content=request.log_content,
            environment_details=request.environment_details or {},
            user_id=str(current_user.id),
            application_name=request.application_name,
            session_id=f"session_{current_user.id}_{int(start_time)}",
            requested_features={StateFeature.MEMORY, StateFeature.INTERACTIVE}
        )
        
        # Create working state from input state
        state = create_working_state(input_state)
        
        # Set thread_id for memory state
        if hasattr(state, 'thread_id'):
            state.thread_id = f"thread_{current_user.id}_{int(start_time)}"
        
        # Set session_id if not already set
        if hasattr(state, 'session_id') and not state.session_id:
            state.session_id = input_state.session_id

        # Configuration with user context
        config = {
            "configurable": {
                "thread_id": f"thread_{current_user.id if current_user else 'anonymous'}_{int(start_time)}",
                "model": "gemini:gemini-1.5-flash",
                "max_search_results": 3,
            }
        }

        # Convert state to dict for graph processing
        state_dict = {
            "messages": [],
            "log_content": state.log_content,
            "log_metadata": state.log_metadata,
            "enabled_features": list(state.enabled_features)
        }

        # Run analysis with memory
        result = None
        similar_issues_count = 0
        async for event in graph.astream(state_dict, config, stream_mode="values"):
            if "analysis_result" in event and event["analysis_result"]:
                result = event["analysis_result"]
                similar_issues_count = len(event.get("similar_issues", []))

        # Note: If using memory features with actual store/checkpointer,
        # they would need to be closed here. For now, we're using in-memory.

    else:
        # Use basic graph without memory
        from ..graph import graph
        from ..state import InputState, create_working_state

        # Create input state
        input_state = InputState(
            log_content=request.log_content,
            environment_details=request.environment_details or {},
            user_id=str(current_user.id) if current_user else None,
            application_name=request.application_name,
            requested_features=set()  # No special features for basic mode
        )
        
        # Create working state
        state = create_working_state(input_state)

        config = {
            "configurable": {
                "model": "gemini:gemini-1.5-flash",
                "max_search_results": 3,
            }
        }
        
        # Convert state to dict for graph processing
        state_dict = {
            "messages": [],
            "log_content": state.log_content,
            "log_metadata": state.log_metadata
        }

        # Run analysis without memory
        result = None
        similar_issues_count = 0
        print(f"[DEBUG] Starting graph stream...")
        async for event in graph.astream(state_dict, config, stream_mode="values"):
            if "analysis_result" in event and event["analysis_result"]:
                result = event["analysis_result"]

    if not result:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Analysis failed to produce results",
        )

    # Handle nested analysis structure
    if isinstance(result, dict) and "analysis" in result:
        # Parse the JSON string if needed
        import json
        if isinstance(result["analysis"], str):
            try:
                result = json.loads(result["analysis"])
            except json.JSONDecodeError:
                result = {"error": "Failed to parse analysis result"}
        else:
            result = result["analysis"]

    # Convert result to response model
    issues = []
    if "issues" in result:
        for issue in result["issues"]:
            issues.append(
                AnalysisIssue(
                    type=issue.get("type", "unknown"),
                    description=issue.get("description", ""),
                    severity=issue.get("severity", "medium"),
                    line_number=issue.get("line_number"),
                    timestamp=issue.get("timestamp"),
                )
            )

    # Extract suggestions (handle both string and dict formats)
    suggestions = []
    for sug in result.get("suggestions", []):
        if isinstance(sug, dict):
            suggestions.append(sug.get("suggestion", str(sug)))
        else:
            suggestions.append(str(sug))
    
    # Extract explanations (handle both string and dict formats)
    explanations = []
    for exp in result.get("explanations", []):
        if isinstance(exp, dict):
            explanations.append(exp.get("explanation", str(exp)))
        else:
            explanations.append(str(exp))
    
    # Extract documentation references (ensure dict format)
    doc_refs = []
    for ref in result.get("documentation_references", []):
        if isinstance(ref, str):
            doc_refs.append({"url": ref, "title": "Documentation"})
        elif isinstance(ref, dict):
            doc_refs.append(ref)
    
    # Extract diagnostic commands (ensure dict format)
    diag_cmds = []
    for cmd in result.get("diagnostic_commands", []):
        if isinstance(cmd, str):
            # Try to extract description from the command if it contains common patterns
            description = "Diagnostic command"
            if "status" in cmd.lower():
                description = "Check service status"
            elif "netstat" in cmd.lower() or "grep" in cmd.lower():
                description = "Check network connections and ports"
            elif "psql" in cmd.lower() or "mysql" in cmd.lower():
                description = "Test database connection"
            elif "systemctl" in cmd.lower():
                description = "Check system service status"
            elif "telnet" in cmd.lower():
                description = "Test network connectivity"
            
            diag_cmds.append({"command": cmd, "description": description})
        elif isinstance(cmd, dict):
            # Ensure the dict has required fields
            if "command" not in cmd:
                cmd["command"] = str(cmd)
            if "description" not in cmd:
                cmd["description"] = "Diagnostic command"
            diag_cmds.append(cmd)
    
    analysis_result = AnalysisResult(
        issues=issues,
        suggestions=suggestions,
        explanations=explanations,
        documentation_references=doc_refs,
        diagnostic_commands=diag_cmds,
        performance_metrics=result.get("performance_metrics"),
    )

    return LogAnalysisResponse(
        analysis_id=str(uuid.uuid4()),
        thread_id=getattr(state, 'thread_id', f"thread_{int(start_time)}"),
        session_id=getattr(state, 'session_id', f"session_{int(start_time)}"),
        analysis_result=analysis_result,
        similar_issues_found=similar_issues_count,
        memory_enabled=current_user is not None and request.enable_memory,
        processing_time=time.time() - start_time,
    )


@router.get("/user/preferences", response_model=UserPreferences)
async def get_user_preferences(current_user: UserResponse = Depends(get_current_user)):
    """Get user preferences."""
    # For now, return default preferences
    # In a real implementation, we'd fetch from memory
    return UserPreferences()


@router.post("/user/preferences", response_model=UserPreferences)
async def update_user_preferences(
    preferences: UserPreferences, current_user: UserResponse = Depends(get_current_user)
):
    """Update user preferences."""
    # For now, just return the provided preferences
    # In a real implementation, we'd store in memory
    return preferences


@router.post("/memory/search", response_model=MemorySearchResponse)
async def search_memory(
    request: MemorySearchRequest, current_user: UserResponse = Depends(get_current_user)
):
    """Search user's memory."""
    start_time = time.time()

    # Create memory service
    graph = create_graph()
    memory_service = MemoryService(store)

    try:
        if request.context_type == "analysis_history":
            results = await memory_service.search_similar_issues(
                current_user.id,
                request.application_name or "all",
                request.query,
                request.limit,
            )
        else:
            # For other context types, use generic search
            results = []

        return MemorySearchResponse(
            results=results,
            total_found=len(results),
            search_time=time.time() - start_time,
        )

    finally:
        await store.close()
        await checkpointer.close()


@router.get("/history", response_model=AnalysisHistoryResponse)
async def get_analysis_history(
    page: int = 1,
    page_size: int = 10,
    application_name: Optional[str] = None,
    current_user: UserResponse = Depends(get_current_user),
):
    """Get user's analysis history."""

    # Create memory service
    graph = create_graph()
    memory_service = MemoryService(store)

    try:
        # Search analysis history
        results = await memory_service.search_similar_issues(
            current_user.id, application_name or "all", "analysis history", page_size
        )

        return AnalysisHistoryResponse(
            analyses=results, total_count=len(results), page=page, page_size=page_size
        )

    finally:
        await store.close()
        await checkpointer.close()


@router.get("/applications", response_model=List[str])
async def get_user_applications(current_user: UserResponse = Depends(get_current_user)):
    """Get list of applications the user has analyzed."""

    # Create memory service
    graph = create_graph()
    memory_service = MemoryService(store)

    try:
        # Search for unique application names
        results = await memory_service.search_similar_issues(
            current_user.id, "all", "application_name", 100
        )

        # Extract unique application names
        applications = set()
        for result in results:
            if "application_name" in result:
                applications.add(result["application_name"])

        return list(applications)

    finally:
        await store.close()
        await checkpointer.close()


@router.get(
    "/applications/{application_name}/context", response_model=ApplicationContext
)
async def get_application_context(
    application_name: str, current_user: UserResponse = Depends(get_current_user)
):
    """Get context for a specific application."""

    # Create memory service
    graph = create_graph()
    memory_service = MemoryService(store)

    try:
        context = await memory_service.get_application_context(
            current_user.id, application_name
        )

        return ApplicationContext(
            application_name=application_name,
            common_patterns=context.get("common_patterns", []),
            successful_solutions=context.get("successful_solutions", []),
            frequent_issues=context.get("frequent_issues", []),
            environment_info=context.get("environment_info", {}),
        )

    finally:
        await store.close()
        await checkpointer.close()


@router.post(
    "/applications/{application_name}/context", response_model=ApplicationContext
)
async def update_application_context(
    application_name: str,
    context: ApplicationContext,
    current_user: UserResponse = Depends(get_current_user),
):
    """Update context for a specific application."""

    # Create memory service
    graph = create_graph()
    memory_service = MemoryService(store)

    try:
        await memory_service.store_application_context(
            current_user.id,
            application_name,
            {
                "common_patterns": context.common_patterns,
                "successful_solutions": context.successful_solutions,
                "frequent_issues": context.frequent_issues,
                "environment_info": context.environment_info,
            },
        )

        return context

    finally:
        await store.close()
        await checkpointer.close()


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": time.time()}
