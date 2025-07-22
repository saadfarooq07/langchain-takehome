#!/usr/bin/env python3
"""Test script for streaming functionality with various log sizes."""

import asyncio
import aiohttp
import json
import os
import sys
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API endpoint
API_URL = "http://localhost:8000/api/v1/analyze/stream"


def generate_test_log(size_mb: float) -> str:
    """Generate a test log of specified size in MB."""
    # Each line is approximately 100 bytes
    bytes_per_line = 100
    total_bytes = int(size_mb * 1024 * 1024)
    num_lines = total_bytes // bytes_per_line
    
    log_lines = []
    timestamp = time.time()
    
    for i in range(num_lines):
        # Mix different types of log entries
        if i % 100 == 0:
            log_lines.append(f"[ERROR] {timestamp + i} Failed to process request #{i}: Connection timeout")
        elif i % 50 == 0:
            log_lines.append(f"[WARN] {timestamp + i} High memory usage detected: 85% utilized")
        elif i % 20 == 0:
            log_lines.append(f"[INFO] {timestamp + i} Successfully processed batch #{i // 20}")
        else:
            log_lines.append(f"[DEBUG] {timestamp + i} Processing item {i} in queue")
    
    return "\n".join(log_lines)


async def test_streaming(size_mb: float, test_name: str):
    """Test streaming analysis with a log of specified size."""
    print(f"\n{'=' * 60}")
    print(f"Testing: {test_name} ({size_mb}MB log)")
    print(f"{'=' * 60}")
    
    # Generate test log
    print(f"Generating {size_mb}MB test log...")
    log_content = generate_test_log(size_mb)
    actual_size = len(log_content.encode('utf-8')) / 1024 / 1024
    print(f"Generated log size: {actual_size:.2f}MB")
    
    # Prepare request
    request_data = {
        "log_content": log_content,
        "application_name": f"test-app-{size_mb}mb",
        "environment_details": {
            "hostname": "test-server",
            "log_type": "application",
            "test_size_mb": size_mb
        }
    }
    
    # Send request and process SSE stream
    print("\nSending request to streaming endpoint...")
    start_time = time.time()
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            API_URL,
            json=request_data,
            headers={"Accept": "text/event-stream"}
        ) as response:
            if response.status != 200:
                print(f"❌ Error: HTTP {response.status}")
                error_text = await response.text()
                print(f"   Response: {error_text}")
                return
            
            # Process SSE events
            chunks_processed = 0
            total_chunks = 0
            is_streaming = False
            
            async for line in response.content:
                line = line.decode('utf-8').strip()
                if not line or line.startswith(':'):
                    continue
                
                if line.startswith('data: '):
                    data = line[6:]
                    if not data:
                        continue
                    
                    try:
                        event = json.loads(data)
                        event_type = event.get('type')
                        event_data = event.get('data', {})
                        
                        if event_type == 'start':
                            is_streaming = event_data.get('is_streaming', False)
                            print(f"✓ Analysis started (streaming: {is_streaming})")
                            
                        elif event_type == 'info':
                            print(f"ℹ️  {event_data.get('message', '')}")
                            
                        elif event_type == 'chunks_identified':
                            total_chunks = event_data.get('total_chunks', 0)
                            print(f"📦 Identified {total_chunks} chunks to process")
                            
                        elif event_type == 'chunk_progress':
                            chunks_processed = event_data.get('chunks_completed', 0)
                            chunk_time = event_data.get('chunk_time', 0)
                            print(f"   Chunk {chunks_processed}/{total_chunks} completed in {chunk_time:.2f}s")
                            
                        elif event_type == 'progress':
                            if not is_streaming:
                                event_num = event_data.get('event_number', 0)
                                if event_num % 5 == 0:  # Print every 5th event
                                    print(f"   Processing event {event_num}...")
                                    
                        elif event_type == 'result':
                            result = event_data.get('analysis_result', {})
                            proc_time = event_data.get('processing_time', 0)
                            
                            print(f"\n✅ Analysis completed in {proc_time:.2f}s")
                            print(f"   Issues found: {len(result.get('issues', []))}")
                            print(f"   Patterns detected: {len(result.get('patterns', []))}")
                            
                            if is_streaming:
                                chunks = event_data.get('chunks_processed', 0)
                                print(f"   Chunks processed: {chunks}")
                                
                            # Show first few issues
                            issues = result.get('issues', [])
                            if issues:
                                print("\n   Sample issues:")
                                for issue in issues[:3]:
                                    print(f"   - {issue.get('severity', 'UNKNOWN')}: {issue.get('description', '')}")
                                if len(issues) > 3:
                                    print(f"   ... and {len(issues) - 3} more issues")
                                    
                        elif event_type == 'complete':
                            total_time = event_data.get('processing_time', 0)
                            print(f"\n✓ Stream completed (total time: {total_time:.2f}s)")
                            
                        elif event_type == 'error':
                            error = event_data.get('error', 'Unknown error')
                            print(f"\n❌ Error: {error}")
                            
                    except json.JSONDecodeError as e:
                        print(f"Failed to parse event: {e}")
                        print(f"Raw data: {data}")
    
    elapsed = time.time() - start_time
    print(f"\n⏱️  Total test time: {elapsed:.2f}s")
    
    # Calculate throughput
    throughput = actual_size / elapsed
    print(f"📊 Throughput: {throughput:.2f} MB/s")


async def main():
    """Run streaming tests with various log sizes."""
    print("🚀 Testing Streaming Functionality")
    print("=" * 60)
    
    # Check if API is running
    print("Checking API availability...")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:8000/docs") as response:
                if response.status == 200:
                    print("✅ API is running")
                else:
                    print(f"❌ API returned status {response.status}")
                    print("Please start the API with: python main.py")
                    return
    except Exception as e:
        print(f"❌ Cannot connect to API: {e}")
        print("Please start the API with: python main.py")
        return
    
    # Run tests with different log sizes
    test_cases = [
        (0.5, "Small log (no streaming)"),
        (5.0, "Medium log (no streaming)"),
        (15.0, "Large log (with streaming)"),
        (50.0, "Very large log (with streaming)"),
    ]
    
    for size_mb, test_name in test_cases:
        try:
            await test_streaming(size_mb, test_name)
        except Exception as e:
            print(f"\n❌ Test failed: {e}")
            import traceback
            traceback.print_exc()
        
        # Small delay between tests
        await asyncio.sleep(2)
    
    print("\n" + "=" * 60)
    print("✅ All streaming tests completed!")
    print("\nSummary:")
    print("- Logs ≤10MB: Processed without chunking")
    print("- Logs >10MB: Automatically chunked and processed in parallel")
    print("- Streaming provides real-time progress updates via SSE")


if __name__ == "__main__":
    asyncio.run(main())