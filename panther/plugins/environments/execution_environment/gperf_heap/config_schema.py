from dataclasses import dataclass, field
from panther.plugins.environments.execution_environment.config_schema import (
    ExecutionEnvironmentConfig,
)


@dataclass
class GperfHeapConfig(ExecutionEnvironmentConfig):
    """
    Configuration for gperf command generation.
    """

    input_file: str | None = None  # Input file for gperf
    output_file: str | None = None  # Output file for gperf
    language: str = "C"  # Language of the output, default is "C"
    keyword_only: bool = False  # Generate keyword-only lookup
    readonly_tables: bool = False  # Generate read-only tables
    switch: bool = False  # Generate switch statements
    compare_strncmp: bool = False  # Use strncmp for comparisons
    hash_function: str | None = None  # Hash function to use
    compare_function: str | None = None  # Comparison function to use
    includes: list[str] = field(default_factory=list)  # List of includes to add
    other_flags: list[str] = field(default_factory=list)  # Other gperf flags
