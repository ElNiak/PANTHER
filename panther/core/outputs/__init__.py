"""
Output Management System

This module provides a comprehensive framework for collecting, aggregating, and managing outputs
from PANTHER execution environments during protocol testing.

## Architecture Overview

The output management system implements a multi-layered collection strategy:

1. **Output Collection Interface (`IOutputCollector`)**: Defines the contract for execution
   environments to expose their generated artifacts (logs, traces, profiles, etc.)

2. **Output Aggregation (`OutputAggregator`)**: Orchestrates collection from multiple execution
   environments and prepares data for tester analysis with event-driven progress tracking

3. **Environment Mixins (`StandardOutputCollectorMixin`)**: Provides standardized output
   collection behaviors with container-to-host path mapping and deferred discovery

4. **Phase Collection Standards (`PhaseCollectionStandard`)**: Centralized pattern definitions
   for protocol-specific, service-type-specific, and language-specific output files

## Key Features

- **Multi-Environment Support**: Collects outputs from Docker Compose, localhost containers,
  and Shadow NS simulation environments
- **Protocol-Aware Collection**: QUIC, HTTP, TCP, and MINIP protocol-specific artifact patterns
- **Service-Type Patterns**: Distinguishes between tester and IUT (Implementation Under Test) outputs
- **Language-Specific Artifacts**: C/C++, Rust, Python, Go compilation and runtime outputs
- **Container Path Mapping**: Intelligent resolution of container paths to host filesystem paths
- **Deferred Discovery**: Fallback scanning for output files not registered during initialization
- **Event Emission**: Progress tracking through environment event emitters

## Usage Example

```python
from panther.core.outputs import OutputAggregator
from panther.core.events.environment.emitter import EnvironmentEventEmitter

# Initialize aggregator
emitter = EnvironmentEventEmitter()
aggregator = OutputAggregator(experiment_dir, emitter)

# Collect from environments implementing IOutputCollector
collected = aggregator.collect_from_environments(environments)

# Organize for tester analysis
organized = aggregator.prepare_for_testers(collected)
```

This system ensures comprehensive artifact collection across diverse protocol testing scenarios
while maintaining consistency and discoverability for analysis workflows.
"""

from .output_aggregator import OutputAggregator

__all__ = ["OutputAggregator"]
