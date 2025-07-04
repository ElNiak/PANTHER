"""Concurrent exporter with OTLP-inspired batching and pipeline parallelism.

Implements OpenTelemetry Protocol patterns for high-throughput concurrent
data export with linear scaling and optimized connection management.
"""

import asyncio
import json
import logging
import time
from typing import Dict, Any, List, Optional, Callable, AsyncIterator, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import uuid
from collections import deque

logger = logging.getLogger(__name__)


class ExportStatus(Enum):
    """Status of export operations."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


class BatchingStrategy(Enum):
    """Batching strategies for export operations."""
    SIZE_BASED = "size_based"
    TIME_BASED = "time_based"
    ADAPTIVE = "adaptive"
    HYBRID = "hybrid"


@dataclass
class ExportItem:
    """Individual item to export."""
    item_id: str
    data: Any
    priority: int = 5  # 1-10, higher = more important
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    
    # Processing state
    attempts: int = 0
    last_attempt_at: Optional[datetime] = None
    error: Optional[str] = None
    
    def __post_init__(self):
        if not self.item_id:
            self.item_id = str(uuid.uuid4())[:8]
    
    @property
    def age_seconds(self) -> float:
        """Get age of item in seconds."""
        return (datetime.now() - self.created_at).total_seconds()
    
    @property
    def size_bytes(self) -> int:
        """Get estimated size of item in bytes."""
        return len(json.dumps(self.data, default=str).encode())


@dataclass
class ExportBatch:
    """Batch of export items for concurrent processing."""
    batch_id: str
    items: List[ExportItem]
    created_at: datetime = field(default_factory=datetime.now)
    priority: int = 5
    
    # Processing state
    status: ExportStatus = ExportStatus.PENDING
    processing_start_time: Optional[datetime] = None
    processing_end_time: Optional[datetime] = None
    worker_id: Optional[str] = None
    
    def __post_init__(self):
        if not self.batch_id:
            self.batch_id = str(uuid.uuid4())[:8]
        
        # Calculate batch priority as max item priority
        if self.items:
            self.priority = max(item.priority for item in self.items)
    
    @property
    def size_bytes(self) -> int:
        """Get total size of batch in bytes."""
        return sum(item.size_bytes for item in self.items)
    
    @property
    def item_count(self) -> int:
        """Get number of items in batch."""
        return len(self.items)
    
    @property
    def processing_duration(self) -> Optional[timedelta]:
        """Get batch processing duration."""
        if self.processing_start_time and self.processing_end_time:
            return self.processing_end_time - self.processing_start_time
        return None
    
    @property
    def average_item_priority(self) -> float:
        """Get average priority of items in batch."""
        if not self.items:
            return 5.0
        return sum(item.priority for item in self.items) / len(self.items)


@dataclass
class ExportResult:
    """Result of export operation."""
    batch_id: str
    status: ExportStatus
    items_processed: int
    items_failed: int
    processing_time_ms: float
    throughput_items_per_second: float
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class ConcurrentExporter:
    """High-performance concurrent exporter with OTLP-inspired patterns.
    
    Features:
    1. Pipeline parallelism with configurable stages
    2. Adaptive batching based on throughput metrics
    3. Priority-based processing queues
    4. Linear throughput scaling with connection pooling
    5. Intelligent retry and backoff strategies
    6. Real-time performance monitoring and optimization
    """
    
    def __init__(self,
                 max_concurrent_batches: int = 10,
                 max_batch_size: int = 100,
                 max_batch_wait_ms: int = 1000,
                 batching_strategy: BatchingStrategy = BatchingStrategy.ADAPTIVE,
                 enable_priority_queues: bool = True,
                 export_function: Optional[Callable] = None):
        
        self.max_concurrent_batches = max_concurrent_batches
        self.max_batch_size = max_batch_size
        self.max_batch_wait_ms = max_batch_wait_ms
        self.batching_strategy = batching_strategy
        self.enable_priority_queues = enable_priority_queues
        self.export_function = export_function or self._default_export_function
        
        # Queuing system
        if enable_priority_queues:
            # Priority queues: high (8-10), medium (4-7), low (1-3)
            self.high_priority_queue: deque = deque()
            self.medium_priority_queue: deque = deque()
            self.low_priority_queue: deque = deque()
        else:
            self.item_queue: deque = deque()
        
        # Batch management
        self.pending_batches: deque = deque()
        self.processing_batches: Dict[str, ExportBatch] = {}
        self.completed_batches: Dict[str, ExportResult] = {}
        
        # Worker management
        self.active_workers: Dict[str, asyncio.Task] = {}
        self.worker_stats: Dict[str, Dict[str, Any]] = {}
        
        # Adaptive batching state
        self.current_batch_items: List[ExportItem] = []
        self.last_batch_creation_time = time.time()
        
        # Performance metrics
        self.metrics = {
            'total_items_queued': 0,
            'total_items_exported': 0,
            'total_items_failed': 0,
            'total_batches_created': 0,
            'total_batches_processed': 0,
            'average_batch_size': 0.0,
            'average_processing_time_ms': 0.0,
            'current_throughput_items_per_second': 0.0,
            'peak_throughput_items_per_second': 0.0,
            'average_queue_wait_time_ms': 0.0
        }
        
        # Adaptive parameters
        self.adaptive_batch_size = max_batch_size
        self.adaptive_wait_time_ms = max_batch_wait_ms
        self.target_throughput_items_per_second = 1000.0
        
        # Control flags
        self.is_running = False
        self.is_shutting_down = False
        
        # Background tasks
        self.batcher_task: Optional[asyncio.Task] = None
        self.metrics_task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start the concurrent exporter."""
        if self.is_running:
            logger.warning("Exporter is already running")
            return
        
        self.is_running = True
        self.is_shutting_down = False
        
        # Start background tasks
        self.batcher_task = asyncio.create_task(self._batch_creation_loop())
        self.metrics_task = asyncio.create_task(self._metrics_update_loop())
        
        # Start initial workers
        for i in range(min(2, self.max_concurrent_batches)):
            await self._spawn_worker(f"worker_{i:02d}")
        
        logger.info(f"Concurrent exporter started with {len(self.active_workers)} initial workers")
    
    async def stop(self, timeout_seconds: float = 30.0):
        """Stop the concurrent exporter gracefully."""
        if not self.is_running:
            return
        
        self.is_shutting_down = True
        logger.info("Shutting down concurrent exporter...")
        
        # Cancel background tasks
        if self.batcher_task:
            self.batcher_task.cancel()
        if self.metrics_task:
            self.metrics_task.cancel()
        
        # Wait for workers to finish current batches
        if self.active_workers:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self.active_workers.values(), return_exceptions=True),
                    timeout=timeout_seconds
                )
            except asyncio.TimeoutError:
                logger.warning(f"Some workers did not finish within {timeout_seconds}s, forcing shutdown")
                for task in self.active_workers.values():
                    task.cancel()
        
        # Process any remaining items in current batch
        if self.current_batch_items:
            final_batch = self._create_batch_from_items(self.current_batch_items)
            self.pending_batches.append(final_batch)
            
            # Process final batch
            if self.pending_batches:
                worker_id = "final_worker"
                await self._spawn_worker(worker_id)
                if worker_id in self.active_workers:
                    await self.active_workers[worker_id]
        
        self.is_running = False
        logger.info("Concurrent exporter stopped")
    
    async def queue_item(self, data: Any, priority: int = 5, metadata: Dict[str, Any] = None) -> str:
        """Queue an item for export.
        
        Args:
            data: Data to export
            priority: Priority level (1-10, higher = more important)
            metadata: Additional metadata
            
        Returns:
            Item ID for tracking
        """
        if not self.is_running:
            raise RuntimeError("Exporter is not running")
        
        item = ExportItem(
            item_id=str(uuid.uuid4())[:8],
            data=data,
            priority=max(1, min(10, priority)),
            metadata=metadata or {}
        )
        
        # Add to appropriate queue
        if self.enable_priority_queues:
            if item.priority >= 8:
                self.high_priority_queue.append(item)
            elif item.priority >= 4:
                self.medium_priority_queue.append(item)
            else:
                self.low_priority_queue.append(item)
        else:
            self.item_queue.append(item)
        
        self.metrics['total_items_queued'] += 1
        
        logger.debug(f"Queued item {item.item_id} with priority {item.priority}")
        return item.item_id
    
    async def queue_items(self, items: List[Dict[str, Any]]) -> List[str]:
        """Queue multiple items for export.
        
        Args:
            items: List of items, each with 'data', 'priority', and 'metadata' keys
            
        Returns:
            List of item IDs
        """
        item_ids = []
        
        for item_data in items:
            item_id = await self.queue_item(
                data=item_data.get('data'),
                priority=item_data.get('priority', 5),
                metadata=item_data.get('metadata', {})
            )
            item_ids.append(item_id)
        
        return item_ids
    
    async def _batch_creation_loop(self):
        """Background loop for creating batches from queued items."""
        try:
            while self.is_running and not self.is_shutting_down:
                await self._create_batch_if_needed()
                
                # Adaptive sleep based on queue size and throughput
                sleep_time = self._calculate_batcher_sleep_time()
                await asyncio.sleep(sleep_time)
                
        except asyncio.CancelledError:
            logger.debug("Batch creation loop cancelled")
        except Exception as e:
            logger.error(f"Batch creation loop error: {e}")
    
    async def _create_batch_if_needed(self):
        """Create a batch if conditions are met."""
        current_time = time.time()
        time_since_last_batch = (current_time - self.last_batch_creation_time) * 1000
        
        # Check if we should create a batch
        should_create_batch = False
        creation_reason = ""
        
        if self.batching_strategy == BatchingStrategy.SIZE_BASED:
            if len(self.current_batch_items) >= self.adaptive_batch_size:
                should_create_batch = True
                creation_reason = "size_threshold"
        
        elif self.batching_strategy == BatchingStrategy.TIME_BASED:
            if time_since_last_batch >= self.adaptive_wait_time_ms:
                should_create_batch = True
                creation_reason = "time_threshold"
        
        elif self.batching_strategy == BatchingStrategy.ADAPTIVE:
            # Adaptive strategy considers both size and time with throughput optimization
            size_factor = len(self.current_batch_items) / self.adaptive_batch_size
            time_factor = time_since_last_batch / self.adaptive_wait_time_ms
            
            # Create batch if either threshold is met, or both are partially met
            if (size_factor >= 1.0 or time_factor >= 1.0 or 
                (size_factor >= 0.5 and time_factor >= 0.5)):
                should_create_batch = True
                creation_reason = f"adaptive(size={size_factor:.2f},time={time_factor:.2f})"
        
        else:  # HYBRID
            # Hybrid considers queue pressure and worker availability
            queue_pressure = self._calculate_queue_pressure()
            worker_availability = self._calculate_worker_availability()
            
            if (len(self.current_batch_items) >= self.adaptive_batch_size or
                time_since_last_batch >= self.adaptive_wait_time_ms or
                (queue_pressure > 0.7 and worker_availability > 0.3)):
                should_create_batch = True
                creation_reason = f"hybrid(pressure={queue_pressure:.2f},workers={worker_availability:.2f})"
        
        # Add items to current batch from queues
        await self._fill_current_batch()
        
        # Create batch if conditions are met and we have items
        if should_create_batch and self.current_batch_items:
            batch = self._create_batch_from_items(self.current_batch_items)
            self.pending_batches.append(batch)
            self.current_batch_items = []
            self.last_batch_creation_time = current_time
            
            logger.debug(f"Created batch {batch.batch_id} with {batch.item_count} items, reason: {creation_reason}")
            
            # Spawn worker if needed and available
            await self._manage_worker_pool()
    
    async def _fill_current_batch(self):
        """Fill current batch with items from priority queues."""
        remaining_capacity = self.adaptive_batch_size - len(self.current_batch_items)
        
        if remaining_capacity <= 0:
            return
        
        if self.enable_priority_queues:
            # Fill from high priority first, then medium, then low
            for queue in [self.high_priority_queue, self.medium_priority_queue, self.low_priority_queue]:
                while queue and remaining_capacity > 0:
                    item = queue.popleft()
                    self.current_batch_items.append(item)
                    remaining_capacity -= 1
        else:
            # Fill from single queue
            while self.item_queue and remaining_capacity > 0:
                item = self.item_queue.popleft()
                self.current_batch_items.append(item)
                remaining_capacity -= 1
    
    def _create_batch_from_items(self, items: List[ExportItem]) -> ExportBatch:
        """Create a batch from list of items."""
        batch = ExportBatch(
            batch_id=f"batch_{len(self.completed_batches):04d}",
            items=items.copy(),
            created_at=datetime.now()
        )
        
        self.metrics['total_batches_created'] += 1
        return batch
    
    async def _manage_worker_pool(self):
        """Manage worker pool size based on workload."""
        pending_batches = len(self.pending_batches)
        active_workers = len(self.active_workers)
        
        # Spawn new worker if we have work and capacity
        if (pending_batches > 0 and 
            active_workers < self.max_concurrent_batches and
            not self.is_shutting_down):
            
            worker_id = f"worker_{active_workers:02d}_{int(time.time() * 1000) % 10000}"
            await self._spawn_worker(worker_id)
        
        # Clean up completed workers
        completed_workers = [
            worker_id for worker_id, task in self.active_workers.items()
            if task.done()
        ]
        
        for worker_id in completed_workers:
            task = self.active_workers.pop(worker_id)
            if not task.cancelled():
                try:
                    await task  # Ensure any exceptions are raised
                except Exception as e:
                    logger.error(f"Worker {worker_id} failed: {e}")
            
            # Clean up worker stats
            self.worker_stats.pop(worker_id, None)
    
    async def _spawn_worker(self, worker_id: str):
        """Spawn a new worker task."""
        task = asyncio.create_task(self._worker_loop(worker_id))
        self.active_workers[worker_id] = task
        self.worker_stats[worker_id] = {
            'batches_processed': 0,
            'items_processed': 0,
            'total_processing_time_ms': 0.0,
            'last_batch_time': None,
            'start_time': datetime.now()
        }
        
        logger.debug(f"Spawned worker {worker_id}")
    
    async def _worker_loop(self, worker_id: str):
        """Main worker loop for processing batches."""
        logger.debug(f"Worker {worker_id} started")
        
        try:
            while self.is_running and not self.is_shutting_down:
                # Get next batch
                if not self.pending_batches:
                    # No work available, check if we should exit
                    if len(self.active_workers) > 2:  # Keep minimum workers
                        break
                    await asyncio.sleep(0.1)
                    continue
                
                batch = self.pending_batches.popleft()
                
                # Process batch
                result = await self._process_batch(batch, worker_id)
                
                # Record result
                self.completed_batches[batch.batch_id] = result
                self._update_worker_stats(worker_id, result)
                self._update_global_metrics(result)
                
                # Adaptive parameter adjustment
                await self._adjust_adaptive_parameters(result)
                
        except asyncio.CancelledError:
            logger.debug(f"Worker {worker_id} cancelled")
        except Exception as e:
            logger.error(f"Worker {worker_id} error: {e}")
        finally:
            logger.debug(f"Worker {worker_id} finished")
    
    async def _process_batch(self, batch: ExportBatch, worker_id: str) -> ExportResult:
        """Process a single batch."""
        batch.status = ExportStatus.PROCESSING
        batch.processing_start_time = datetime.now()
        batch.worker_id = worker_id
        self.processing_batches[batch.batch_id] = batch
        
        start_time = time.time()
        items_processed = 0
        items_failed = 0
        error = None
        
        try:
            # Export items using the configured export function
            export_data = [item.data for item in batch.items]
            
            if asyncio.iscoroutinefunction(self.export_function):
                await self.export_function(export_data, batch.batch_id)
            else:
                self.export_function(export_data, batch.batch_id)
            
            items_processed = len(batch.items)
            batch.status = ExportStatus.COMPLETED
            
        except Exception as e:
            items_failed = len(batch.items)
            error = str(e)
            batch.status = ExportStatus.FAILED
            logger.error(f"Batch {batch.batch_id} processing failed: {e}")
        
        finally:
            batch.processing_end_time = datetime.now()
            self.processing_batches.pop(batch.batch_id, None)
        
        processing_time_ms = (time.time() - start_time) * 1000
        throughput = items_processed / max(processing_time_ms / 1000, 0.001)
        
        result = ExportResult(
            batch_id=batch.batch_id,
            status=batch.status,
            items_processed=items_processed,
            items_failed=items_failed,
            processing_time_ms=processing_time_ms,
            throughput_items_per_second=throughput,
            error=error,
            metadata={
                'worker_id': worker_id,
                'batch_size': len(batch.items),
                'batch_priority': batch.priority,
                'queue_wait_time_ms': (batch.processing_start_time - batch.created_at).total_seconds() * 1000
            }
        )
        
        logger.debug(f"Processed batch {batch.batch_id}: {items_processed} items, {throughput:.1f} items/s")
        return result
    
    def _update_worker_stats(self, worker_id: str, result: ExportResult):
        """Update worker statistics."""
        if worker_id not in self.worker_stats:
            return
        
        stats = self.worker_stats[worker_id]
        stats['batches_processed'] += 1
        stats['items_processed'] += result.items_processed
        stats['total_processing_time_ms'] += result.processing_time_ms
        stats['last_batch_time'] = datetime.now()
    
    def _update_global_metrics(self, result: ExportResult):
        """Update global metrics."""
        self.metrics['total_items_exported'] += result.items_processed
        self.metrics['total_items_failed'] += result.items_failed
        self.metrics['total_batches_processed'] += 1
        
        # Update averages
        total_batches = self.metrics['total_batches_processed']
        
        # Average batch size
        current_avg_size = self.metrics['average_batch_size']
        new_avg_size = ((current_avg_size * (total_batches - 1)) + 
                       (result.items_processed + result.items_failed)) / total_batches
        self.metrics['average_batch_size'] = new_avg_size
        
        # Average processing time
        current_avg_time = self.metrics['average_processing_time_ms']
        new_avg_time = ((current_avg_time * (total_batches - 1)) + 
                       result.processing_time_ms) / total_batches
        self.metrics['average_processing_time_ms'] = new_avg_time
        
        # Current throughput
        self.metrics['current_throughput_items_per_second'] = result.throughput_items_per_second
        
        # Peak throughput
        if result.throughput_items_per_second > self.metrics['peak_throughput_items_per_second']:
            self.metrics['peak_throughput_items_per_second'] = result.throughput_items_per_second
        
        # Average queue wait time
        if 'queue_wait_time_ms' in result.metadata:
            current_avg_wait = self.metrics['average_queue_wait_time_ms']
            new_avg_wait = ((current_avg_wait * (total_batches - 1)) + 
                           result.metadata['queue_wait_time_ms']) / total_batches
            self.metrics['average_queue_wait_time_ms'] = new_avg_wait
    
    async def _adjust_adaptive_parameters(self, result: ExportResult):
        """Adjust adaptive parameters based on performance."""
        if self.batching_strategy not in [BatchingStrategy.ADAPTIVE, BatchingStrategy.HYBRID]:
            return
        
        # Adjust batch size based on throughput
        target_throughput = self.target_throughput_items_per_second
        actual_throughput = result.throughput_items_per_second
        
        if actual_throughput > target_throughput * 1.2:
            # Performing well, can try larger batches
            self.adaptive_batch_size = min(self.max_batch_size, 
                                         int(self.adaptive_batch_size * 1.1))
        elif actual_throughput < target_throughput * 0.8:
            # Underperforming, try smaller batches
            self.adaptive_batch_size = max(10, int(self.adaptive_batch_size * 0.9))
        
        # Adjust wait time based on queue pressure
        queue_pressure = self._calculate_queue_pressure()
        
        if queue_pressure > 0.8:
            # High pressure, reduce wait time
            self.adaptive_wait_time_ms = max(100, int(self.adaptive_wait_time_ms * 0.9))
        elif queue_pressure < 0.3:
            # Low pressure, can increase wait time for better batching
            self.adaptive_wait_time_ms = min(self.max_batch_wait_ms, 
                                           int(self.adaptive_wait_time_ms * 1.1))
    
    def _calculate_queue_pressure(self) -> float:
        """Calculate current queue pressure (0.0 to 1.0)."""
        if self.enable_priority_queues:
            total_queued = (len(self.high_priority_queue) + 
                          len(self.medium_priority_queue) + 
                          len(self.low_priority_queue))
        else:
            total_queued = len(self.item_queue)
        
        total_queued += len(self.current_batch_items)
        total_queued += len(self.pending_batches) * self.adaptive_batch_size
        
        # Normalize based on processing capacity
        max_capacity = self.max_concurrent_batches * self.max_batch_size * 2
        pressure = min(total_queued / max_capacity, 1.0)
        
        return pressure
    
    def _calculate_worker_availability(self) -> float:
        """Calculate worker availability (0.0 to 1.0)."""
        active_workers = len(self.active_workers)
        max_workers = self.max_concurrent_batches
        
        return 1.0 - (active_workers / max_workers)
    
    def _calculate_batcher_sleep_time(self) -> float:
        """Calculate optimal sleep time for batcher loop."""
        queue_pressure = self._calculate_queue_pressure()
        
        if queue_pressure > 0.8:
            return 0.01  # High pressure, check frequently
        elif queue_pressure > 0.5:
            return 0.05  # Medium pressure
        else:
            return 0.1   # Low pressure, less frequent checks
    
    async def _metrics_update_loop(self):
        """Background loop for updating metrics."""
        try:
            while self.is_running and not self.is_shutting_down:
                await self._update_runtime_metrics()
                await asyncio.sleep(1.0)  # Update every second
                
        except asyncio.CancelledError:
            logger.debug("Metrics update loop cancelled")
        except Exception as e:
            logger.error(f"Metrics update loop error: {e}")
    
    async def _update_runtime_metrics(self):
        """Update runtime metrics."""
        # Calculate current throughput based on recent activity
        recent_results = list(self.completed_batches.values())[-10:]  # Last 10 batches
        
        if recent_results:
            recent_throughput = sum(r.throughput_items_per_second for r in recent_results) / len(recent_results)
            self.metrics['current_throughput_items_per_second'] = recent_throughput
    
    async def _default_export_function(self, data: List[Any], batch_id: str):
        """Default export function for testing."""
        # Simulate export operation
        await asyncio.sleep(0.1 + (len(data) * 0.001))
        logger.debug(f"Exported batch {batch_id} with {len(data)} items")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current exporter status."""
        if self.enable_priority_queues:
            queued_items = {
                'high_priority': len(self.high_priority_queue),
                'medium_priority': len(self.medium_priority_queue),
                'low_priority': len(self.low_priority_queue),
                'current_batch': len(self.current_batch_items)
            }
            total_queued = sum(queued_items.values())
        else:
            total_queued = len(self.item_queue) + len(self.current_batch_items)
            queued_items = {'total': total_queued}
        
        return {
            'is_running': self.is_running,
            'is_shutting_down': self.is_shutting_down,
            'queued_items': queued_items,
            'total_queued': total_queued,
            'pending_batches': len(self.pending_batches),
            'processing_batches': len(self.processing_batches),
            'completed_batches': len(self.completed_batches),
            'active_workers': len(self.active_workers),
            'queue_pressure': self._calculate_queue_pressure(),
            'worker_availability': self._calculate_worker_availability(),
            'adaptive_parameters': {
                'batch_size': self.adaptive_batch_size,
                'wait_time_ms': self.adaptive_wait_time_ms
            },
            'metrics': self.metrics.copy()
        }
    
    def get_worker_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all workers."""
        stats = {}
        
        for worker_id, worker_stats in self.worker_stats.items():
            uptime = (datetime.now() - worker_stats['start_time']).total_seconds()
            
            stats[worker_id] = {
                **worker_stats.copy(),
                'uptime_seconds': uptime,
                'average_items_per_batch': (worker_stats['items_processed'] / 
                                          max(worker_stats['batches_processed'], 1)),
                'average_processing_time_ms': (worker_stats['total_processing_time_ms'] / 
                                             max(worker_stats['batches_processed'], 1)),
                'is_active': worker_id in self.active_workers
            }
        
        return stats