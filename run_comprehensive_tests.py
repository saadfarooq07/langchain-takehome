#!/usr/bin/env python3
"""
Comprehensive test runner for the Log Analyzer Agent.

This script runs all test suites with proper configuration and reporting.
"""

import os
import sys
import subprocess
import argparse
import time
from pathlib import Path


def run_command(cmd, description, timeout=300):
    """Run a command with timeout and error handling."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {cmd}")
    print(f"{'='*60}")
    
    start_time = time.time()
    
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        duration = time.time() - start_time
        
        if result.returncode == 0:
            print(f"✅ SUCCESS ({duration:.1f}s): {description}")
            if result.stdout:
                print("STDOUT:")
                print(result.stdout)
        else:
            print(f"❌ FAILED ({duration:.1f}s): {description}")
            print("STDOUT:")
            print(result.stdout)
            print("STDERR:")
            print(result.stderr)
            return False
            
    except subprocess.TimeoutExpired:
        print(f"⏰ TIMEOUT ({timeout}s): {description}")
        return False
    except Exception as e:
        print(f"💥 ERROR: {description} - {e}")
        return False
    
    return True


def check_environment():
    """Check if the environment is properly set up."""
    print("🔍 Checking environment...")
    
    # Check if we're in the right directory
    if not Path("src/log_analyzer_agent").exists():
        print("❌ Error: Not in the correct project directory")
        print("   Please run this script from the project root directory")
        return False
    
    # Check if package is installed in editable mode
    try:
        import src.log_analyzer_agent
        print("✅ Package is importable")
    except ImportError:
        print("❌ Error: Package not installed")
        print("   Please run: pip install -e .")
        return False
    
    # Check for required environment variables
    required_env_vars = ["GEMINI_API_KEY", "GROQ_API_KEY", "TAVILY_API_KEY"]
    missing_vars = []
    
    for var in required_env_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"⚠️  Warning: Missing environment variables: {', '.join(missing_vars)}")
        print("   Some tests may be skipped or use mocked APIs")
    else:
        print("✅ All required environment variables are set")
    
    return True


def run_unit_tests(verbose=False, coverage=False):
    """Run unit tests."""
    cmd = "python -m pytest tests/unit"
    
    if verbose:
        cmd += " -v"
    
    if coverage:
        cmd += " --cov=src/log_analyzer_agent --cov-report=term-missing --cov-report=html"
    
    cmd += " --tb=short"
    
    return run_command(cmd, "Unit Tests", timeout=300)


def run_integration_tests(verbose=False):
    """Run integration tests."""
    cmd = "python -m pytest tests/integration -m integration"
    
    if verbose:
        cmd += " -v"
    
    cmd += " --tb=short"
    
    return run_command(cmd, "Integration Tests", timeout=600)


def run_functional_tests(verbose=False):
    """Run functional tests."""
    cmd = "python -m pytest tests/functional -m functional"
    
    if verbose:
        cmd += " -v"
    
    cmd += " --tb=short"
    
    return run_command(cmd, "Functional Tests", timeout=900)


def run_e2e_tests(verbose=False):
    """Run end-to-end tests."""
    cmd = "python -m pytest tests/e2e -m e2e"
    
    if verbose:
        cmd += " -v"
    
    cmd += " --tb=short"
    
    return run_command(cmd, "End-to-End Tests", timeout=1200)


def run_performance_tests(verbose=False):
    """Run performance tests."""
    cmd = "python -m pytest tests/performance -m performance"
    
    if verbose:
        cmd += " -v"
    
    cmd += " --tb=short"
    
    return run_command(cmd, "Performance Tests", timeout=1800)


def run_api_tests(verbose=False):
    """Run tests that require API keys."""
    cmd = "python -m pytest tests/ -m requires_api"
    
    if verbose:
        cmd += " -v"
    
    cmd += " --tb=short"
    
    return run_command(cmd, "API Integration Tests", timeout=600)


def run_quick_tests(verbose=False):
    """Run quick tests (excluding slow and performance tests)."""
    cmd = "python -m pytest tests/ -m 'not slow and not performance and not e2e'"
    
    if verbose:
        cmd += " -v"
    
    cmd += " --tb=short"
    
    return run_command(cmd, "Quick Tests", timeout=300)


def run_all_tests(verbose=False, coverage=False):
    """Run all test suites."""
    cmd = "python -m pytest tests/"
    
    if verbose:
        cmd += " -v"
    
    if coverage:
        cmd += " --cov=src/log_analyzer_agent --cov-report=term-missing --cov-report=html"
    
    cmd += " --tb=short"
    
    return run_command(cmd, "All Tests", timeout=3600)


def generate_test_report():
    """Generate a comprehensive test report."""
    print("\n" + "="*60)
    print("GENERATING TEST REPORT")
    print("="*60)
    
    # Run tests with JUnit XML output for reporting
    cmd = "python -m pytest tests/ --junitxml=test-results.xml --html=test-report.html --self-contained-html"
    
    if run_command(cmd, "Test Report Generation", timeout=3600):
        print("\n📊 Test reports generated:")
        print("   - test-results.xml (JUnit format)")
        print("   - test-report.html (HTML report)")
        
        if Path("htmlcov").exists():
            print("   - htmlcov/index.html (Coverage report)")
        
        return True
    
    return False


def run_linting():
    """Run code linting and formatting checks."""
    print("\n" + "="*60)
    print("RUNNING CODE QUALITY CHECKS")
    print("="*60)
    
    success = True
    
    # Check if tools are available
    tools = {
        "black": "python -m black --check --diff src/ tests/",
        "isort": "python -m isort --check-only --diff src/ tests/",
        "flake8": "python -m flake8 src/ tests/",
        "mypy": "python -m mypy src/log_analyzer_agent --ignore-missing-imports"
    }
    
    for tool, cmd in tools.items():
        try:
            subprocess.run(f"python -m {tool} --version", shell=True, capture_output=True, check=True)
            if not run_command(cmd, f"Code Quality - {tool.upper()}", timeout=120):
                success = False
        except subprocess.CalledProcessError:
            print(f"⚠️  {tool} not installed, skipping")
    
    return success


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(description="Comprehensive test runner for Log Analyzer Agent")
    
    parser.add_argument("--suite", choices=[
        "unit", "integration", "functional", "e2e", "performance", 
        "api", "quick", "all"
    ], default="quick", help="Test suite to run")
    
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--coverage", "-c", action="store_true", help="Generate coverage report")
    parser.add_argument("--lint", "-l", action="store_true", help="Run linting checks")
    parser.add_argument("--report", "-r", action="store_true", help="Generate test report")
    parser.add_argument("--no-env-check", action="store_true", help="Skip environment check")
    
    args = parser.parse_args()
    
    print("🧪 Log Analyzer Agent - Comprehensive Test Runner")
    print("=" * 60)
    
    # Check environment
    if not args.no_env_check and not check_environment():
        sys.exit(1)
    
    # Run linting if requested
    if args.lint:
        if not run_linting():
            print("⚠️  Linting issues found, but continuing with tests...")
    
    # Run selected test suite
    success = True
    
    if args.suite == "unit":
        success = run_unit_tests(args.verbose, args.coverage)
    elif args.suite == "integration":
        success = run_integration_tests(args.verbose)
    elif args.suite == "functional":
        success = run_functional_tests(args.verbose)
    elif args.suite == "e2e":
        success = run_e2e_tests(args.verbose)
    elif args.suite == "performance":
        success = run_performance_tests(args.verbose)
    elif args.suite == "api":
        success = run_api_tests(args.verbose)
    elif args.suite == "quick":
        success = run_quick_tests(args.verbose)
    elif args.suite == "all":
        success = run_all_tests(args.verbose, args.coverage)
    
    # Generate report if requested
    if args.report:
        generate_test_report()
    
    # Final summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    if success:
        print("🎉 All tests completed successfully!")
        exit_code = 0
    else:
        print("💥 Some tests failed!")
        exit_code = 1
    
    print(f"\nTest suite: {args.suite}")
    print(f"Verbose: {args.verbose}")
    print(f"Coverage: {args.coverage}")
    print(f"Linting: {args.lint}")
    print(f"Report: {args.report}")
    
    if args.coverage and Path("htmlcov/index.html").exists():
        print(f"\n📊 Coverage report: file://{Path('htmlcov/index.html').absolute()}")
    
    if args.report and Path("test-report.html").exists():
        print(f"📋 Test report: file://{Path('test-report.html').absolute()}")
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()