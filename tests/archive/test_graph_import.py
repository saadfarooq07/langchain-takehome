#!/usr/bin/env python3
"""Test if the graph imports successfully."""

try:
    print("Importing graph module...")
    from src.log_analyzer_agent.graph import graph
    print("✅ Graph imported successfully!")
    print(f"Graph type: {type(graph)}")
except Exception as e:
    print(f"❌ Import failed: {e}")
    import traceback
    traceback.print_exc()