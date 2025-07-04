"""
Smart Progress Tracking with Real-Time Hierarchy Updates

Tracks task progress across hierarchical structures, automatically calculating
parent progress based on children and providing real-time updates.
"""

from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta
import statistics

# Import boss notifier if available
try:
    from .boss_notifier import BossNotifier, NotificationPriority
    BOSS_NOTIFIER_AVAILABLE = True
except ImportError:
    BOSS_NOTIFIER_AVAILABLE = False
    class NotificationPriority:
        HIGH = "high"
        MEDIUM = "medium"

# Milestone/blocker detector will be imported lazily to avoid circular imports


class TaskStatus(Enum):
    """Task status states"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class ProgressCalculationMethod(Enum):
    """Methods for calculating parent progress"""
    WEIGHTED = "weighted"      # Based on estimated hours
    SIMPLE = "simple"          # Equal weight for all children
    MILESTONE = "milestone"    # Based on key milestones


@dataclass
class TaskProgress:
    """Progress information for a task"""
    task_id: str
    status: TaskStatus
    completion_percentage: float  # 0.0 to 1.0
    estimated_hours: float
    actual_hours: float
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    children_progress: Dict[str, float]  # child_id -> completion
    is_milestone: bool = False
    blocked_by: List[str] = None


@dataclass
class ProgressUpdate:
    """Real-time progress update event"""
    task_id: str
    old_progress: float
    new_progress: float
    status_changed: bool
    old_status: Optional[TaskStatus]
    new_status: Optional[TaskStatus]
    timestamp: datetime
    triggered_by: str  # What caused the update
    parent_updates: List[Tuple[str, float]]  # Parent tasks affected


class SmartProgressTracker:
    """Tracks progress across task hierarchies with real-time updates"""
    
    def __init__(self, project_name: str):
        self.project_name = project_name
        self.task_progress: Dict[str, TaskProgress] = {}
        self.task_hierarchy: Dict[str, List[str]] = {}  # parent_id -> children
        self.parent_map: Dict[str, str] = {}  # child_id -> parent_id
        self.update_history: List[ProgressUpdate] = []
        self.milestones: Set[str] = set()
        
        # Initialize boss notifier if available
        if BOSS_NOTIFIER_AVAILABLE:
            self.boss_notifier = BossNotifier()
        else:
            self.boss_notifier = None
            
        # Milestone/blocker detector will be initialized lazily
        self._detector = None
    
    def register_task(self, 
                      task_id: str,
                      parent_id: Optional[str] = None,
                      estimated_hours: float = 0,
                      is_milestone: bool = False) -> TaskProgress:
        """
        Register a task in the progress tracking system.
        
        Args:
            task_id: Unique task identifier
            parent_id: Parent task ID if this is a subtask
            estimated_hours: Estimated hours for completion
            is_milestone: Whether this is a milestone task
            
        Returns:
            TaskProgress object for the registered task
        """
        # Create progress entry
        progress = TaskProgress(
            task_id=task_id,
            status=TaskStatus.PENDING,
            completion_percentage=0.0,
            estimated_hours=estimated_hours,
            actual_hours=0.0,
            started_at=None,
            completed_at=None,
            children_progress={},
            is_milestone=is_milestone,
            blocked_by=[]
        )
        
        self.task_progress[task_id] = progress
        
        # Update hierarchy
        if parent_id:
            if parent_id not in self.task_hierarchy:
                self.task_hierarchy[parent_id] = []
            self.task_hierarchy[parent_id].append(task_id)
            self.parent_map[task_id] = parent_id
            
            # Add to parent's children progress
            if parent_id in self.task_progress:
                self.task_progress[parent_id].children_progress[task_id] = 0.0
        
        # Track milestones
        if is_milestone:
            self.milestones.add(task_id)
        
        return progress
    
    def update_task_progress(self,
                            task_id: str,
                            completion_percentage: Optional[float] = None,
                            status: Optional[TaskStatus] = None,
                            actual_hours: Optional[float] = None,
                            trigger_reason: str = "manual_update") -> ProgressUpdate:
        """
        Update task progress and propagate changes up the hierarchy.
        
        Args:
            task_id: Task to update
            completion_percentage: New completion percentage (0.0-1.0)
            status: New status
            actual_hours: Actual hours spent
            trigger_reason: What triggered this update
            
        Returns:
            ProgressUpdate with all changes
        """
        if task_id not in self.task_progress:
            raise ValueError(f"Task {task_id} not found in progress tracker")
        
        task = self.task_progress[task_id]
        old_progress = task.completion_percentage
        old_status = task.status
        
        # Track what changed
        status_changed = False
        progress_changed = False
        
        # Update completion percentage
        if completion_percentage is not None:
            task.completion_percentage = max(0.0, min(1.0, completion_percentage))
            progress_changed = old_progress != task.completion_percentage
        
        # Update status
        if status is not None:
            task.status = status
            status_changed = old_status != status
            
            # Handle status-based progress updates
            if status == TaskStatus.COMPLETED:
                task.completion_percentage = 1.0
                task.completed_at = datetime.now()
                progress_changed = True
            elif status == TaskStatus.IN_PROGRESS and task.started_at is None:
                task.started_at = datetime.now()
                if task.completion_percentage == 0:
                    task.completion_percentage = 0.1  # Minimum progress for started tasks
                    progress_changed = True
        
        # Update actual hours
        if actual_hours is not None:
            task.actual_hours = actual_hours
        
        # Create update record
        update = ProgressUpdate(
            task_id=task_id,
            old_progress=old_progress,
            new_progress=task.completion_percentage,
            status_changed=status_changed,
            old_status=old_status if status_changed else None,
            new_status=task.status if status_changed else None,
            timestamp=datetime.now(),
            triggered_by=trigger_reason,
            parent_updates=[]
        )
        
        # Propagate to parents if progress changed
        if progress_changed or status_changed:
            self._propagate_progress_to_parents(task_id, update)
        
        # Record history
        self.update_history.append(update)
        
        # Send notifications for significant changes
        self._send_progress_notifications(update)
        
        return update
    
    def _propagate_progress_to_parents(self, task_id: str, update: ProgressUpdate):
        """Propagate progress changes up the task hierarchy"""
        if task_id not in self.parent_map:
            return
        
        parent_id = self.parent_map[task_id]
        parent = self.task_progress.get(parent_id)
        
        if not parent:
            return
        
        # Update parent's record of child progress
        parent.children_progress[task_id] = self.task_progress[task_id].completion_percentage
        
        # Calculate new parent progress
        old_parent_progress = parent.completion_percentage
        new_parent_progress = self._calculate_parent_progress(parent_id)
        
        # Check if all children are complete for automatic parent completion
        all_children_complete = self._check_all_children_complete(parent_id)
        
        # Store old status for comparison
        old_parent_status = parent.status
        
        if new_parent_progress != old_parent_progress:
            parent.completion_percentage = new_parent_progress
            update.parent_updates.append((parent_id, new_parent_progress))
            
            # Update parent status based on completion
            if all_children_complete and parent.status != TaskStatus.COMPLETED:
                # All children complete - automatically complete parent
                parent.status = TaskStatus.COMPLETED
                parent.completed_at = datetime.now()
                parent.completion_percentage = 1.0
                
                # Send notification about automatic completion
                if self.boss_notifier:
                    # Get child task names for the notification
                    completed_children = [child_id for child_id in self.task_hierarchy.get(parent_id, [])]
                    self.boss_notifier.notify_task_progress(
                        task_id=parent_id,
                        task_name=f"Auto-completed: {parent_id}",
                        completion_percentage=100,
                        completed_subtasks=completed_children,
                        remaining_subtasks=[]
                    )
            elif new_parent_progress == 1.0 and parent.status != TaskStatus.COMPLETED:
                # Progress calculation shows 100% - complete parent
                parent.status = TaskStatus.COMPLETED
                parent.completed_at = datetime.now()
            elif new_parent_progress > 0 and parent.status == TaskStatus.PENDING:
                parent.status = TaskStatus.IN_PROGRESS
                if parent.started_at is None:
                    parent.started_at = datetime.now()
            
            # Check if parent was unblocked due to children completion
            if old_parent_status == TaskStatus.BLOCKED and all_children_complete:
                # Automatically unblock parent when all blocking children are complete
                parent.status = TaskStatus.COMPLETED
                parent.blocked_by = []
                parent.completed_at = datetime.now()
                parent.completion_percentage = 1.0
                
                if self.boss_notifier:
                    # Get child task names for the notification
                    completed_children = [child_id for child_id in self.task_hierarchy.get(parent_id, [])]
                    self.boss_notifier.notify_task_progress(
                        task_id=parent_id,
                        task_name=f"Auto-unblocked and completed: {parent_id}",
                        completion_percentage=100,
                        completed_subtasks=completed_children,
                        remaining_subtasks=[]
                    )
            
            # Recursively propagate to grandparents
            self._propagate_progress_to_parents(parent_id, update)
    
    def _check_all_children_complete(self, parent_id: str) -> bool:
        """
        Check if all children of a parent task are complete.
        
        Args:
            parent_id: Parent task ID to check
            
        Returns:
            True if all children are complete, False otherwise
        """
        children_ids = self.task_hierarchy.get(parent_id, [])
        
        if not children_ids:
            # No children, check parent's own status
            parent = self.task_progress.get(parent_id)
            return parent and parent.completion_percentage >= 1.0
        
        # Check all children
        for child_id in children_ids:
            child = self.task_progress.get(child_id)
            if not child or child.status != TaskStatus.COMPLETED:
                return False
        
        return True
    
    def _calculate_parent_progress(self, 
                                   parent_id: str,
                                   method: ProgressCalculationMethod = ProgressCalculationMethod.WEIGHTED) -> float:
        """
        Calculate parent progress based on children.
        
        Args:
            parent_id: Parent task ID
            method: Calculation method to use
            
        Returns:
            Progress percentage (0.0-1.0)
        """
        parent = self.task_progress.get(parent_id)
        if not parent:
            return 0.0
        
        children_ids = self.task_hierarchy.get(parent_id, [])
        if not children_ids:
            # No children, use parent's own progress
            return parent.completion_percentage
        
        children_progress = []
        children_weights = []
        
        for child_id in children_ids:
            child = self.task_progress.get(child_id)
            if child:
                children_progress.append(child.completion_percentage)
                
                if method == ProgressCalculationMethod.WEIGHTED:
                    # Weight by estimated hours
                    weight = child.estimated_hours if child.estimated_hours > 0 else 1.0
                    children_weights.append(weight)
                elif method == ProgressCalculationMethod.MILESTONE:
                    # Milestones have higher weight
                    weight = 3.0 if child.is_milestone else 1.0
                    children_weights.append(weight)
                else:  # SIMPLE
                    children_weights.append(1.0)
        
        if not children_progress:
            return parent.completion_percentage
        
        # Calculate weighted average
        if sum(children_weights) > 0:
            weighted_progress = sum(p * w for p, w in zip(children_progress, children_weights))
            return weighted_progress / sum(children_weights)
        else:
            return statistics.mean(children_progress)
    
    def get_hierarchy_progress(self, root_task_id: str) -> Dict[str, Any]:
        """
        Get complete progress information for a task hierarchy.
        
        Args:
            root_task_id: Root task to start from
            
        Returns:
            Hierarchical progress information
        """
        def build_tree(task_id: str) -> Dict[str, Any]:
            task = self.task_progress.get(task_id)
            if not task:
                return {}
            
            children = []
            for child_id in self.task_hierarchy.get(task_id, []):
                child_tree = build_tree(child_id)
                if child_tree:
                    children.append(child_tree)
            
            return {
                "task_id": task_id,
                "status": task.status.value,
                "completion": round(task.completion_percentage * 100, 1),
                "estimated_hours": task.estimated_hours,
                "actual_hours": task.actual_hours,
                "is_milestone": task.is_milestone,
                "started_at": task.started_at.isoformat() if task.started_at else None,
                "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                "children": children
            }
        
        return build_tree(root_task_id)
    
    def identify_blockers(self) -> List[Dict[str, Any]]:
        """Identify tasks that are blocking progress"""
        blockers = []
        
        for task_id, task in self.task_progress.items():
            if task.status == TaskStatus.BLOCKED:
                # Find what's blocking this task
                blocking_info = {
                    "task_id": task_id,
                    "blocked_by": task.blocked_by,
                    "impact": self._calculate_blocker_impact(task_id),
                    "is_milestone": task.is_milestone,
                    "days_blocked": self._calculate_blocked_duration(task)
                }
                blockers.append(blocking_info)
        
        # Sort by impact
        blockers.sort(key=lambda x: x["impact"], reverse=True)
        
        return blockers
    
    def _calculate_blocker_impact(self, blocked_task_id: str) -> int:
        """Calculate how many tasks are impacted by this blocker"""
        impacted = set()
        to_check = [blocked_task_id]
        
        while to_check:
            task_id = to_check.pop(0)
            if task_id in impacted:
                continue  # Already processed
                
            impacted.add(task_id)
            
            # Add all children to check
            for child_id in self.task_hierarchy.get(task_id, []):
                if child_id not in impacted:
                    to_check.append(child_id)
            
            # Add all tasks that depend on this
            for other_id, other_task in self.task_progress.items():
                if task_id in other_task.blocked_by and other_id not in impacted:
                    to_check.append(other_id)
        
        return len(impacted)
    
    def _calculate_blocked_duration(self, task: TaskProgress) -> int:
        """Calculate how many days a task has been blocked"""
        if task.status != TaskStatus.BLOCKED or not task.started_at:
            return 0
        
        # Look for when it became blocked
        blocked_since = task.started_at
        for update in reversed(self.update_history):
            if update.task_id == task.task_id and update.new_status == TaskStatus.BLOCKED:
                blocked_since = update.timestamp
                break
        
        return (datetime.now() - blocked_since).days
    
    def get_milestone_status(self) -> List[Dict[str, Any]]:
        """Get status of all milestone tasks"""
        milestones = []
        
        for milestone_id in self.milestones:
            task = self.task_progress.get(milestone_id)
            if task:
                # Calculate days until/since milestone
                if task.status == TaskStatus.COMPLETED:
                    days_offset = (datetime.now() - task.completed_at).days
                    time_status = f"Completed {days_offset} days ago"
                else:
                    # Estimate completion based on current progress
                    if task.completion_percentage > 0 and task.started_at:
                        elapsed = (datetime.now() - task.started_at).total_seconds() / 3600
                        if task.completion_percentage > 0:
                            estimated_total = elapsed / task.completion_percentage
                            remaining_hours = estimated_total - elapsed
                            days_remaining = remaining_hours / 24
                            time_status = f"~{int(days_remaining)} days remaining"
                        else:
                            time_status = "Not started"
                    else:
                        time_status = "Not started"
                
                milestones.append({
                    "task_id": milestone_id,
                    "status": task.status.value,
                    "completion": round(task.completion_percentage * 100, 1),
                    "time_status": time_status,
                    "blocked": task.status == TaskStatus.BLOCKED,
                    "children_count": len(self.task_hierarchy.get(milestone_id, []))
                })
        
        return milestones
    
    def _send_progress_notifications(self, update: ProgressUpdate):
        """Send notifications for significant progress changes"""
        if not self.boss_notifier:
            return
        
        task = self.task_progress.get(update.task_id)
        if not task:
            return
        
        # Milestone completion
        if task.is_milestone and update.new_status == TaskStatus.COMPLETED:
            # Get subtasks for the milestone
            completed_subtasks = [child_id for child_id in self.task_hierarchy.get(update.task_id, [])]
            self.boss_notifier.notify_task_progress(
                task_id=update.task_id,
                task_name=f"Milestone: {update.task_id}",
                completion_percentage=100,
                completed_subtasks=completed_subtasks,
                remaining_subtasks=[]
            )
        
        # Task blocked
        elif update.new_status == TaskStatus.BLOCKED:
            blocker_impact = self._calculate_blocker_impact(update.task_id)
            self.boss_notifier.notify_blocker(
                task_id=update.task_id,
                task_name=update.task_id,
                blocker_description=f"Task has {blocker_impact} dependent tasks blocked",
                blocker_type="dependency" if blocker_impact > 5 else "standard",
                suggested_solutions=["Review blocking dependencies", "Escalate if critical path", f"Unblock {blocker_impact} dependent tasks"]
            )
        
        # Significant progress jumps
        elif abs(update.new_progress - update.old_progress) > 0.25:
            # Get subtask information
            completed_subtasks = []
            remaining_subtasks = []
            for child_id in self.task_hierarchy.get(update.task_id, []):
                child = self.task_progress.get(child_id)
                if child and child.status == TaskStatus.COMPLETED:
                    completed_subtasks.append(child_id)
                elif child:
                    remaining_subtasks.append(child_id)
                    
            self.boss_notifier.notify_task_progress(
                task_id=update.task_id,
                task_name=update.task_id,
                completion_percentage=update.new_progress * 100,
                completed_subtasks=completed_subtasks,
                remaining_subtasks=remaining_subtasks
            )
    
    def mark_task_blocked(self, task_id: str, blocked_by: List[str], reason: str = ""):
        """Mark a task as blocked by other tasks"""
        if task_id in self.task_progress:
            task = self.task_progress[task_id]
            task.status = TaskStatus.BLOCKED
            task.blocked_by = blocked_by
            
            # Create update
            update = ProgressUpdate(
                task_id=task_id,
                old_progress=task.completion_percentage,
                new_progress=task.completion_percentage,
                status_changed=True,
                old_status=task.status,
                new_status=TaskStatus.BLOCKED,
                timestamp=datetime.now(),
                triggered_by=f"blocked_by: {', '.join(blocked_by)} - {reason}",
                parent_updates=[]
            )
            
            self.update_history.append(update)
            self._send_progress_notifications(update)
    
    def unblock_task(self, task_id: str):
        """Remove blocked status from a task"""
        if task_id in self.task_progress:
            task = self.task_progress[task_id]
            if task.status == TaskStatus.BLOCKED:
                # Restore to in progress or pending
                new_status = TaskStatus.IN_PROGRESS if task.completion_percentage > 0 else TaskStatus.PENDING
                task.status = new_status
                task.blocked_by = []
                
                # Create update
                update = ProgressUpdate(
                    task_id=task_id,
                    old_progress=task.completion_percentage,
                    new_progress=task.completion_percentage,
                    status_changed=True,
                    old_status=TaskStatus.BLOCKED,
                    new_status=new_status,
                    timestamp=datetime.now(),
                    triggered_by="unblocked",
                    parent_updates=[]
                )
                
                self.update_history.append(update)
    
    def check_and_update_parent_completion(self, parent_id: str) -> bool:
        """
        Explicitly check if a parent should be marked complete based on children.
        
        Args:
            parent_id: Parent task ID to check
            
        Returns:
            True if parent was updated to complete, False otherwise
        """
        parent = self.task_progress.get(parent_id)
        if not parent or parent.status == TaskStatus.COMPLETED:
            return False
        
        if self._check_all_children_complete(parent_id):
            # Update parent to complete
            old_status = parent.status
            parent.status = TaskStatus.COMPLETED
            parent.completion_percentage = 1.0
            parent.completed_at = datetime.now()
            
            # Create update record
            update = ProgressUpdate(
                task_id=parent_id,
                old_progress=parent.completion_percentage,
                new_progress=1.0,
                status_changed=True,
                old_status=old_status,
                new_status=TaskStatus.COMPLETED,
                timestamp=datetime.now(),
                triggered_by="auto_parent_completion",
                parent_updates=[]
            )
            
            self.update_history.append(update)
            
            # Send notification
            if self.boss_notifier:
                # Get child task names for the notification
                completed_children = [child_id for child_id in self.task_hierarchy.get(parent_id, [])]
                self.boss_notifier.notify_task_progress(
                    task_id=parent_id,
                    task_name=f"Auto-completed: {parent_id}",
                    completion_percentage=100,
                    completed_subtasks=completed_children,
                    remaining_subtasks=[]
                )
            
            # Propagate to grandparents
            self._propagate_progress_to_parents(parent_id, update)
            
            return True
        
        return False
    
    def batch_check_parent_completions(self) -> List[str]:
        """
        Check all parent tasks and update any that should be complete.
        
        Returns:
            List of parent task IDs that were updated to complete
        """
        updated_parents = []
        
        # Find all parent tasks
        parent_tasks = set()
        for parent_id in self.task_hierarchy.keys():
            if parent_id in self.task_progress:
                parent_tasks.add(parent_id)
        
        # Check each parent
        for parent_id in parent_tasks:
            if self.check_and_update_parent_completion(parent_id):
                updated_parents.append(parent_id)
        
        return updated_parents
    
    @property
    def detector(self):
        """Lazy load milestone/blocker detector to avoid circular imports"""
        if self._detector is None:
            try:
                from .milestone_blocker_detector import MilestoneBlockerDetector
                self._detector = MilestoneBlockerDetector(self)
            except ImportError:
                pass
        return self._detector
    
    def run_milestone_blocker_detection(self,
                                       target_dates: Optional[Dict[str, datetime]] = None,
                                       send_notifications: bool = True) -> Dict[str, Any]:
        """
        Run milestone and blocker detection cycle.
        
        Args:
            target_dates: Optional milestone target dates
            send_notifications: Whether to send notifications
            
        Returns:
            Detection summary
        """
        if self.detector:
            return self.detector.run_detection_cycle(target_dates, send_notifications)
        else:
            return {
                "error": "Milestone/blocker detector not available",
                "milestone_alerts": 0,
                "blocker_alerts": 0
            }
    
    def get_milestone_risks(self, 
                           target_dates: Optional[Dict[str, datetime]] = None) -> List[Any]:
        """Get current milestone risks"""
        if self.detector:
            return self.detector.detect_milestone_risks(target_dates)
        return []
    
    def get_critical_blockers(self) -> List[Any]:
        """Get current critical blockers"""
        if self.detector:
            return self.detector.detect_critical_blockers()
        return []
    
    def get_milestone_blocker_dashboard(self) -> Dict[str, Any]:
        """Get dashboard summary of milestones and blockers"""
        if self.detector:
            return self.detector.get_dashboard_summary()
        return {
            "error": "Milestone/blocker detector not available",
            "overview": {},
            "milestones": {},
            "blockers": {}
        }
    
    def get_progress_summary(self) -> Dict[str, Any]:
        """Get overall progress summary for the project"""
        total_tasks = len(self.task_progress)
        completed_tasks = sum(1 for t in self.task_progress.values() if t.status == TaskStatus.COMPLETED)
        blocked_tasks = sum(1 for t in self.task_progress.values() if t.status == TaskStatus.BLOCKED)
        in_progress_tasks = sum(1 for t in self.task_progress.values() if t.status == TaskStatus.IN_PROGRESS)
        
        # Calculate overall progress
        all_progress = [t.completion_percentage for t in self.task_progress.values()]
        overall_progress = statistics.mean(all_progress) if all_progress else 0.0
        
        # Estimate completion
        total_estimated = sum(t.estimated_hours for t in self.task_progress.values())
        total_actual = sum(t.actual_hours for t in self.task_progress.values())
        
        return {
            "total_tasks": total_tasks,
            "completed": completed_tasks,
            "in_progress": in_progress_tasks,
            "blocked": blocked_tasks,
            "pending": total_tasks - completed_tasks - in_progress_tasks - blocked_tasks,
            "overall_progress": round(overall_progress * 100, 1),
            "total_estimated_hours": total_estimated,
            "total_actual_hours": total_actual,
            "efficiency_ratio": total_actual / total_estimated if total_estimated > 0 else 1.0,
            "milestone_count": len(self.milestones),
            "milestones_completed": sum(1 for m in self.milestones if self.task_progress.get(m, {}).status == TaskStatus.COMPLETED)
        }