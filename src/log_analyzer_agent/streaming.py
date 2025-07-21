"""Log streaming implementation for processing large files efficiently.

This module provides streaming capabilities for processing large log files
that would otherwise consume too much memory. It implements intelligent
chunking with overlap to maintain context across chunk boundaries.

Key features:
- Memory-efficient chunked processing
- Context preservation across chunks
- Parallel chunk processing
- Progress tracking
- Result aggregation
"""

import asyncio
from typing import AsyncIterator, Dict, Any, List, Optional, Tuple, Callable
from dataclasses import dataclass
from datetime import datetime
import hashlib
import re


@dataclass
class LogChunk:
    """Represents a chunk of log data."""
    index: int
    content: str
    start_line: int
    end_line: int
    start_byte: int
    end_byte: int
    overlap_lines: int
    total_chunks: int
    metadata: Dict[str, Any]


@dataclass
class ChunkResult:
    """Result from processing a single chunk."""
    chunk_index: int
    issues: List[Dict[str, Any]]
    patterns: List[str]
    summary: str
    processing_time: float
    error: Optional[str] = None


class LogStreamer:
    """Handles streaming and chunking of large log files."""
    
    def __init__(
        self,
        chunk_size_bytes: int = 10 * 1024 * 1024,  # 10MB
        chunk_size_lines: Optional[int] = None,  # Alternative: chunk by lines
        overlap_lines: int = 100,
        min_chunk_size_bytes: int = 1024,  # 1KB minimum
        encoding: str = 'utf-8'
    ):
        """Initialize the log streamer.
        
        Args:
            chunk_size_bytes: Target size for each chunk in bytes
            chunk_size_lines: Alternative chunking by number of lines
            overlap_lines: Number of lines to overlap between chunks
            min_chunk_size_bytes: Minimum chunk size to process
            encoding: Text encoding for the log file
        """
        self.chunk_size_bytes = chunk_size_bytes
        self.chunk_size_lines = chunk_size_lines
        self.overlap_lines = overlap_lines
        self.min_chunk_size_bytes = min_chunk_size_bytes
        self.encoding = encoding
        
    async def stream_log_content(
        self,
        log_content: str,
        preserve_context: bool = True
    ) -> AsyncIterator[LogChunk]:
        """Stream log content in chunks.
        
        Args:
            log_content: The full log content to stream
            preserve_context: Whether to preserve context with overlapping lines
            
        Yields:
            LogChunk objects
        """
        # Determine if we need to chunk
        content_size = len(log_content.encode(self.encoding))
        if content_size <= self.chunk_size_bytes:
            # Small enough to process as single chunk
            lines = log_content.split('\n')
            yield LogChunk(
                index=0,
                content=log_content,
                start_line=0,
                end_line=len(lines) - 1,
                start_byte=0,
                end_byte=content_size,
                overlap_lines=0,
                total_chunks=1,
                metadata={
                    "is_single_chunk": True,
                    "total_lines": len(lines),
                    "total_bytes": content_size
                }
            )
            return
            
        # Split into lines for chunking
        lines = log_content.split('\n')
        total_lines = len(lines)
        
        # Calculate chunks
        chunks = list(self._calculate_chunks(lines, content_size))
        total_chunks = len(chunks)
        
        # Yield chunks
        for i, (start_idx, end_idx, overlap_start) in enumerate(chunks):
            chunk_lines = lines[start_idx:end_idx]
            
            # Add overlap from previous chunk if needed
            if preserve_context and overlap_start is not None:
                overlap_content = lines[overlap_start:start_idx]
                chunk_lines = overlap_content + chunk_lines
                actual_start = overlap_start
            else:
                actual_start = start_idx
                
            chunk_content = '\n'.join(chunk_lines)
            
            # Calculate byte positions (approximate)
            start_byte = sum(len(line.encode(self.encoding)) + 1 for line in lines[:actual_start])
            end_byte = start_byte + len(chunk_content.encode(self.encoding))
            
            yield LogChunk(
                index=i,
                content=chunk_content,
                start_line=actual_start,
                end_line=end_idx - 1,
                start_byte=start_byte,
                end_byte=end_byte,
                overlap_lines=start_idx - actual_start if overlap_start else 0,
                total_chunks=total_chunks,
                metadata={
                    "chunk_number": i + 1,
                    "total_chunks": total_chunks,
                    "has_overlap": overlap_start is not None,
                    "progress_percent": (i + 1) / total_chunks * 100
                }
            )
            
            # Allow other tasks to run
            await asyncio.sleep(0)
            
    def _calculate_chunks(
        self,
        lines: List[str],
        total_size: int
    ) -> List[Tuple[int, int, Optional[int]]]:
        """Calculate chunk boundaries.
        
        Returns:
            List of (start_index, end_index, overlap_start_index) tuples
        """
        chunks = []
        current_start = 0
        
        if self.chunk_size_lines:
            # Chunk by lines
            chunk_size = self.chunk_size_lines
            
            while current_start < len(lines):
                end_idx = min(current_start + chunk_size, len(lines))
                
                # Calculate overlap start
                overlap_start = None
                if current_start > 0 and self.overlap_lines > 0:
                    overlap_start = max(0, current_start - self.overlap_lines)
                    
                chunks.append((current_start, end_idx, overlap_start))
                current_start = end_idx
                
        else:
            # Chunk by bytes
            current_size = 0
            chunk_start = 0
            
            for i, line in enumerate(lines):
                line_size = len(line.encode(self.encoding)) + 1  # +1 for newline
                current_size += line_size
                
                if current_size >= self.chunk_size_bytes:
                    # End chunk here
                    end_idx = i + 1
                    
                    # Calculate overlap start
                    overlap_start = None
                    if chunk_start > 0 and self.overlap_lines > 0:
                        overlap_start = max(0, chunk_start - self.overlap_lines)
                        
                    chunks.append((chunk_start, end_idx, overlap_start))
                    
                    # Start next chunk
                    chunk_start = end_idx
                    current_size = 0
                    
            # Add final chunk if needed
            if chunk_start < len(lines):
                overlap_start = None
                if chunk_start > 0 and self.overlap_lines > 0:
                    overlap_start = max(0, chunk_start - self.overlap_lines)
                chunks.append((chunk_start, len(lines), overlap_start))
                
        return chunks
        
    async def process_log_stream(
        self,
        log_content: str,
        processor: Callable[[LogChunk], ChunkResult],
        max_concurrent: int = 3,
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> Dict[str, Any]:
        """Process log content in streaming fashion with parallel processing.
        
        Args:
            log_content: The log content to process
            processor: Async function to process each chunk
            max_concurrent: Maximum number of chunks to process concurrently
            progress_callback: Optional callback for progress updates
            
        Returns:
            Aggregated results from all chunks
        """
        results = []
        errors = []
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_chunk(chunk: LogChunk) -> ChunkResult:
            """Process a single chunk with semaphore control."""
            async with semaphore:
                try:
                    result = await processor(chunk)
                    
                    # Report progress
                    if progress_callback:
                        progress = (chunk.index + 1) / chunk.total_chunks * 100
                        progress_callback(progress)
                        
                    return result
                except Exception as e:
                    return ChunkResult(
                        chunk_index=chunk.index,
                        issues=[],
                        patterns=[],
                        summary="",
                        processing_time=0,
                        error=str(e)
                    )
                    
        # Create tasks for all chunks
        tasks = []
        async for chunk in self.stream_log_content(log_content):
            task = asyncio.create_task(process_chunk(chunk))
            tasks.append(task)
            
        # Wait for all tasks to complete
        chunk_results = await asyncio.gather(*tasks)
        
        # Aggregate results
        aggregated = self._aggregate_results(chunk_results)
        
        return aggregated
        
    def _aggregate_results(self, chunk_results: List[ChunkResult]) -> Dict[str, Any]:
        """Aggregate results from multiple chunks.
        
        Args:
            chunk_results: Results from processing each chunk
            
        Returns:
            Aggregated analysis results
        """
        all_issues = []
        all_patterns = []
        all_summaries = []
        total_processing_time = 0
        errors = []
        
        # Sort results by chunk index
        chunk_results.sort(key=lambda r: r.chunk_index)
        
        for result in chunk_results:
            if result.error:
                errors.append({
                    "chunk": result.chunk_index,
                    "error": result.error
                })
                continue
                
            all_issues.extend(result.issues)
            all_patterns.extend(result.patterns)
            if result.summary:
                all_summaries.append(result.summary)
            total_processing_time += result.processing_time
            
        # Deduplicate issues (same issue might appear in overlapping regions)
        unique_issues = self._deduplicate_issues(all_issues)
        
        # Merge patterns
        pattern_counts = {}
        for pattern in all_patterns:
            pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1
            
        # Sort patterns by frequency
        top_patterns = sorted(
            pattern_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        # Create combined summary
        combined_summary = self._create_combined_summary(all_summaries, len(chunk_results))
        
        return {
            "issues": unique_issues,
            "patterns": [p[0] for p in top_patterns],
            "pattern_counts": dict(top_patterns),
            "summary": combined_summary,
            "metadata": {
                "chunks_processed": len(chunk_results),
                "chunks_with_errors": len(errors),
                "total_processing_time": total_processing_time,
                "errors": errors
            }
        }
        
    def _deduplicate_issues(self, issues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate issues from overlapping chunks."""
        seen = set()
        unique_issues = []
        
        for issue in issues:
            # Create a hash of the issue
            issue_key = hashlib.md5(
                f"{issue.get('message', '')}{issue.get('line', '')}{issue.get('severity', '')}".encode()
            ).hexdigest()
            
            if issue_key not in seen:
                seen.add(issue_key)
                unique_issues.append(issue)
                
        return unique_issues
        
    def _create_combined_summary(self, summaries: List[str], total_chunks: int) -> str:
        """Create a combined summary from chunk summaries."""
        if not summaries:
            return "No summary available"
            
        if len(summaries) == 1:
            return summaries[0]
            
        # Combine summaries
        combined = f"Analysis of {total_chunks} log chunks:\n\n"
        
        for i, summary in enumerate(summaries[:5]):  # Limit to first 5
            if summary:
                combined += f"Chunk {i+1}: {summary}\n"
                
        if len(summaries) > 5:
            combined += f"\n... and {len(summaries) - 5} more chunks"
            
        return combined


# Convenience function for streaming large logs
async def stream_and_analyze_log(
    log_content: str,
    analysis_func: Callable[[str], Dict[str, Any]],
    chunk_size_mb: int = 10,
    max_concurrent: int = 3
) -> Dict[str, Any]:
    """Stream and analyze a large log file.
    
    Args:
        log_content: The log content to analyze
        analysis_func: Async function to analyze each chunk
        chunk_size_mb: Size of each chunk in MB
        max_concurrent: Maximum concurrent chunk processing
        
    Returns:
        Aggregated analysis results
    """
    streamer = LogStreamer(chunk_size_bytes=chunk_size_mb * 1024 * 1024)
    
    async def process_chunk(chunk: LogChunk) -> ChunkResult:
        """Process a single chunk."""
        start_time = datetime.now()
        
        try:
            # Analyze the chunk
            result = await analysis_func(chunk.content)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return ChunkResult(
                chunk_index=chunk.index,
                issues=result.get("issues", []),
                patterns=result.get("patterns", []),
                summary=result.get("summary", ""),
                processing_time=processing_time
            )
        except Exception as e:
            return ChunkResult(
                chunk_index=chunk.index,
                issues=[],
                patterns=[],
                summary="",
                processing_time=0,
                error=str(e)
            )
            
    return await streamer.process_log_stream(
        log_content,
        process_chunk,
        max_concurrent
    )