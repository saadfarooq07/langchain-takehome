#!/usr/bin/env python3
"""
Test script for the enhanced dataset creation functionality.
Tests the core logic without making API calls to LangSmith.
"""

import json
import sys
from pathlib import Path

# Add the scripts directory to the path
sys.path.append(str(Path(__file__).parent))

from create_langsmith_dataset_v2 import (
    EnhancedIssueDetector, 
    load_loghub_dataset,
    sample_entries,
    transform_entry,
    create_deterministic_splits,
    calculate_statistics,
    SYSTEM_DISTRIBUTION,
    ERROR_RATIO,
    DATASET_SPLITS
)


def test_issue_detector():
    """Test the enhanced issue detector."""
    print("=== Testing Enhanced Issue Detector ===")
    
    detector = EnhancedIssueDetector()
    
    # Test error log
    error_entry = {
        "id": "test_001",
        "log_source": "Apache",
        "raw_log": "Connection refused to database server on port 5432",
        "severity": "error",
        "expected_analysis": {"is_error": True, "category": "connection"}
    }
    
    error_analysis = detector.detect_and_analyze(error_entry)
    print(f"Error log analysis:")
    print(f"  Issues: {len(error_analysis['issues'])}")
    print(f"  Issue type: {error_analysis['issues'][0]['type'] if error_analysis['issues'] else 'None'}")
    print(f"  Explanations: {len(error_analysis['explanations'])}")
    print(f"  Suggestions: {len(error_analysis['suggestions'])}")
    print(f"  Commands: {len(error_analysis['diagnostic_commands'])}")
    
    # Test normal log
    normal_entry = {
        "id": "test_002", 
        "log_source": "Spark",
        "raw_log": "Times: total = 41, boot = 17, init = 24, finish = 0",
        "severity": "info",
        "expected_analysis": {"is_error": False, "category": "initialization"}
    }
    
    normal_analysis = detector.detect_and_analyze(normal_entry)
    print(f"\nNormal log analysis:")
    print(f"  Issues: {len(normal_analysis['issues'])}")
    print(f"  Explanations: {len(normal_analysis['explanations'])}")
    print(f"  Suggestions: {len(normal_analysis['suggestions'])}")
    print(f"  Commands: {len(normal_analysis['diagnostic_commands'])}")
    
    return True


def test_data_loading_and_transformation():
    """Test data loading and transformation."""
    print("\n=== Testing Data Loading and Transformation ===")
    
    # Check if source data exists
    source_path = Path("../../loghub/loghub_evaluation_dataset/train_dataset.json")
    if not source_path.exists():
        print(f"Source dataset not found at {source_path}")
        return False
    
    # Load a small sample
    all_entries = load_loghub_dataset(source_path)
    print(f"Loaded {len(all_entries)} entries from source dataset")
    
    # Test sampling with smaller distribution for testing
    test_distribution = {k: min(v, 3) for k, v in SYSTEM_DISTRIBUTION.items()}
    sampled = sample_entries(all_entries, test_distribution, ERROR_RATIO)
    print(f"Sampled {len(sampled)} entries")
    
    # Test transformation
    detector = EnhancedIssueDetector()
    transformed = []
    
    for entry in sampled[:5]:  # Test first 5
        try:
            example = transform_entry(entry, detector)
            transformed.append(example)
            
            # Validate structure
            assert "inputs" in example
            assert "outputs" in example  
            assert "metadata" in example
            assert "log_content" in example["inputs"]
            assert "issues" in example["outputs"]
            assert "explanations" in example["outputs"]
            assert "suggestions" in example["outputs"]
            
        except Exception as e:
            print(f"Error transforming entry {entry.get('id')}: {e}")
            return False
    
    print(f"Successfully transformed {len(transformed)} entries")
    
    # Test a sample output
    if transformed:
        sample = transformed[0]
        print(f"\nSample transformed entry:")
        print(f"  Original log: {sample['inputs']['log_content'][:100]}...")
        print(f"  Is error: {sample['metadata']['is_error']}")
        print(f"  Issues count: {len(sample['outputs']['issues'])}")
        print(f"  Has explanations: {len(sample['outputs']['explanations']) > 0}")
        print(f"  Has suggestions: {len(sample['outputs']['suggestions']) > 0}")
    
    return True


def test_dataset_splits():
    """Test dataset splitting functionality."""
    print("\n=== Testing Dataset Splitting ===")
    
    # Create mock examples
    mock_examples = []
    for i in range(20):
        mock_examples.append({
            "inputs": {"log_content": f"test log {i}"},
            "outputs": {"issues": [], "explanations": [], "suggestions": []},
            "metadata": {"original_id": f"test_{i:03d}", "is_error": i % 3 == 0}
        })
    
    # Test splitting
    splits = create_deterministic_splits(mock_examples, DATASET_SPLITS)
    
    print(f"Split sizes:")
    for split_name, examples in splits.items():
        print(f"  {split_name}: {len(examples)} examples")
    
    # Verify all examples are accounted for
    total_split = sum(len(examples) for examples in splits.values())
    print(f"Total in splits: {total_split}, Original: {len(mock_examples)}")
    
    # Test deterministic property - should get same splits
    splits2 = create_deterministic_splits(mock_examples, DATASET_SPLITS)
    for split_name in splits:
        ids1 = [ex["metadata"]["original_id"] for ex in splits[split_name]]
        ids2 = [ex["metadata"]["original_id"] for ex in splits2[split_name]]
        assert ids1 == ids2, f"Split {split_name} not deterministic"
    
    print("✓ Splits are deterministic")
    
    return True


def test_statistics_calculation():
    """Test statistics calculation."""
    print("\n=== Testing Statistics Calculation ===")
    
    # Create mock examples with various properties
    mock_examples = [
        {
            "metadata": {"log_source": "Apache", "severity": "error", "is_error": True, "category": "connection"},
            "outputs": {
                "issues": [{"type": "connection_failure"}],
                "suggestions": ["check network", "verify firewall"],
                "diagnostic_commands": [{"command": "ping"}],
                "documentation_references": [{"title": "guide"}]
            }
        },
        {
            "metadata": {"log_source": "HDFS", "severity": "info", "is_error": False, "category": "initialization"},
            "outputs": {
                "issues": [],
                "suggestions": ["monitor"],
                "diagnostic_commands": [],
                "documentation_references": []
            }
        }
    ]
    
    stats = calculate_statistics(mock_examples)
    
    print(f"Statistics calculated:")
    print(f"  Total examples: {stats['total_examples']}")
    print(f"  Error count: {stats['error_count']}")
    print(f"  Systems: {dict(stats['by_system'])}")
    print(f"  Avg suggestions: {stats['avg_suggestions_per_example']}")
    print(f"  Examples with docs: {stats['examples_with_docs']}")
    
    # Verify calculations
    assert stats['total_examples'] == 2
    assert stats['error_count'] == 1
    assert stats['by_system']['Apache'] == 1
    assert stats['avg_suggestions_per_example'] == 1.5  # (2 + 1) / 2
    
    print("✓ Statistics calculations correct")
    
    return True


def main():
    """Run all tests."""
    print("Starting enhanced dataset creation tests...\n")
    
    tests = [
        test_issue_detector,
        test_data_loading_and_transformation,
        test_dataset_splits,
        test_statistics_calculation
    ]
    
    passed = 0
    for test in tests:
        try:
            if test():
                passed += 1
                print("✓ PASSED\n")
            else:
                print("✗ FAILED\n")
        except Exception as e:
            print(f"✗ FAILED with exception: {e}\n")
    
    print(f"=== Test Results ===")
    print(f"Passed: {passed}/{len(tests)} tests")
    
    if passed == len(tests):
        print("🎉 All tests passed! The enhanced dataset creation script is ready to use.")
        return True
    else:
        print("❌ Some tests failed. Please review the implementation.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
