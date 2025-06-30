"""
Execution Environment Test Suite

Comprehensive testing for PANTHER's execution environment plugins including:
- gperf_cpu: CPU performance profiling
- gperf_heap: Memory/heap profiling
- helgrind: Thread analysis with Valgrind
- iterations: Repeated execution runs
- memcheck: Memory error detection with Valgrind
- strace: System call tracing

Test Categories:
- Unit tests: Individual component testing
- Integration tests: Workflow and Docker integration
- Property-based tests: Robustness testing with Hypothesis
- Performance tests: Benchmarking and stress testing
"""
