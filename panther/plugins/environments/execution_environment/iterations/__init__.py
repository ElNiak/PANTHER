"""Iterative execution environment for repeated test runs.

Re-runs each test scenario a configurable number of times
to collect statistical data (mean, variance, percentiles)
for performance and reliability metrics.

Key features:
    - Configurable iteration count
    - Warm-up iterations excluded from results
    - Automatic statistical aggregation

See `IterationsConfig` for all configuration options.
"""
