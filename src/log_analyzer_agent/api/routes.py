"""API routes for log analyzer agent."""

import time
import uuid
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status

from ..services.auth_service import AuthService
from ..services.memory_service import MemoryService
from ..graph import create_enhanced_graph
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

    # Create enhanced graph with memory if user is authenticated
    if current_user and request.enable_memory:
        graph, store, checkpointer = await create_enhanced_graph()

        # Create enhanced state with user context
        state = State(
            log_content=request.log_content,
            environment_details=request.environment_details or {},
            user_id=current_user.id,
            application_name=request.application_name,
            application_version=request.application_version,
            environment_type=request.environment_type,
            start_time=start_time,
        )

        # Configuration with user context
        config = {
            "configurable": {
                "user_id": current_user.id,
                "thread_id": state.thread_id,
                "model": "gemini:gemini-1.5-flash",
                "max_search_results": 3,
            }
        }

        # Run analysis with memory
        result = None
        similar_issues_count = 0
        async for event in graph.astream(state.__dict__, config, stream_mode="values"):
            if "analysis_result" in event and event["analysis_result"]:
                result = event["analysis_result"]
                similar_issues_count = len(event.get("similar_issues", []))

        # Close connections
        await store.close()
        await checkpointer.close()

    else:
        # Use basic graph without memory
        from ..graph import graph

        state = State(
            log_content=request.log_content,
            environment_details=request.environment_details or {},
            application_name=request.application_name,
            application_version=request.application_version,
            environment_type=request.environment_type,
            start_time=start_time,
        )

        config = {
            "configurable": {
                "model": "gemini:gemini-1.5-flash",
                "max_search_results": 3,
            }
        }

        # Run analysis without memory
        result = None
        similar_issues_count = 0
        for event in graph.stream(state.__dict__, config, stream_mode="values"):
            if "analysis_result" in event and event["analysis_result"]:
                result = event["analysis_result"]

    if not result:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Analysis failed to produce results",
        )

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

    analysis_result = AnalysisResult(
        issues=issues,
        suggestions=result.get("suggestions", []),
        explanations=result.get("explanations", []),
        documentation_references=result.get("documentation_references", []),
        diagnostic_commands=result.get("diagnostic_commands", []),
        performance_metrics=result.get("performance_metrics"),
    )

    return LogAnalysisResponse(
        analysis_id=str(uuid.uuid4()),
        thread_id=state.thread_id,
        session_id=state.session_id,
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
    graph, store, checkpointer = await create_enhanced_graph()
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
    graph, store, checkpointer = await create_enhanced_graph()
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
    graph, store, checkpointer = await create_enhanced_graph()
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
    graph, store, checkpointer = await create_enhanced_graph()
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
    graph, store, checkpointer = await create_enhanced_graph()
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
