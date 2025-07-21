# Running Evaluations with Gemini 1.5 Flash and Kimi K2 Instruct

This document provides instructions for running evaluations of the Log Analyzer Agent using Gemini 1.5 Flash as the primary model and Kimi K2 Instruct as the orchestration model.

## Prerequisites

1. **API Keys Required:**
   - `GEMINI_API_KEY` - For Google Gemini API
   - `GROQ_API_KEY` - For Groq API (Kimi K2)
   - `TAVILY_API_KEY` - For web search functionality
   - `LANGSMITH_API_KEY` - For evaluation tracking

2. **Setup:**
   ```bash
   # Copy environment template
   cp .env.example .env
   
   # Add your API keys to .env file
   ```

## Model Configuration

- **Primary Model (Log Analysis):** `gemini:gemini-1.5-flash`
- **Orchestration Model (Routing):** `groq:moonshotai/kimi-k2-instruct`

## Quick Start

### Option 1: Using the Shell Script

```bash
# Run with default settings (10 examples)
./run_gemini_kimi_eval.sh

# Run with custom settings
./run_gemini_kimi_eval.sh --max-examples 50 --experiment-prefix "my-test"

# See all options
./run_gemini_kimi_eval.sh --help
```

### Option 2: Direct Python Commands

```bash
# Source environment variables first
source .env

# Run evaluation with consolidated script
python evaluation/scripts/evaluate_agent_consolidated.py \
  --dataset "log-analyzer-evaluation" \
  --primary-model "gemini:gemini-1.5-flash" \
  --orchestration-model "groq:moonshotai/kimi-k2-instruct" \
  --max-examples 50 \
  --experiment-prefix "gemini15-kimik2-eval"
```

### Option 3: Using the Unified Runner

```bash
# Using the main evaluation runner
python evaluation/run_evaluation.py evaluate \
  --primary-model "gemini:gemini-1.5-flash" \
  --orchestration-model "groq:moonshotai/kimi-k2-instruct" \
  --max-examples 50
```

### Option 4: Environment Variables

```bash
# Set models via environment
export PRIMARY_MODEL_PROVIDER=gemini
export PRIMARY_MODEL_NAME=gemini-1.5-flash
export ORCHESTRATION_MODEL_PROVIDER=groq
export ORCHESTRATION_MODEL_NAME=moonshotai/kimi-k2-instruct

# Run evaluation
python evaluation/run_evaluation.py evaluate
```

## Test Script

For a quick verification that everything is set up correctly:

```bash
python test_eval_setup.py
```

This runs a minimal evaluation with just 3 examples to verify the setup.

## Evaluation Datasets

Available datasets in LangSmith:
- `log-analyzer-evaluation` (default, full dataset)
- `log-analyzer-evaluation-test` (test subset)
- `log-analyzer-evaluation-train` (training subset)
- `log-analyzer-evaluation-validation` (validation subset)

## Evaluation Metrics

The evaluation measures:
1. **Issue Detection** - How well the agent identifies problems
2. **Severity Assessment** - Accuracy of severity classifications
3. **Explanation Quality** - Clarity and relevance of explanations
4. **Suggestion Relevance** - Actionability of recommendations
5. **Documentation References** - Quality of documentation links
6. **Diagnostic Commands** - Appropriateness of debugging commands
7. **Overall Completeness** - Structure and consistency

## Output

Results are saved in two places:
1. **JSON File**: `evaluation_results_consolidated_YYYYMMDD_HHMMSS.json`
2. **LangSmith Dashboard**: https://smith.langchain.com/

## Example Commands

### Standard Evaluation (50 examples)
```bash
./run_gemini_kimi_eval.sh --max-examples 50
```

### Quick Test (10 examples)
```bash
./run_gemini_kimi_eval.sh --max-examples 10 --experiment-prefix "quick-test"
```

### Compare Implementations
```bash
python evaluation/run_evaluation.py compare \
  --primary-model "gemini:gemini-1.5-flash" \
  --orchestration-model "groq:moonshotai/kimi-k2-instruct" \
  --max-examples 20
```

### Performance Benchmark
```bash
python evaluation/run_evaluation.py benchmark \
  --primary-model "gemini:gemini-1.5-flash" \
  --orchestration-model "groq:moonshotai/kimi-k2-instruct"
```

## Troubleshooting

1. **API Key Issues**
   - Ensure all keys are set in `.env`
   - Run `source .env` before running scripts

2. **Import Errors**
   - Install package: `pip install -e .`
   - Install requirements: `pip install -r requirements.txt`

3. **Model Not Found**
   - Gemini model name: `gemini-1.5-flash` (not 2.5)
   - Kimi K2 full name: `moonshotai/kimi-k2-instruct`

4. **Rate Limits**
   - Reduce `--max-examples` if hitting API limits
   - Add delays between runs

## Notes

- The evaluation uses semantic matching, not just exact string comparison
- Results include precision, recall, and F1 scores
- Each run creates a unique experiment in LangSmith for tracking