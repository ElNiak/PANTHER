"""
PANTHER Results Processing and Analysis System

This package provides a comprehensive framework for collecting, processing, and analyzing
test results in the PANTHER protocol testing environment. It implements a flexible
chain-of-responsibility pattern for result handling with specialized processors for
different result types and storage backends.

## Architecture Overview

The results system implements a modular pipeline for result processing:

```mermaid
graph TD
    A[Test Execution] --> B[ResultCollector]
    B --> C[Result Handlers Chain]

    C --> D[LocalStorageHandler]
    C --> E[ValidationHandler]
    C --> F[ParserHandler]
    C --> G[StorageHandler]

    D --> H[File System Storage]
    E --> I[Result Validation]
    F --> J[Data Parsing]
    G --> K[Database Storage]

    B --> L[Result Registry]
    L --> M[Handler Mapping]
```

## Core Components

### 1. **ResultCollector**
Central orchestrator that coordinates result processing across registered handlers:
- **Handler Registration**: Maps result types to specific processing chains
- **Result Routing**: Dispatches results to appropriate handlers based on type
- **Chain Coordination**: Manages the execution flow through handler chains
- **Error Handling**: Provides graceful error recovery and logging

### 2. **ResultHandler (Abstract Base)**
Foundation for all result processing implementations using chain-of-responsibility:
- **Chain Management**: Links handlers together for sequential processing
- **Output Directory Management**: Creates and manages result storage directories
- **Logging Integration**: Structured logging for result processing activities
- **Extensible Interface**: Abstract base enabling custom handler implementations

### 3. **Specialized Result Handlers**
Domain-specific result processors for different data types and storage needs:

#### **LocalStorageHandler**
- File system-based result storage with organized directory structures
- Supports multiple file formats (JSON, text, binary)
- Automatic directory creation and permission management
- Efficient file naming and organization strategies

#### **ValidationHandler**
- Result data validation and integrity checking
- Schema validation for structured result data
- Data quality assessment and anomaly detection
- Validation reporting and error categorization

#### **ParserHandler**
- Multi-format result parsing and normalization
- Protocol-specific result interpretation (QUIC, HTTP, TCP, MINIP)
- Data transformation and structure standardization
- Format detection and automatic parser selection

#### **StorageHandler**
- Database and persistent storage integration
- Batch processing for high-throughput scenarios
- Transaction management and data consistency
- Query optimization and indexing strategies

## Key Features

- **Flexible Handler Chains**: Configurable processing pipelines with chain-of-responsibility
- **Type-Based Routing**: Automatic handler selection based on result type metadata
- **Extensible Architecture**: Easy addition of custom handlers and processors
- **Error Recovery**: Graceful handling of processing failures with detailed logging
- **Storage Abstraction**: Multiple storage backends with consistent interfaces
- **Protocol-Aware Processing**: Specialized handling for different protocol test results

## Usage Examples

```python
from panther.core.results import ResultCollector
from panther.core.results.result_handlers import (
    LocalStorageHandler, ValidationHandler, ParserHandler
)

# Initialize collector and register handlers
collector = ResultCollector()

# Set up processing chain for test results
validation_handler = ValidationHandler(output_dir, experiment_name)
parser_handler = ParserHandler(output_dir, experiment_name)
storage_handler = LocalStorageHandler(output_dir, experiment_name)

# Chain handlers together
validation_handler.set_next_handler(parser_handler)
parser_handler.set_next_handler(storage_handler)

# Register handler chain for specific result types
collector.register_handler("quic_test_result", validation_handler)
collector.register_handler("http_benchmark", validation_handler)

# Process results
result = {
    "type": "quic_test_result",
    "test_name": "handshake_performance",
    "metrics": {...},
    "timestamp": "2024-01-01T12:00:00Z"
}

collector.collect(result)
```

## Processing Pipeline

The results system follows a standardized processing flow:

1. **Result Ingestion**: Tests produce structured result data with type metadata
2. **Handler Selection**: ResultCollector routes to registered handlers by type
3. **Chain Execution**: Handlers process results sequentially through the chain
4. **Validation**: Data integrity and schema validation
5. **Parsing**: Format normalization and structure standardization
6. **Storage**: Persistent storage with appropriate backends
7. **Error Handling**: Graceful recovery and detailed error reporting

## Performance Characteristics

- **Processing Latency**: ~10-50ms per result depending on handler chain complexity
- **Throughput**: ~100-1000 results/second for typical handler configurations
- **Memory Usage**: O(1) for streaming processing, O(n) for batch operations
- **Storage Efficiency**: Optimized file organization and compression strategies

This results system enables comprehensive test data management, analysis, and long-term
storage for complex protocol testing scenarios with high reliability and performance.
"""

# Import key modules for easier access
from . import result_collector, result_handler
from .result_handlers import *

# Define the public API
__all__ = ["result_collector", "result_handler"]
