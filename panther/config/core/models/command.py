"""
Pydantic configuration models for command processor.

This module provides modern validation models using Pydantic for type safety
and configuration validation in the command processor.
"""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field, validator


class CommandProcessorConfig(BaseModel):
    """Configuration for command processor operations."""

    max_commands: int = Field(
        100, ge=1, le=1000, description="Maximum number of commands to process"
    )
    timeout_seconds: int = Field(
        60, ge=1, le=3600, description="Timeout for command processing in seconds"
    )
    allow_shell_operators: bool = Field(
        False, description="Whether to allow shell operators like &&, ||"
    )
    blocked_commands: List[str] = Field(
        default_factory=lambda: ["rm -rf", "dd if=", "mkfs"],
        description="List of dangerous command patterns to block",
    )
    log_commands: bool = Field(True, description="Whether to log processed commands")

    @validator("blocked_commands")
    def validate_blocked_commands(cls, v):
        """Ensure blocked commands list is not empty and contains valid patterns."""
        if not v:
            return ["rm -rf", "dd if=", "mkfs"]  # Default dangerous patterns
        return [cmd.strip() for cmd in v if cmd.strip()]


class ProcessingResult(BaseModel):
    """Result of command processing operations."""

    processed_commands: Dict[str, List[str]] = Field(
        ..., description="Dictionary of processed commands by type"
    )
    total_count: int = Field(
        ..., ge=0, description="Total number of commands processed"
    )
    processing_time: float = Field(
        ..., ge=0.0, description="Time taken to process commands in seconds"
    )
    success_count: int = Field(
        0, ge=0, description="Number of successfully processed commands"
    )
    error_count: int = Field(
        0, ge=0, description="Number of commands that failed processing"
    )

    @validator("total_count")
    def validate_total_count(cls, v, values):
        """Ensure total count matches actual processed commands."""
        if "processed_commands" in values:
            actual_count = sum(
                len(cmds) for cmds in values["processed_commands"].values()
            )
            if v != actual_count:
                raise ValueError(f"Total count {v} doesn't match actual {actual_count}")
        return v

    @validator("success_count")
    def validate_success_count(cls, v, values):
        """Ensure success count doesn't exceed total count."""
        if "total_count" in values and v > values["total_count"]:
            raise ValueError("Success count cannot exceed total count")
        return v


class CommandValidationConfig(BaseModel):
    """Configuration for command validation."""

    strict_mode: bool = Field(
        False, description="Whether to use strict validation mode"
    )
    allow_empty_commands: bool = Field(
        False, description="Whether to allow empty command strings"
    )
    max_command_length: int = Field(
        1000, ge=1, le=10000, description="Maximum length of individual commands"
    )
    validate_shell_syntax: bool = Field(
        True, description="Whether to validate shell command syntax"
    )
    require_absolute_paths: bool = Field(
        False, description="Whether to require absolute paths for file operations"
    )
