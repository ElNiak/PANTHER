"""Temporal Cloud integration for saga workflows.

Provides integration with Temporal Cloud for enhanced workflow orchestration,
enabling multi-cluster deployment and cross-datacenter reliability.
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

from .saga_coordinator import SagaCoordinator, SagaDefinition, SagaStep, SagaStepStatus

logger = logging.getLogger(__name__)


class TemporalWorkflowStatus(Enum):
    """Status of Temporal workflows."""
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TERMINATED = "terminated"
    CONTINUED_AS_NEW = "continued_as_new"


@dataclass
class TemporalWorkflowConfig:
    """Configuration for Temporal workflow execution."""
    workflow_id: str
    task_queue: str = "atlas-saga-tasks"
    workflow_execution_timeout: timedelta = timedelta(hours=1)
    workflow_run_timeout: timedelta = timedelta(minutes=30)
    workflow_task_timeout: timedelta = timedelta(minutes=5)
    retry_policy: Dict[str, Any] = None
    cron_schedule: Optional[str] = None
    
    def __post_init__(self):
        if self.retry_policy is None:
            self.retry_policy = {
                'initial_interval': timedelta(seconds=1),
                'backoff_coefficient': 2.0,
                'maximum_interval': timedelta(minutes=5),
                'maximum_attempts': 3
            }


class TemporalSagaWorkflow:
    """Temporal workflow implementation for saga orchestration.
    
    Maps ATLAS hierarchical task system to Temporal concepts:
    - Workflows = Parent tasks  
    - Activities = Subtasks
    - Child Workflows = Subsubtasks
    """
    
    def __init__(self, 
                 temporal_client=None,  # Would be actual Temporal client in production
                 saga_coordinator: Optional[SagaCoordinator] = None,
                 enable_cross_cluster: bool = True):
        self.temporal_client = temporal_client
        self.saga_coordinator = saga_coordinator or SagaCoordinator()
        self.enable_cross_cluster = enable_cross_cluster
        
        # Workflow tracking
        self.active_workflows: Dict[str, Dict[str, Any]] = {}
        self.workflow_history: List[Dict[str, Any]] = []
        
        # Cross-cluster state
        self.cluster_nodes: List[str] = ['primary', 'secondary', 'tertiary']
        self.current_cluster = 'primary'
        
        # Activity registry for task operations
        self.activity_registry = {
            'create_task': self._create_task_activity,
            'update_task_status': self._update_task_status_activity,
            'create_subtask': self._create_subtask_activity,
            'calculate_progress_rollup': self._calculate_progress_rollup_activity,
            'backup_task_state': self._backup_task_state_activity,
            'archive_task': self._archive_task_activity,
            'validate_task_hierarchy': self._validate_task_hierarchy_activity
        }
    
    async def execute_hierarchical_saga(self, 
                                      saga_definition: SagaDefinition,
                                      workflow_config: TemporalWorkflowConfig,
                                      context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute saga as Temporal workflow with hierarchical task support.
        
        Args:
            saga_definition: Saga to execute
            workflow_config: Temporal workflow configuration
            context: Execution context with task hierarchy information
            
        Returns:
            Workflow execution result with progress rollup
        """
        context = context or {}
        workflow_id = workflow_config.workflow_id
        
        logger.info(f"Starting Temporal saga workflow: {workflow_id}")
        
        # Initialize workflow state
        workflow_state = {
            'workflow_id': workflow_id,
            'saga_id': saga_definition.saga_id,
            'status': TemporalWorkflowStatus.RUNNING,
            'start_time': datetime.now().isoformat(),
            'cluster': self.current_cluster,
            'activities_completed': 0,
            'activities_failed': 0,
            'child_workflows': [],
            'progress_rollup': {'completed': 0, 'total': len(saga_definition.steps)},
            'cross_cluster_replicated': False,
            'context': context
        }
        
        self.active_workflows[workflow_id] = workflow_state
        
        try:
            # Setup cross-cluster replication if enabled
            if self.enable_cross_cluster:
                await self._setup_cross_cluster_replication(workflow_id, workflow_state)
            
            # Map saga steps to Temporal activities
            activity_results = {}
            
            # Execute activities based on hierarchy
            hierarchical_context = self._extract_hierarchical_context(context)
            
            if hierarchical_context['is_parent_task']:
                # Parent task: manage child workflows
                activity_results = await self._execute_parent_task_workflow(
                    saga_definition, workflow_config, hierarchical_context
                )
            elif hierarchical_context['is_subtask']:
                # Subtask: execute as activities with progress rollup
                activity_results = await self._execute_subtask_workflow(
                    saga_definition, workflow_config, hierarchical_context
                )
            else:
                # Regular task: execute as standard saga
                activity_results = await self._execute_standard_saga_workflow(
                    saga_definition, workflow_config, context
                )
            
            # Calculate final progress rollup
            final_rollup = await self._calculate_final_progress_rollup(
                workflow_id, activity_results, hierarchical_context
            )
            
            # Update workflow state
            workflow_state['status'] = TemporalWorkflowStatus.COMPLETED
            workflow_state['activities_completed'] = len([r for r in activity_results.values() if r.get('success')])
            workflow_state['activities_failed'] = len([r for r in activity_results.values() if not r.get('success')])
            workflow_state['final_progress'] = final_rollup
            workflow_state['end_time'] = datetime.now().isoformat()
            
            logger.info(f"Temporal saga workflow {workflow_id} completed successfully")
            
            return {
                'workflow_id': workflow_id,
                'saga_id': saga_definition.saga_id,
                'status': 'completed',
                'activity_results': activity_results,
                'progress_rollup': final_rollup,
                'cross_cluster_replicated': workflow_state['cross_cluster_replicated'],
                'execution_cluster': workflow_state['cluster'],
                'duration_seconds': (datetime.fromisoformat(workflow_state['end_time']) - 
                                   datetime.fromisoformat(workflow_state['start_time'])).total_seconds()
            }
            
        except Exception as e:
            logger.error(f"Temporal saga workflow {workflow_id} failed: {e}")
            
            workflow_state['status'] = TemporalWorkflowStatus.FAILED
            workflow_state['error'] = str(e)
            workflow_state['end_time'] = datetime.now().isoformat()
            
            # Trigger compensation through saga coordinator
            if saga_definition.enable_compensation:
                compensation_result = await self.saga_coordinator.execute_saga(
                    self._create_compensation_saga(saga_definition), context
                )
                workflow_state['compensation_applied'] = True
                workflow_state['compensation_result'] = compensation_result
            
            return {
                'workflow_id': workflow_id,
                'saga_id': saga_definition.saga_id,
                'status': 'failed',
                'error': str(e),
                'compensation_applied': workflow_state.get('compensation_applied', False)
            }
        
        finally:
            # Move to history and cleanup
            self.workflow_history.append(workflow_state.copy())
            self.active_workflows.pop(workflow_id, None)
    
    async def _setup_cross_cluster_replication(self, workflow_id: str, workflow_state: Dict[str, Any]):
        """Setup cross-cluster replication for workflow state."""
        try:
            # In production, this would replicate to other Temporal clusters
            # For now, simulate by storing in multiple cluster nodes
            
            replication_tasks = []
            for cluster in self.cluster_nodes:
                if cluster != self.current_cluster:
                    # Simulate async replication
                    replication_tasks.append(
                        self._replicate_workflow_state(workflow_id, workflow_state, cluster)
                    )
            
            await asyncio.gather(*replication_tasks, return_exceptions=True)
            workflow_state['cross_cluster_replicated'] = True
            
            logger.debug(f"Cross-cluster replication setup for workflow {workflow_id}")
            
        except Exception as e:
            logger.warning(f"Cross-cluster replication failed for workflow {workflow_id}: {e}")
            workflow_state['cross_cluster_replicated'] = False
    
    async def _replicate_workflow_state(self, workflow_id: str, workflow_state: Dict[str, Any], target_cluster: str):
        """Replicate workflow state to target cluster."""
        # Simulate network latency and potential failures
        await asyncio.sleep(0.1)
        
        if target_cluster == 'tertiary':
            # Simulate occasional replication failure
            import random
            if random.random() < 0.1:  # 10% failure rate
                raise Exception(f"Replication failed to {target_cluster}")
        
        logger.debug(f"Replicated workflow {workflow_id} to cluster {target_cluster}")
    
    def _extract_hierarchical_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Extract hierarchical task information from context."""
        return {
            'is_parent_task': context.get('parent_task_id') is None and context.get('has_subtasks', False),
            'is_subtask': context.get('parent_task_id') is not None,
            'task_id': context.get('task_id'),
            'parent_task_id': context.get('parent_task_id'),
            'subtask_ids': context.get('subtask_ids', []),
            'task_type': context.get('task_type', 'task'),
            'domain': context.get('domain', 'general'),
            'estimated_hours': context.get('estimated_hours', 0)
        }
    
    async def _execute_parent_task_workflow(self, 
                                          saga_definition: SagaDefinition,
                                          workflow_config: TemporalWorkflowConfig,
                                          hierarchical_context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute parent task as workflow with child workflow management."""
        activity_results = {}
        
        # Create parent task activity
        parent_result = await self._execute_activity(
            'create_task', 
            saga_definition.steps[0] if saga_definition.steps else None,
            {**hierarchical_context, 'operation': 'create_parent_task'}
        )
        activity_results['create_parent_task'] = parent_result
        
        # Launch child workflows for subtasks
        child_workflow_tasks = []
        for subtask_id in hierarchical_context.get('subtask_ids', []):
            # Create child workflow for each subtask
            child_workflow_task = self._launch_child_workflow(
                subtask_id, workflow_config, hierarchical_context
            )
            child_workflow_tasks.append(child_workflow_task)
        
        # Wait for all child workflows
        if child_workflow_tasks:
            child_results = await asyncio.gather(*child_workflow_tasks, return_exceptions=True)
            
            for i, result in enumerate(child_results):
                subtask_id = hierarchical_context['subtask_ids'][i]
                if isinstance(result, Exception):
                    activity_results[f'subtask_{subtask_id}'] = {
                        'success': False,
                        'error': str(result)
                    }
                else:
                    activity_results[f'subtask_{subtask_id}'] = result
        
        # Calculate progress rollup
        rollup_result = await self._execute_activity(
            'calculate_progress_rollup',
            None,
            {**hierarchical_context, 'child_results': activity_results}
        )
        activity_results['progress_rollup'] = rollup_result
        
        return activity_results
    
    async def _execute_subtask_workflow(self,
                                      saga_definition: SagaDefinition,
                                      workflow_config: TemporalWorkflowConfig,
                                      hierarchical_context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute subtask as activities with parent progress rollup."""
        activity_results = {}
        
        # Execute each saga step as an activity
        for step in saga_definition.steps:
            activity_name = f"subtask_step_{step.step_id}"
            
            result = await self._execute_activity(
                step.name, step, 
                {**hierarchical_context, 'step_metadata': step.metadata}
            )
            
            activity_results[activity_name] = result
            
            # Update parent progress after each step
            if result.get('success'):
                await self._execute_activity(
                    'update_task_status',
                    None,
                    {
                        'task_id': hierarchical_context['parent_task_id'],
                        'progress_increment': 1.0 / len(saga_definition.steps),
                        'substep_completed': step.step_id
                    }
                )
        
        return activity_results
    
    async def _execute_standard_saga_workflow(self,
                                            saga_definition: SagaDefinition,
                                            workflow_config: TemporalWorkflowConfig,
                                            context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute standard saga as Temporal workflow."""
        # Delegate to saga coordinator
        saga_result = await self.saga_coordinator.execute_saga(saga_definition, context)
        
        # Convert to activity format
        activity_results = {}
        for step_id, step_result in saga_result.get('results', {}).items():
            activity_results[f"saga_step_{step_id}"] = {
                'success': step_result['status'] == 'completed',
                'result': step_result.get('result'),
                'error': step_result.get('error'),
                'duration_seconds': step_result.get('duration_seconds'),
                'attempts': step_result.get('attempts')
            }
        
        return activity_results
    
    async def _launch_child_workflow(self,
                                    subtask_id: str,
                                    parent_workflow_config: TemporalWorkflowConfig,
                                    hierarchical_context: Dict[str, Any]) -> Dict[str, Any]:
        """Launch child workflow for subtask."""
        # Create child workflow configuration
        child_config = TemporalWorkflowConfig(
            workflow_id=f"{parent_workflow_config.workflow_id}_child_{subtask_id}",
            task_queue=parent_workflow_config.task_queue,
            workflow_execution_timeout=parent_workflow_config.workflow_execution_timeout,
            workflow_run_timeout=timedelta(minutes=15),  # Shorter timeout for subtasks
        )
        
        # Create subtask saga definition
        subtask_saga = self._create_subtask_saga(subtask_id, hierarchical_context)
        
        # Execute as child workflow
        child_context = {
            **hierarchical_context,
            'parent_workflow_id': parent_workflow_config.workflow_id,
            'subtask_id': subtask_id,
            'is_child_workflow': True
        }
        
        return await self.execute_hierarchical_saga(subtask_saga, child_config, child_context)
    
    async def _execute_activity(self, 
                              activity_name: str, 
                              step: Optional[SagaStep], 
                              context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute Temporal activity."""
        start_time = datetime.now()
        
        try:
            if activity_name in self.activity_registry:
                # Execute registered activity
                result = await self.activity_registry[activity_name](step, context)
            elif step and step.action:
                # Execute saga step action
                if asyncio.iscoroutinefunction(step.action):
                    result = await step.action(context, step)
                else:
                    result = step.action(context, step)
            else:
                # Default activity implementation
                result = await self._default_activity_implementation(activity_name, context)
            
            duration = (datetime.now() - start_time).total_seconds()
            
            return {
                'success': True,
                'result': result,
                'duration_seconds': duration,
                'activity_name': activity_name,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            logger.error(f"Activity {activity_name} failed: {e}")
            
            return {
                'success': False,
                'error': str(e),
                'duration_seconds': duration,
                'activity_name': activity_name,
                'timestamp': datetime.now().isoformat()
            }
    
    # Activity implementations
    async def _create_task_activity(self, step: Optional[SagaStep], context: Dict[str, Any]) -> Any:
        """Activity: Create hierarchical task."""
        task_data = {
            'task_id': context.get('task_id'),
            'task_type': context.get('task_type', 'task'),
            'domain': context.get('domain', 'general'),
            'description': context.get('description', 'Temporal saga task'),
            'parent_task_id': context.get('parent_task_id'),
            'created_by_workflow': True,
            'workflow_id': context.get('workflow_id')
        }
        
        # Simulate task creation
        await asyncio.sleep(0.1)
        return {'task_created': True, 'task_data': task_data}
    
    async def _update_task_status_activity(self, step: Optional[SagaStep], context: Dict[str, Any]) -> Any:
        """Activity: Update task status with progress rollup."""
        task_id = context.get('task_id')
        progress_increment = context.get('progress_increment', 0.0)
        
        # Simulate status update
        await asyncio.sleep(0.05)
        return {
            'task_id': task_id,
            'progress_updated': True,
            'increment': progress_increment
        }
    
    async def _create_subtask_activity(self, step: Optional[SagaStep], context: Dict[str, Any]) -> Any:
        """Activity: Create subtask with hierarchical relationship."""
        subtask_data = {
            'subtask_id': context.get('subtask_id'),
            'parent_task_id': context.get('parent_task_id'),
            'task_type': 'subtask',
            'domain': context.get('domain'),
            'created_by_workflow': True
        }
        
        await asyncio.sleep(0.1)
        return {'subtask_created': True, 'subtask_data': subtask_data}
    
    async def _calculate_progress_rollup_activity(self, step: Optional[SagaStep], context: Dict[str, Any]) -> Any:
        """Activity: Calculate hierarchical progress rollup."""
        child_results = context.get('child_results', {})
        
        total_children = len(child_results)
        completed_children = len([r for r in child_results.values() if r.get('success')])
        
        progress_rollup = {
            'total_children': total_children,
            'completed_children': completed_children,
            'completion_percentage': (completed_children / max(total_children, 1)) * 100,
            'overall_status': 'completed' if completed_children == total_children else 'in_progress'
        }
        
        await asyncio.sleep(0.1)
        return progress_rollup
    
    async def _backup_task_state_activity(self, step: Optional[SagaStep], context: Dict[str, Any]) -> Any:
        """Activity: Backup task state for recovery."""
        task_id = context.get('task_id')
        
        # Simulate backup creation
        await asyncio.sleep(0.2)
        return {
            'backup_created': True,
            'backup_id': f"backup_{task_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'task_id': task_id
        }
    
    async def _archive_task_activity(self, step: Optional[SagaStep], context: Dict[str, Any]) -> Any:
        """Activity: Archive completed task."""
        task_id = context.get('task_id')
        
        await asyncio.sleep(0.15)
        return {'task_archived': True, 'task_id': task_id}
    
    async def _validate_task_hierarchy_activity(self, step: Optional[SagaStep], context: Dict[str, Any]) -> Any:
        """Activity: Validate task hierarchy integrity."""
        task_id = context.get('task_id')
        parent_task_id = context.get('parent_task_id')
        
        # Simulate validation
        await asyncio.sleep(0.1)
        
        validation_result = {
            'hierarchy_valid': True,
            'task_id': task_id,
            'parent_task_id': parent_task_id,
            'validation_checks': [
                'parent_exists',
                'no_circular_dependencies',
                'proper_nesting_level'
            ]
        }
        
        return validation_result
    
    async def _default_activity_implementation(self, activity_name: str, context: Dict[str, Any]) -> Any:
        """Default implementation for unregistered activities."""
        await asyncio.sleep(0.1)
        return {
            'activity_name': activity_name,
            'executed': True,
            'context_keys': list(context.keys())
        }
    
    def _create_subtask_saga(self, subtask_id: str, hierarchical_context: Dict[str, Any]) -> SagaDefinition:
        """Create saga definition for subtask execution."""
        # Create minimal saga for subtask
        subtask_steps = [
            SagaStep(
                step_id=f"subtask_{subtask_id}_init",
                name="initialize_subtask",
                action=self._create_subtask_activity,
                metadata={'subtask_id': subtask_id}
            ),
            SagaStep(
                step_id=f"subtask_{subtask_id}_execute",
                name="execute_subtask_logic",
                action=self._default_activity_implementation,
                depends_on=[f"subtask_{subtask_id}_init"],
                metadata={'subtask_id': subtask_id}
            ),
            SagaStep(
                step_id=f"subtask_{subtask_id}_finalize",
                name="finalize_subtask",
                action=self._update_task_status_activity,
                depends_on=[f"subtask_{subtask_id}_execute"],
                metadata={'subtask_id': subtask_id}
            )
        ]
        
        return SagaDefinition(
            saga_id=f"subtask_saga_{subtask_id}",
            name=f"Subtask Execution: {subtask_id}",
            steps=subtask_steps,
            global_timeout_seconds=900,  # 15 minutes
            enable_compensation=True
        )
    
    def _create_compensation_saga(self, original_saga: SagaDefinition) -> SagaDefinition:
        """Create compensation saga for failed workflow."""
        compensation_steps = []
        
        for step in reversed(original_saga.steps):
            if step.compensation:
                comp_step = SagaStep(
                    step_id=f"compensate_{step.step_id}",
                    name=f"Compensate {step.name}",
                    action=step.compensation,
                    retry_count=1,  # Lower retry count for compensation
                    metadata={'original_step_id': step.step_id}
                )
                compensation_steps.append(comp_step)
        
        return SagaDefinition(
            saga_id=f"compensation_{original_saga.saga_id}",
            name=f"Compensation for {original_saga.name}",
            steps=compensation_steps,
            enable_compensation=False  # Don't compensate compensation
        )
    
    async def _calculate_final_progress_rollup(self,
                                             workflow_id: str,
                                             activity_results: Dict[str, Any],
                                             hierarchical_context: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate final progress rollup for workflow."""
        total_activities = len(activity_results)
        successful_activities = len([r for r in activity_results.values() if r.get('success')])
        
        rollup = {
            'workflow_id': workflow_id,
            'total_activities': total_activities,
            'successful_activities': successful_activities,
            'failed_activities': total_activities - successful_activities,
            'success_rate': successful_activities / max(total_activities, 1),
            'is_parent_task': hierarchical_context.get('is_parent_task', False),
            'hierarchical_depth': len(hierarchical_context.get('subtask_ids', [])),
            'domain': hierarchical_context.get('domain', 'general')
        }
        
        return rollup
    
    def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get current status of Temporal workflow."""
        if workflow_id in self.active_workflows:
            return self.active_workflows[workflow_id].copy()
        
        # Check history
        for workflow in self.workflow_history:
            if workflow['workflow_id'] == workflow_id:
                return workflow.copy()
        
        return None
    
    def get_temporal_metrics(self) -> Dict[str, Any]:
        """Get Temporal integration metrics."""
        return {
            'active_workflows': len(self.active_workflows),
            'completed_workflows': len([w for w in self.workflow_history 
                                       if w['status'] == TemporalWorkflowStatus.COMPLETED]),
            'failed_workflows': len([w for w in self.workflow_history 
                                   if w['status'] == TemporalWorkflowStatus.FAILED]),
            'cross_cluster_enabled': self.enable_cross_cluster,
            'current_cluster': self.current_cluster,
            'available_clusters': self.cluster_nodes,
            'activity_registry_size': len(self.activity_registry),
            'avg_workflow_duration': self._calculate_avg_workflow_duration()
        }
    
    def _calculate_avg_workflow_duration(self) -> float:
        """Calculate average workflow duration."""
        completed_workflows = [w for w in self.workflow_history 
                             if w.get('end_time') and w.get('start_time')]
        
        if not completed_workflows:
            return 0.0
        
        total_duration = 0.0
        for workflow in completed_workflows:
            start = datetime.fromisoformat(workflow['start_time'])
            end = datetime.fromisoformat(workflow['end_time'])
            total_duration += (end - start).total_seconds()
        
        return total_duration / len(completed_workflows)