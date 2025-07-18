# Evaluation Guide

This guide explains how to evaluate the Log Analyzer Agent's performance and effectiveness.

## Evaluation Framework

The Log Analyzer Agent includes a comprehensive evaluation framework in the `evaluation/` directory. This framework helps you:

1. Measure agent performance across different metrics
2. Compare different agent configurations
3. Analyze performance on different types of logs
4. Track improvements over time

## Running Basic Evaluations

### Simple Evaluation

For a quick evaluation of the agent's core capabilities:

```bash
python evaluate_simple.py
```

This runs a basic evaluation that checks:
- Issue detection accuracy
- Severity classification correctness
- Suggestion quality
- Diagnostic command relevance

### Comprehensive Evaluation

For a more thorough evaluation:

```bash
python evaluate_enhanced.py
```

This runs a comprehensive evaluation that includes:
- Performance metrics (response time, memory usage)
- Advanced analysis quality metrics
- Cross-system comparison

## Using LangSmith for Evaluation

The agent integrates with LangSmith for more detailed evaluation:

### Setup LangSmith

1. Set your LangSmith API key:
   ```
   export LANGCHAIN_API_KEY=your_langsmith_api_key
   ```

2. Create a LangSmith dataset:
   ```bash
   python create_langsmith_dataset_v2.py
   ```

### Run LangSmith Evaluation

```bash
python evaluate_langsmith_fixed.py
```

This will:
1. Run the agent on each example in the dataset
2. Apply multiple evaluators to each run
3. Generate detailed metrics and feedback
4. Store results in your LangSmith account for analysis

## Custom Evaluation Metrics

The evaluation framework includes several metrics:

| Metric | Description |
|--------|-------------|
| Issue Detection | Measures ability to identify issues in logs |
| Severity Classification | Accuracy of severity ratings |
| Suggestion Quality | Relevance and usefulness of suggestions |
| Documentation Reference | Quality of documentation references |
| Response Time | Speed of analysis |
| Memory Efficiency | Resource usage during analysis |

## Benchmark Against Different Log Types

To evaluate performance across different systems:

```bash
python -c "from evaluation.benchmark.benchmark_runner import BenchmarkRunner; from evaluation.configurations.full_config import FullGraphConfiguration; from evaluation.providers.loghub_provider import LogHubMultiProvider; runner = BenchmarkRunner(); runner.run_comprehensive_benchmark()"
```

This will run the agent against logs from various systems and generate a comprehensive report.

## Evaluation Output

Evaluation results are stored in the `evaluation_results/` directory by default. Each evaluation run creates:

1. `summary.json` - Overall metrics
2. `details.json` - Per-sample metrics
3. `report.html` - Visual report of results

Example summary output:

```json
{
  "overall_score": 0.87,
  "metrics": {
    "issue_detection": {
      "precision": 0.92,
      "recall": 0.85,
      "f1": 0.88
    },
    "severity_classification": {
      "accuracy": 0.84
    },
    "suggestion_quality": {
      "relevance": 0.89,
      "actionability": 0.86
    },
    "response_time": {
      "average": 3.2,
      "p95": 5.7
    }
  },
  "by_system": {
    "apache": 0.91,
    "hadoop": 0.86,
    "zookeeper": 0.89,
    "linux": 0.85
  }
}
```

## Creating Regression Tests

You can save evaluation results as regression tests:

```python
from evaluation.benchmark.benchmark_runner import BenchmarkRunner
from evaluation.configurations.minimal_config import MinimalGraphConfiguration
from evaluation.providers.loghub_provider import LogHubProvider

# Run benchmark
runner = BenchmarkRunner(results_dir="regression_tests")
runner.run_benchmark(
    MinimalGraphConfiguration(),
    LogHubProvider("Apache", data_dir="data/loghub")
)
```

These can be used to detect performance regressions when making changes to the agent.

## Interpreting Results

When analyzing evaluation results, consider:

1. **Overall Score**: General measure of agent performance
2. **Issue Detection Metrics**:
   - High precision means few false positives
   - High recall means few missed issues
   - F1 score balances precision and recall
3. **Response Time**:
   - Average: Typical performance
   - P95: Performance under load
4. **System-Specific Metrics**:
   - Look for variations across different log types
   - Some systems are inherently more challenging

## Evaluating Model Performance

To compare different models:

```bash
python langsmith_evaluation_examples.py
```

This will evaluate the agent with different models (Gemini, Kimi, etc.) and compare their performance.

## Continuous Evaluation

For ongoing evaluation in CI/CD pipelines:

```bash
# Add to your CI workflow
python run_tests.py --include-evaluation
```

This runs core tests plus key evaluation metrics to ensure changes don't degrade performance.