#!/usr/bin/env python3
"""
Quick test script to verify parallel evaluation functionality.
"""

import subprocess
import sys
import os

def test_parallel_evaluation():
    """Test the parallel evaluation with a small dataset."""
    print("Testing parallel evaluation functionality...")
    print("="*60)
    
    # Test command
    cmd = [
        sys.executable,
        "evaluation/run_evaluation.py",
        "evaluate",
        "--parallel",
        "--max-examples", "5",  # Small number for testing
        "--batch-size", "3",
        "--experiment-prefix", "test-parallel"
    ]
    
    print(f"Running command: {' '.join(cmd)}")
    print("="*60)
    
    try:
        # Run the evaluation
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        
        if result.returncode == 0:
            print("✅ Parallel evaluation completed successfully!")
            print("\nOutput:")
            print(result.stdout)
            
            # Check for expected output patterns
            if "Parallel evaluation complete!" in result.stdout:
                print("\n✅ Found expected completion message")
            else:
                print("\n⚠️  Did not find expected completion message")
                
            if "Progress:" in result.stdout:
                print("✅ Progress tracking is working")
            else:
                print("⚠️  Progress tracking not visible")
                
            if "Throughput:" in result.stdout:
                print("✅ Throughput calculation is working")
            else:
                print("⚠️  Throughput calculation not visible")
                
        else:
            print("❌ Parallel evaluation failed!")
            print("\nError output:")
            print(result.stderr)
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Evaluation timed out after 2 minutes")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False
    
    return True

if __name__ == "__main__":
    # Check if we're in the right directory
    if not os.path.exists("evaluation/run_evaluation.py"):
        print("Error: Please run this script from the project root directory")
        sys.exit(1)
    
    # Run the test
    success = test_parallel_evaluation()
    
    if success:
        print("\n✅ All tests passed! Parallel evaluation is working correctly.")
        sys.exit(0)
    else:
        print("\n❌ Tests failed. Please check the error messages above.")
        sys.exit(1)