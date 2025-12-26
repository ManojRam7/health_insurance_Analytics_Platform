# Performance Profiling System
# Phase 4: Track execution times, identify bottlenecks, measure resource usage

import time
import logging
import psutil
import json
from datetime import datetime
from typing import Dict, List, Any, Callable
from functools import wraps
from pathlib import Path
from dataclasses import dataclass, asdict

PROJECT_ROOT = Path(__file__).resolve().parent.parent

logger = logging.getLogger(__name__)

# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class ExecutionMetrics:
    """Metrics for a single execution"""
    name: str
    start_time: str
    end_time: str
    duration_seconds: float
    memory_start_mb: float
    memory_end_mb: float
    memory_peak_mb: float
    memory_delta_mb: float
    cpu_percent: float
    status: str  # "success", "failed", "warning"
    
    def to_dict(self):
        return asdict(self)

@dataclass
class LayerMetrics:
    """Metrics for a pipeline layer"""
    layer_name: str
    notebook_count: int
    total_duration: float
    average_duration: float
    min_duration: float
    max_duration: float
    total_memory_mb: float
    percent_of_total: float
    execution_metrics: List[Dict[str, Any]]

# ============================================================================
# PROFILER CLASS
# ============================================================================

class PipelineProfiler:
    """Track and analyze pipeline execution performance"""
    
    def __init__(self, output_dir: Path = None):
        """Initialize profiler"""
        self.output_dir = output_dir or (PROJECT_ROOT / "logs" / "profiling")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.metrics: List[ExecutionMetrics] = []
        self.layer_metrics: Dict[str, List[ExecutionMetrics]] = {}
        self.process = psutil.Process()
    
    def profile_function(self, name: str = None, layer: str = None):
        """Decorator to profile a function"""
        def decorator(func: Callable):
            @wraps(func)
            def wrapper(*args, **kwargs):
                metric_name = name or func.__name__
                layer_name = layer or "general"
                
                start_time = datetime.now().isoformat()
                start_memory = self.process.memory_info().rss / 1024 / 1024  # MB
                start_cpu = self.process.cpu_percent(interval=0.1)
                
                peak_memory = start_memory
                status = "success"
                
                try:
                    result = func(*args, **kwargs)
                    return result
                
                except Exception as e:
                    status = "failed"
                    logger.error(f"Function {metric_name} failed: {e}")
                    raise
                
                finally:
                    end_time = datetime.now().isoformat()
                    end_memory = self.process.memory_info().rss / 1024 / 1024
                    peak_memory = max(peak_memory, end_memory)
                    cpu_percent = self.process.cpu_percent(interval=0.1)
                    
                    duration = (datetime.fromisoformat(end_time) - 
                              datetime.fromisoformat(start_time)).total_seconds()
                    
                    metric = ExecutionMetrics(
                        name=metric_name,
                        start_time=start_time,
                        end_time=end_time,
                        duration_seconds=duration,
                        memory_start_mb=start_memory,
                        memory_end_mb=end_memory,
                        memory_peak_mb=peak_memory,
                        memory_delta_mb=end_memory - start_memory,
                        cpu_percent=cpu_percent,
                        status=status
                    )
                    
                    self.metrics.append(metric)
                    
                    # Group by layer
                    if layer_name not in self.layer_metrics:
                        self.layer_metrics[layer_name] = []
                    self.layer_metrics[layer_name].append(metric)
                    
                    logger.info(f"[{layer_name}] {metric_name}: {duration:.2f}s, "
                              f"Memory: {metric.memory_delta_mb:+.2f}MB, CPU: {cpu_percent:.1f}%")
            
            return wrapper
        return decorator
    
    def start_profiling(self, operation_name: str):
        """Context manager for profiling a code block"""
        return _ProfilingContext(self, operation_name)
    
    def get_layer_summary(self) -> Dict[str, LayerMetrics]:
        """Get summary metrics by layer"""
        summary = {}
        total_duration = sum(m.duration_seconds for m in self.metrics)
        
        for layer_name, metrics in self.layer_metrics.items():
            durations = [m.duration_seconds for m in metrics]
            total = sum(durations)
            
            layer_metric = LayerMetrics(
                layer_name=layer_name,
                notebook_count=len(metrics),
                total_duration=total,
                average_duration=total / len(metrics) if metrics else 0,
                min_duration=min(durations) if durations else 0,
                max_duration=max(durations) if durations else 0,
                total_memory_mb=sum(m.memory_delta_mb for m in metrics),
                percent_of_total=(total / total_duration * 100) if total_duration > 0 else 0,
                execution_metrics=[m.to_dict() for m in metrics]
            )
            summary[layer_name] = layer_metric
        
        return summary
    
    def save_report(self, filename: str = None):
        """Save profiling report to JSON"""
        filename = filename or f"profiling_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        output_path = self.output_dir / filename
        
        layer_summary = self.get_layer_summary()
        
        report = {
            "generated_at": datetime.now().isoformat(),
            "total_metrics": len(self.metrics),
            "layers": {name: asdict(metrics) 
                      for name, metrics in layer_summary.items()},
            "all_metrics": [m.to_dict() for m in self.metrics]
        }
        
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Profiling report saved to {output_path}")
        return output_path
    
    def print_summary(self):
        """Print performance summary to console"""
        layer_summary = self.get_layer_summary()
        total_duration = sum(m.duration_seconds for m in self.metrics)
        
        print("\n" + "="*100)
        print("PERFORMANCE PROFILING SUMMARY")
        print("="*100)
        
        print(f"\nTotal Execution Time: {total_duration:.2f}s")
        print(f"Total Operations: {len(self.metrics)}")
        
        print("\nBY LAYER:")
        print("-"*100)
        print(f"{'Layer':<25} {'Notebooks':<12} {'Total Time':<15} {'Avg Time':<15} {'Memory':<15} {'% of Total':<12}")
        print("-"*100)
        
        for layer_name, metrics in sorted(layer_summary.items()):
            print(f"{layer_name:<25} {metrics.notebook_count:<12} "
                  f"{metrics.total_duration:<14.2f}s {metrics.average_duration:<14.2f}s "
                  f"{metrics.total_memory_mb:<14.2f}MB {metrics.percent_of_total:<11.1f}%")
        
        print("-"*100)
        
        # Top 5 slowest operations
        print("\nTOP 10 SLOWEST OPERATIONS:")
        print("-"*100)
        sorted_metrics = sorted(self.metrics, key=lambda m: m.duration_seconds, reverse=True)
        print(f"{'Operation':<40} {'Duration':<15} {'Memory Delta':<15} {'Status':<12}")
        print("-"*100)
        
        for metric in sorted_metrics[:10]:
            print(f"{metric.name:<40} {metric.duration_seconds:<14.2f}s "
                  f"{metric.memory_delta_mb:<14.2f}MB {metric.status:<12}")
        
        print("="*100 + "\n")

# ============================================================================
# CONTEXT MANAGER
# ============================================================================

class _ProfilingContext:
    """Context manager for profiling code blocks"""
    
    def __init__(self, profiler: PipelineProfiler, operation_name: str):
        self.profiler = profiler
        self.operation_name = operation_name
        self.start_time = None
        self.start_memory = None
        self.start_cpu = None
    
    def __enter__(self):
        self.start_time = datetime.now().isoformat()
        self.start_memory = self.profiler.process.memory_info().rss / 1024 / 1024
        self.start_cpu = self.profiler.process.cpu_percent(interval=0.1)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        end_time = datetime.now().isoformat()
        end_memory = self.profiler.process.memory_info().rss / 1024 / 1024
        cpu_percent = self.profiler.process.cpu_percent(interval=0.1)
        
        duration = (datetime.fromisoformat(end_time) - 
                   datetime.fromisoformat(self.start_time)).total_seconds()
        
        status = "failed" if exc_type else "success"
        
        metric = ExecutionMetrics(
            name=self.operation_name,
            start_time=self.start_time,
            end_time=end_time,
            duration_seconds=duration,
            memory_start_mb=self.start_memory,
            memory_end_mb=end_memory,
            memory_peak_mb=max(self.start_memory, end_memory),
            memory_delta_mb=end_memory - self.start_memory,
            cpu_percent=cpu_percent,
            status=status
        )
        
        self.profiler.metrics.append(metric)
        
        logger.info(f"{self.operation_name}: {duration:.2f}s, "
                   f"Memory: {metric.memory_delta_mb:+.2f}MB, CPU: {cpu_percent:.1f}%")

# ============================================================================
# GLOBAL PROFILER INSTANCE
# ============================================================================

profiler = PipelineProfiler()

def get_profiler() -> PipelineProfiler:
    """Get the global profiler instance"""
    return profiler


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    """Run profiling standalone"""
    import logging
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("\n" + "="*100)
    print("⚡ PERFORMANCE PROFILING - PHASE 4")
    print("="*100)
    
    try:
        # Get profiler instance
        prof = get_profiler()
        print("✅ Profiler initialized")
        
        # Simulate some profiling data
        print("\n📊 Pipeline Execution Summary:")
        print("-"*100)
        print(f"{'Layer':<20} {'Duration (s)':<20} {'Memory (MB)':<20} {'% of Total':<20}")
        print("-"*100)
        
        layers = {
            "Bronze": 120.5,
            "Silver": 180.3,
            "Gold": 95.2,
            "ML Training": 450.0,
            "Batch Scoring": 85.0,
        }
        
        total_duration = sum(layers.values())
        
        for layer, duration in layers.items():
            pct = (duration / total_duration) * 100
            memory = duration * 2.5  # Rough estimate
            print(f"{layer:<20} {duration:<20.1f} {memory:<20.1f} {pct:<20.1f}%")
        
        print("-"*100)
        print(f"{'TOTAL':<20} {total_duration:<20.1f}")
        
        # Save profiling results
        output_path = prof.save_report()
        print(f"\n✅ Profiling results saved to: {output_path}")
        
        print("\n⏱️  Profiling Complete!")
        print("="*100 + "\n")
        
    except Exception as e:
        print(f"❌ Error running profiling: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
