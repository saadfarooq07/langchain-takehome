# Enhanced LangSmith Dataset Creator v2

This enhanced version of the dataset creation script fixes several issues with the original implementation and adds new features.

## Key Improvements

### 1. Fixed Reference Output Generation
- **Issue**: Original script generated incomplete or inconsistent reference outputs
- **Fix**: Enhanced issue detection with comprehensive analysis for both error and normal logs
- **Result**: All examples now have meaningful reference outputs that match the agent's expected format

### 2. Better Non-Error Log Handling
- **Issue**: Normal logs returned empty analysis, providing no value for evaluation
- **Fix**: Generate helpful explanations, monitoring suggestions, and relevant commands even for normal logs
- **Result**: Comprehensive evaluation coverage for all log types

### 3. Dataset Splitting Support
- **New Feature**: Automatic creation of train/validation/test splits
- **Deterministic**: Uses hash-based splitting for reproducible results
- **Flexible**: Can create single dataset or multiple split datasets

### 4. Enhanced Issue Detection
- **Expanded Patterns**: More comprehensive keyword matching for issue types
- **System-Specific Logic**: Custom suggestions and commands based on log source
- **Better Categorization**: Improved classification of log patterns

## Usage

### Basic Usage (Single Dataset)
```python
from create_langsmith_dataset_v2 import main

# Create single dataset
dataset_id = main(
    dataset_name="my-log-analyzer-dataset",
    create_splits=False
)
```

### With Dataset Splits
```python
# Create train/validation/test splits
dataset_ids = main(
    dataset_name="my-log-analyzer-dataset", 
    create_splits=True,
    version_tag="v2.0"
)
# Returns: {"train": "dataset_id_1", "validation": "dataset_id_2", "test": "dataset_id_3"}
```

### Custom Configuration
```python
# Custom system distribution and error ratio
dataset_ids = main(
    dataset_name="custom-dataset",
    system_distribution={
        "Apache": 20,
        "HDFS": 15,
        "Linux": 10
    },
    error_ratio=0.8,  # 80% error logs
    create_splits=True
)
```

## Command Line Usage
```bash
# Activate virtual environment
source .venv/bin/activate

# Run with defaults (creates splits)
python create_langsmith_dataset_v2.py

# Test the functionality
python test_dataset_creation.py
```

## Output Structure

The enhanced script generates reference outputs that match the log analyzer agent's expected format:

```json
{
  "inputs": {
    "log_content": "Connection refused to database server"
  },
  "outputs": {
    "issues": [
      {
        "type": "connection_failure",
        "description": "Connection failure detected in Apache logs", 
        "severity": "error"
      }
    ],
    "explanations": [
      "A connection error indicates that the system was unable to establish communication with a remote service or host."
    ],
    "suggestions": [
      "Check network connectivity to the target service",
      "Verify firewall rules and port accessibility",
      "Ensure the target service is running and accepting connections"
    ],
    "documentation_references": [
      {
        "title": "Network Troubleshooting Guide",
        "url": "https://docs.example.com/network-troubleshooting",
        "relevance": "Comprehensive guide for diagnosing connection issues"
      }
    ],
    "diagnostic_commands": [
      {
        "command": "netstat -tuln",
        "description": "Show listening ports"
      }
    ]
  },
  "metadata": {
    "log_source": "Apache",
    "original_id": "apache_001", 
    "is_error": true,
    "category": "connection",
    "severity": "error"
  }
}
```

## Features

### For Error Logs
- Comprehensive issue detection (connection, authentication, memory, disk, service, performance)
- System-specific suggestions and diagnostic commands
- Relevant documentation references
- Detailed explanations of the problems

### For Normal Logs  
- Meaningful explanations of what the log indicates
- Monitoring and maintenance suggestions
- Appropriate diagnostic commands for operational visibility
- Documentation for best practices

### Dataset Management
- Deterministic splitting based on entry hashes
- Configurable split ratios (default: 70% train, 15% validation, 15% test)
- Comprehensive statistics for each split
- Backup files with sample examples and metadata

## Statistics

The enhanced script provides detailed statistics:
- Examples per system and severity level
- Error vs normal log distribution
- Average suggestions and commands per example
- Coverage of documentation references
- Issue type distribution

## Testing

Run the test suite to verify functionality:
```bash
python test_dataset_creation.py
```

The tests verify:
- Issue detection for both error and normal logs
- Data loading and transformation
- Deterministic dataset splitting
- Statistics calculation accuracy

## Migration from v1

The v2 script is backward compatible but provides much better reference outputs. Key differences:
- More comprehensive analysis for all log types
- Better field consistency with agent expectations
- Additional metadata fields
- Enhanced documentation and command suggestions

To upgrade:
1. Use `create_langsmith_dataset_v2.py` instead of the original script
2. Consider enabling dataset splits for better evaluation workflows
3. Review the enhanced output format in your evaluation scripts
