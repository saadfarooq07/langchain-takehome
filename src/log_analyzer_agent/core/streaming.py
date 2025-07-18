"""Streaming support for processing large log files.

This module provides efficient streaming capabilities for analyzing
large log files that don't fit in memory.
"""

import asyncio
from typing import AsyncIterator, Dict, Any, List, Optional, Callable, Tuple
from dataclasses import dataclass
import aiofiles
from io import StringIO
import json

from langchain_core.messages import BaseMessage, AIMessage, HumanMessage
from langchain_core.language_models import BaseChatModel

from .states import WorkingState
from .config import Config
from .logging import get_logger, log_execution_time
from .analyzers import LogPreprocessor, LogMetadata


logger = get_logger("log_analyzer.streaming")


@dataclass
class ChunkMetadata:
    """Metadata for a log chunk."""
    chunk_index: int
    total_chunks: int
    line_start: int
    line_end: int
    size_bytes: int
    has_more: bool


@dataclass
class ChunkAnalysis:
    """Analysis result for a chunk."""
    chunk_metadata: ChunkMetadata
    issues: List[Dict[str, Any]]
    patterns: List[str]
    severity_counts: Dict[str, int]
    key_events: List[str]


class LogStreamer:
    """Streams large log files in chunks."""
    
    def __init__(
        self,
        chunk_size_mb: float = 1.0,
        overlap_lines: int = 50
    ):
        """Initialize log streamer.
        
        Args:
            chunk_size_mb: Size of each chunk in megabytes
            overlap_lines: Number of lines to overlap between chunks
        """
        self.chunk_size_bytes = int(chunk_size_mb * 1024 * 1024)
        self.overlap_lines = overlap_lines
        self.logger = get_logger("log_analyzer.log_streamer")
    
    async def stream_file(
        self,
        file_path: str
    ) -> AsyncIterator[Tuple[str, ChunkMetadata]]:
        """Stream a log file in chunks.
        
        Args:
            file_path: Path to log file
            
        Yields:
            Tuples of (chunk_content, metadata)
        """
        self.logger.info(f"Starting to stream file: {file_path}")
        
        async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
            chunk_index = 0
            line_number = 0
            overlap_buffer = []
            
            while True:
                chunk_lines = overlap_buffer.copy()
                chunk_size = sum(len(line) for line in chunk_lines)
                chunk_start_line = line_number - len(overlap_buffer)
                
                # Read lines until we reach chunk size
                async for line in f:
                    line_number += 1
                    chunk_lines.append(line)
                    chunk_size += len(line)
                    
                    if chunk_size >= self.chunk_size_bytes:
                        break
                
                if not chunk_lines:
                    break
                
                # Check if there's more content
                current_pos = await f.tell()
                await f.seek(0, 2)  # Seek to end
                end_pos = await f.tell()
                await f.seek(current_pos)  # Seek back
                has_more = current_pos < end_pos
                
                # Prepare overlap for next chunk
                if has_more and len(chunk_lines) > self.overlap_lines:
                    overlap_buffer = chunk_lines[-self.overlap_lines:]
                else:
                    overlap_buffer = []
                
                # Create chunk metadata
                metadata = ChunkMetadata(
                    chunk_index=chunk_index,
                    total_chunks=-1,  # Unknown until complete
                    line_start=chunk_start_line,
                    line_end=line_number,
                    size_bytes=chunk_size,
                    has_more=has_more
                )
                
                yield ''.join(chunk_lines), metadata
                
                chunk_index += 1
                
                if not has_more:
                    break
        
        self.logger.info(f"Completed streaming {chunk_index} chunks")
    
    async def stream_content(
        self,
        content: str
    ) -> AsyncIterator[Tuple[str, ChunkMetadata]]:
        """Stream log content from string.
        
        Args:
            content: Log content as string
            
        Yields:
            Tuples of (chunk_content, metadata)
        """
        lines = content.split('\n')
        total_lines = len(lines)
        chunk_index = 0
        line_index = 0
        
        while line_index < total_lines:
            chunk_lines = []
            chunk_size = 0
            chunk_start = line_index
            
            # Add overlap from previous chunk if not first chunk
            if chunk_index > 0 and line_index >= self.overlap_lines:
                overlap_start = line_index - self.overlap_lines
                for i in range(overlap_start, line_index):
                    if i < total_lines:
                        chunk_lines.append(lines[i])
                        chunk_size += len(lines[i]) + 1  # +1 for newline
            
            # Add lines until chunk size reached
            while line_index < total_lines and chunk_size < self.chunk_size_bytes:
                line = lines[line_index]
                chunk_lines.append(line)
                chunk_size += len(line) + 1
                line_index += 1
            
            # Create metadata
            metadata = ChunkMetadata(
                chunk_index=chunk_index,
                total_chunks=-1,
                line_start=chunk_start,
                line_end=line_index,
                size_bytes=chunk_size,
                has_more=line_index < total_lines
            )
            
            yield '\n'.join(chunk_lines), metadata
            chunk_index += 1


class StreamingAnalyzer:
    """Analyzes log streams chunk by chunk."""
    
    def __init__(
        self,
        model: BaseChatModel,
        config: Config
    ):
        """Initialize streaming analyzer.
        
        Args:
            model: Language model
            config: Configuration
        """
        self.model = model
        self.config = config
        self.preprocessor = LogPreprocessor()
        self.logger = get_logger("log_analyzer.streaming_analyzer")
    
    @log_execution_time("log_analyzer.streaming_analyzer")
    async def analyze_chunk(
        self,
        chunk_content: str,
        chunk_metadata: ChunkMetadata,
        previous_context: Optional[str] = None
    ) -> ChunkAnalysis:
        """Analyze a single chunk.
        
        Args:
            chunk_content: Chunk content
            chunk_metadata: Chunk metadata
            previous_context: Context from previous chunk
            
        Returns:
            Chunk analysis
        """
        self.logger.debug(f"Analyzing chunk {chunk_metadata.chunk_index}")
        
        # Build prompt
        prompt_parts = [
            "You are analyzing a chunk of a larger log file.",
            f"This is chunk {chunk_metadata.chunk_index + 1}.",
            f"Lines {chunk_metadata.line_start} to {chunk_metadata.line_end}.",
        ]
        
        if previous_context:
            prompt_parts.append(f"\nContext from previous chunk:\n{previous_context}")
        
        prompt_parts.extend([
            f"\nLog chunk:\n{chunk_content}",
            "\nAnalyze this chunk and identify:",
            "1. Any errors or issues (with line numbers)",
            "2. Patterns or trends",
            "3. Severity distribution",
            "4. Key events that might be relevant for root cause analysis",
            "\nProvide a concise analysis focusing on actionable insights."
        ])
        
        prompt = '\n'.join(prompt_parts)
        
        # Call model
        response = await self.model.ainvoke([HumanMessage(content=prompt)])
        
        # Parse response (simplified for now)
        analysis = self._parse_chunk_analysis(response.content)
        
        return ChunkAnalysis(
            chunk_metadata=chunk_metadata,
            issues=analysis.get("issues", []),
            patterns=analysis.get("patterns", []),
            severity_counts=analysis.get("severity_counts", {}),
            key_events=analysis.get("key_events", [])
        )
    
    def _parse_chunk_analysis(self, response: str) -> Dict[str, Any]:
        """Parse chunk analysis response."""
        # Simple parsing - in production use structured output
        return {
            "issues": [],
            "patterns": [],
            "severity_counts": {},
            "key_events": []
        }
    
    async def merge_analyses(
        self,
        chunk_analyses: List[ChunkAnalysis]
    ) -> Dict[str, Any]:
        """Merge multiple chunk analyses into final result.
        
        Args:
            chunk_analyses: List of chunk analyses
            
        Returns:
            Merged analysis result
        """
        self.logger.info(f"Merging {len(chunk_analyses)} chunk analyses")
        
        # Aggregate results
        all_issues = []
        all_patterns = set()
        total_severities = {}
        all_key_events = []
        
        for analysis in chunk_analyses:
            all_issues.extend(analysis.issues)
            all_patterns.update(analysis.patterns)
            all_key_events.extend(analysis.key_events)
            
            for severity, count in analysis.severity_counts.items():
                total_severities[severity] = total_severities.get(severity, 0) + count
        
        # Build summary prompt
        summary_prompt = [
            "Based on the analysis of all log chunks, provide a comprehensive summary:",
            f"\nTotal chunks analyzed: {len(chunk_analyses)}",
            f"Total issues found: {len(all_issues)}",
            f"Patterns detected: {', '.join(all_patterns)}",
            f"Severity distribution: {total_severities}",
            "\nKey events across all chunks:",
        ]
        
        for event in all_key_events[:20]:  # Top 20 events
            summary_prompt.append(f"- {event}")
        
        summary_prompt.extend([
            "\nProvide:",
            "1. Root cause analysis",
            "2. Priority issues to address",
            "3. Recommended actions",
            "4. Relevant documentation or commands"
        ])
        
        # Get final analysis
        response = await self.model.ainvoke([
            HumanMessage(content='\n'.join(summary_prompt))
        ])
        
        return {
            "issues": all_issues,
            "root_cause": self._extract_root_cause(response.content),
            "recommendations": self._extract_recommendations(response.content),
            "metadata": {
                "chunks_analyzed": len(chunk_analyses),
                "total_issues": len(all_issues),
                "patterns": list(all_patterns),
                "severity_distribution": total_severities
            }
        }
    
    def _extract_root_cause(self, response: str) -> str:
        """Extract root cause from response."""
        # Simplified extraction
        return "Root cause analysis from merged chunks"
    
    def _extract_recommendations(self, response: str) -> List[str]:
        """Extract recommendations from response."""
        # Simplified extraction
        return ["Recommendation 1", "Recommendation 2"]


class StreamingLogAnalyzerNode:
    """Node implementation for streaming log analysis."""
    
    def __init__(self):
        """Initialize streaming node."""
        self.logger = get_logger("log_analyzer.streaming_node")
    
    async def __call__(
        self,
        state: WorkingState,
        config: Config
    ) -> Dict[str, Any]:
        """Execute streaming analysis.
        
        Args:
            state: Working state
            config: Configuration
            
        Returns:
            State updates
        """
        if not state.has_feature("streaming"):
            self.logger.debug("Streaming not enabled")
            return {}
        
        # Get log content
        log_content = self._extract_log_content(state)
        if not log_content:
            return {}
        
        # Check if content is large enough to warrant streaming
        size_mb = len(log_content.encode('utf-8')) / (1024 * 1024)
        if size_mb < 5:  # Less than 5MB, use regular analysis
            self.logger.info(f"Log size {size_mb:.1f}MB is below streaming threshold")
            return {}
        
        self.logger.info(f"Starting streaming analysis for {size_mb:.1f}MB log")
        
        # Create components
        from langchain_google_genai import ChatGoogleGenerativeAI
        model = ChatGoogleGenerativeAI(
            model=config.primary_model.model_name,
            temperature=config.primary_model.temperature,
            google_api_key=config.primary_model.get_api_key()
        )
        
        streamer = LogStreamer(chunk_size_mb=1.0)
        analyzer = StreamingAnalyzer(model, config)
        
        # Stream and analyze chunks
        chunk_analyses = []
        previous_context = None
        
        async for chunk_content, metadata in streamer.stream_content(log_content):
            # Update progress
            progress_msg = f"Analyzing chunk {metadata.chunk_index + 1}..."
            state.messages.append(AIMessage(content=progress_msg))
            
            # Analyze chunk
            analysis = await analyzer.analyze_chunk(
                chunk_content,
                metadata,
                previous_context
            )
            chunk_analyses.append(analysis)
            
            # Create context for next chunk
            if analysis.key_events:
                previous_context = f"Key events: {'; '.join(analysis.key_events[:5])}"
        
        # Merge analyses
        final_analysis = await analyzer.merge_analyses(chunk_analyses)
        
        # Update state
        return {
            "current_analysis": final_analysis,
            "messages": [AIMessage(
                content=f"Completed streaming analysis of {len(chunk_analyses)} chunks"
            )]
        }
    
    def _extract_log_content(self, state: WorkingState) -> Optional[str]:
        """Extract log content from state."""
        if state.messages:
            last_message = state.messages[-1]
            if isinstance(last_message, HumanMessage):
                return str(last_message.content)
        return None


# Convenience function for enabling streaming
def create_streaming_node() -> StreamingLogAnalyzerNode:
    """Create a streaming analyzer node."""
    return StreamingLogAnalyzerNode()