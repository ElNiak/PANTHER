"""Saga coordinator for managing distributed task transactions.

Implements the Saga pattern for hierarchical task operations, ensuring
either all operations succeed or all are properly compensated.
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import uuid

logger = logging.getLogger(__name__)


class SagaStepStatus(Enum):
    """Status of individual saga steps."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    COMPENSATING = "compensating"
    COMPENSATED = "compensated"
    COMPENSATION_FAILED = "compensation_failed"


class SagaExecutionStrategy(Enum):
    """Execution strategies for saga steps."""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    MIXED = "mixed"


@dataclass
class SagaStep:
    """Represents a single step in a saga transaction."""
    step_id: str
    name: str
    action: Callable[..., Any]
    compensation: Optional[Callable[..., Any]] = None
    retry_count: int = 3
    timeout_seconds: int = 300  # 5 minutes
    depends_on: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Runtime state
    status: SagaStepStatus = SagaStepStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    attempts: int = 0
    
    def __post_init__(self):
        if not self.step_id:
            self.step_id = str(uuid.uuid4())[:8]
    
    @property
    def duration(self) -> Optional[timedelta]:
        """Get step execution duration."""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None
    
    @property
    def is_complete(self) -> bool:
        """Check if step is in a terminal state."""
        return self.status in [
            SagaStepStatus.COMPLETED,
            SagaStepStatus.COMPENSATED,
            SagaStepStatus.COMPENSATION_FAILED
        ]
    
    @property
    def needs_compensation(self) -> bool:
        """Check if step needs compensation."""
        return (self.status == SagaStepStatus.COMPLETED and 
                self.compensation is not None)


@dataclass
class SagaDefinition:
    """Defines a saga transaction with steps and execution strategy."""
    saga_id: str
    name: str
    steps: List[SagaStep]
    strategy: SagaExecutionStrategy = SagaExecutionStrategy.SEQUENTIAL
    global_timeout_seconds: int = 1800  # 30 minutes
    enable_compensation: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.saga_id:
            self.saga_id = str(uuid.uuid4())[:8]
        
        # Validate dependency graph
        self._validate_dependencies()
    
    def _validate_dependencies(self):
        """Validate that step dependencies form a valid DAG."""
        step_ids = {step.step_id for step in self.steps}
        
        for step in self.steps:
            for dep_id in step.depends_on:
                if dep_id not in step_ids:
                    raise ValueError(f"Step {step.step_id} depends on unknown step {dep_id}")
        
        # Check for cycles (simplified check)
        visited = set()
        rec_stack = set()
        
        def has_cycle(step_id: str) -> bool:
            if step_id in rec_stack:
                return True
            if step_id in visited:
                return False
            
            visited.add(step_id)
            rec_stack.add(step_id)
            
            step = next((s for s in self.steps if s.step_id == step_id), None)
            if step:
                for dep_id in step.depends_on:
                    if has_cycle(dep_id):
                        return True
            
            rec_stack.remove(step_id)
            return False
        
        for step in self.steps:
            if has_cycle(step.step_id):
                raise ValueError(f"Circular dependency detected involving step {step.step_id}")
    
    def get_executable_steps(self) -> List[SagaStep]:
        """Get steps that can be executed now (dependencies satisfied)."""
        executable = []
        
        for step in self.steps:
            if step.status != SagaStepStatus.PENDING:
                continue
            
            # Check if all dependencies are completed
            deps_satisfied = all(
                any(s.step_id == dep_id and s.status == SagaStepStatus.COMPLETED 
                    for s in self.steps)
                for dep_id in step.depends_on
            )
            
            if deps_satisfied:
                executable.append(step)
        
        return executable


class SagaCoordinator:
    """Coordinates saga execution with hierarchical task support.
    
    Manages the execution of saga transactions for complex task operations,
    providing transactional integrity and automatic compensation.
    """
    
    def __init__(self, 
                 max_concurrent_sagas: int = 10,
                 default_timeout: int = 1800,
                 enable_metrics: bool = True):
        self.max_concurrent_sagas = max_concurrent_sagas
        self.default_timeout = default_timeout
        self.enable_metrics = enable_metrics
        
        # Active sagas
        self.active_sagas: Dict[str, SagaDefinition] = {}
        self.saga_locks: Dict[str, asyncio.Lock] = {}
        
        # Execution tracking
        self.execution_history: List[Dict[str, Any]] = []
        self.compensation_history: List[Dict[str, Any]] = []
        
        # Metrics
        self.metrics = {
            'total_sagas': 0,
            'successful_sagas': 0,
            'failed_sagas': 0,
            'compensated_sagas': 0,
            'avg_execution_time': 0.0,
            'step_success_rate': 0.0
        }
    
    async def execute_saga(self, saga_definition: SagaDefinition, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute a saga transaction.
        
        Args:
            saga_definition: The saga to execute
            context: Execution context passed to all steps
            
        Returns:
            Dictionary with execution results and metadata
        """
        context = context or {}
        saga_id = saga_definition.saga_id
        
        # Check concurrent limit
        if len(self.active_sagas) >= self.max_concurrent_sagas:
            raise RuntimeError(f"Maximum concurrent sagas ({self.max_concurrent_sagas}) exceeded")
        
        # Initialize saga state
        self.active_sagas[saga_id] = saga_definition
        self.saga_locks[saga_id] = asyncio.Lock()
        
        start_time = datetime.now()
        execution_result = {
            'saga_id': saga_id,
            'start_time': start_time.isoformat(),
            'status': 'running',
            'steps_completed': 0,
            'steps_failed': 0,
            'compensation_applied': False,
            'error': None,
            'results': {}
        }
        
        try:
            logger.info(f"Starting saga execution: {saga_id} ({saga_definition.name})")
            
            # Execute based on strategy
            if saga_definition.strategy == SagaExecutionStrategy.SEQUENTIAL:
                await self._execute_sequential(saga_definition, context, execution_result)
            elif saga_definition.strategy == SagaExecutionStrategy.PARALLEL:
                await self._execute_parallel(saga_definition, context, execution_result)
            else:  # MIXED
                await self._execute_mixed(saga_definition, context, execution_result)
            
            # Check final status
            all_completed = all(step.status == SagaStepStatus.COMPLETED for step in saga_definition.steps)
            
            if all_completed:
                execution_result['status'] = 'completed'
                execution_result['steps_completed'] = len(saga_definition.steps)
                logger.info(f"Saga {saga_id} completed successfully")
            else:
                # Some steps failed, trigger compensation
                execution_result['status'] = 'compensating'
                await self._compensate_saga(saga_definition, context, execution_result)
        
        except asyncio.TimeoutError:
            execution_result['status'] = 'timeout'
            execution_result['error'] = f"Saga timed out after {saga_definition.global_timeout_seconds} seconds"
            logger.error(f"Saga {saga_id} timed out")
            
            # Trigger compensation for completed steps
            if saga_definition.enable_compensation:
                await self._compensate_saga(saga_definition, context, execution_result)
        
        except Exception as e:
            execution_result['status'] = 'failed'
            execution_result['error'] = str(e)
            logger.error(f"Saga {saga_id} failed: {e}")
            
            # Trigger compensation
            if saga_definition.enable_compensation:
                await self._compensate_saga(saga_definition, context, execution_result)
        
        finally:
            # Cleanup
            end_time = datetime.now()
            execution_result['end_time'] = end_time.isoformat()
            execution_result['duration_seconds'] = (end_time - start_time).total_seconds()
            
            # Collect step results
            for step in saga_definition.steps:
                execution_result['results'][step.step_id] = {
                    'name': step.name,
                    'status': step.status.value,
                    'result': step.result,
                    'error': step.error,
                    'duration_seconds': step.duration.total_seconds() if step.duration else None,
                    'attempts': step.attempts
                }
            
            # Update metrics
            await self._update_metrics(saga_definition, execution_result)
            
            # Record history
            self.execution_history.append(execution_result.copy())
            
            # Cleanup active state
            self.active_sagas.pop(saga_id, None)
            self.saga_locks.pop(saga_id, None)
        
        return execution_result
    
    async def _execute_sequential(self, saga: SagaDefinition, context: Dict[str, Any], result: Dict[str, Any]):
        """Execute saga steps sequentially."""
        timeout = asyncio.timeout(saga.global_timeout_seconds)
        
        async with timeout:
            while True:
                executable_steps = saga.get_executable_steps()
                
                if not executable_steps:
                    # Check if we're done or stuck
                    pending_steps = [s for s in saga.steps if s.status == SagaStepStatus.PENDING]
                    if not pending_steps:
                        break  # All steps processed
                    else:
                        # Deadlock - dependencies not satisfied
                        raise RuntimeError(f"Dependency deadlock detected in saga {saga.saga_id}")
                
                # Execute one step at a time
                step = executable_steps[0]
                await self._execute_step(step, context)
                
                if step.status == SagaStepStatus.FAILED:
                    result['steps_failed'] += 1
                    break
                elif step.status == SagaStepStatus.COMPLETED:
                    result['steps_completed'] += 1
    
    async def _execute_parallel(self, saga: SagaDefinition, context: Dict[str, Any], result: Dict[str, Any]):
        """Execute saga steps in parallel where possible."""
        timeout = asyncio.timeout(saga.global_timeout_seconds)
        
        async with timeout:
            while True:
                executable_steps = saga.get_executable_steps()
                
                if not executable_steps:
                    pending_steps = [s for s in saga.steps if s.status == SagaStepStatus.PENDING]
                    if not pending_steps:
                        break  # All steps processed
                    else:
                        raise RuntimeError(f"Dependency deadlock detected in saga {saga.saga_id}")
                
                # Execute all executable steps in parallel
                tasks = [self._execute_step(step, context) for step in executable_steps]
                await asyncio.gather(*tasks, return_exceptions=True)
                
                # Update counters
                for step in executable_steps:
                    if step.status == SagaStepStatus.FAILED:
                        result['steps_failed'] += 1
                    elif step.status == SagaStepStatus.COMPLETED:
                        result['steps_completed'] += 1
                
                # Stop if any step failed
                if result['steps_failed'] > 0:
                    break
    
    async def _execute_mixed(self, saga: SagaDefinition, context: Dict[str, Any], result: Dict[str, Any]):
        """Execute saga with mixed strategy (batched parallel execution)."""
        timeout = asyncio.timeout(saga.global_timeout_seconds)
        
        async with timeout:
            # Group steps by dependency level
            dependency_levels = self._compute_dependency_levels(saga)
            
            for level_steps in dependency_levels:
                # Execute all steps in this level in parallel
                tasks = [self._execute_step(step, context) for step in level_steps]
                await asyncio.gather(*tasks, return_exceptions=True)
                
                # Update counters and check for failures
                for step in level_steps:
                    if step.status == SagaStepStatus.FAILED:
                        result['steps_failed'] += 1
                    elif step.status == SagaStepStatus.COMPLETED:
                        result['steps_completed'] += 1
                
                # Stop if any step in this level failed
                if result['steps_failed'] > 0:
                    break
    
    def _compute_dependency_levels(self, saga: SagaDefinition) -> List[List[SagaStep]]:
        """Compute dependency levels for mixed execution strategy."""
        levels = []
        remaining_steps = saga.steps.copy()
        
        while remaining_steps:
            # Find steps with no remaining dependencies
            current_level = []
            completed_step_ids = {s.step_id for s in saga.steps if s not in remaining_steps}
            
            for step in remaining_steps[:]:  # Copy to avoid modification during iteration
                deps_satisfied = all(dep_id in completed_step_ids for dep_id in step.depends_on)
                if deps_satisfied:
                    current_level.append(step)
                    remaining_steps.remove(step)
            
            if not current_level:
                # Circular dependency or other issue
                raise RuntimeError(f"Unable to resolve dependencies in saga {saga.saga_id}")
            
            levels.append(current_level)
            completed_step_ids.update(step.step_id for step in current_level)
        
        return levels
    
    async def _execute_step(self, step: SagaStep, context: Dict[str, Any]):
        """Execute a single saga step with retry logic."""
        step.status = SagaStepStatus.RUNNING
        step.start_time = datetime.now()
        
        for attempt in range(step.retry_count + 1):
            step.attempts = attempt + 1
            
            try:
                logger.debug(f"Executing step {step.step_id} ({step.name}), attempt {attempt + 1}")
                
                # Execute with timeout
                timeout = asyncio.timeout(step.timeout_seconds)
                async with timeout:
                    if asyncio.iscoroutinefunction(step.action):
                        step.result = await step.action(context, step)
                    else:
                        step.result = step.action(context, step)
                
                # Success
                step.status = SagaStepStatus.COMPLETED
                step.end_time = datetime.now()
                logger.debug(f"Step {step.step_id} completed successfully")
                return
                
            except asyncio.TimeoutError:
                error_msg = f"Step {step.step_id} timed out after {step.timeout_seconds} seconds"
                logger.warning(error_msg)
                step.error = error_msg
                
                if attempt < step.retry_count:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    continue
                
            except Exception as e:
                error_msg = f"Step {step.step_id} failed: {str(e)}"
                logger.warning(error_msg)
                step.error = error_msg
                
                if attempt < step.retry_count:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    continue
        
        # All retries exhausted
        step.status = SagaStepStatus.FAILED
        step.end_time = datetime.now()
        logger.error(f"Step {step.step_id} failed after {step.retry_count + 1} attempts")
    
    async def _compensate_saga(self, saga: SagaDefinition, context: Dict[str, Any], result: Dict[str, Any]):
        """Apply compensation to completed steps in reverse order."""
        if not saga.enable_compensation:
            return
        
        logger.info(f"Starting compensation for saga {saga.saga_id}")
        result['compensation_applied'] = True
        
        # Get completed steps in reverse execution order
        completed_steps = [s for s in saga.steps if s.needs_compensation]
        completed_steps.reverse()
        
        compensation_results = []
        
        for step in completed_steps:
            if step.compensation is None:
                continue
            
            step.status = SagaStepStatus.COMPENSATING
            
            try:
                logger.debug(f"Compensating step {step.step_id}")
                
                if asyncio.iscoroutinefunction(step.compensation):
                    compensation_result = await step.compensation(context, step)
                else:
                    compensation_result = step.compensation(context, step)
                
                step.status = SagaStepStatus.COMPENSATED
                compensation_results.append({
                    'step_id': step.step_id,
                    'status': 'compensated',
                    'result': compensation_result
                })
                
                logger.debug(f"Step {step.step_id} compensated successfully")
                
            except Exception as e:
                step.status = SagaStepStatus.COMPENSATION_FAILED
                error_msg = f"Compensation failed for step {step.step_id}: {str(e)}"
                logger.error(error_msg)
                
                compensation_results.append({
                    'step_id': step.step_id,
                    'status': 'compensation_failed',
                    'error': error_msg
                })
        
        # Record compensation history
        self.compensation_history.append({
            'saga_id': saga.saga_id,
            'timestamp': datetime.now().isoformat(),
            'compensated_steps': compensation_results,
            'total_steps_compensated': len([r for r in compensation_results if r['status'] == 'compensated']),
            'compensation_failures': len([r for r in compensation_results if r['status'] == 'compensation_failed'])
        })
        
        result['compensation_results'] = compensation_results
    
    async def _update_metrics(self, saga: SagaDefinition, result: Dict[str, Any]):
        """Update saga execution metrics."""
        if not self.enable_metrics:
            return
        
        self.metrics['total_sagas'] += 1
        
        if result['status'] == 'completed':
            self.metrics['successful_sagas'] += 1
        elif result['status'] in ['failed', 'timeout']:
            self.metrics['failed_sagas'] += 1
        elif result['compensation_applied']:
            self.metrics['compensated_sagas'] += 1
        
        # Update average execution time
        if 'duration_seconds' in result:
            current_avg = self.metrics['avg_execution_time']
            total_sagas = self.metrics['total_sagas']
            new_avg = ((current_avg * (total_sagas - 1)) + result['duration_seconds']) / total_sagas
            self.metrics['avg_execution_time'] = new_avg
        
        # Update step success rate
        total_steps = sum(len(s.steps) for s in self.active_sagas.values()) + len(saga.steps)
        if total_steps > 0:
            successful_steps = sum(1 for step in saga.steps if step.status == SagaStepStatus.COMPLETED)
            self.metrics['step_success_rate'] = successful_steps / total_steps
    
    async def cancel_saga(self, saga_id: str, reason: str = "Manual cancellation") -> bool:
        """Cancel a running saga and trigger compensation."""
        if saga_id not in self.active_sagas:
            return False
        
        saga = self.active_sagas[saga_id]
        
        async with self.saga_locks[saga_id]:
            logger.info(f"Cancelling saga {saga_id}: {reason}")
            
            # Mark running steps as failed
            for step in saga.steps:
                if step.status == SagaStepStatus.RUNNING:
                    step.status = SagaStepStatus.FAILED
                    step.error = f"Cancelled: {reason}"
                    step.end_time = datetime.now()
            
            # Trigger compensation
            if saga.enable_compensation:
                compensation_result = {}
                await self._compensate_saga(saga, {}, compensation_result)
        
        return True
    
    def get_saga_status(self, saga_id: str) -> Optional[Dict[str, Any]]:
        """Get current status of a saga."""
        if saga_id not in self.active_sagas:
            return None
        
        saga = self.active_sagas[saga_id]
        
        return {
            'saga_id': saga_id,
            'name': saga.name,
            'strategy': saga.strategy.value,
            'total_steps': len(saga.steps),
            'completed_steps': len([s for s in saga.steps if s.status == SagaStepStatus.COMPLETED]),
            'failed_steps': len([s for s in saga.steps if s.status == SagaStepStatus.FAILED]),
            'running_steps': len([s for s in saga.steps if s.status == SagaStepStatus.RUNNING]),
            'steps': [
                {
                    'step_id': step.step_id,
                    'name': step.name,
                    'status': step.status.value,
                    'attempts': step.attempts,
                    'error': step.error
                }
                for step in saga.steps
            ]
        }
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get saga execution metrics."""
        return {
            **self.metrics,
            'active_sagas': len(self.active_sagas),
            'execution_history_size': len(self.execution_history),
            'compensation_history_size': len(self.compensation_history)
        }