# ISSUE 2: Unify Metrics Systems - Implementation Plan

## Overview

**Issue**: Remove duplicate metrics functionality between builder and core systems  
**Impact**: Eliminate 1,800+ lines of duplicated code, unify metrics API  
**Effort**: 3-5 days  
**Risk**: Medium - requires careful migration and API consolidation  

## Current State Analysis

### Duplicate Metrics Systems Identified

#### System A: Builder Metrics (`panther/builder_metrics/`)
- **Purpose**: CLI-focused metrics for build operations
- **Files**: 7 files, ~800 lines of code
- **Key Components**:
  - `core.py` - Basic MetricsCollector (157 lines)
  - `storage.py` - JSONLinesStorage (111 lines) 
  - `resource_sampler.py` - Basic CPU/memory monitoring (115 lines)
  - `utils.py` - Utility functions
  - `cli.py` - CLI integration
  - `pytest_plugin.py` - Test integration

#### System B: Core Metrics (`panther/core/metrics/`)  
- **Purpose**: Advanced experiment metrics collection
- **Files**: 4 files, ~1,500+ lines of code
- **Key Components**:
  - `metrics_collector.py` - Advanced MetricsCollector (1,112 lines)
  - `metrics_exporter.py` - Multi-format export (935 lines)
  - `metrics_reporter.py` - Report generation
  - `resource_monitor.py` - Detailed resource monitoring (425 lines)

### Functional Overlap Analysis

#### 1. MetricsCollector Classes (90% Overlap)

**Builder Metrics Pattern**:
```python
class MetricsCollector:
    def record(self, name: str, value: float, tags: Optional[Dict[str, str]] = None)
    def flush(self, kind: str, extra: Optional[Dict[str, Any]] = None) -> str
    def get_config_hash(self, config_data: Union[str, Dict[str, Any]]) -> str
```

**Core Metrics Pattern**:
```python  
class MetricsCollector:
    def record_metric(self, name: str, metric_type: MetricType, value: Any, ...)
    def start_timer(self, name: str, phase: Optional[Phase] = None, ...)
    def increment_counter(self, name: str, value: int = 1, ...)
    def record_gauge(self, name: str, value: float, ...)
    def finalize(self) -> None
```

#### 2. Resource Monitoring (85% Overlap)

**Builder ResourceSampler**:
```python
class ResourceSampler:
    def start(self) -> None
    def stop(self) -> Dict[str, float]
    def get_current_stats(self) -> Dict[str, float]
    # Returns: cpu.avg_load, cpu.max_load, ram.peak_mb, ram.avg_mb
```

**Core ResourceMonitor**:
```python
class ResourceMonitor:
    def start(self, phase: Optional[Phase] = None) -> None
    def stop(self) -> None
    def get_current_snapshot(self) -> ResourceSnapshot
    # Records: cpu_percent, memory_percent, disk_io, network_io, processes
```

#### 3. Storage Mechanisms (70% Overlap)

**Builder JSONLinesStorage**:
```python
class JSONLinesStorage:
    def write_record(self, record: Dict[str, Any]) -> None
    def read_records(self, date: Optional[str] = None) -> List[Dict[str, Any]]
    def get_record_by_id(self, run_id: str) -> Optional[Dict[str, Any]]
```

**Core Metrics Storage** (via MetricsExporter):
```python
class MetricsExporter:
    def export_to_json(self, output_path: Path) -> bool
    def export_to_csv(self, output_dir: Path) -> bool
    def export_prometheus_format(self, output_path: Path) -> bool
```

### Impact Analysis

#### Code Duplication Metrics
- **Total Duplicate Lines**: ~1,800+ lines across both systems
- **Overlapping Classes**: 3 major classes (MetricsCollector, ResourceMonitor/Sampler, Storage)
- **Redundant Functionality**: 15+ methods with similar implementation
- **Import Redundancy**: 25+ shared dependencies (psutil, threading, time, json)

#### API Inconsistencies
- **Different Method Names**: `record()` vs `record_metric()`
- **Different Parameter Signatures**: Tags vs metadata/labels
- **Different Storage Formats**: JSONL vs JSON/CSV/Prometheus
- **Different Resource Metrics**: Simple averages vs detailed snapshots

## Implementation Strategy

### Phase 1: Enhance Core Metrics System for Builder Use Cases

#### 1.1 Add Builder-Compatible API to Core MetricsCollector
**File**: `panther/core/metrics/metrics_collector.py`
**Location**: After line 983 (end of class)
**Action**: ADD

```python
def record(
    self, 
    name: str, 
    value: float, 
    tags: Optional[Dict[str, str]] = None,
    kind: str = "builder"
) -> None:
    """Builder-compatible record method for backward compatibility.
    
    Args:
        name: Metric name (e.g., "container.build_seconds")
        value: Metric value
        tags: Optional tags for the metric (mapped to labels)
        kind: Type of metrics ("builder", "tests", etc.) - mapped to component
    """
    # Map builder API to core metrics API
    self.record_metric(
        name=name,
        metric_type=MetricType.GAUGE,  # Default for builder metrics
        value=value,
        component=kind,
        labels=tags or {},
        metadata={"source": "builder_compat"}
    )

def flush(self, kind: str, extra: Optional[Dict[str, Any]] = None) -> str:
    """Builder-compatible flush method.
    
    Args:
        kind: Type of metrics ("builder", "tests", etc.)
        extra: Additional metadata
        
    Returns:
        The run ID for this flush (experiment name)
    """
    # Export current metrics in builder-compatible format
    from .metrics_exporter import MetricsExporter
    
    exporter = MetricsExporter(self)
    output_path = self.metrics_dir / f"{kind}_{int(time.time())}.json"
    
    if exporter.export_to_json(output_path, include_raw_data=True):
        self.logger.info("Metrics flushed to %s", output_path)
        return self.experiment_name
    else:
        self.logger.error("Failed to flush metrics")
        return ""

def get_config_hash(self, config_data: Union[str, Dict[str, Any]]) -> str:
    """Generate a hash for configuration data (builder compatibility).
    
    Args:
        config_data: Configuration data as string or dict
        
    Returns:
        SHA256 hash of the configuration
    """
    import hashlib
    import json
    
    if isinstance(config_data, dict):
        config_data = json.dumps(config_data, sort_keys=True)
    
    return hashlib.sha256(config_data.encode()).hexdigest()[:16]
```

#### 1.2 Add Global Collector Factory
**File**: `panther/core/metrics/metrics_collector.py`
**Location**: After line 1111 (end of file)
**Action**: ADD

```python
# Global collector management for builder compatibility
_global_collector: Optional[MetricsCollector] = None
_collector_lock = threading.Lock()

def get_current_collector() -> MetricsCollector:
    """Get or create the current global metrics collector (builder compatibility)."""
    global _global_collector
    with _collector_lock:
        if _global_collector is None:
            from pathlib import Path
            # Create collector with default settings for builder use
            output_dir = Path.cwd() / ".panther-metrics"
            _global_collector = MetricsCollector(
                experiment_name="builder_metrics",
                output_dir=output_dir,
                collection_interval=5.0
            )
        return _global_collector

def record(name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
    """Record a metric using the global collector (builder compatibility).
    
    Args:
        name: Metric name (e.g., "container.build_seconds")  
        value: Metric value
        tags: Optional tags for the metric
    """
    collector = get_current_collector()
    collector.record(name, value, tags)

def flush(kind: str, extra: Optional[Dict[str, Any]] = None) -> str:
    """Flush metrics using the global collector (builder compatibility).
    
    Args:
        kind: Type of metrics ("builder", "tests", etc.)
        extra: Additional metadata
        
    Returns:
        The run ID for this flush
    """
    collector = get_current_collector()
    return collector.flush(kind, extra)
```

#### 1.3 Enhance ResourceMonitor for Builder Compatibility  
**File**: `panther/core/metrics/resource_monitor.py`
**Location**: After line 425 (end of class)
**Action**: ADD

```python
def get_builder_compatible_stats(self) -> Dict[str, float]:
    """Get resource stats in builder-compatible format.
    
    Returns:
        Dictionary with builder-expected keys
    """
    snapshot = self.get_current_snapshot()
    
    # Map core resource format to builder format
    return {
        "cpu.current_load": snapshot.cpu_percent,
        "cpu.avg_load": snapshot.cpu_percent,  # Approximation for compatibility
        "cpu.max_load": snapshot.cpu_percent,  # Single sample, so same as current
        "ram.current_mb": snapshot.memory_used_mb,
        "ram.avg_mb": snapshot.memory_used_mb,  # Single sample approximation
        "ram.peak_mb": snapshot.memory_used_mb,  # Single sample, so same as current
    }

def start_builder_sampling(self, interval: float = 1.0) -> None:
    """Start resource monitoring with builder-compatible interface.
    
    Args:
        interval: Sampling interval in seconds (maps to monitor interval)
    """
    # Update interval if different
    self.interval = interval
    self.start()

def stop_builder_sampling(self) -> Dict[str, float]:
    """Stop resource monitoring and return builder-compatible metrics.
    
    Returns:
        Dictionary containing CPU and memory metrics in builder format
    """
    self.stop()
    
    # Get aggregated metrics from collector
    cpu_metrics = self.metrics_collector.get_metrics(
        metric_type=MetricType.GAUGE,
        component="resource_monitor"
    )
    
    # Calculate builder-compatible aggregations
    cpu_values = [m.value for m in cpu_metrics if m.name == "cpu_percent"]
    memory_values = [m.value for m in cpu_metrics if m.name == "memory_used_mb"]
    
    if not cpu_values or not memory_values:
        return {}
    
    return {
        "cpu.avg_load": sum(cpu_values) / len(cpu_values),
        "cpu.max_load": max(cpu_values),
        "ram.peak_mb": max(memory_values),
        "ram.avg_mb": sum(memory_values) / len(memory_values),
    }
```

### Phase 2: Create Unified Interface Module

#### 2.1 Create Compatibility Layer
**File**: `panther/core/metrics/builder_compat.py`
**Action**: CREATE

```python
"""
Compatibility layer for builder metrics.

This module provides a drop-in replacement for the builder_metrics
system using the enhanced core metrics system.
"""

from typing import Dict, List, Optional, Any, Union
from pathlib import Path

from .metrics_collector import MetricsCollector, get_current_collector
from .resource_monitor import ResourceMonitor


class CompatMetricsCollector:
    """Drop-in replacement for builder_metrics.core.MetricsCollector."""
    
    def __init__(self, storage_path: Optional[Path] = None):
        """Initialize using core metrics system.
        
        Args:
            storage_path: Path to store metrics files (mapped to output_dir)
        """
        if storage_path is None:
            storage_path = Path.cwd() / ".panther-metrics"
        
        self._core_collector = MetricsCollector(
            experiment_name="builder_metrics",
            output_dir=storage_path
        )
        
        # Create resource monitor for sampling compatibility
        self._resource_monitor = ResourceMonitor(
            metrics_collector=self._core_collector,
            interval=1.0
        )
        
    def record(
        self, name: str, value: float, tags: Optional[Dict[str, str]] = None
    ) -> None:
        """Record a metric value (builder compatibility)."""
        self._core_collector.record(name, value, tags)
    
    def flush(self, kind: str, extra: Optional[Dict[str, Any]] = None) -> str:
        """Flush collected metrics to storage (builder compatibility)."""
        return self._core_collector.flush(kind, extra)
    
    def get_config_hash(self, config_data: Union[str, Dict[str, Any]]) -> str:
        """Generate a hash for configuration data (builder compatibility)."""
        return self._core_collector.get_config_hash(config_data)


class CompatResourceSampler:
    """Drop-in replacement for builder_metrics.resource_sampler.ResourceSampler."""
    
    def __init__(self, interval: float = 1.0):
        """Initialize using core resource monitor.
        
        Args:
            interval: Sampling interval in seconds
        """
        # Get global collector for resource monitoring
        self._collector = get_current_collector()
        self._resource_monitor = ResourceMonitor(
            metrics_collector=self._collector,
            interval=interval
        )
        
    def start(self) -> None:
        """Start resource sampling (builder compatibility)."""
        self._resource_monitor.start_builder_sampling()
        
    def stop(self) -> Dict[str, float]:
        """Stop resource sampling and return metrics (builder compatibility)."""
        return self._resource_monitor.stop_builder_sampling()
        
    def get_current_stats(self) -> Dict[str, float]:
        """Get current resource usage (builder compatibility)."""
        return self._resource_monitor.get_builder_compatible_stats()


class CompatJSONLinesStorage:
    """Drop-in replacement for builder_metrics.storage.JSONLinesStorage."""
    
    def __init__(self, base_path: Path):
        """Initialize using core metrics exporter.
        
        Args:
            base_path: Base directory for storing metrics files
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        
    def write_record(self, record: Dict[str, Any]) -> None:
        """Write a metrics record to storage (builder compatibility)."""
        # Use core metrics JSON export format
        from datetime import datetime
        import json
        
        # Create filename based on current date
        now = datetime.now()
        filename = f"{now.strftime('%Y-%m-%d')}.jsonl"
        filepath = self.base_path / filename
        
        # Append the record as a JSON line
        with open(filepath, "a", encoding="utf-8") as f:
            json.dump(record, f, separators=(",", ":"))
            f.write("\n")
            
    def read_records(
        self, date: Optional[str] = None, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Read metrics records from storage (builder compatibility)."""
        records = []
        
        if date:
            # Read from specific date file
            filepath = self.base_path / f"{date}.jsonl"
            if filepath.exists():
                records.extend(self._read_file(filepath))
        else:
            # Read from all files, newest first
            files = sorted(self.base_path.glob("*.jsonl"), reverse=True)
            for filepath in files:
                records.extend(self._read_file(filepath))
                if limit and len(records) >= limit:
                    break
                    
        # Sort by timestamp, newest first
        records.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        if limit:
            records = records[:limit]
            
        return records
        
    def _read_file(self, filepath: Path) -> List[Dict[str, Any]]:
        """Read records from a single JSONL file."""
        records = []
        try:
            with open(filepath, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            import json
                            record = json.loads(line)
                            records.append(record)
                        except json.JSONDecodeError:
                            continue
        except FileNotFoundError:
            pass
        return records
        
    def get_record_by_id(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific record by run ID (builder compatibility)."""
        files = sorted(self.base_path.glob("*.jsonl"), reverse=True)
        for filepath in files:
            records = self._read_file(filepath)
            for record in records:
                if record.get("run_id") == run_id:
                    return record
        return None
        
    def list_files(self) -> List[Path]:
        """List all metrics files (builder compatibility)."""
        return sorted(self.base_path.glob("*.jsonl"), reverse=True)


# Global compatibility functions
def record(name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
    """Record a metric using the global collector (builder compatibility)."""
    from .metrics_collector import record as core_record
    core_record(name, value, tags)

def flush(kind: str, extra: Optional[Dict[str, Any]] = None) -> str:
    """Flush metrics using the global collector (builder compatibility)."""
    from .metrics_collector import flush as core_flush
    return core_flush(kind, extra)
```

### Phase 3: Update Import Statements and Migration

#### 3.1 Files Requiring Import Updates

**Search and Replace Operations**:

1. **All files importing builder_metrics.core**:
```python
# OLD
from panther.builder_metrics.core import MetricsCollector, record, flush
from panther.builder_metrics.core import get_current_collector

# NEW  
from panther.core.metrics.builder_compat import CompatMetricsCollector as MetricsCollector
from panther.core.metrics.builder_compat import record, flush
from panther.core.metrics.metrics_collector import get_current_collector
```

2. **All files importing builder_metrics.resource_sampler**:
```python
# OLD
from panther.builder_metrics.resource_sampler import ResourceSampler

# NEW
from panther.core.metrics.builder_compat import CompatResourceSampler as ResourceSampler
```

3. **All files importing builder_metrics.storage**:
```python
# OLD
from panther.builder_metrics.storage import JSONLinesStorage

# NEW  
from panther.core.metrics.builder_compat import CompatJSONLinesStorage as JSONLinesStorage
```

#### 3.2 Files to Update (Based on Usage Analysis)

**Primary Files Using Builder Metrics**:
```
panther/panther_builder.py - Main builder script
panther/cli/ - CLI modules (if any)
tests/ - Test files using metrics
```

**Find and Update Command**:
```bash
# Find all files importing builder_metrics
grep -r "from panther.builder_metrics" panther/ --include="*.py"
grep -r "import panther.builder_metrics" panther/ --include="*.py"

# Update imports systematically
find panther/ -name "*.py" -exec sed -i.bak \
  's/from panther\.builder_metrics\.core/from panther.core.metrics.builder_compat/g' {} \;
find panther/ -name "*.py" -exec sed -i.bak \
  's/from panther\.builder_metrics\.resource_sampler/from panther.core.metrics.builder_compat/g' {} \;
find panther/ -name "*.py" -exec sed -i.bak \
  's/from panther\.builder_metrics\.storage/from panther.core.metrics.builder_compat/g' {} \;
```

### Phase 4: Remove Builder Metrics System

#### 4.1 Files to Remove
**Action**: DELETE

```
panther/builder_metrics/
├── __init__.py
├── cli.py (138 lines)
├── core.py (157 lines)  
├── metrics.md (Documentation)
├── pytest_plugin.py (Plugin integration)
├── resource_sampler.py (115 lines)
├── storage.py (111 lines)
└── utils.py (Utility functions)
```

**Total Removed**: ~800+ lines of duplicate code

#### 4.2 Update __init__.py Files
**File**: `panther/__init__.py`
**Action**: REMOVE references to builder_metrics

**File**: `panther/core/metrics/__init__.py`  
**Action**: ADD builder compatibility exports

```python
# Add to existing __init__.py
from .builder_compat import (
    CompatMetricsCollector,
    CompatResourceSampler, 
    CompatJSONLinesStorage,
    record,
    flush
)

# For backward compatibility
MetricsCollector = CompatMetricsCollector
ResourceSampler = CompatResourceSampler
JSONLinesStorage = CompatJSONLinesStorage
```

### Phase 5: Testing and Validation

#### 5.1 Create Compatibility Tests
**File**: `tests/unit/test_core/test_builder_metrics_compat.py`
**Action**: CREATE

```python
"""Tests for builder metrics compatibility layer."""

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from panther.core.metrics.builder_compat import (
    CompatMetricsCollector,
    CompatResourceSampler,
    CompatJSONLinesStorage,
    record,
    flush
)


class TestCompatMetricsCollector:
    """Test builder metrics compatibility."""
    
    def test_record_basic(self):
        """Test basic record functionality."""
        collector = CompatMetricsCollector()
        
        # Should not raise exception
        collector.record("test.metric", 42.0)
        collector.record("test.tagged", 1.5, {"tag": "value"})
        
    def test_flush_creates_output(self, tmp_path):
        """Test flush creates output files."""
        collector = CompatMetricsCollector(tmp_path)
        collector.record("test.metric", 42.0)
        
        run_id = collector.flush("test")
        assert run_id == "builder_metrics"
        
        # Should have created JSON file
        json_files = list(tmp_path.glob("*.json"))
        assert len(json_files) >= 1
        
    def test_config_hash(self):
        """Test configuration hashing."""
        collector = CompatMetricsCollector()
        
        # Test with dict
        config = {"key": "value", "number": 42}
        hash1 = collector.get_config_hash(config)
        hash2 = collector.get_config_hash(config)
        assert hash1 == hash2
        assert len(hash1) == 16
        
        # Test with string
        hash3 = collector.get_config_hash("test string")
        assert len(hash3) == 16
        assert hash3 != hash1


class TestCompatResourceSampler:
    """Test resource sampler compatibility."""
    
    @patch('panther.core.metrics.resource_monitor.psutil')
    def test_sampling_cycle(self, mock_psutil):
        """Test start/stop sampling cycle."""
        # Mock psutil
        mock_psutil.cpu_percent.return_value = 25.0
        mock_psutil.virtual_memory.return_value = MagicMock(used=1024*1024*512)  # 512 MB
        
        sampler = CompatResourceSampler(interval=0.1)
        
        # Should not raise
        sampler.start()
        stats = sampler.stop()
        
        # Should return expected format
        expected_keys = ["cpu.avg_load", "cpu.max_load", "ram.peak_mb", "ram.avg_mb"]
        for key in expected_keys:
            assert key in stats
            
    @patch('panther.core.metrics.resource_monitor.psutil')
    def test_current_stats(self, mock_psutil):
        """Test get_current_stats method."""
        # Mock psutil
        mock_psutil.cpu_percent.return_value = 50.0
        mock_psutil.virtual_memory.return_value = MagicMock(used=1024*1024*1024)  # 1 GB
        
        sampler = CompatResourceSampler()
        stats = sampler.get_current_stats()
        
        expected_keys = ["cpu.current_load", "ram.current_mb"]
        for key in expected_keys:
            assert key in stats


class TestCompatJSONLinesStorage:
    """Test JSON Lines storage compatibility."""
    
    def test_write_and_read_record(self, tmp_path):
        """Test writing and reading records."""
        storage = CompatJSONLinesStorage(tmp_path)
        
        # Write test record
        record = {
            "run_id": "test-123",
            "timestamp": "2024-01-01T00:00:00Z",
            "metrics": {"test": 42.0}
        }
        storage.write_record(record)
        
        # Read records
        records = storage.read_records()
        assert len(records) == 1
        assert records[0]["run_id"] == "test-123"
        
    def test_read_by_id(self, tmp_path):
        """Test reading record by ID."""
        storage = CompatJSONLinesStorage(tmp_path)
        
        # Write multiple records
        for i in range(3):
            record = {
                "run_id": f"test-{i}",
                "timestamp": f"2024-01-0{i+1}T00:00:00Z",
                "value": i * 10
            }
            storage.write_record(record)
            
        # Find specific record
        found = storage.get_record_by_id("test-1")
        assert found is not None
        assert found["value"] == 10
        
        # Non-existent record
        not_found = storage.get_record_by_id("test-999")
        assert not_found is None
        
    def test_list_files(self, tmp_path):
        """Test listing files."""
        storage = CompatJSONLinesStorage(tmp_path)
        
        # Initially no files
        files = storage.list_files()
        assert len(files) == 0
        
        # Write record to create file
        storage.write_record({"test": "data"})
        
        # Should have one file
        files = storage.list_files()
        assert len(files) == 1
        assert files[0].suffix == ".jsonl"


class TestGlobalFunctions:
    """Test global compatibility functions."""
    
    def test_global_record_and_flush(self):
        """Test global record and flush functions."""
        # Should not raise exceptions
        record("global.test", 123.45)
        record("global.tagged", 67.89, {"env": "test"})
        
        # Flush should return run ID
        run_id = flush("unittest")
        assert isinstance(run_id, str)
        assert len(run_id) > 0


@pytest.mark.integration
class TestBackwardCompatibility:
    """Integration tests for full backward compatibility."""
    
    def test_drop_in_replacement(self, tmp_path):
        """Test that new system works as drop-in replacement."""
        # This simulates the exact usage pattern from the old system
        
        from panther.core.metrics.builder_compat import (
            CompatMetricsCollector as MetricsCollector,
            CompatResourceSampler as ResourceSampler
        )
        
        # Create collector
        collector = MetricsCollector(tmp_path)
        
        # Record metrics
        collector.record("build.duration", 45.6)
        collector.record("test.count", 12.0, {"suite": "unit"})
        
        # Sample resources
        sampler = ResourceSampler(interval=0.1)
        sampler.start()
        # Simulate some work
        import time
        time.sleep(0.2)
        stats = sampler.stop()
        
        # Record resource stats
        for key, value in stats.items():
            collector.record(f"resource.{key}", value)
            
        # Flush metrics
        run_id = collector.flush("integration_test")
        
        # Validate output
        assert run_id == "builder_metrics"
        json_files = list(tmp_path.glob("*.json"))
        assert len(json_files) >= 1
```

#### 5.2 Regression Testing Strategy

**Test Migration Impact**:
```bash
# Run existing tests with new metrics system
python -m pytest tests/unit/test_core/ -k "metrics" -v

# Run builder-specific tests
python -m pytest tests/unit/ -k "builder" -v  

# Integration test with real builder usage
python panther_builder.py check --enable-metrics

# Validate metrics output format
python -c "
from panther.core.metrics.builder_compat import record, flush
record('test.migration', 42.0)
run_id = flush('migration_test')
print(f'Migration test successful: {run_id}')
"
```

#### 5.3 Performance Validation

**Benchmark Comparison**:
```python
# Test performance impact of unified system
import time
from panther.core.metrics.builder_compat import record

# Time 1000 metric recordings
start = time.time()
for i in range(1000):
    record(f"perf.test.{i}", float(i))
duration = time.time() - start

print(f"1000 recordings in {duration:.3f}s ({1000/duration:.0f} rec/sec)")
# Should be comparable to old system performance
```

## Implementation Steps

### Step 1: Preparation (Day 1)
1. **Backup original files**
2. **Run existing tests** to establish baseline
3. **Analyze current builder_metrics usage** across codebase
4. **Document API mapping** between old and new systems

### Step 2: Core System Enhancement (Day 2)
1. **Add builder compatibility methods** to MetricsCollector
2. **Enhance ResourceMonitor** with builder-compatible interface
3. **Add global collector functions** for backward compatibility
4. **Test enhanced core system** in isolation

### Step 3: Compatibility Layer Creation (Day 3)
1. **Create builder_compat.py** with drop-in replacement classes
2. **Implement CompatMetricsCollector** with exact API matching
3. **Implement CompatResourceSampler** with sampling interface
4. **Implement CompatJSONLinesStorage** with file format compatibility
5. **Test compatibility layer** thoroughly

### Step 4: Migration and Cleanup (Day 4)
1. **Update import statements** across codebase
2. **Replace builder_metrics references** with core metrics
3. **Update __init__.py files** for proper exports
4. **Remove builder_metrics directory** and files
5. **Test migrated codebase** functionality

### Step 5: Validation and Optimization (Day 5)
1. **Run comprehensive test suite** including integration tests
2. **Validate metrics output** matches expected formats
3. **Performance testing** to ensure no regressions
4. **Documentation updates** for unified metrics system
5. **Final cleanup** and code review

## Risk Mitigation

### Low-Risk Factors
- **Compatibility layer**: Maintains exact API compatibility
- **Comprehensive testing**: Full test coverage for compatibility
- **Gradual migration**: Phased approach minimizes risk

### Potential Issues & Solutions

1. **API Behavioral Differences**:
   - **Risk**: Subtle differences in metric recording behavior
   - **Solution**: Extensive compatibility testing and behavioral matching
   - **Check**: Validate metric output formats match exactly

2. **Performance Impact**:
   - **Risk**: Core system might be slower than simple builder system
   - **Solution**: Performance benchmarking and optimization
   - **Check**: Measure recording rates before/after migration

3. **File Format Changes**:
   - **Risk**: Storage format differences might break existing tooling
   - **Solution**: Maintain exact JSONL format compatibility
   - **Check**: Test reading existing metrics files with new system

4. **Threading Behavior**:
   - **Risk**: Core system uses more advanced threading
   - **Solution**: Ensure thread safety in compatibility layer
   - **Check**: Concurrent access testing

## Testing Strategy

### Unit Tests
```bash
# Test compatibility layer thoroughly
python -m pytest tests/unit/test_core/test_builder_metrics_compat.py -v

# Test core metrics enhancements
python -m pytest tests/unit/test_core/test_metrics_collector.py -v

# Test resource monitor compatibility
python -m pytest tests/unit/test_core/test_resource_monitor.py -v
```

### Integration Tests
```bash
# Test builder integration
python panther_builder.py check --enable-metrics

# Test CLI integration
python -m panther.cli metrics --export json

# Test pytest plugin compatibility (if used)
python -m pytest --enable-metrics tests/unit/test_simple.py
```

### Migration Validation
```bash
# Verify import migrations work
python -c "from panther.core.metrics.builder_compat import record, flush; record('test', 1.0); print('SUCCESS')"

# Verify storage compatibility
python scripts/validate_metrics_migration.py

# Verify no broken imports
python -m py_compile panther/**/*.py
```

## Expected Results

### Code Reduction
- **~800+ lines removed** from builder_metrics system
- **~200+ lines added** for compatibility layer
- **Net reduction: ~600+ lines** of duplicate code
- **7 duplicate files eliminated**

### API Improvements
- **Single metrics API** for all PANTHER components
- **Consistent method signatures** across systems
- **Advanced features available** to builder (phases, components, detailed monitoring)
- **Multiple export formats** (JSON, CSV, Prometheus) for builder metrics

### Performance Benefits
- **Reduced memory footprint** from eliminating duplicate classes
- **Better thread management** with unified collection system
- **More efficient resource monitoring** with advanced snapshots
- **Consolidated storage** reducing I/O overhead

### Maintainability Improvements
- **Single point of change** for metrics functionality
- **Unified testing strategy** for all metrics
- **Consistent error handling** across metrics operations
- **Better integration** between builder and experiment metrics

## Rollback Plan

If issues arise:

1. **Immediate**: Restore builder_metrics directory from backup
2. **Revert imports**: Use sed scripts to restore original import statements
3. **Remove compatibility layer**: Delete builder_compat.py
4. **Remove core enhancements**: Comment out added methods in core classes
5. **Validate**: Ensure system returns to original functionality

## Success Criteria

- [ ] All builder metrics functionality preserved
- [ ] Existing builder scripts work without modification
- [ ] No performance degradation (< 5% overhead)
- [ ] All tests pass including new compatibility tests
- [ ] Metrics output format unchanged for existing tools
- [ ] Resource monitoring provides same or better data
- [ ] File storage format maintains backward compatibility
- [ ] Memory usage reduced due to code consolidation

---

**Implementation Timeline**: 5 days  
**Files Modified**: 15+ files (migrations + new compatibility layer)  
**Lines of Code Impact**: -600+ lines (significant reduction)  
**Risk Level**: Medium (careful migration required)  
**Rollback Complexity**: Low (well-defined restoration process)