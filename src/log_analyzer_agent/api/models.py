"""Pydantic models for API requests and responses."""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, EmailStr


class UserRegistration(BaseModel):
    """User registration request model."""

    email: EmailStr
    password: str = Field(
        ..., min_length=8, description="Password must be at least 8 characters"
    )
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    """User login request model."""

    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """User response model."""

    id: str
    email: str
    full_name: Optional[str] = None
    is_active: bool = True
    created_at: str


class AuthResponse(BaseModel):
    """Authentication response model."""

    user: UserResponse
    access_token: str
    token_type: str = "bearer"


class LogAnalysisRequest(BaseModel):
    """Log analysis request model."""

    log_content: str = Field(..., description="Log content to analyze")
    application_name: Optional[str] = Field(None, description="Name of the application")
    application_version: Optional[str] = Field(
        None, description="Version of the application"
    )
    environment_type: Optional[str] = Field(
        None, description="Environment type (dev, staging, prod)"
    )
    environment_details: Optional[Dict[str, Any]] = Field(
        None, description="Additional environment details"
    )
    environment_context: Optional[str] = Field(
        None, description="Environment context description"
    )
    enable_memory: bool = Field(True, description="Enable memory-based analysis")
    enable_enhanced_analysis: bool = Field(False, description="Enable enhanced analysis with better output quality")


class AnalysisIssue(BaseModel):
    """Analysis issue model."""

    type: str = "general"
    description: str = ""
    severity: str = "medium"
    message: Optional[str] = None  # Alternative to description
    line_number: Optional[int] = None
    timestamp: Optional[str] = None
    category: Optional[str] = None
    suggested_solution: Optional[str] = None
    documentation_link: Optional[str] = None
    root_cause: Optional[str] = None
    impact: Optional[str] = None


class AnalysisResult(BaseModel):
    """Analysis result model."""

    issues: List[AnalysisIssue]
    summary: str = ""
    recommendations: List[str] = []
    analyzed_lines: int = 0
    processing_time: float = 0.0
    confidence_score: float = 0.95
    # Additional fields for compatibility
    suggestions: List[str] = []
    explanations: List[str] = []
    documentation_references: List[Dict[str, str]] = []
    diagnostic_commands: List[Dict[str, str]] = []
    performance_metrics: Optional[Dict[str, Any]] = None


class LogAnalysisResponse(BaseModel):
    """Log analysis response model."""

    analysis_id: str
    status: str = "completed"
    result: Optional[AnalysisResult] = None
    created_at: Optional[Any] = None  # datetime
    completed_at: Optional[Any] = None  # datetime
    # Legacy fields for compatibility
    thread_id: Optional[str] = None
    session_id: Optional[str] = None
    analysis_result: Optional[AnalysisResult] = None
    similar_issues_found: int = 0
    memory_enabled: bool = True
    processing_time: float = 0.0


class UserPreferences(BaseModel):
    """User preferences model."""

    analysis_style: str = Field(
        "comprehensive", description="Analysis style preference"
    )
    output_format: str = Field("detailed", description="Output format preference")
    include_diagnostic_commands: bool = Field(
        True, description="Include diagnostic commands"
    )
    severity_threshold: str = Field("medium", description="Minimum severity threshold")
    max_suggestions: int = Field(10, description="Maximum number of suggestions")


class MemorySearchRequest(BaseModel):
    """Memory search request model."""

    query: str = Field(..., description="Search query")
    application_name: Optional[str] = Field(
        None, description="Filter by application name"
    )
    context_type: str = Field(
        "analysis_history", description="Type of memory context to search"
    )
    limit: int = Field(10, description="Maximum number of results")


class MemorySearchResponse(BaseModel):
    """Memory search response model."""

    results: List[Dict[str, Any]]
    total_found: int
    search_time: float


class AnalysisHistoryItem(BaseModel):
    """Individual analysis history item."""
    
    analysis_id: str
    timestamp: Any  # datetime
    log_source: str
    issue_count: int
    status: str
    summary: str


class AnalysisHistoryResponse(BaseModel):
    """Analysis history response model."""

    analyses: List[Dict[str, Any]]
    total_count: int
    page: int
    page_size: int


class ApplicationContext(BaseModel):
    """Application context model."""

    application_name: str
    common_patterns: List[str] = Field(default_factory=list)
    successful_solutions: List[Dict[str, Any]] = Field(default_factory=list)
    frequent_issues: List[Dict[str, Any]] = Field(default_factory=list)
    environment_info: Dict[str, Any] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str
    message: str
    details: Optional[Dict[str, Any]] = None
