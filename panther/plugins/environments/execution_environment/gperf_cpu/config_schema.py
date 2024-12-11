from dataclasses import dataclass, field
import os
from typing import List, Optional
from panther.plugins.environments.execution_environment.config_schema import ExecutionEnvironmentConfig


@dataclass
class GperfCpuConfig(ExecutionEnvironmentConfig):
    """
    Configuration for gperf command generation.
    """
    input_file: Optional[str] = None   # Input file for gperf
    output_file: Optional[str] = None  # Output file for gperf
    language: str = "C"  # Language of the output, default is "C"
    keyword_only: bool = False  # Generate keyword-only lookup
    readonly_tables: bool = False  # Generate read-only tables
    switch: bool = False  # Generate switch statements
    compare_strncmp: bool = False  # Use strncmp for comparisons
    hash_function: Optional[str] = None  # Hash function to use
    compare_function: Optional[str] = None  # Comparison function to use
    includes: List[str] = field(default_factory=list)  # List of includes to add
    other_flags: List[str] = field(default_factory=list)  # Other gperf flags

    