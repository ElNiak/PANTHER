"""
Progress Tracking Automation with Smart Milestone Detection

Provides automated progress tracking with intelligent milestone detection,
completion percentage calculation, and pattern-based learning for better 
project timeline estimation.
"""

from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json
import statistics

from .progress_tracker import SmartProgressTracker, TaskStatus, ProgressUpdate


class MilestoneType(Enum):
    """Types of milestones that can be automatically detected"""
    PROGRESS_QUARTER = "25%"      # 25% completion
    PROGRESS_HALF = "50%"         # 50% completion  
    PROGRESS_THREE_QUARTER = "75%"  # 75% completion
    PROGRESS_COMPLETE = "100%"    # 100% completion
    TIME_CHECKPOINT = "time"      # Time-based milestone
    DEPENDENCY_GATE = "dependency"  # All dependencies complete


@dataclass
class MilestoneEvent:
    """Represents a milestone achievement"""
    task_id: str
    milestone_type: MilestoneType
    achieved_at: datetime
    completion_percentage: float
    estimated_vs_actual: Optional[float] = None  # Ratio of actual vs estimated time
    impact_score: float = 0.0  # How important this milestone is
    pattern_learned: Optional[str] = None  # Pattern extracted for future use


@dataclass
class ProgressPattern:
    """Learned patterns from task completion"""
    pattern_name: str
    task_type: str
    domain: str
    average_velocity: float  # Progress per hour
    milestone_timing: Dict[str, float]  # Milestone -> typical percentage of total time
    accuracy_score: float  # How accurate predictions using this pattern are
    sample_count: int  # Number of tasks this pattern is based on
    last_updated: datetime = field(default_factory=datetime.now)


@dataclass
class ProgressAlert:
    """Alert for progress tracking events"""
    alert_type: str  # "milestone", "delay", "acceleration", "blocker"
    task_id: str
    message: str
    severity: str  # "info", "warning", "critical"
    suggested_actions: List[str]
    created_at: datetime = field(default_factory=datetime.now)


class ProgressTrackingAutomation:
    """Automated progress tracking with smart milestone detection"""
    
    def __init__(self, project_name: str, storage_manager=None):
        self.project_name = project_name
        self.storage_manager = storage_manager
        self.progress_tracker = SmartProgressTracker(project_name)
        
        # Milestone tracking
        self.milestone_thresholds = [0.25, 0.50, 0.75, 1.00]
        self.milestone_history: Dict[str, List[MilestoneEvent]] = {}
        self.pattern_database: Dict[str, ProgressPattern] = {}
        self.alerts: List[ProgressAlert] = []
        
        # Load existing data
        self._load_historical_data()
    
    def track_progress_milestones(self, 
                                task_id: str,
                                current_completion: Optional[float] = None,
                                status: Optional[str] = None,
                                context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Main MCP function for automated progress tracking with milestone detection.
        
        Args:
            task_id: Task to track
            current_completion: Current completion percentage (0.0-1.0)
            status: Current task status
            context: Additional context information
            
        Returns:
            Progress tracking results with milestone detection
        """
        results = {
            "task_id": task_id,
            "milestones_detected": [],
            "alerts_generated": [],
            "patterns_learned": [],
            "next_milestone": None,
            "estimated_completion": None,
            "velocity_analysis": None
        }
        
        try:
            # Convert status string to TaskStatus enum if provided
            task_status = None
            if status:
                status_map = {
                    "planning": TaskStatus.PENDING,
                    "active": TaskStatus.IN_PROGRESS,
                    "blocked": TaskStatus.BLOCKED,
                    "completed": TaskStatus.COMPLETED,
                    "archived": TaskStatus.ARCHIVED
                }
                task_status = status_map.get(status, TaskStatus.PENDING)
            
            # Update progress in tracker
            if current_completion is not None or task_status is not None:
                update = self.progress_tracker.update_task_progress(
                    task_id=task_id,
                    completion_percentage=current_completion,
                    status=task_status,
                    trigger_reason="automated_milestone_tracking"
                )
                
                # Detect milestones
                milestones = self._detect_milestones(task_id, update)
                results["milestones_detected"] = [
                    {
                        "type": m.milestone_type.value,
                        "achieved_at": m.achieved_at.isoformat(),
                        "completion": m.completion_percentage,
                        "impact_score": m.impact_score
                    } for m in milestones
                ]
                
                # Generate alerts
                alerts = self._generate_progress_alerts(task_id, update, milestones)
                results["alerts_generated"] = [
                    {
                        "type": a.alert_type,
                        "message": a.message,
                        "severity": a.severity,
                        "actions": a.suggested_actions
                    } for a in alerts
                ]
                
                # Learn patterns
                patterns = self._learn_progress_patterns(task_id, milestones)
                results["patterns_learned"] = [p.pattern_name for p in patterns]
            
            # Calculate next milestone and estimates
            next_milestone = self._calculate_next_milestone(task_id)
            if next_milestone:
                results["next_milestone"] = {
                    "type": next_milestone["type"],
                    "target_completion": next_milestone["target"],
                    "estimated_date": next_milestone["estimated_date"].isoformat()
                }
            
            # Velocity analysis
            velocity = self._analyze_task_velocity(task_id)
            if velocity:
                results["velocity_analysis"] = velocity
            
            # Estimated completion
            completion_estimate = self._estimate_completion_date(task_id)
            if completion_estimate:
                results["estimated_completion"] = completion_estimate.isoformat()
            
            # Save progress data
            self._save_progress_data()
            
            return results
            
        except Exception as e:
            return {
                "error": f"Progress tracking failed: {str(e)}",
                "task_id": task_id
            }
    
    def _detect_milestones(self, task_id: str, update: ProgressUpdate) -> List[MilestoneEvent]:
        """Detect milestone achievements based on progress update"""
        milestones = []
        
        # Progress-based milestones
        for threshold in self.milestone_thresholds:
            if (update.old_progress < threshold <= update.new_progress):
                milestone_type = {
                    0.25: MilestoneType.PROGRESS_QUARTER,
                    0.50: MilestoneType.PROGRESS_HALF, 
                    0.75: MilestoneType.PROGRESS_THREE_QUARTER,
                    1.00: MilestoneType.PROGRESS_COMPLETE
                }[threshold]
                
                milestone = MilestoneEvent(
                    task_id=task_id,
                    milestone_type=milestone_type,
                    achieved_at=update.timestamp,
                    completion_percentage=threshold,
                    impact_score=self._calculate_milestone_impact(task_id, threshold)
                )
                
                milestones.append(milestone)
                
                # Add to history
                if task_id not in self.milestone_history:
                    self.milestone_history[task_id] = []
                self.milestone_history[task_id].append(milestone)
        
        # Status-based milestones
        if update.status_changed:
            if update.new_status == TaskStatus.COMPLETED:
                completion_milestone = MilestoneEvent(
                    task_id=task_id,
                    milestone_type=MilestoneType.PROGRESS_COMPLETE,
                    achieved_at=update.timestamp,
                    completion_percentage=1.0,
                    impact_score=self._calculate_milestone_impact(task_id, 1.0)
                )
                milestones.append(completion_milestone)
        
        return milestones
    
    def _calculate_milestone_impact(self, task_id: str, completion_threshold: float) -> float:
        """Calculate impact score for a milestone (0.0-1.0)"""
        # Get task from progress tracker
        task = self.progress_tracker.task_progress.get(task_id)
        if not task:
            return 0.5
        
        impact = 0.0
        
        # Base impact from completion threshold
        impact += completion_threshold * 0.4
        
        # Impact from milestone status
        if task.is_milestone:
            impact += 0.3
        
        # Impact from children count
        children_count = len(self.progress_tracker.task_hierarchy.get(task_id, []))
        if children_count > 0:
            impact += min(children_count * 0.05, 0.2)
        
        # Impact from estimated hours (larger tasks = higher impact)
        if task.estimated_hours > 0:
            normalized_hours = min(task.estimated_hours / 40, 1.0)  # Normalize to work weeks
            impact += normalized_hours * 0.1
        
        return min(impact, 1.0)
    
    def _generate_progress_alerts(self, 
                                task_id: str, 
                                update: ProgressUpdate, 
                                milestones: List[MilestoneEvent]) -> List[ProgressAlert]:
        """Generate alerts based on progress updates and milestones"""
        alerts = []
        
        # Milestone achievement alerts
        for milestone in milestones:
            if milestone.impact_score > 0.7:
                alerts.append(ProgressAlert(
                    alert_type="milestone",
                    task_id=task_id,
                    message=f"High-impact milestone achieved: {milestone.milestone_type.value} completion",
                    severity="info",
                    suggested_actions=[
                        "Review progress with stakeholders",
                        "Update project timeline estimates",
                        "Celebrate team achievement"
                    ]
                ))
        
        # Progress velocity alerts
        velocity = self._analyze_task_velocity(task_id)
        if velocity:
            if velocity["trend"] == "accelerating" and velocity["change_factor"] > 1.5:
                alerts.append(ProgressAlert(
                    alert_type="acceleration", 
                    task_id=task_id,
                    message=f"Task accelerating: {velocity['change_factor']:.1f}x faster than expected",
                    severity="info",
                    suggested_actions=[
                        "Capture acceleration factors for future estimates",
                        "Consider reallocating resources to other tasks"
                    ]
                ))
            elif velocity["trend"] == "slowing" and velocity["change_factor"] < 0.5:
                alerts.append(ProgressAlert(
                    alert_type="delay",
                    task_id=task_id, 
                    message=f"Task slowing: {velocity['change_factor']:.1f}x slower than expected",
                    severity="warning",
                    suggested_actions=[
                        "Investigate blocking factors",
                        "Consider additional resources",
                        "Review task complexity assumptions"
                    ]
                ))
        
        # Parent completion opportunity alerts
        for parent_id, parent_progress in update.parent_updates:
            if parent_progress > 0.9:
                alerts.append(ProgressAlert(
                    alert_type="milestone",
                    task_id=parent_id,
                    message=f"Parent task near completion: {parent_progress*100:.0f}%",
                    severity="info", 
                    suggested_actions=[
                        "Complete remaining subtasks",
                        "Prepare for next milestone",
                        "Update stakeholders on progress"
                    ]
                ))
        
        # Add alerts to global list
        self.alerts.extend(alerts)
        
        return alerts
    
    def _learn_progress_patterns(self, task_id: str, milestones: List[MilestoneEvent]) -> List[ProgressPattern]:
        """Learn patterns from milestone achievements"""
        patterns = []
        
        # Get task context
        task = self.progress_tracker.task_progress.get(task_id)
        if not task:
            return patterns
        
        # Only learn from completed tasks
        if task.status != TaskStatus.COMPLETED:
            return patterns
        
        # Extract pattern characteristics
        task_context = self._extract_task_context(task_id)
        pattern_key = f"{task_context['domain']}_{task_context['type']}"
        
        # Calculate velocity and timing
        if task.started_at and task.completed_at:
            total_duration = (task.completed_at - task.started_at).total_seconds() / 3600
            velocity = 1.0 / total_duration if total_duration > 0 else 0
            
            # Calculate milestone timing
            milestone_timing = {}
            for milestone in self.milestone_history.get(task_id, []):
                if milestone.milestone_type in [MilestoneType.PROGRESS_QUARTER, 
                                              MilestoneType.PROGRESS_HALF,
                                              MilestoneType.PROGRESS_THREE_QUARTER]:
                    time_to_milestone = (milestone.achieved_at - task.started_at).total_seconds() / 3600
                    timing_ratio = time_to_milestone / total_duration if total_duration > 0 else 0
                    milestone_timing[milestone.milestone_type.value] = timing_ratio
            
            # Update or create pattern
            if pattern_key in self.pattern_database:
                existing = self.pattern_database[pattern_key]
                # Weighted average update
                weight = 1.0 / (existing.sample_count + 1)
                existing.average_velocity = (existing.average_velocity * (1 - weight)) + (velocity * weight)
                
                # Update milestone timing
                for milestone_type, timing in milestone_timing.items():
                    if milestone_type in existing.milestone_timing:
                        existing.milestone_timing[milestone_type] = (
                            existing.milestone_timing[milestone_type] * (1 - weight) + timing * weight
                        )
                    else:
                        existing.milestone_timing[milestone_type] = timing
                
                existing.sample_count += 1
                existing.last_updated = datetime.now()
                patterns.append(existing)
            else:
                # Create new pattern
                new_pattern = ProgressPattern(
                    pattern_name=pattern_key,
                    task_type=task_context['type'],
                    domain=task_context['domain'], 
                    average_velocity=velocity,
                    milestone_timing=milestone_timing,
                    accuracy_score=0.5,  # Start with neutral accuracy
                    sample_count=1
                )
                self.pattern_database[pattern_key] = new_pattern
                patterns.append(new_pattern)
        
        return patterns
    
    def _extract_task_context(self, task_id: str) -> Dict[str, str]:
        """Extract context information from task ID and metadata"""
        # Parse task ID for context clues
        parts = task_id.split("_")
        
        context = {
            "domain": "general",
            "type": "task"
        }
        
        # Extract domain and type from task ID structure
        if len(parts) >= 4:
            if "TASK" in parts:
                task_index = parts.index("TASK")
                if task_index + 1 < len(parts):
                    context["domain"] = parts[task_index + 1]
            
            if "SUBTASK" in task_id:
                context["type"] = "subtask"
            elif "SUBSUBTASK" in task_id:
                context["type"] = "subsubtask"
            elif "TASK" in task_id:
                context["type"] = "task"
        
        return context
    
    def _calculate_next_milestone(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Calculate next milestone for a task"""
        task = self.progress_tracker.task_progress.get(task_id)
        if not task:
            return None
        
        current_progress = task.completion_percentage
        
        # Find next threshold
        next_threshold = None
        for threshold in self.milestone_thresholds:
            if current_progress < threshold:
                next_threshold = threshold
                break
        
        if not next_threshold:
            return None
        
        # Estimate when milestone will be reached
        estimated_date = self._estimate_milestone_date(task_id, next_threshold)
        
        milestone_types = {
            0.25: "25% Completion",
            0.50: "50% Completion", 
            0.75: "75% Completion",
            1.00: "Task Complete"
        }
        
        return {
            "type": milestone_types.get(next_threshold, "Unknown"),
            "target": next_threshold,
            "estimated_date": estimated_date
        }
    
    def _estimate_milestone_date(self, task_id: str, target_completion: float) -> datetime:
        """Estimate when a milestone will be reached"""
        task = self.progress_tracker.task_progress.get(task_id)
        if not task:
            return datetime.now() + timedelta(days=7)  # Default estimate
        
        current_progress = task.completion_percentage
        remaining_progress = target_completion - current_progress
        
        # Calculate velocity from pattern database
        task_context = self._extract_task_context(task_id)
        pattern_key = f"{task_context['domain']}_{task_context['type']}"
        
        if pattern_key in self.pattern_database:
            pattern = self.pattern_database[pattern_key]
            estimated_hours = remaining_progress / pattern.average_velocity if pattern.average_velocity > 0 else 40
        else:
            # Fallback estimate based on task size
            estimated_hours = remaining_progress * task.estimated_hours if task.estimated_hours > 0 else 20
        
        return datetime.now() + timedelta(hours=estimated_hours)
    
    def _analyze_task_velocity(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Analyze current task velocity compared to patterns"""
        task = self.progress_tracker.task_progress.get(task_id)
        if not task or not task.started_at:
            return None
        
        elapsed_hours = (datetime.now() - task.started_at).total_seconds() / 3600
        current_velocity = task.completion_percentage / elapsed_hours if elapsed_hours > 0 else 0
        
        # Compare to pattern velocity
        task_context = self._extract_task_context(task_id)
        pattern_key = f"{task_context['domain']}_{task_context['type']}"
        
        if pattern_key in self.pattern_database:
            pattern = self.pattern_database[pattern_key]
            expected_velocity = pattern.average_velocity
            change_factor = current_velocity / expected_velocity if expected_velocity > 0 else 1.0
            
            if change_factor > 1.2:
                trend = "accelerating"
            elif change_factor < 0.8:
                trend = "slowing"
            else:
                trend = "on_track"
            
            return {
                "current_velocity": current_velocity,
                "expected_velocity": expected_velocity,
                "change_factor": change_factor,
                "trend": trend
            }
        
        return {
            "current_velocity": current_velocity,
            "trend": "unknown"
        }
    
    def _estimate_completion_date(self, task_id: str) -> Optional[datetime]:
        """Estimate completion date for a task"""
        task = self.progress_tracker.task_progress.get(task_id)
        if not task or task.status == TaskStatus.COMPLETED:
            return task.completed_at if task.completed_at else None
        
        remaining_progress = 1.0 - task.completion_percentage
        
        # Use velocity analysis for estimate
        velocity_analysis = self._analyze_task_velocity(task_id)
        if velocity_analysis and velocity_analysis.get("current_velocity", 0) > 0:
            remaining_hours = remaining_progress / velocity_analysis["current_velocity"]
            return datetime.now() + timedelta(hours=remaining_hours)
        
        # Fallback to estimated hours
        if task.estimated_hours > 0:
            remaining_hours = remaining_progress * task.estimated_hours
            return datetime.now() + timedelta(hours=remaining_hours)
        
        return None
    
    def get_progress_dashboard(self) -> Dict[str, Any]:
        """Get comprehensive progress dashboard"""
        return {
            "project_overview": self.progress_tracker.get_progress_summary(),
            "recent_milestones": self._get_recent_milestones(),
            "active_alerts": [
                {
                    "type": a.alert_type,
                    "task_id": a.task_id,
                    "message": a.message,
                    "severity": a.severity
                } for a in self.alerts[-10:]  # Last 10 alerts
            ],
            "pattern_insights": self._get_pattern_insights(),
            "milestone_forecast": self._get_milestone_forecast()
        }
    
    def _get_recent_milestones(self) -> List[Dict[str, Any]]:
        """Get recent milestone achievements"""
        all_milestones = []
        for task_milestones in self.milestone_history.values():
            all_milestones.extend(task_milestones)
        
        # Sort by date and take recent ones
        recent = sorted(all_milestones, key=lambda m: m.achieved_at, reverse=True)[:10]
        
        return [
            {
                "task_id": m.task_id,
                "type": m.milestone_type.value,
                "achieved_at": m.achieved_at.isoformat(),
                "completion": m.completion_percentage,
                "impact": m.impact_score
            } for m in recent
        ]
    
    def _get_pattern_insights(self) -> List[Dict[str, Any]]:
        """Get insights from learned patterns"""
        insights = []
        
        for pattern in self.pattern_database.values():
            if pattern.sample_count >= 2:  # Only patterns with multiple samples
                insights.append({
                    "pattern_name": pattern.pattern_name,
                    "domain": pattern.domain,
                    "average_velocity": pattern.average_velocity,
                    "sample_count": pattern.sample_count,
                    "milestone_timing": pattern.milestone_timing
                })
        
        return insights
    
    def _get_milestone_forecast(self) -> List[Dict[str, Any]]:
        """Get forecast of upcoming milestones"""
        forecast = []
        
        for task_id, task in self.progress_tracker.task_progress.items():
            if task.status in [TaskStatus.PENDING, TaskStatus.IN_PROGRESS]:
                next_milestone = self._calculate_next_milestone(task_id)
                if next_milestone:
                    forecast.append({
                        "task_id": task_id,
                        "milestone_type": next_milestone["type"],
                        "estimated_date": next_milestone["estimated_date"],
                        "current_progress": round(task.completion_percentage * 100, 1)
                    })
        
        # Sort by estimated date
        forecast.sort(key=lambda f: f["estimated_date"])
        
        return forecast[:20]  # Top 20 upcoming milestones
    
    def _load_historical_data(self):
        """Load historical milestone and pattern data"""
        if not self.storage_manager:
            return
        
        try:
            # Load milestone history
            milestone_data = self.storage_manager.load_project_data(
                self.project_name, "milestone_history.json"
            )
            if milestone_data:
                # Convert dict data back to MilestoneEvent objects
                for task_id, milestones_data in milestone_data.items():
                    self.milestone_history[task_id] = []
                    for m_data in milestones_data:
                        milestone = MilestoneEvent(
                            task_id=m_data["task_id"],
                            milestone_type=MilestoneType(m_data["milestone_type"]),
                            achieved_at=datetime.fromisoformat(m_data["achieved_at"]),
                            completion_percentage=m_data["completion_percentage"],
                            impact_score=m_data.get("impact_score", 0.0)
                        )
                        self.milestone_history[task_id].append(milestone)
            
            # Load pattern database
            pattern_data = self.storage_manager.load_project_data(
                self.project_name, "progress_patterns.json"
            )
            if pattern_data:
                for pattern_key, p_data in pattern_data.items():
                    pattern = ProgressPattern(
                        pattern_name=p_data["pattern_name"],
                        task_type=p_data["task_type"],
                        domain=p_data["domain"],
                        average_velocity=p_data["average_velocity"],
                        milestone_timing=p_data["milestone_timing"],
                        accuracy_score=p_data["accuracy_score"],
                        sample_count=p_data["sample_count"],
                        last_updated=datetime.fromisoformat(p_data["last_updated"])
                    )
                    self.pattern_database[pattern_key] = pattern
                    
        except Exception as e:
            # Continue without historical data if loading fails
            pass
    
    def _save_progress_data(self):
        """Save milestone and pattern data"""
        if not self.storage_manager:
            return
        
        try:
            # Save milestone history
            milestone_data = {}
            for task_id, milestones in self.milestone_history.items():
                milestone_data[task_id] = [
                    {
                        "task_id": m.task_id,
                        "milestone_type": m.milestone_type.value,
                        "achieved_at": m.achieved_at.isoformat(),
                        "completion_percentage": m.completion_percentage,
                        "impact_score": m.impact_score
                    } for m in milestones
                ]
            
            self.storage_manager.save_project_data(
                self.project_name, "milestone_history.json", milestone_data
            )
            
            # Save pattern database
            pattern_data = {}
            for pattern_key, pattern in self.pattern_database.items():
                pattern_data[pattern_key] = {
                    "pattern_name": pattern.pattern_name,
                    "task_type": pattern.task_type,
                    "domain": pattern.domain,
                    "average_velocity": pattern.average_velocity,
                    "milestone_timing": pattern.milestone_timing,
                    "accuracy_score": pattern.accuracy_score,
                    "sample_count": pattern.sample_count,
                    "last_updated": pattern.last_updated.isoformat()
                }
            
            self.storage_manager.save_project_data(
                self.project_name, "progress_patterns.json", pattern_data
            )
            
        except Exception as e:
            # Continue without saving if save fails
            pass