#!/usr/bin/env python3
"""
Demo script showing how to use streaming with the log analyzer agent.
"""

import asyncio
from typing import Dict, Any
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.markdown import Markdown

from src.log_analyzer_agent.streaming import StreamingLogAnalyzer


class StreamingDemo:
    """Demo class for showcasing streaming capabilities."""
    
    def __init__(self):
        self.console = Console()
        self.analyzer = StreamingLogAnalyzer()
        self.current_content = ""
        self.current_node = ""
        self.tools_used = []
    
    async def demo_token_streaming(self, log_content: str):
        """Demo: Stream tokens as they're generated."""
        self.console.print("\n[bold blue]🔄 Token Streaming Demo[/bold blue]")
        self.console.print(f"[dim]Analyzing: {log_content[:100]}...[/dim]\n")
        
        with Live(console=self.console, refresh_per_second=10) as live:
            content = ""
            
            async for event in self.analyzer.stream_analysis(
                log_content,
                stream_mode="events"
            ):
                if event["type"] == "token":
                    content += event["content"]
                    panel = Panel(
                        content,
                        title=f"[yellow]Node: {event.get('node', 'unknown')}[/yellow]",
                        border_style="blue"
                    )
                    live.update(panel)
                
                elif event["type"] == "tool_start":
                    self.console.print(f"\n[green]🔧 Tool Started:[/green] {event['tool']}")
                
                elif event["type"] == "tool_end":
                    self.console.print(f"[green]✅ Tool Completed:[/green] {event['tool']}")
    
    async def demo_progress_tracking(self, log_content: str):
        """Demo: Track progress through different nodes."""
        self.console.print("\n[bold blue]📊 Progress Tracking Demo[/bold blue]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        ) as progress:
            
            task = progress.add_task("[cyan]Analyzing logs...", total=None)
            
            async for event in self.analyzer.stream_analysis(
                log_content,
                stream_mode="events"
            ):
                if event["type"] == "node_start":
                    progress.update(task, description=f"[cyan]Processing: {event['node']}...")
                
                elif event["type"] == "node_end":
                    progress.update(task, description=f"[green]Completed: {event['node']}")
                
                elif event["type"] == "state_update":
                    updates = event.get("updates", {})
                    if updates.get("analysis_complete"):
                        progress.update(task, description="[bold green]Analysis Complete! ✨")
                        break
    
    async def demo_real_time_updates(self, log_content: str):
        """Demo: Real-time state updates."""
        self.console.print("\n[bold blue]🔴 Real-time Updates Demo[/bold blue]")
        
        issues_found = []
        suggestions = []
        
        async for update in self.analyzer.stream_analysis(
            log_content,
            stream_mode="updates"
        ):
            node = update["node"]
            updates = update["updates"]
            
            self.console.print(f"\n[yellow]Update from {node}:[/yellow]")
            
            # Check for analysis results
            if "analysis_result" in updates and updates["analysis_result"]:
                result = updates["analysis_result"]
                
                if "issues" in result:
                    issues_found = result["issues"]
                    self.console.print(f"  [red]Issues found:[/red] {len(issues_found)}")
                    for issue in issues_found:
                        self.console.print(f"    • {issue.get('description', 'Unknown issue')}")
                
                if "suggestions" in result:
                    suggestions = result["suggestions"]
                    self.console.print(f"  [green]Suggestions:[/green]")
                    for suggestion in suggestions:
                        self.console.print(f"    • {suggestion}")
            
            # Check for tool usage
            if "latest_message" in updates:
                msg = updates["latest_message"]
                if msg["type"] == "ai_message" and msg.get("tool_calls"):
                    self.console.print(f"  [cyan]Tools called:[/cyan]")
                    for tool_call in msg["tool_calls"]:
                        self.console.print(f"    • {tool_call.get('name', 'unknown')}")
    
    async def demo_callback_based_streaming(self, log_content: str):
        """Demo: Using callbacks for different events."""
        self.console.print("\n[bold blue]🎯 Callback-based Streaming Demo[/bold blue]")
        
        # Define callbacks
        async def on_token(token: str):
            # In a real app, you might update a UI element here
            pass
        
        async def on_tool_start(tool: str, inputs: Dict):
            self.console.print(f"\n[cyan]🔧 {tool} started[/cyan]")
            if tool == "search_documentation":
                self.console.print(f"  Searching for: {inputs.get('query', 'N/A')}")
        
        async def on_tool_end(tool: str, output: Any):
            self.console.print(f"[green]✅ {tool} completed[/green]")
            if tool == "search_documentation" and output:
                self.console.print(f"  Found {len(output)} results")
        
        async def on_complete(result: Dict):
            self.console.print("\n[bold green]🎉 Analysis Complete![/bold green]")
            
            # Display summary
            issues = result.get("issues", [])
            suggestions = result.get("suggestions", [])
            
            summary_md = f"""
## Analysis Summary

**Issues Found:** {len(issues)}
**Suggestions Provided:** {len(suggestions)}

### Key Findings:
{result.get('summary', 'No summary available')}
            """
            
            self.console.print(Panel(
                Markdown(summary_md),
                title="[bold]Final Analysis[/bold]",
                border_style="green"
            ))
        
        # Run with callbacks
        await self.analyzer.stream_with_callback(
            log_content,
            on_token=on_token,
            on_tool_start=on_tool_start,
            on_tool_end=on_tool_end,
            on_complete=on_complete
        )


async def main():
    """Run all streaming demos."""
    demo = StreamingDemo()
    
    # Sample log content with errors
    log_content = """
2024-01-15 10:23:45 ERROR [database] Connection timeout after 30000ms
2024-01-15 10:23:46 ERROR [database] Failed to connect to primary database server at 192.168.1.100:5432
2024-01-15 10:23:47 WARN  [connection-pool] All connection attempts failed, falling back to read replica
2024-01-15 10:23:48 ERROR [app] DatabaseException: No available database connections
2024-01-15 10:23:49 ERROR [api] Request handler crashed: NullPointerException at UserService.getUser()
2024-01-15 10:23:50 INFO  [monitor] System health check failed - database unreachable
    """
    
    console = Console()
    
    console.print("\n[bold magenta]🚀 Log Analyzer Streaming Demos[/bold magenta]")
    console.print("[dim]Demonstrating various streaming modes and capabilities[/dim]\n")
    
    # Run demos
    demos = [
        ("Token Streaming", demo.demo_token_streaming),
        ("Progress Tracking", demo.demo_progress_tracking),
        ("Real-time Updates", demo.demo_real_time_updates),
        ("Callback-based Streaming", demo.demo_callback_based_streaming)
    ]
    
    for name, demo_func in demos:
        console.print(f"\n{'='*60}")
        await demo_func(log_content)
        console.print(f"{'='*60}\n")
        
        # Small delay between demos
        await asyncio.sleep(1)
    
    console.print("[bold green]✅ All demos completed![/bold green]")


if __name__ == "__main__":
    # Note: You'll need to install rich for the fancy output
    # pip install rich
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user")
    except ImportError:
        print("Please install 'rich' for the best demo experience: pip install rich")
        # Fallback to simple demo
        analyzer = StreamingLogAnalyzer()
        
        async def simple_demo():
            log = "ERROR: Connection timeout to database"
            print("Analyzing:", log)
            
            async for event in analyzer.stream_analysis(log, stream_mode="events"):
                if event["type"] == "token":
                    print(event["content"], end="", flush=True)
            print("\n\nDone!")
        
        asyncio.run(simple_demo())