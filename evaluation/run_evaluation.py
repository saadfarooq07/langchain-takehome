#!/usr/bin/env python3
"""
Unified CLI interface for log analyzer evaluation framework.
Provides a single entry point for all evaluation operations.
"""

import argparse
import asyncio
import subprocess
import sys
import os
from pathlib import Path


def create_dataset(args):
    """Create a new evaluation dataset in LangSmith."""
    print("Creating evaluation dataset...")
    cmd = [
        sys.executable,
        "evaluation/scripts/create_langsmith_dataset.py"
    ]
    
    if args.dataset_name:
        print(f"Dataset name: {args.dataset_name}")
        # The create_langsmith_dataset.py script would need to be updated to accept this parameter
    
    if args.samples:
        print(f"Number of samples: {args.samples}")
        # The create_langsmith_dataset.py script would need to be updated to accept this parameter
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        print("Dataset created successfully!")
        print(result.stdout)
    else:
        print("Error creating dataset:")
        print(result.stderr)
        sys.exit(1)


def evaluate(args):
    """Run evaluation on the log analyzer agent."""
    print("Running evaluation...")
    
    # Choose evaluation script based on parallel flag
    if args.parallel:
        script_path = "evaluation/scripts/evaluate_agent_parallel.py"
        print(f"Using parallel evaluation with batch size: {args.batch_size}")
    else:
        script_path = "evaluation/scripts/evaluate_agent_consolidated.py"
    
    cmd = [
        sys.executable,
        script_path,
        "--dataset", args.dataset,
    ]
    
    if args.max_examples:
        cmd.extend(["--max-examples", str(args.max_examples)])
    
    if args.experiment_prefix:
        cmd.extend(["--experiment-prefix", args.experiment_prefix])
    
    if args.primary_model:
        cmd.extend(["--primary-model", args.primary_model])
    
    if args.orchestration_model:
        cmd.extend(["--orchestration-model", args.orchestration_model])
    
    if args.parallel and args.batch_size:
        cmd.extend(["--batch-size", str(args.batch_size)])
    
    if args.use_improved:
        cmd.append("--use-improved")
    elif args.use_original:
        cmd.append("--use-original")
    
    # Set environment variable if needed
    env = os.environ.copy()
    if args.use_improved:
        env["USE_IMPROVED_LOG_ANALYZER"] = "true"
    
    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    
    if result.returncode == 0:
        print(result.stdout)
    else:
        print("Error running evaluation:")
        print(result.stderr)
        sys.exit(1)


def compare(args):
    """Run comparative evaluation between configurations."""
    print("Running comparative evaluation...")
    
    # Run evaluation for original implementation
    print("\n" + "="*60)
    print("Evaluating ORIGINAL implementation")
    print("="*60)
    
    original_cmd = [
        sys.executable,
        "evaluation/scripts/evaluate_agent_consolidated.py",
        "--dataset", args.dataset,
        "--use-original",
        "--experiment-prefix", f"compare-original-{args.experiment_suffix}"
    ]
    
    if args.max_examples:
        original_cmd.extend(["--max-examples", str(args.max_examples)])
    
    original_result = subprocess.run(original_cmd, capture_output=True, text=True)
    
    if original_result.returncode == 0:
        print(original_result.stdout)
    else:
        print("Error evaluating original:")
        print(original_result.stderr)
    
    # Run evaluation for improved implementation
    print("\n" + "="*60)
    print("Evaluating IMPROVED implementation")
    print("="*60)
    
    improved_cmd = [
        sys.executable,
        "evaluation/scripts/evaluate_agent_consolidated.py",
        "--dataset", args.dataset,
        "--use-improved",
        "--experiment-prefix", f"compare-improved-{args.experiment_suffix}"
    ]
    
    if args.max_examples:
        improved_cmd.extend(["--max-examples", str(args.max_examples)])
    
    env = os.environ.copy()
    env["USE_IMPROVED_LOG_ANALYZER"] = "true"
    
    improved_result = subprocess.run(improved_cmd, env=env, capture_output=True, text=True)
    
    if improved_result.returncode == 0:
        print(improved_result.stdout)
    else:
        print("Error evaluating improved:")
        print(improved_result.stderr)
    
    print("\n" + "="*60)
    print("COMPARISON SUMMARY")
    print("="*60)
    print(f"View detailed comparison in LangSmith: https://smith.langchain.com/")
    print(f"Look for experiments starting with 'compare-*-{args.experiment_suffix}'")


def benchmark(args):
    """Run performance benchmarks."""
    print("Running benchmarks...")
    
    benchmark_script = Path("evaluation/benchmark/benchmark_runner.py")
    if benchmark_script.exists():
        cmd = [sys.executable, str(benchmark_script)]
        
        if args.benchmark_type:
            cmd.extend(["--type", args.benchmark_type])
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(result.stdout)
        else:
            print("Error running benchmarks:")
            print(result.stderr)
            sys.exit(1)
    else:
        print("Benchmark runner not found. Creating basic benchmark...")
        # Could implement a basic benchmark here or create the benchmark runner
        print("Benchmark functionality not yet implemented.")


def list_datasets(args):
    """List available evaluation datasets."""
    print("Listing available datasets in LangSmith...")
    
    print("\nAvailable datasets:")
    print("- log-analyzer-evaluation (default)")
    print("- log-analyzer-evaluation-test")
    print("- log-analyzer-evaluation-train")
    print("- log-analyzer-evaluation-validation")
    print("\nTo view all datasets, visit: https://smith.langchain.com/")


def main():
    """Main entry point for the evaluation CLI."""
    parser = argparse.ArgumentParser(
        description="Unified CLI for log analyzer evaluation framework",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create a new evaluation dataset
  %(prog)s create-dataset --samples 100
  
  # Run evaluation with default settings
  %(prog)s evaluate
  
  # Run evaluation on specific dataset with improved implementation
  %(prog)s evaluate --dataset my-dataset --use-improved
  
  # Run parallel evaluation for faster execution
  %(prog)s evaluate --parallel --batch-size 20
  
  # Run parallel evaluation with custom models
  %(prog)s evaluate --parallel --primary-model gemini:gemini-2.0-flash-exp --batch-size 25
  
  # Compare original vs improved implementations
  %(prog)s compare --max-examples 50
  
  # Run performance benchmarks
  %(prog)s benchmark --type memory
  
  # List available datasets
  %(prog)s list-datasets
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Create dataset command
    create_parser = subparsers.add_parser(
        'create-dataset',
        help='Create a new evaluation dataset in LangSmith'
    )
    create_parser.add_argument(
        '--dataset-name',
        help='Name for the new dataset'
    )
    create_parser.add_argument(
        '--samples',
        type=int,
        help='Number of samples to include'
    )
    
    # Evaluate command
    eval_parser = subparsers.add_parser(
        'evaluate',
        help='Run evaluation on the log analyzer agent'
    )
    eval_parser.add_argument(
        '--dataset',
        default='log-analyzer-evaluation',
        help='Dataset name in LangSmith (default: log-analyzer-evaluation)'
    )
    eval_parser.add_argument(
        '--max-examples',
        type=int,
        help='Maximum number of examples to evaluate'
    )
    eval_parser.add_argument(
        '--experiment-prefix',
        help='Custom experiment prefix'
    )
    eval_parser.add_argument(
        '--use-improved',
        action='store_true',
        help='Use improved implementation'
    )
    eval_parser.add_argument(
        '--use-original',
        action='store_true',
        help='Use original implementation (default)'
    )
    eval_parser.add_argument(
        '--primary-model',
        help='Primary model in provider:model format (e.g., gemini:gemini-2.0-flash-exp)'
    )
    eval_parser.add_argument(
        '--orchestration-model',
        help='Orchestration model in provider:model format (e.g., groq:deepseek-r1-distill-llama-70b)'
    )
    eval_parser.add_argument(
        '--parallel',
        action='store_true',
        help='Run evaluations in parallel for faster execution'
    )
    eval_parser.add_argument(
        '--batch-size',
        type=int,
        default=10,
        help='Number of evaluations to run in parallel (default: 10)'
    )
    
    # Compare command
    compare_parser = subparsers.add_parser(
        'compare',
        help='Run comparative evaluation between configurations'
    )
    compare_parser.add_argument(
        '--dataset',
        default='log-analyzer-evaluation',
        help='Dataset name in LangSmith (default: log-analyzer-evaluation)'
    )
    compare_parser.add_argument(
        '--max-examples',
        type=int,
        help='Maximum number of examples to evaluate'
    )
    compare_parser.add_argument(
        '--experiment-suffix',
        default='comparison',
        help='Suffix for experiment names (default: comparison)'
    )
    
    # Benchmark command
    bench_parser = subparsers.add_parser(
        'benchmark',
        help='Run performance benchmarks'
    )
    bench_parser.add_argument(
        '--type',
        choices=['memory', 'speed', 'all'],
        default='all',
        help='Type of benchmark to run (default: all)'
    )
    
    # List datasets command
    list_parser = subparsers.add_parser(
        'list-datasets',
        help='List available evaluation datasets'
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Dispatch to appropriate function
    if args.command == 'create-dataset':
        create_dataset(args)
    elif args.command == 'evaluate':
        evaluate(args)
    elif args.command == 'compare':
        compare(args)
    elif args.command == 'benchmark':
        benchmark(args)
    elif args.command == 'list-datasets':
        list_datasets(args)


if __name__ == "__main__":
    main()