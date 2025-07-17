"""Benchmark runner for comprehensive evaluation."""

import asyncio
import time
import json
import traceback
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime

from ..core.interfaces import BenchmarkProvider, DatasetProvider, GraphConfiguration, EvaluationResult
from ..providers.loghub_provider import LogHubProvider
from ..configurations.minimal_config import MinimalGraphConfiguration
from ..configurations.full_config import FullGraphConfiguration
from ..configurations.memory_config import MemoryGraphConfiguration
from ..configurations.interactive_config import InteractiveGraphConfiguration


class BenchmarkRunner(BenchmarkProvider):
    """Comprehensive benchmark runner for log analysis evaluation."""
    
    def __init__(self, 
                 results_dir: str = "evaluation_results",
                 save_detailed_results: bool = True,
                 timeout_per_sample: float = 120.0):
        """Initialize the benchmark runner.
        
        Args:
            results_dir: Directory to save results
            save_detailed_results: Whether to save detailed results
            timeout_per_sample: Timeout for each sample evaluation
        """
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(exist_ok=True)
        
        self.save_detailed_results = save_detailed_results
        self.timeout_per_sample = timeout_per_sample
        
        # Available configurations
        self.configurations = {
            "minimal": MinimalGraphConfiguration(),
            "full": FullGraphConfiguration(),
            "memory": MemoryGraphConfiguration(),
            "interactive": InteractiveGraphConfiguration()
        }
    
    def get_name(self) -> str:
        """Get the name of the benchmark provider."""
        return "ComprehensiveBenchmark"
    
    async def run_benchmark(self, graph_config: GraphConfiguration, dataset_provider: DatasetProvider) -> Dict[str, Any]:
        """Run benchmark against the given graph and dataset.
        
        Args:
            graph_config: Graph configuration to evaluate
            dataset_provider: Dataset provider for test data
            
        Returns:
            Benchmark results
        """
        print(f"Starting benchmark: {graph_config.get_name()} on {dataset_provider.get_name()}")
        
        # Initialize results
        results = {
            "benchmark_name": self.get_name(),
            "graph_config": graph_config.get_name(),
            "dataset": dataset_provider.get_name(),
            "start_time": datetime.now().isoformat(),
            "evaluators": [e.get_name() for e in graph_config.get_evaluators()],
            "samples_processed": 0,
            "samples_failed": 0,
            "total_samples": 0,
            "evaluation_metrics": {},
            "detailed_results": [] if self.save_detailed_results else None,
            "summary": {}
        }
        
        try:
            # Create graph instance
            graph = await graph_config.create_graph()
            
            # Load samples
            samples = dataset_provider.load_samples()
            results["total_samples"] = len(samples)
            
            print(f"Loaded {len(samples)} samples")
            
            # Process each sample
            for i, sample in enumerate(samples):
                if i % 10 == 0:
                    print(f"Processing sample {i+1}/{len(samples)}")
                
                try:
                    # Evaluate single sample
                    sample_result = await self._evaluate_sample(
                        graph, sample, graph_config, dataset_provider
                    )
                    
                    # Update results
                    results["samples_processed"] += 1
                    self._update_metrics(results["evaluation_metrics"], sample_result)
                    
                    if self.save_detailed_results:
                        results["detailed_results"].append({
                            "sample_id": i,
                            "sample_metadata": sample.metadata,
                            "evaluation_result": sample_result
                        })
                
                except Exception as e:
                    print(f"Error evaluating sample {i}: {e}")
                    results["samples_failed"] += 1
                    
                    if self.save_detailed_results:
                        results["detailed_results"].append({
                            "sample_id": i,
                            "error": str(e),
                            "traceback": traceback.format_exc()
                        })
            
            # Calculate summary statistics
            results["summary"] = self._calculate_summary(results["evaluation_metrics"])
            results["end_time"] = datetime.now().isoformat()
            
            # Save results
            await self._save_results(results)
            
            print(f"Benchmark completed: {results['samples_processed']}/{results['total_samples']} samples processed")
            
            return results
            
        except Exception as e:
            print(f"Benchmark failed: {e}")
            results["error"] = str(e)
            results["traceback"] = traceback.format_exc()
            results["end_time"] = datetime.now().isoformat()
            
            await self._save_results(results)
            raise
    
    async def _evaluate_sample(self, graph, sample, graph_config: GraphConfiguration, dataset_provider: DatasetProvider) -> Dict[str, Any]:
        """Evaluate a single sample."""
        start_time = time.time()
        
        try:
            # Prepare input
            input_data = {
                "log_content": sample.content,
                "environment_details": sample.metadata
            }
            
            # Run analysis with timeout
            analysis_result = await asyncio.wait_for(
                self._run_analysis(graph, input_data),
                timeout=self.timeout_per_sample
            )
            
            end_time = time.time()
            response_time = end_time - start_time
            
            # Prepare outputs for evaluation
            outputs = {
                "analysis_result": analysis_result,
                "response_time": response_time,
                "start_time": start_time,
                "end_time": end_time
            }
            
            # Prepare reference data
            reference = {
                "log_content": sample.content,
                "system_type": sample.system_type.value,
                "dataset": sample.dataset,
                "metadata": sample.metadata,
                "log_size": len(sample.content) / (1024 * 1024),  # MB
                "log_count": len(sample.content.split('\n'))
            }
            
            # Run evaluators
            evaluation_results = {}
            for evaluator in graph_config.get_evaluators():
                if evaluator.applies_to(sample.system_type):
                    try:
                        metric = await evaluator.evaluate(outputs, reference)
                        evaluation_results[evaluator.get_name()] = metric.to_dict()
                    except Exception as e:
                        print(f"Evaluator {evaluator.get_name()} failed: {e}")
                        evaluation_results[evaluator.get_name()] = {
                            "error": str(e),
                            "key": evaluator.get_name().lower(),
                            "value": 0.0,
                            "score": 0.0,
                            "comment": f"Evaluation failed: {e}"
                        }
            
            return {
                "success": True,
                "response_time": response_time,
                "evaluation_results": evaluation_results,
                "outputs": outputs,
                "reference": reference
            }
            
        except asyncio.TimeoutError:
            return {
                "success": False,
                "error": "Timeout",
                "response_time": self.timeout_per_sample,
                "evaluation_results": {}
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "response_time": time.time() - start_time,
                "evaluation_results": {}
            }
    
    async def _run_analysis(self, graph, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run analysis on the graph."""
        # This depends on the specific graph implementation
        # For now, we'll use a generic approach
        
        try:
            # Try to invoke the graph directly
            if hasattr(graph, 'invoke'):
                result = await graph.invoke(input_data)
            elif hasattr(graph, 'run'):
                result = await graph.run(input_data)
            else:
                # Fallback - assume it's a callable
                result = await graph(input_data)
            
            # Extract analysis result
            if isinstance(result, dict):
                return result.get("analysis_result", result)
            else:
                return {"raw_result": str(result)}
                
        except Exception as e:
            return {
                "error": str(e),
                "summary": "Analysis failed",
                "issues": [],
                "recommendations": []
            }
    
    def _update_metrics(self, metrics: Dict[str, Any], sample_result: Dict[str, Any]) -> None:
        """Update accumulated metrics with sample result."""
        if not sample_result.get("success", False):
            return
        
        evaluation_results = sample_result.get("evaluation_results", {})
        
        for evaluator_name, metric_data in evaluation_results.items():
            if evaluator_name not in metrics:
                metrics[evaluator_name] = {
                    "scores": [],
                    "values": [],
                    "results": [],
                    "comments": []
                }
            
            metrics[evaluator_name]["scores"].append(metric_data.get("score", 0.0))
            metrics[evaluator_name]["values"].append(metric_data.get("value", 0.0))
            metrics[evaluator_name]["results"].append(metric_data.get("result", "failed"))
            metrics[evaluator_name]["comments"].append(metric_data.get("comment", ""))
    
    def _calculate_summary(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate summary statistics from accumulated metrics."""
        summary = {}
        
        for evaluator_name, metric_data in metrics.items():
            scores = metric_data["scores"]
            values = metric_data["values"]
            results = metric_data["results"]
            
            if scores:
                summary[evaluator_name] = {
                    "avg_score": sum(scores) / len(scores),
                    "min_score": min(scores),
                    "max_score": max(scores),
                    "avg_value": sum(values) / len(values) if values else 0.0,
                    "samples_count": len(scores),
                    "pass_rate": sum(1 for r in results if r == "passed") / len(results),
                    "fail_rate": sum(1 for r in results if r == "failed") / len(results),
                    "partial_rate": sum(1 for r in results if r == "partial") / len(results),
                    "skip_rate": sum(1 for r in results if r == "skipped") / len(results)
                }
        
        # Calculate overall score
        if summary:
            overall_scores = [data["avg_score"] for data in summary.values()]
            summary["overall"] = {
                "avg_score": sum(overall_scores) / len(overall_scores),
                "min_score": min(overall_scores),
                "max_score": max(overall_scores),
                "evaluators_count": len(summary)
            }
        
        return summary
    
    async def _save_results(self, results: Dict[str, Any]) -> None:
        """Save results to file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"benchmark_{results['graph_config']}_{results['dataset']}_{timestamp}.json"
        filepath = self.results_dir / filename
        
        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"Results saved to: {filepath}")
    
    async def run_comprehensive_benchmark(self, 
                                        dataset_names: List[str] = None,
                                        config_names: List[str] = None) -> Dict[str, Any]:
        """Run comprehensive benchmark across multiple datasets and configurations.
        
        Args:
            dataset_names: List of dataset names to test (default: all available)
            config_names: List of configuration names to test (default: all available)
            
        Returns:
            Comprehensive benchmark results
        """
        # Default datasets
        if dataset_names is None:
            dataset_names = ["HDFS", "BGL", "Hadoop", "Apache", "Linux"]
        
        # Default configurations
        if config_names is None:
            config_names = ["minimal", "full", "memory", "interactive"]
        
        comprehensive_results = {
            "benchmark_name": "ComprehensiveBenchmark",
            "start_time": datetime.now().isoformat(),
            "datasets": dataset_names,
            "configurations": config_names,
            "results": {},
            "summary": {}
        }
        
        try:
            # Run benchmark for each combination
            for dataset_name in dataset_names:
                comprehensive_results["results"][dataset_name] = {}
                
                # Create dataset provider
                dataset_provider = LogHubProvider(dataset_name)
                
                for config_name in config_names:
                    if config_name not in self.configurations:
                        print(f"Unknown configuration: {config_name}")
                        continue
                    
                    config = self.configurations[config_name]
                    
                    print(f"Running benchmark: {config_name} on {dataset_name}")
                    
                    try:
                        result = await self.run_benchmark(config, dataset_provider)
                        comprehensive_results["results"][dataset_name][config_name] = result
                        
                    except Exception as e:
                        print(f"Benchmark failed for {config_name} on {dataset_name}: {e}")
                        comprehensive_results["results"][dataset_name][config_name] = {
                            "error": str(e),
                            "traceback": traceback.format_exc()
                        }
            
            # Calculate comprehensive summary
            comprehensive_results["summary"] = self._calculate_comprehensive_summary(
                comprehensive_results["results"]
            )
            
            comprehensive_results["end_time"] = datetime.now().isoformat()
            
            # Save comprehensive results
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"comprehensive_benchmark_{timestamp}.json"
            filepath = self.results_dir / filename
            
            with open(filepath, 'w') as f:
                json.dump(comprehensive_results, f, indent=2, default=str)
            
            print(f"Comprehensive results saved to: {filepath}")
            
            return comprehensive_results
            
        except Exception as e:
            comprehensive_results["error"] = str(e)
            comprehensive_results["traceback"] = traceback.format_exc()
            comprehensive_results["end_time"] = datetime.now().isoformat()
            
            # Save error results
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"comprehensive_benchmark_error_{timestamp}.json"
            filepath = self.results_dir / filename
            
            with open(filepath, 'w') as f:
                json.dump(comprehensive_results, f, indent=2, default=str)
            
            raise
    
    def _calculate_comprehensive_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate summary across all datasets and configurations."""
        summary = {
            "by_dataset": {},
            "by_configuration": {},
            "overall": {}
        }
        
        # Summary by dataset
        for dataset_name, dataset_results in results.items():
            dataset_scores = []
            
            for config_name, config_result in dataset_results.items():
                if "summary" in config_result and "overall" in config_result["summary"]:
                    dataset_scores.append(config_result["summary"]["overall"]["avg_score"])
            
            if dataset_scores:
                summary["by_dataset"][dataset_name] = {
                    "avg_score": sum(dataset_scores) / len(dataset_scores),
                    "min_score": min(dataset_scores),
                    "max_score": max(dataset_scores),
                    "configurations_tested": len(dataset_scores)
                }
        
        # Summary by configuration
        for config_name in self.configurations.keys():
            config_scores = []
            
            for dataset_name, dataset_results in results.items():
                if config_name in dataset_results:
                    config_result = dataset_results[config_name]
                    if "summary" in config_result and "overall" in config_result["summary"]:
                        config_scores.append(config_result["summary"]["overall"]["avg_score"])
            
            if config_scores:
                summary["by_configuration"][config_name] = {
                    "avg_score": sum(config_scores) / len(config_scores),
                    "min_score": min(config_scores),
                    "max_score": max(config_scores),
                    "datasets_tested": len(config_scores)
                }
        
        # Overall summary
        all_scores = []
        for dataset_summary in summary["by_dataset"].values():
            all_scores.append(dataset_summary["avg_score"])
        
        if all_scores:
            summary["overall"] = {
                "avg_score": sum(all_scores) / len(all_scores),
                "min_score": min(all_scores),
                "max_score": max(all_scores),
                "datasets_count": len(summary["by_dataset"]),
                "configurations_count": len(summary["by_configuration"])
            }
        
        return summary