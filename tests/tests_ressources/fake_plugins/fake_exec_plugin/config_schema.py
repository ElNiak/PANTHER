from typing import List, Optional

from pydantic import Field

from panther.config.core.models.environment import ExecutionEnvironmentConfig


class GperfCpuConfig(ExecutionEnvironmentConfig):
    """Configuration for gperf command generation."""

    input_file: Optional[str] = Field(default=None, description="Input file for gperf")
    output_file: Optional[str] = Field(
        default=None, description="Output file for gperf"
    )
    language: str = Field(default="C", description="Language of the output")
    keyword_only: bool = Field(
        default=False, description="Generate keyword-only lookup"
    )
    readonly_tables: bool = Field(
        default=False, description="Generate read-only tables"
    )
    switch: bool = Field(default=False, description="Generate switch statements")
    compare_strncmp: bool = Field(
        default=False, description="Use strncmp for comparisons"
    )
    hash_function: Optional[str] = Field(
        default=None, description="Hash function to use"
    )
    compare_function: Optional[str] = Field(
        default=None, description="Comparison function to use"
    )
    includes: List[str] = Field(
        default_factory=list, description="List of includes to add"
    )
    other_flags: List[str] = Field(
        default_factory=list, description="Other gperf flags"
    )
