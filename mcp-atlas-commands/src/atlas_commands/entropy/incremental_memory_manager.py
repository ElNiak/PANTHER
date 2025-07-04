"""Incremental memory manager with entropy-triggered processing.

Manages memory operations incrementally based on entropy analysis,
preventing token explosion through intelligent chunking and batching.
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional, AsyncIterator, Union, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import uuid

from .entropy_processor import EntropyProcessor, EntropyAnalysis, ProcessingMode, ProcessingTrigger

logger = logging.getLogger(__name__)


class ChunkingStrategy(Enum):
    """Strategies for chunking memory operations."""
    ENTROPY_BASED = "entropy_based"
    SIZE_BASED = "size_based"
    SEMANTIC_BASED = "semantic_based"
    HYBRID = "hybrid"
    ADAPTIVE = "adaptive"


class MemoryOperationType(Enum):
    """Types of memory operations."""
    SEARCH = "search"
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    BULK_QUERY = "bulk_query"
    RELATIONSHIP_QUERY = "relationship_query"
    GRAPH_TRAVERSAL = "graph_traversal"


@dataclass
class MemoryChunk:
    """Represents a chunk of memory data for incremental processing."""
    chunk_id: str
    content: str
    chunk_index: int
    total_chunks: int
    entropy_score: float
    processing_mode: ProcessingMode
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Processing state
    processed: bool = False
    processing_start_time: Optional[datetime] = None
    processing_end_time: Optional[datetime] = None
    processing_result: Optional[Any] = None
    processing_error: Optional[str] = None
    
    def __post_init__(self):
        if not self.chunk_id:
            self.chunk_id = str(uuid.uuid4())[:8]
    
    @property
    def processing_duration(self) -> Optional[timedelta]:
        """Get chunk processing duration."""
        if self.processing_start_time and self.processing_end_time:
            return self.processing_end_time - self.processing_start_time
        return None
    
    @property
    def is_high_entropy(self) -> bool:
        """Check if chunk has high entropy."""
        return self.entropy_score > 0.7
    
    @property
    def size_bytes(self) -> int:
        """Get chunk size in bytes."""
        return len(self.content.encode('utf-8'))


@dataclass
class IncrementalOperation:
    """Represents an incremental memory operation."""
    operation_id: str
    operation_type: MemoryOperationType
    chunks: List[MemoryChunk]
    chunking_strategy: ChunkingStrategy
    total_entropy: float
    estimated_processing_time: timedelta
    
    # Progress tracking
    chunks_processed: int = 0
    chunks_failed: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    def __post_init__(self):
        if not self.operation_id:
            self.operation_id = str(uuid.uuid4())[:8]
    
    @property
    def progress_percentage(self) -> float:
        """Get operation progress as percentage."""
        if not self.chunks:
            return 100.0
        return (self.chunks_processed / len(self.chunks)) * 100
    
    @property
    def is_complete(self) -> bool:
        """Check if operation is complete."""
        return self.chunks_processed + self.chunks_failed >= len(self.chunks)
    
    @property
    def success_rate(self) -> float:
        """Get success rate for processed chunks."""
        total_processed = self.chunks_processed + self.chunks_failed
        if total_processed == 0:
            return 100.0
        return (self.chunks_processed / total_processed) * 100


class IncrementalMemoryManager:
    """Manages memory operations incrementally with entropy-triggered processing.
    
    Features:
    1. Entropy-based chunking for optimal processing
    2. Adaptive batching based on information density
    3. Streaming processing for high-entropy content
    4. Intelligent caching and memoization
    5. Progress tracking and error recovery
    """
    
    def __init__(self,
                 entropy_processor: Optional[EntropyProcessor] = None,
                 max_concurrent_operations: int = 5,
                 default_chunk_size: int = 1000,
                 enable_caching: bool = True):
        self.entropy_processor = entropy_processor or EntropyProcessor()
        self.max_concurrent_operations = max_concurrent_operations
        self.default_chunk_size = default_chunk_size
        self.enable_caching = enable_caching
        
        # Active operations tracking
        self.active_operations: Dict[str, IncrementalOperation] = {}
        self.operation_history: List[Dict[str, Any]] = []
        
        # Caching and memoization
        self.chunk_cache: Dict[str, Any] = {}
        self.entropy_cache: Dict[str, EntropyAnalysis] = {}
        
        # Performance metrics
        self.metrics = {
            'total_operations': 0,
            'total_chunks_processed': 0,
            'average_chunk_processing_time': 0.0,
            'entropy_cache_hits': 0,
            'chunk_cache_hits': 0,
            'operations_by_strategy': {},
            'operations_by_type': {}
        }
        
        # Adaptive parameters
        self.adaptive_chunk_sizes: Dict[str, int] = {}  # Per operation type
        self.processing_time_estimates: Dict[ProcessingMode, float] = {
            ProcessingMode.INCREMENTAL: 0.1,
            ProcessingMode.BATCH: 0.05,
            ProcessingMode.STREAMING: 0.02,
            ProcessingMode.COMPRESSED: 0.03,
            ProcessingMode.FILTERED: 0.01,
            ProcessingMode.BYPASSED: 0.001
        }
    
    async def process_memory_operation(self,
                                     content: Union[str, List[str]],
                                     operation_type: MemoryOperationType,
                                     context: Dict[str, Any] = None,
                                     chunking_strategy: ChunkingStrategy = ChunkingStrategy.ADAPTIVE) -> AsyncIterator[Dict[str, Any]]:
        """Process memory operation incrementally with entropy analysis.
        
        Args:
            content: Content to process (string or list of strings)
            operation_type: Type of memory operation
            context: Additional context for processing
            chunking_strategy: Strategy for chunking content
            
        Yields:
            Processing results for each chunk
        """
        context = context or {}
        
        # Check concurrent operation limit
        if len(self.active_operations) >= self.max_concurrent_operations:
            raise RuntimeError(f"Maximum concurrent operations ({self.max_concurrent_operations}) exceeded")
        
        # Prepare content for processing
        if isinstance(content, list):
            combined_content = '\n'.join(str(item) for item in content)
        else:
            combined_content = str(content)
        
        # Analyze entropy and determine processing strategy
        entropy_analysis = await self._analyze_content_entropy(combined_content, context)
        
        # Create chunks based on entropy analysis
        chunks = await self._create_chunks(
            combined_content, 
            entropy_analysis, 
            chunking_strategy, 
            operation_type
        )
        
        # Create incremental operation
        operation = IncrementalOperation(
            operation_id=f"incr_{operation_type.value}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            operation_type=operation_type,
            chunks=chunks,
            chunking_strategy=chunking_strategy,
            total_entropy=entropy_analysis.content_entropy,
            estimated_processing_time=self._estimate_processing_time(chunks, entropy_analysis)
        )
        
        operation.start_time = datetime.now()
        self.active_operations[operation.operation_id] = operation
        
        try:
            logger.info(f"Starting incremental operation {operation.operation_id}: {len(chunks)} chunks, strategy={chunking_strategy.value}")
            
            # Process chunks based on entropy analysis recommendations
            if entropy_analysis.recommended_mode == ProcessingMode.STREAMING:
                async for result in self._process_streaming(operation, context):
                    yield result
            elif entropy_analysis.recommended_mode == ProcessingMode.BATCH:
                async for result in self._process_batch(operation, context):
                    yield result
            elif entropy_analysis.recommended_mode == ProcessingMode.INCREMENTAL:
                async for result in self._process_incremental(operation, context):
                    yield result
            else:
                # Compressed/filtered/bypassed modes
                async for result in self._process_optimized(operation, context, entropy_analysis.recommended_mode):
                    yield result
            
        except Exception as e:
            logger.error(f"Incremental operation {operation.operation_id} failed: {e}")
            yield {
                'operation_id': operation.operation_id,
                'status': 'error',
                'error': str(e),
                'chunks_processed': operation.chunks_processed,
                'total_chunks': len(operation.chunks)
            }
        
        finally:
            # Finalize operation
            operation.end_time = datetime.now()
            await self._finalize_operation(operation)
    
    async def _analyze_content_entropy(self, content: str, context: Dict[str, Any]) -> EntropyAnalysis:
        """Analyze content entropy with caching."""
        # Create cache key
        cache_key = hash((content[:100], json.dumps(context, sort_keys=True)))
        
        if self.enable_caching and cache_key in self.entropy_cache:
            self.metrics['entropy_cache_hits'] += 1
            return self.entropy_cache[cache_key]
        
        # Perform entropy analysis
        analysis = self.entropy_processor.analyze_content_entropy(content, context)
        
        # Cache result
        if self.enable_caching:
            self.entropy_cache[cache_key] = analysis
            
            # Limit cache size
            if len(self.entropy_cache) > 1000:
                # Remove oldest entries
                oldest_keys = list(self.entropy_cache.keys())[:100]
                for key in oldest_keys:
                    del self.entropy_cache[key]
        
        return analysis
    
    async def _create_chunks(self,
                           content: str,
                           entropy_analysis: EntropyAnalysis,
                           chunking_strategy: ChunkingStrategy,
                           operation_type: MemoryOperationType) -> List[MemoryChunk]:
        """Create chunks based on entropy analysis and strategy."""
        chunks = []
        
        if chunking_strategy == ChunkingStrategy.ENTROPY_BASED:
            chunk_positions = entropy_analysis.chunk_suggestions
        elif chunking_strategy == ChunkingStrategy.SIZE_BASED:
            chunk_size = self._get_adaptive_chunk_size(operation_type)
            chunk_positions = self._create_size_based_chunks(content, chunk_size)
        elif chunking_strategy == ChunkingStrategy.SEMANTIC_BASED:
            chunk_positions = await self._create_semantic_chunks(content)
        elif chunking_strategy == ChunkingStrategy.HYBRID:
            chunk_positions = await self._create_hybrid_chunks(content, entropy_analysis)
        else:  # ADAPTIVE
            chunk_positions = await self._create_adaptive_chunks(content, entropy_analysis, operation_type)
        
        # Create MemoryChunk objects
        for i, (start, end) in enumerate(chunk_positions):
            chunk_content = content[start:end]
            
            # Calculate chunk-specific entropy
            chunk_entropy_analysis = await self._analyze_content_entropy(chunk_content, {})
            
            chunk = MemoryChunk(
                chunk_id=f"chunk_{i:03d}",
                content=chunk_content,
                chunk_index=i,
                total_chunks=len(chunk_positions),
                entropy_score=chunk_entropy_analysis.content_entropy,
                processing_mode=chunk_entropy_analysis.recommended_mode,
                metadata={
                    'start_position': start,
                    'end_position': end,
                    'entropy_analysis': chunk_entropy_analysis,
                    'chunking_strategy': chunking_strategy.value
                }
            )
            
            chunks.append(chunk)
        
        return chunks
    
    def _create_size_based_chunks(self, content: str, chunk_size: int) -> List[Tuple[int, int]]:
        """Create size-based chunks with overlap."""
        chunks = []
        overlap = min(50, chunk_size // 10)
        
        start = 0
        while start < len(content):
            end = min(start + chunk_size, len(content))
            chunks.append((start, end))
            
            if end >= len(content):
                break
            
            start = end - overlap
        
        return chunks
    
    async def _create_semantic_chunks(self, content: str) -> List[Tuple[int, int]]:
        """Create semantically coherent chunks."""
        # Simple semantic chunking based on paragraphs and sentences
        chunks = []
        
        # Split by paragraphs first
        paragraphs = content.split('\n\n')
        current_start = 0
        current_chunk = ""
        chunk_start = 0
        
        for paragraph in paragraphs:
            if len(current_chunk) + len(paragraph) > self.default_chunk_size and current_chunk:
                # Finalize current chunk
                chunks.append((chunk_start, current_start))
                chunk_start = current_start
                current_chunk = paragraph
            else:
                current_chunk += paragraph + "\n\n"
            
            current_start += len(paragraph) + 2  # +2 for \n\n
        
        # Add final chunk
        if current_chunk:
            chunks.append((chunk_start, len(content)))
        
        return chunks if chunks else [(0, len(content))]
    
    async def _create_hybrid_chunks(self, content: str, entropy_analysis: EntropyAnalysis) -> List[Tuple[int, int]]:
        """Create chunks using hybrid strategy."""
        # Combine entropy-based and semantic chunking
        entropy_chunks = entropy_analysis.chunk_suggestions
        semantic_chunks = await self._create_semantic_chunks(content)
        
        # Merge strategies by taking the more granular chunking in high-entropy regions
        combined_chunks = []
        
        for entropy_start, entropy_end in entropy_chunks:
            # Find overlapping semantic chunks
            overlapping_semantic = [
                (s, e) for s, e in semantic_chunks
                if not (e <= entropy_start or s >= entropy_end)
            ]
            
            if overlapping_semantic:
                # Use semantic boundaries within entropy chunk
                for sem_start, sem_end in overlapping_semantic:
                    actual_start = max(entropy_start, sem_start)
                    actual_end = min(entropy_end, sem_end)
                    if actual_start < actual_end:
                        combined_chunks.append((actual_start, actual_end))
            else:
                # Use entropy chunk as-is
                combined_chunks.append((entropy_start, entropy_end))
        
        # Remove overlaps and sort
        combined_chunks = sorted(set(combined_chunks))
        return combined_chunks if combined_chunks else [(0, len(content))]
    
    async def _create_adaptive_chunks(self,
                                    content: str,
                                    entropy_analysis: EntropyAnalysis,
                                    operation_type: MemoryOperationType) -> List[Tuple[int, int]]:
        """Create chunks using adaptive strategy based on content and operation type."""
        # Choose strategy based on content characteristics and operation type
        if entropy_analysis.content_entropy > 0.8:
            # High entropy - use entropy-based chunking
            return entropy_analysis.chunk_suggestions
        elif operation_type in [MemoryOperationType.SEARCH, MemoryOperationType.RELATIONSHIP_QUERY]:
            # Search operations benefit from semantic chunking
            return await self._create_semantic_chunks(content)
        elif ProcessingTrigger.INFORMATION_OVERFLOW in entropy_analysis.processing_triggers:
            # Information overflow - aggressive size-based chunking
            small_chunk_size = self.default_chunk_size // 2
            return self._create_size_based_chunks(content, small_chunk_size)
        else:
            # Default to hybrid approach
            return await self._create_hybrid_chunks(content, entropy_analysis)
    
    def _get_adaptive_chunk_size(self, operation_type: MemoryOperationType) -> int:
        """Get adaptive chunk size based on operation type and performance history."""
        if operation_type.value in self.adaptive_chunk_sizes:
            return self.adaptive_chunk_sizes[operation_type.value]
        
        # Default sizes by operation type
        default_sizes = {
            MemoryOperationType.SEARCH: 800,
            MemoryOperationType.CREATE: 1200,
            MemoryOperationType.UPDATE: 1000,
            MemoryOperationType.DELETE: 500,
            MemoryOperationType.BULK_QUERY: 1500,
            MemoryOperationType.RELATIONSHIP_QUERY: 600,
            MemoryOperationType.GRAPH_TRAVERSAL: 400
        }
        
        return default_sizes.get(operation_type, self.default_chunk_size)
    
    def _estimate_processing_time(self, chunks: List[MemoryChunk], entropy_analysis: EntropyAnalysis) -> timedelta:
        """Estimate total processing time for operation."""
        total_time = 0.0
        
        for chunk in chunks:
            mode_time = self.processing_time_estimates.get(chunk.processing_mode, 0.1)
            entropy_factor = 1.0 + chunk.entropy_score  # Higher entropy takes longer
            size_factor = chunk.size_bytes / 1000  # Time increases with size
            
            chunk_time = mode_time * entropy_factor * size_factor
            total_time += chunk_time
        
        return timedelta(seconds=total_time)
    
    async def _process_streaming(self, operation: IncrementalOperation, context: Dict[str, Any]) -> AsyncIterator[Dict[str, Any]]:
        """Process chunks in streaming mode."""
        for chunk in operation.chunks:
            try:
                chunk.processing_start_time = datetime.now()
                
                # Simulate processing with entropy-based delay
                processing_delay = 0.01 + (chunk.entropy_score * 0.05)
                await asyncio.sleep(processing_delay)
                
                # Process chunk
                result = await self._process_single_chunk(chunk, context)
                
                chunk.processing_end_time = datetime.now()
                chunk.processed = True
                chunk.processing_result = result
                operation.chunks_processed += 1
                
                yield {
                    'operation_id': operation.operation_id,
                    'chunk_id': chunk.chunk_id,
                    'chunk_index': chunk.chunk_index,
                    'status': 'completed',
                    'result': result,
                    'progress': operation.progress_percentage,
                    'processing_mode': 'streaming'
                }
                
            except Exception as e:
                chunk.processing_end_time = datetime.now()
                chunk.processing_error = str(e)
                operation.chunks_failed += 1
                
                yield {
                    'operation_id': operation.operation_id,
                    'chunk_id': chunk.chunk_id,
                    'chunk_index': chunk.chunk_index,
                    'status': 'error',
                    'error': str(e),
                    'progress': operation.progress_percentage,
                    'processing_mode': 'streaming'
                }
    
    async def _process_batch(self, operation: IncrementalOperation, context: Dict[str, Any]) -> AsyncIterator[Dict[str, Any]]:
        """Process chunks in batch mode."""
        batch_size = min(5, max(2, len(operation.chunks) // 4))  # Adaptive batch size
        
        for i in range(0, len(operation.chunks), batch_size):
            batch = operation.chunks[i:i + batch_size]
            batch_results = []
            
            # Process batch concurrently
            tasks = [self._process_single_chunk(chunk, context) for chunk in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for chunk, result in zip(batch, results):
                chunk.processing_end_time = datetime.now()
                
                if isinstance(result, Exception):
                    chunk.processing_error = str(result)
                    operation.chunks_failed += 1
                    status = 'error'
                else:
                    chunk.processed = True
                    chunk.processing_result = result
                    operation.chunks_processed += 1
                    status = 'completed'
                
                batch_results.append({
                    'chunk_id': chunk.chunk_id,
                    'chunk_index': chunk.chunk_index,
                    'status': status,
                    'result': result if not isinstance(result, Exception) else None,
                    'error': str(result) if isinstance(result, Exception) else None
                })
            
            yield {
                'operation_id': operation.operation_id,
                'batch_index': i // batch_size,
                'batch_results': batch_results,
                'progress': operation.progress_percentage,
                'processing_mode': 'batch'
            }
    
    async def _process_incremental(self, operation: IncrementalOperation, context: Dict[str, Any]) -> AsyncIterator[Dict[str, Any]]:
        """Process chunks incrementally with adaptive pacing."""
        for i, chunk in enumerate(operation.chunks):
            try:
                chunk.processing_start_time = datetime.now()
                
                # Adaptive delay based on entropy and system load
                adaptive_delay = self._calculate_adaptive_delay(chunk, i, len(operation.chunks))
                if adaptive_delay > 0:
                    await asyncio.sleep(adaptive_delay)
                
                result = await self._process_single_chunk(chunk, context)
                
                chunk.processing_end_time = datetime.now()
                chunk.processed = True
                chunk.processing_result = result
                operation.chunks_processed += 1
                
                # Update adaptive parameters based on performance
                await self._update_adaptive_parameters(chunk, operation)
                
                yield {
                    'operation_id': operation.operation_id,
                    'chunk_id': chunk.chunk_id,
                    'chunk_index': chunk.chunk_index,
                    'status': 'completed',
                    'result': result,
                    'progress': operation.progress_percentage,
                    'processing_mode': 'incremental',
                    'adaptive_delay': adaptive_delay
                }
                
            except Exception as e:
                chunk.processing_end_time = datetime.now()
                chunk.processing_error = str(e)
                operation.chunks_failed += 1
                
                yield {
                    'operation_id': operation.operation_id,
                    'chunk_id': chunk.chunk_id,
                    'chunk_index': chunk.chunk_index,
                    'status': 'error',
                    'error': str(e),
                    'progress': operation.progress_percentage,
                    'processing_mode': 'incremental'
                }
    
    async def _process_optimized(self,
                               operation: IncrementalOperation,
                               context: Dict[str, Any],
                               mode: ProcessingMode) -> AsyncIterator[Dict[str, Any]]:
        """Process chunks in optimized modes (compressed/filtered/bypassed)."""
        if mode == ProcessingMode.BYPASSED:
            # Minimal processing for low-entropy content
            for chunk in operation.chunks:
                chunk.processed = True
                operation.chunks_processed += 1
                
                yield {
                    'operation_id': operation.operation_id,
                    'chunk_id': chunk.chunk_id,
                    'status': 'bypassed',
                    'result': {'content': chunk.content[:100] + '...'},
                    'progress': operation.progress_percentage,
                    'processing_mode': 'bypassed'
                }
        else:
            # Compressed or filtered processing
            for chunk in operation.chunks:
                try:
                    # Optimized processing
                    if mode == ProcessingMode.COMPRESSED:
                        result = await self._process_compressed_chunk(chunk, context)
                    else:  # FILTERED
                        result = await self._process_filtered_chunk(chunk, context)
                    
                    chunk.processed = True
                    chunk.processing_result = result
                    operation.chunks_processed += 1
                    
                    yield {
                        'operation_id': operation.operation_id,
                        'chunk_id': chunk.chunk_id,
                        'status': 'completed',
                        'result': result,
                        'progress': operation.progress_percentage,
                        'processing_mode': mode.value
                    }
                    
                except Exception as e:
                    chunk.processing_error = str(e)
                    operation.chunks_failed += 1
                    
                    yield {
                        'operation_id': operation.operation_id,
                        'chunk_id': chunk.chunk_id,
                        'status': 'error',
                        'error': str(e),
                        'progress': operation.progress_percentage,
                        'processing_mode': mode.value
                    }
    
    async def _process_single_chunk(self, chunk: MemoryChunk, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single chunk."""
        # Check cache first
        cache_key = hash((chunk.content[:50], json.dumps(context, sort_keys=True)))
        
        if self.enable_caching and cache_key in self.chunk_cache:
            self.metrics['chunk_cache_hits'] += 1
            return self.chunk_cache[cache_key]
        
        # Simulate actual processing
        await asyncio.sleep(0.01)  # Base processing time
        
        result = {
            'chunk_id': chunk.chunk_id,
            'entropy_score': chunk.entropy_score,
            'size_bytes': chunk.size_bytes,
            'processing_mode': chunk.processing_mode.value,
            'content_summary': chunk.content[:100] + ('...' if len(chunk.content) > 100 else ''),
            'processed_at': datetime.now().isoformat()
        }
        
        # Cache result
        if self.enable_caching:
            self.chunk_cache[cache_key] = result
            
            # Limit cache size
            if len(self.chunk_cache) > 500:
                oldest_keys = list(self.chunk_cache.keys())[:50]
                for key in oldest_keys:
                    del self.chunk_cache[key]
        
        return result
    
    async def _process_compressed_chunk(self, chunk: MemoryChunk, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process chunk in compressed mode."""
        # Simulate compression processing
        await asyncio.sleep(0.005)
        
        return {
            'chunk_id': chunk.chunk_id,
            'compressed_size': len(chunk.content) // 2,  # Simulated compression
            'original_size': len(chunk.content),
            'compression_ratio': 0.5,
            'processing_mode': 'compressed'
        }
    
    async def _process_filtered_chunk(self, chunk: MemoryChunk, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process chunk in filtered mode."""
        # Simulate filtering processing
        await asyncio.sleep(0.003)
        
        # Extract key information only
        key_info = chunk.content[:50] if chunk.entropy_score > 0.5 else "Low information content"
        
        return {
            'chunk_id': chunk.chunk_id,
            'filtered_content': key_info,
            'information_retained': chunk.entropy_score,
            'processing_mode': 'filtered'
        }
    
    def _calculate_adaptive_delay(self, chunk: MemoryChunk, chunk_index: int, total_chunks: int) -> float:
        """Calculate adaptive delay based on chunk characteristics and system state."""
        base_delay = 0.01
        
        # Entropy-based adjustment
        entropy_factor = chunk.entropy_score * 0.02
        
        # Progress-based adjustment (slow down towards end for accuracy)
        progress = chunk_index / max(total_chunks, 1)
        progress_factor = progress * 0.01
        
        # System load simulation (would be actual load in production)
        load_factor = 0.005  # Simulated low load
        
        return base_delay + entropy_factor + progress_factor + load_factor
    
    async def _update_adaptive_parameters(self, chunk: MemoryChunk, operation: IncrementalOperation):
        """Update adaptive parameters based on chunk processing performance."""
        if chunk.processing_duration:
            processing_time = chunk.processing_duration.total_seconds()
            
            # Update processing time estimates
            mode_avg = self.processing_time_estimates.get(chunk.processing_mode, 0.1)
            # Exponential moving average
            self.processing_time_estimates[chunk.processing_mode] = (mode_avg * 0.9) + (processing_time * 0.1)
            
            # Update adaptive chunk sizes
            operation_type = operation.operation_type.value
            if processing_time > 0.2:  # Too slow, reduce chunk size
                current_size = self.adaptive_chunk_sizes.get(operation_type, self.default_chunk_size)
                self.adaptive_chunk_sizes[operation_type] = max(500, int(current_size * 0.9))
            elif processing_time < 0.05:  # Too fast, can increase chunk size
                current_size = self.adaptive_chunk_sizes.get(operation_type, self.default_chunk_size)
                self.adaptive_chunk_sizes[operation_type] = min(2000, int(current_size * 1.1))
    
    async def _finalize_operation(self, operation: IncrementalOperation):
        """Finalize operation and update metrics."""
        # Calculate final metrics
        total_processing_time = 0.0
        successful_chunks = 0
        
        for chunk in operation.chunks:
            if chunk.processing_duration:
                total_processing_time += chunk.processing_duration.total_seconds()
            if chunk.processed:
                successful_chunks += 1
        
        # Update global metrics
        self.metrics['total_operations'] += 1
        self.metrics['total_chunks_processed'] += successful_chunks
        
        # Update average processing time
        if successful_chunks > 0:
            avg_chunk_time = total_processing_time / successful_chunks
            current_avg = self.metrics['average_chunk_processing_time']
            total_ops = self.metrics['total_operations']
            new_avg = ((current_avg * (total_ops - 1)) + avg_chunk_time) / total_ops
            self.metrics['average_chunk_processing_time'] = new_avg
        
        # Update strategy and type counters
        strategy_key = operation.chunking_strategy.value
        self.metrics['operations_by_strategy'][strategy_key] = \
            self.metrics['operations_by_strategy'].get(strategy_key, 0) + 1
        
        type_key = operation.operation_type.value
        self.metrics['operations_by_type'][type_key] = \
            self.metrics['operations_by_type'].get(type_key, 0) + 1
        
        # Store operation summary in history
        operation_summary = {
            'operation_id': operation.operation_id,
            'operation_type': operation.operation_type.value,
            'chunking_strategy': operation.chunking_strategy.value,
            'total_chunks': len(operation.chunks),
            'chunks_processed': operation.chunks_processed,
            'chunks_failed': operation.chunks_failed,
            'success_rate': operation.success_rate,
            'total_entropy': operation.total_entropy,
            'estimated_time': operation.estimated_processing_time.total_seconds(),
            'actual_time': (operation.end_time - operation.start_time).total_seconds() if operation.end_time and operation.start_time else None,
            'start_time': operation.start_time.isoformat() if operation.start_time else None,
            'end_time': operation.end_time.isoformat() if operation.end_time else None
        }
        
        self.operation_history.append(operation_summary)
        
        # Limit history size
        if len(self.operation_history) > 1000:
            self.operation_history = self.operation_history[-1000:]
        
        # Remove from active operations
        self.active_operations.pop(operation.operation_id, None)
        
        logger.info(f"Operation {operation.operation_id} finalized: {operation.success_rate:.1f}% success rate")
    
    def get_operation_status(self, operation_id: str) -> Optional[Dict[str, Any]]:
        """Get status of an active operation."""
        operation = self.active_operations.get(operation_id)
        if not operation:
            return None
        
        return {
            'operation_id': operation_id,
            'operation_type': operation.operation_type.value,
            'chunking_strategy': operation.chunking_strategy.value,
            'progress_percentage': operation.progress_percentage,
            'chunks_processed': operation.chunks_processed,
            'chunks_failed': operation.chunks_failed,
            'total_chunks': len(operation.chunks),
            'is_complete': operation.is_complete,
            'success_rate': operation.success_rate,
            'estimated_completion_time': operation.estimated_processing_time,
            'elapsed_time': (datetime.now() - operation.start_time).total_seconds() if operation.start_time else None
        }
    
    def get_incremental_metrics(self) -> Dict[str, Any]:
        """Get comprehensive metrics for incremental processing."""
        return {
            **self.metrics,
            'active_operations': len(self.active_operations),
            'cache_stats': {
                'entropy_cache_size': len(self.entropy_cache),
                'chunk_cache_size': len(self.chunk_cache),
                'entropy_cache_hits': self.metrics['entropy_cache_hits'],
                'chunk_cache_hits': self.metrics['chunk_cache_hits']
            },
            'adaptive_parameters': {
                'adaptive_chunk_sizes': self.adaptive_chunk_sizes,
                'processing_time_estimates': {k.value: v for k, v in self.processing_time_estimates.items()}
            },
            'operation_history_size': len(self.operation_history)
        }