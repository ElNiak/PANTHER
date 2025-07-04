"""Entropy-triggered incremental processing for memory operations.

Implements information-theoretic processing that triggers incremental
operations based on information entropy to prevent token explosion.
"""

from .entropy_processor import EntropyProcessor, EntropyThresholds, ProcessingTrigger
from .incremental_memory_manager import IncrementalMemoryManager, MemoryChunk, ChunkingStrategy

__all__ = [
    'EntropyProcessor',
    'EntropyThresholds', 
    'ProcessingTrigger',
    'IncrementalMemoryManager',
    'MemoryChunk',
    'ChunkingStrategy'
]