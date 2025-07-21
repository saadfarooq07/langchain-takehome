"""Streaming routes for real-time log analysis updates."""

import asyncio
import json
import time
import uuid
from typing import Optional, AsyncGenerator, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse

from ..graph import graph
from ..state import InputState, StateFeature, create_working_state
from ..streaming import LogStreamer, LogChunk, ChunkResult
from .auth import get_current_user_optional
from .models import LogAnalysisRequest, UserResponse

router = APIRouter()

# Size threshold for triggering streaming (10MB)
STREAMING_THRESHOLD_BYTES = 10 * 1024 * 1024


async def process_chunk(
    chunk: LogChunk,
    environment_details: Dict[str, Any],
    current_user: Optional[UserResponse],
    config: Dict[str, Any]
) -> ChunkResult:
    """Process a single log chunk through the analysis graph."""
    start_time = time.time()
    
    try:
        # Create input state for this chunk
        input_state = InputState(
            log_content=chunk.content,
            environment_details=environment_details,
            user_id=str(current_user.id) if current_user else None,
            application_name=environment_details.get("application_name", "unknown"),
            requested_features=set()
        )
        
        # Create working state
        state = create_working_state(input_state)
        
        # Convert state to dict
        state_dict = {
            "messages": [],
            "log_content": state.log_content,
            "log_metadata": {
                **state.log_metadata,
                "chunk_index": chunk.index,
                "total_chunks": chunk.total_chunks,
                "chunk_lines": f"{chunk.start_line}-{chunk.end_line}"
            }
        }
        
        # Run analysis on chunk
        result = None
        async for event in graph.astream(state_dict, config, stream_mode="values"):
            if "analysis_result" in event and event["analysis_result"]:
                result = event["analysis_result"]
                break
        
        # Extract issues from result
        issues = []
        patterns = []
        summary = ""
        
        if result:
            if isinstance(result, dict):
                if "analysis" in result and isinstance(result["analysis"], str):
                    try:
                        analysis = json.loads(result["analysis"])
                        issues = analysis.get("issues", [])
                        patterns = analysis.get("patterns", [])
                        summary = analysis.get("summary", "")
                    except json.JSONDecodeError:
                        pass
                else:
                    issues = result.get("issues", [])
                    patterns = result.get("patterns", [])
                    summary = result.get("summary", "")
        
        return ChunkResult(
            chunk_index=chunk.index,
            issues=issues,
            patterns=patterns,
            summary=summary,
            processing_time=time.time() - start_time
        )
        
    except Exception as e:
        return ChunkResult(
            chunk_index=chunk.index,
            issues=[],
            patterns=[],
            summary="",
            processing_time=time.time() - start_time,
            error=str(e)
        )


def aggregate_chunk_results(results: List[ChunkResult]) -> Dict[str, Any]:
    """Aggregate results from multiple chunks into a unified analysis."""
    all_issues = []
    all_patterns = []
    summaries = []
    total_time = 0
    errors = []
    
    # Sort results by chunk index
    sorted_results = sorted(results, key=lambda r: r.chunk_index)
    
    for result in sorted_results:
        if result.error:
            errors.append(f"Chunk {result.chunk_index}: {result.error}")
        else:
            # Deduplicate issues based on description
            for issue in result.issues:
                if not any(i.get("description") == issue.get("description") for i in all_issues):
                    all_issues.append(issue)
            
            # Collect unique patterns
            for pattern in result.patterns:
                if pattern not in all_patterns:
                    all_patterns.append(pattern)
            
            if result.summary:
                summaries.append(f"[Chunk {result.chunk_index}] {result.summary}")
        
        total_time += result.processing_time
    
    # Create aggregated result
    aggregated = {
        "issues": all_issues,
        "patterns": all_patterns,
        "summary": "\n".join(summaries) if summaries else "Log analysis completed",
        "suggestions": [],
        "metadata": {
            "chunks_processed": len(results),
            "total_processing_time": total_time,
            "errors": errors
        }
    }
    
    # Generate suggestions based on issues
    if all_issues:
        aggregated["suggestions"] = [
            "Review the identified issues in priority order",
            "Check system logs for additional context",
            "Consider implementing monitoring for detected patterns"
        ]
    
    return aggregated


async def event_generator(
    request: LogAnalysisRequest,
    current_user: Optional[UserResponse],
) -> AsyncGenerator[str, None]:
    """Generate SSE events for log analysis."""
    start_time = time.time()
    log_size = len(request.log_content.encode('utf-8'))
    
    # Send initial event
    yield json.dumps({
        "type": "start",
        "data": {
            "analysis_id": str(uuid.uuid4()),
            "timestamp": start_time,
            "log_size_bytes": log_size,
            "is_streaming": log_size > STREAMING_THRESHOLD_BYTES
        }
    })
    
    try:
        # Configuration for analysis
        config = {
            "configurable": {
                "model": "gemini:gemini-1.5-flash",
                "max_search_results": 3,
            }
        }
        
        # Check if we should use streaming
        if log_size > STREAMING_THRESHOLD_BYTES:
            # Use streaming for large logs
            yield json.dumps({
                "type": "info",
                "data": {
                    "message": f"Large log detected ({log_size / 1024 / 1024:.1f}MB). Processing in chunks...",
                    "chunk_size_mb": 10
                }
            })
            
            # Initialize streamer
            streamer = LogStreamer(chunk_size_bytes=10 * 1024 * 1024)
            
            # Collect chunks
            chunks = []
            async for chunk in streamer.stream_log_content(request.log_content):
                chunks.append(chunk)
            
            yield json.dumps({
                "type": "chunks_identified",
                "data": {
                    "total_chunks": len(chunks),
                    "message": f"Processing {len(chunks)} chunks..."
                }
            })
            
            # Process chunks in parallel
            chunk_tasks = []
            for chunk in chunks:
                task = process_chunk(
                    chunk,
                    request.environment_details or {},
                    current_user,
                    config
                )
                chunk_tasks.append(task)
            
            # Process and yield progress
            results = []
            for i, task in enumerate(asyncio.as_completed(chunk_tasks)):
                result = await task
                results.append(result)
                
                yield json.dumps({
                    "type": "chunk_progress",
                    "data": {
                        "chunks_completed": i + 1,
                        "total_chunks": len(chunks),
                        "current_chunk": result.chunk_index,
                        "chunk_time": result.processing_time,
                        "has_error": result.error is not None
                    }
                })
            
            # Aggregate results
            final_result = aggregate_chunk_results(results)
            
            # Send aggregated result
            yield json.dumps({
                "type": "result",
                "data": {
                    "analysis_result": final_result,
                    "processing_time": time.time() - start_time,
                    "chunks_processed": len(results)
                }
            })
            
        else:
            # Regular processing for smaller logs
            # Create input state
            input_state = InputState(
                log_content=request.log_content,
                environment_details=request.environment_details or {},
                user_id=str(current_user.id) if current_user else None,
                application_name=request.application_name,
                requested_features=set()  # No special features for streaming
            )
            
            # Create working state
            state = create_working_state(input_state)
            
            # Convert state to dict for graph processing
            state_dict = {
                "messages": [],
                "log_content": state.log_content,
                "log_metadata": state.log_metadata
            }
            
            # Stream events
            event_count = 0
            async for event in graph.astream(state_dict, config, stream_mode="values"):
                event_count += 1
                
                # Send progress event
                yield json.dumps({
                    "type": "progress",
                    "data": {
                        "event_number": event_count,
                        "keys": list(event.keys()),
                        "has_result": "analysis_result" in event
                    }
                })
                
                # If we have analysis result, send it
                if "analysis_result" in event and event["analysis_result"]:
                    result = event["analysis_result"]
                    
                    # Handle nested analysis structure
                    if isinstance(result, dict) and "analysis" in result:
                        import json as json_module
                        if isinstance(result["analysis"], str):
                            try:
                                result = json_module.loads(result["analysis"])
                            except json_module.JSONDecodeError:
                                result = {"error": "Failed to parse analysis result"}
                        else:
                            result = result["analysis"]
                    
                    # Send result event
                    yield json.dumps({
                        "type": "result",
                        "data": {
                            "analysis_result": result,
                            "processing_time": time.time() - start_time
                        }
                    })
            
            # Send completion event
            yield json.dumps({
                "type": "complete",
                "data": {
                    "total_events": event_count,
                    "processing_time": time.time() - start_time
                }
            })
        
    except Exception as e:
        # Send error event
        yield json.dumps({
            "type": "error",
            "data": {
                "error": str(e),
                "processing_time": time.time() - start_time
            }
        })


@router.post("/analyze/stream")
async def analyze_logs_stream(
    request: LogAnalysisRequest,
    current_user: Optional[UserResponse] = Depends(get_current_user_optional),
):
    """Stream log analysis results using Server-Sent Events."""
    return EventSourceResponse(
        event_generator(request, current_user),
        media_type="text/event-stream"
    )