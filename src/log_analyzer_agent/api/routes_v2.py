"""API routes for log analyzer agent with multi-tenant support."""

import os
import time
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
import asyncpg

from ..graph import create_enhanced_graph
from ..state import State
from .middleware import (
    require_auth, 
    get_tenant_id, 
    get_current_user_id,
    get_tenant_filter,
    get_auth_service
)
from .models import (
    LogAnalysisRequest,
    LogAnalysisResponse,
    AnalysisResult,
    AnalysisIssue,
    AnalysisHistoryItem,
    AnalysisHistoryResponse,
)


router = APIRouter()


@router.post("/analyze", response_model=LogAnalysisResponse)
async def analyze_logs(
    request: LogAnalysisRequest,
    auth_data: Dict[str, Any] = Depends(require_auth),
):
    """Analyze log content with tenant isolation."""
    start_time = time.time()
    analysis_id = str(uuid.uuid4())
    tenant_id = get_tenant_id()
    user_id = get_current_user_id()
    
    try:
        # Create the enhanced graph
        graph = create_enhanced_graph()
        
        # Prepare initial state
        initial_state = State(
            messages=[],
            log_content=request.log_content,
            environment_context=request.environment_context or "Not specified",
            analysis_complete=False,
            issues_found=[],
            tool_calls=[],
            needs_user_input=False,
            iteration_count=0,
        )
        
        # Store analysis in database
        db_url = os.getenv("DATABASE_URL")
        conn = await asyncpg.connect(db_url)
        try:
            # Create analysis record
            await conn.execute("""
                INSERT INTO log_analyses 
                (id, tenant_id, user_id, name, log_source, status, model_used)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            """, uuid.UUID(analysis_id), uuid.UUID(tenant_id), 
                uuid.UUID(user_id) if user_id else None,
                f"Analysis at {datetime.utcnow().isoformat()}",
                request.log_source or "unknown",
                "processing", "gemini-2.5-flash")
            
            # Run the graph
            final_state = None
            async for event in graph.astream(initial_state):
                if "__end__" in event:
                    final_state = event["__end__"]
            
            if not final_state:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Analysis failed to complete"
                )
            
            # Extract results
            issues = []
            if hasattr(final_state, "issues_found"):
                for issue in final_state.issues_found:
                    issues.append(
                        AnalysisIssue(
                            severity=issue.get("severity", "unknown"),
                            message=issue.get("message", ""),
                            line_number=issue.get("line_number"),
                            timestamp=issue.get("timestamp"),
                            category=issue.get("category", "general"),
                            suggested_solution=issue.get("suggested_solution"),
                            documentation_link=issue.get("documentation_link"),
                        )
                    )
            
            # Get final message with analysis
            final_message = ""
            recommendations = []
            summary = ""
            
            if hasattr(final_state, "messages") and final_state.messages:
                # Get the last AI message
                for msg in reversed(final_state.messages):
                    if hasattr(msg, "content") and isinstance(msg.content, str):
                        final_message = msg.content
                        # Extract summary and recommendations
                        if "summary:" in final_message.lower():
                            summary = final_message.split("summary:", 1)[1].split("\n")[0].strip()
                        break
            
            # Update analysis record
            await conn.execute("""
                UPDATE log_analyses 
                SET status = $1, completed_at = $2, summary = $3,
                    issues_found = $4, recommendations = $5,
                    total_lines_analyzed = $6, error_count = $7, warning_count = $8,
                    analysis_duration_ms = $9
                WHERE id = $10 AND tenant_id = $11
            """, "completed", datetime.utcnow(), summary,
                [{"severity": i.severity, "message": i.message} for i in issues],
                recommendations,
                len(request.log_content.split("\n")),
                sum(1 for i in issues if i.severity == "error"),
                sum(1 for i in issues if i.severity == "warning"),
                int((time.time() - start_time) * 1000),
                uuid.UUID(analysis_id), uuid.UUID(tenant_id))
            
            result = AnalysisResult(
                issues=issues,
                summary=summary or "Analysis completed successfully",
                recommendations=recommendations,
                analyzed_lines=len(request.log_content.split("\n")),
                processing_time=time.time() - start_time,
                confidence_score=0.95,  # Placeholder
            )
            
            return LogAnalysisResponse(
                analysis_id=analysis_id,
                status="completed",
                result=result,
                created_at=datetime.utcnow(),
            )
            
        finally:
            await conn.close()
        
    except Exception as e:
        # Update analysis as failed
        try:
            conn = await asyncpg.connect(db_url)
            await conn.execute("""
                UPDATE log_analyses 
                SET status = $1, error_message = $2
                WHERE id = $3 AND tenant_id = $4
            """, "failed", str(e), uuid.UUID(analysis_id), uuid.UUID(tenant_id))
            await conn.close()
        except:
            pass
            
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {str(e)}"
        )


@router.get("/analyses", response_model=List[AnalysisHistoryItem])
async def get_analysis_history(
    limit: int = 50,
    offset: int = 0,
    auth_data: Dict[str, Any] = Depends(require_auth),
):
    """Get analysis history for the current tenant."""
    tenant_id = get_tenant_id()
    
    db_url = os.getenv("DATABASE_URL")
    conn = await asyncpg.connect(db_url)
    try:
        # Get analyses for tenant
        analyses = await conn.fetch("""
            SELECT id, name, log_source, status, summary,
                   total_lines_analyzed, error_count, warning_count,
                   created_at, completed_at
            FROM log_analyses
            WHERE tenant_id = $1
            ORDER BY created_at DESC
            LIMIT $2 OFFSET $3
        """, uuid.UUID(tenant_id), limit, offset)
        
        return [
            AnalysisHistoryItem(
                analysis_id=str(analysis["id"]),
                timestamp=analysis["created_at"],
                log_source=analysis["log_source"] or "unknown",
                issue_count=analysis["error_count"] + analysis["warning_count"],
                status=analysis["status"],
                summary=analysis["summary"] or "No summary available",
            )
            for analysis in analyses
        ]
        
    finally:
        await conn.close()


@router.get("/analyses/{analysis_id}", response_model=LogAnalysisResponse)
async def get_analysis(
    analysis_id: str,
    auth_data: Dict[str, Any] = Depends(require_auth),
):
    """Get a specific analysis by ID."""
    tenant_id = get_tenant_id()
    
    db_url = os.getenv("DATABASE_URL")
    conn = await asyncpg.connect(db_url)
    try:
        # Get analysis
        analysis = await conn.fetchrow("""
            SELECT id, status, summary, issues_found, recommendations,
                   total_lines_analyzed, error_count, warning_count,
                   analysis_duration_ms, created_at, completed_at
            FROM log_analyses
            WHERE id = $1 AND tenant_id = $2
        """, uuid.UUID(analysis_id), uuid.UUID(tenant_id))
        
        if not analysis:
            raise HTTPException(status_code=404, detail="Analysis not found")
        
        # Convert issues
        issues = []
        for issue in analysis["issues_found"] or []:
            issues.append(
                AnalysisIssue(
                    severity=issue.get("severity", "unknown"),
                    message=issue.get("message", ""),
                    line_number=issue.get("line_number"),
                    timestamp=issue.get("timestamp"),
                    category=issue.get("category", "general"),
                )
            )
        
        result = AnalysisResult(
            issues=issues,
            summary=analysis["summary"] or "",
            recommendations=analysis["recommendations"] or [],
            analyzed_lines=analysis["total_lines_analyzed"],
            processing_time=analysis["analysis_duration_ms"] / 1000.0 if analysis["analysis_duration_ms"] else 0,
            confidence_score=0.95,
        )
        
        return LogAnalysisResponse(
            analysis_id=str(analysis["id"]),
            status=analysis["status"],
            result=result if analysis["status"] == "completed" else None,
            created_at=analysis["created_at"],
            completed_at=analysis["completed_at"],
        )
        
    finally:
        await conn.close()


@router.delete("/analyses/{analysis_id}")
async def delete_analysis(
    analysis_id: str,
    auth_data: Dict[str, Any] = Depends(require_auth),
):
    """Delete an analysis (soft delete)."""
    tenant_id = get_tenant_id()
    
    db_url = os.getenv("DATABASE_URL")
    conn = await asyncpg.connect(db_url)
    try:
        # For now, actually delete. In production, you'd soft delete
        result = await conn.execute("""
            DELETE FROM log_analyses
            WHERE id = $1 AND tenant_id = $2
        """, uuid.UUID(analysis_id), uuid.UUID(tenant_id))
        
        if result == "DELETE 0":
            raise HTTPException(status_code=404, detail="Analysis not found")
        
        return {"message": "Analysis deleted successfully"}
        
    finally:
        await conn.close()


@router.get("/stats")
async def get_tenant_stats(
    auth_data: Dict[str, Any] = Depends(require_auth),
):
    """Get statistics for the current tenant."""
    tenant_id = get_tenant_id()
    
    db_url = os.getenv("DATABASE_URL")
    conn = await asyncpg.connect(db_url)
    try:
        # Get stats
        stats = await conn.fetchrow("""
            SELECT 
                COUNT(*) as total_analyses,
                COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_analyses,
                COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_analyses,
                SUM(total_lines_analyzed) as total_lines_analyzed,
                SUM(error_count) as total_errors,
                SUM(warning_count) as total_warnings,
                AVG(analysis_duration_ms) as avg_duration_ms
            FROM log_analyses
            WHERE tenant_id = $1
        """, uuid.UUID(tenant_id))
        
        # Get recent analyses
        recent = await conn.fetch("""
            SELECT created_at, error_count + warning_count as issue_count
            FROM log_analyses
            WHERE tenant_id = $1 AND created_at > NOW() - INTERVAL '30 days'
            ORDER BY created_at DESC
            LIMIT 100
        """, uuid.UUID(tenant_id))
        
        return {
            "total_analyses": stats["total_analyses"] or 0,
            "completed_analyses": stats["completed_analyses"] or 0,
            "failed_analyses": stats["failed_analyses"] or 0,
            "total_lines_analyzed": stats["total_lines_analyzed"] or 0,
            "total_issues_found": (stats["total_errors"] or 0) + (stats["total_warnings"] or 0),
            "average_analysis_time_seconds": (stats["avg_duration_ms"] or 0) / 1000.0,
            "recent_activity": [
                {
                    "date": r["created_at"].isoformat(),
                    "issue_count": r["issue_count"]
                }
                for r in recent
            ]
        }
        
    finally:
        await conn.close()