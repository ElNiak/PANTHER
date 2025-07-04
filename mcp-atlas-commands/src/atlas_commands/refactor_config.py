"""
Configuration for ATLAS MCP server refactoring.

This module provides feature flags and configuration options
to safely roll out the registry-based architecture.
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class RefactorConfig:
    """Configuration for the MCP server refactoring."""
    
    # Feature flags for gradual rollout
    enable_tool_registry: bool = True  # Phase 3: Registry enabled
    enable_consistent_error_handling: bool = True  # Phase 3: Error handling enabled
    enable_logging_improvements: bool = True
    enable_memory_integration: bool = True  # Phase 3: Memory integration enabled
    
    # Legacy settings (removed in Phase 3)
    # Note: Legacy handler system has been completely removed
    
    # Performance settings (configurable via environment)
    max_concurrent_tools: int = 10  # Will be overridden in from_env()
    tool_timeout: float = 60.0  # Will be overridden in from_env()
    
    # Debug settings
    debug_tool_dispatch: bool = False
    log_tool_performance: bool = False
    
    @classmethod
    def from_env(cls) -> 'RefactorConfig':
        """Create configuration from environment variables."""
        return cls(
            enable_tool_registry=os.getenv('ATLAS_ENABLE_TOOL_REGISTRY', 'true').lower() == 'true',
            enable_consistent_error_handling=os.getenv('ATLAS_ENABLE_ERROR_HANDLING', 'true').lower() == 'true',
            enable_logging_improvements=os.getenv('ATLAS_ENABLE_LOGGING', 'true').lower() == 'true',
            enable_memory_integration=os.getenv('ATLAS_ENABLE_MEMORY', 'true').lower() == 'true',
            max_concurrent_tools=int(os.getenv('ATLAS_MAX_CONCURRENT_TOOLS', '10')),
            tool_timeout=float(os.getenv('ATLAS_TOOL_TIMEOUT', '60.0')),
            debug_tool_dispatch=os.getenv('ATLAS_DEBUG_DISPATCH', 'false').lower() == 'true',
            log_tool_performance=os.getenv('ATLAS_LOG_PERFORMANCE', 'false').lower() == 'true',
        )


# Global configuration instance
config = RefactorConfig.from_env()


def get_config() -> RefactorConfig:
    """Get the current refactor configuration."""
    return config


def update_config(**kwargs) -> None:
    """Update configuration at runtime."""
    global config
    for key, value in kwargs.items():
        if hasattr(config, key):
            setattr(config, key, value)
        else:
            raise ValueError(f"Unknown config key: {key}")


# Phase Migration History (for reference):
# Phase 0: Safe preparations with logging improvements
# Phase 1: Tool registry with legacy fallback  
# Phase 2: Full registry, no fallback
# Phase 3: Complete migration, all 58 tools in registry pattern ✅ CURRENT