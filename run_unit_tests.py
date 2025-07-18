#!/usr/bin/env python3
"""Simple test runner to verify unit tests work."""

import subprocess
import sys
from pathlib import Path

def run_tests():
    """Run unit tests and display results."""
    test_dir = Path("tests/unit")
    
    if not test_dir.exists():
        print(f"Error: Test directory '{test_dir}' not found")
        return 1
    
    print("Running unit tests...")
    print("=" * 60)
    
    # Run pytest
    cmd = [sys.executable, "-m", "pytest", str(test_dir), "-v", "--tb=short"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    
    return result.returncode

if __name__ == "__main__":
    sys.exit(run_tests())