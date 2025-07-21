# Log Analyzer Agent Evaluation

This directory contains the evaluation framework for the LangGraph-based log analyzer agent.

## Overview

The evaluation system uses LangSmith to assess the agent's performance on a curated dataset of log analysis tasks. It measures multiple aspects of the agent's output including issue detection accuracy, severity assessment, quality of explanations, relevance of suggestions, and completeness of documentation.

## Quick Start

```bash
# Use the unified CLI for all evaluation tasks
python evaluation/run_evaluation.py --help

# Create a dataset
python evaluation/run_evaluation.py create-dataset

# Run evaluation
python evaluation/run_evaluation.py evaluate

# Compare implementations
python evaluation/run_evaluation.py compare

# Run benchmarks
python evaluation/run_evaluation.py benchmark
```

## Key Components

### Unified CLI Interface

- **`run_evaluation.py`** - Single entry point for all evaluation operations
  - `create-dataset` - Create evaluation datasets
  - `evaluate` - Run evaluations with various configurations
  - `compare` - Compare original vs improved implementations
  - `benchmark` - Run performance benchmarks
  - `list-datasets` - List available datasets

### Core Scripts

- **`scripts/evaluate_agent_consolidated.py`** - Main evaluation script with comprehensive metrics
  - Supports both original and improved implementations
  - Switch using `--use-improved` flag or `USE_IMPROVED_LOG_ANALYZER=true` env var
- **`scripts/create_langsmith_dataset.py`** - Creates evaluation datasets from LogHub logs

### Evaluators

Located in `evaluators/`:
- `issue_detection.py` - Measures issue detection accuracy with semantic matching
- `analysis_quality.py` - Evaluates explanation and suggestion quality
- `documentation_relevance.py` - Assesses documentation reference quality
- `response_time.py` - Measures performance metrics
- `memory_efficiency.py` - Tracks memory usage
- `trajectory.py` - Analyzes agent decision paths

### Dataset Creation

The evaluation dataset is created from LogHub logs with:
- 100 diverse log entries from 16 different systems
- 70% error cases, 30% normal logs
- Expected outputs including issues, explanations, suggestions, documentation, and commands

## Usage Examples

### Creating Datasets

```bash
# Create default dataset
python evaluation/run_evaluation.py create-dataset

# Create with custom parameters (when supported)
python evaluation/run_evaluation.py create-dataset --samples 200 --dataset-name my-dataset
```

### Running Evaluations

```bash
# Run standard evaluation
python evaluation/run_evaluation.py evaluate

# Use improved implementation
python evaluation/run_evaluation.py evaluate --use-improved

# Run with specific dataset and limit examples
python evaluation/run_evaluation.py evaluate --dataset my-dataset --max-examples 10

# Custom experiment name
python evaluation/run_evaluation.py evaluate --experiment-prefix experiment-v1
```

### Comparing Implementations

```bash
# Compare original vs improved on full dataset
python evaluation/run_evaluation.py compare

# Compare with limited examples
python evaluation/run_evaluation.py compare --max-examples 50

# Custom experiment suffix
python evaluation/run_evaluation.py compare --experiment-suffix feature-test
```

### Running Benchmarks

```bash
# Run all benchmarks
python evaluation/run_evaluation.py benchmark

# Run specific benchmark type
python evaluation/run_evaluation.py benchmark --type memory
python evaluation/run_evaluation.py benchmark --type speed
```

## Evaluation Metrics

### Core Metrics

1. **Issue Detection (30% weight)**
   - Semantic matching of issue types
   - F1 score based on precision and recall
   - Handles flexible type matching

2. **Severity Assessment (15% weight)**
   - Accuracy of severity levels
   - Tolerance for minor differences
   - Distribution matching

3. **Explanation Quality (15% weight)**
   - Coverage and relevance
   - Technical accuracy
   - Concept preservation

4. **Suggestion Relevance (15% weight)**
   - Actionability of suggestions
   - Specificity and detail
   - Relevance to identified issues

5. **Documentation References (10% weight)**
   - Structure and validity
   - Relevance to issues
   - URL format checking

6. **Diagnostic Commands (10% weight)**
   - Command appropriateness
   - Coverage of issues
   - Use of standard tools

7. **Overall Completeness (5% weight)**
   - Field presence and population
   - Consistency between fields

### Summary Metrics

- **Precision/Recall/F1**: Overall issue detection accuracy
- **Response Quality**: Weighted average of all metrics

## Expected Output Structure

The agent must return outputs matching this structure:

```json
{
    "issues": [
        {
            "type": "connection_failure",
            "description": "Connection refused to database server",
            "severity": "error"
        }
    ],
    "explanations": [
        "The database connection was refused, indicating the server may be down or unreachable."
    ],
    "suggestions": [
        "Check if the database service is running",
        "Verify network connectivity to the database server",
        "Review database connection configuration"
    ],
    "documentation_references": [
        {
            "title": "Database Connection Troubleshooting",
            "url": "https://docs.example.com/db-troubleshooting",
            "relevance": "Guide for resolving connection issues"
        }
    ],
    "diagnostic_commands": [
        {
            "command": "systemctl status postgresql",
            "description": "Check database service status"
        }
    ]
}
```

## Semantic Issue Type Groups

The evaluation uses semantic matching for issue types:

- **connection**: network, socket, timeout, refused
- **authentication**: auth, login, credential, permission
- **memory**: heap, oom, allocation, ram
- **disk**: storage, filesystem, space, volume
- **service**: failure, crash, error, exception
- **performance**: slow, latency, delay, bottleneck
- **general**: error, warning, issue, problem

## Best Practices

1. **Consistent Structure**: Always return all required fields
2. **Meaningful Descriptions**: Provide clear, actionable content
3. **Severity Accuracy**: Use appropriate severity levels
4. **Relevant Documentation**: Include helpful references
5. **Practical Commands**: Suggest standard diagnostic tools

## Viewing Results

Results are available in:
1. **Console Output**: Summary statistics and scores
2. **JSON File**: Detailed metrics saved locally
3. **LangSmith UI**: Full evaluation details at https://smith.langchain.com/

## Archive

Old evaluation scripts have been archived in `scripts/archive/` for reference. The consolidated evaluation system provides all functionality from previous versions with improved modularity and flexibility.