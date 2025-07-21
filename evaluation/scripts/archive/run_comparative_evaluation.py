#!/usr/bin/env python3
"""
Run comparative evaluations of the log analyzer agent with different configurations.
This script tests different models, prompts, and configurations to find optimal settings.
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

from langsmith import Client
from langsmith.evaluation import aevaluate

from evaluation.scripts.evaluate_agent import (
    run_agent_on_input,
    evaluate_issue_detection,
    evaluate_issue_type_accuracy,
    evaluate_severity_accuracy,
    evaluate_explanation_quality,
    evaluate_suggestion_quality,
    evaluate_documentation_relevance,
    evaluate_diagnostic_commands,
    evaluate_response_completeness,
    precision_summary_evaluator,
    recall_summary_evaluator,
    f1_summary_evaluator
)


class ComparativeEvaluator:
    """Run and compare multiple evaluation experiments."""
    
    def __init__(self, dataset_name: str = "log-analyzer-evaluation-v3"):
        self.dataset_name = dataset_name
        self.client = Client()
        self.evaluators = [
            evaluate_issue_detection,
            evaluate_issue_type_accuracy,
            evaluate_severity_accuracy,
            evaluate_explanation_quality,
            evaluate_suggestion_quality,
            evaluate_documentation_relevance,
            evaluate_diagnostic_commands,
            evaluate_response_completeness
        ]
        self.summary_evaluators = [
            precision_summary_evaluator,
            recall_summary_evaluator,
            f1_summary_evaluator
        ]
    
    async def run_experiment(
        self,
        name: str,
        config: Dict[str, Any],
        max_examples: Optional[int] = None
    ) -> Dict[str, Any]:
        """Run a single experiment with given configuration."""
        print(f"\n{'='*60}")
        print(f"Running experiment: {name}")
        print(f"Configuration: {json.dumps(config, indent=2)}")
        print(f"{'='*60}")
        
        # Create a modified agent runner that uses the config
        async def configured_agent(inputs: Dict[str, Any]) -> Dict[str, Any]:
            # Here you would modify the agent configuration
            # For now, we'll use the standard agent
            return await run_agent_on_input(inputs)
        
        # Run evaluation
        experiment_prefix = f"comparative-{name}-{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        results = await aevaluate(
            configured_agent,
            data=self.dataset_name,
            evaluators=self.evaluators,
            summary_evaluators=self.summary_evaluators,
            experiment_prefix=experiment_prefix,
            max_concurrency=5,
            num_repetitions=1,
            metadata={
                "experiment_type": "comparative",
                "configuration": config,
                "timestamp": datetime.now().isoformat()
            }
        )
        
        # Collect metrics
        metrics = {}
        total_examples = 0
        errors = 0
        
        async for result in results:
            total_examples += 1
            if result.error:
                errors += 1
                continue
            
            for feedback in result.feedback:
                if feedback.key not in metrics:
                    metrics[feedback.key] = []
                metrics[feedback.key].append(feedback.score)
        
        # Calculate averages
        avg_metrics = {
            key: sum(scores) / len(scores) if scores else 0
            for key, scores in metrics.items()
        }
        
        return {
            "name": name,
            "experiment_name": experiment_prefix,
            "config": config,
            "total_examples": total_examples,
            "errors": errors,
            "metrics": avg_metrics,
            "timestamp": datetime.now().isoformat()
        }
    
    async def run_comparative_study(self, experiments: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Run multiple experiments and compare results."""
        print("Starting Comparative Evaluation Study")
        print(f"Dataset: {self.dataset_name}")
        print(f"Number of experiments: {len(experiments)}")
        
        results = []
        experiment_names = []
        
        for exp in experiments:
            result = await self.run_experiment(
                name=exp["name"],
                config=exp["config"],
                max_examples=exp.get("max_examples")
            )
            results.append(result)
            experiment_names.append(result["experiment_name"])
        
        # Display comparison
        print("\n" + "="*80)
        print("COMPARATIVE RESULTS")
        print("="*80)
        
        # Create comparison table
        print("\nMetric Comparison:")
        print("-" * 80)
        
        # Header
        print(f"{'Metric':<30}", end="")
        for result in results:
            print(f"{result['name']:<20}", end="")
        print()
        print("-" * 80)
        
        # Get all metric keys
        all_metrics = set()
        for result in results:
            all_metrics.update(result["metrics"].keys())
        
        # Display each metric
        for metric in sorted(all_metrics):
            print(f"{metric:<30}", end="")
            for result in results:
                score = result["metrics"].get(metric, 0)
                print(f"{score:<20.2%}", end="")
            print()
        
        # Success rate
        print(f"{'Success Rate':<30}", end="")
        for result in results:
            success_rate = (result["total_examples"] - result["errors"]) / result["total_examples"]
            print(f"{success_rate:<20.2%}", end="")
        print()
        
        # Create comparative experiment in LangSmith
        if len(experiment_names) > 1:
            try:
                comparative_exp = self.client.create_comparative_experiment(
                    name=f"Log Analyzer Comparison - {datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    experiments=experiment_names,
                    reference_dataset=self.dataset_name,
                    description="Comparative evaluation of different log analyzer configurations"
                )
                print(f"\nComparative experiment created in LangSmith: {comparative_exp.id}")
            except Exception as e:
                print(f"\nFailed to create comparative experiment: {e}")
        
        # Save results
        output_file = Path(f"comparative_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(output_file, 'w') as f:
            json.dump({
                "dataset": self.dataset_name,
                "experiments": results,
                "timestamp": datetime.now().isoformat()
            }, f, indent=2)
        
        print(f"\nResults saved to: {output_file}")
        
        return {
            "experiments": results,
            "best_overall": self._find_best_experiment(results)
        }
    
    def _find_best_experiment(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Find the best performing experiment based on key metrics."""
        # Define weights for different metrics
        metric_weights = {
            "issue_detection": 0.2,
            "issue_type_accuracy": 0.15,
            "severity_accuracy": 0.15,
            "explanation_quality": 0.1,
            "suggestion_quality": 0.1,
            "documentation_relevance": 0.1,
            "diagnostic_commands": 0.1,
            "response_completeness": 0.1
        }
        
        best_score = -1
        best_experiment = None
        
        for result in results:
            # Calculate weighted score
            score = 0
            for metric, weight in metric_weights.items():
                score += result["metrics"].get(metric, 0) * weight
            
            # Factor in success rate
            success_rate = (result["total_examples"] - result["errors"]) / result["total_examples"]
            score *= success_rate
            
            if score > best_score:
                best_score = score
                best_experiment = result
        
        return {
            "name": best_experiment["name"],
            "score": best_score,
            "config": best_experiment["config"]
        }


# Define experiment configurations
EXPERIMENTS = [
    {
        "name": "baseline",
        "config": {
            "model": "default",
            "temperature": 0.0,
            "max_iterations": 3
        }
    },
    {
        "name": "high-temperature",
        "config": {
            "model": "default",
            "temperature": 0.7,
            "max_iterations": 3
        }
    },
    {
        "name": "more-iterations",
        "config": {
            "model": "default",
            "temperature": 0.0,
            "max_iterations": 5
        }
    },
    {
        "name": "minimal-iterations",
        "config": {
            "model": "default",
            "temperature": 0.0,
            "max_iterations": 2
        }
    }
]


async def main():
    """Run the comparative evaluation."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run comparative evaluation experiments")
    parser.add_argument("--dataset", default="log-analyzer-evaluation-v3",
                       help="Name of the LangSmith dataset")
    parser.add_argument("--max-examples", type=int, default=None,
                       help="Maximum examples per experiment")
    parser.add_argument("--experiments", type=str, default=None,
                       help="JSON file with experiment configurations")
    
    args = parser.parse_args()
    
    # Load experiments
    if args.experiments:
        with open(args.experiments, 'r') as f:
            experiments = json.load(f)
    else:
        experiments = EXPERIMENTS
    
    # Add max_examples to each experiment if specified
    if args.max_examples:
        for exp in experiments:
            exp["max_examples"] = args.max_examples
    
    # Run comparative study
    evaluator = ComparativeEvaluator(dataset_name=args.dataset)
    results = await evaluator.run_comparative_study(experiments)
    
    # Display best configuration
    best = results["best_overall"]
    print(f"\n{'='*60}")
    print("BEST CONFIGURATION")
    print(f"{'='*60}")
    print(f"Name: {best['name']}")
    print(f"Score: {best['score']:.2%}")
    print(f"Configuration: {json.dumps(best['config'], indent=2)}")


if __name__ == "__main__":
    asyncio.run(main())