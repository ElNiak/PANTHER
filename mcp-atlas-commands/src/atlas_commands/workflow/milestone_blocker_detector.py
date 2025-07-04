"""
Milestone and Blocker Detection System

Provides intelligent detection of milestones approaching, milestone risks,
and critical blockers that need immediate attention.
"""

from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import statistics

from .progress_tracker import SmartProgressTracker, TaskStatus, TaskProgress
from .boss_notifier import BossNotifier, NotificationPriority


class MilestoneRisk(Enum):
    """Risk levels for milestone completion"""
    ON_TRACK = "on_track"      # Green - likely to complete on time
    AT_RISK = "at_risk"        # Yellow - may miss deadline
    HIGH_RISK = "high_risk"    # Red - likely to miss deadline
    MISSED = "missed"          # Already past deadline


class BlockerSeverity(Enum):
    """Severity levels for blockers"""
    LOW = "low"                # Affects 1-2 tasks
    MEDIUM = "medium"          # Affects 3-5 tasks
    HIGH = "high"              # Affects 6-10 tasks
    CRITICAL = "critical"      # Affects >10 tasks or milestones


@dataclass
class MilestoneAlert:
    """Alert for milestone status"""
    milestone_id: str
    milestone_name: str
    risk_level: MilestoneRisk
    completion_percentage: float
    estimated_completion_date: Optional[datetime]
    target_date: Optional[datetime]
    days_remaining: Optional[int]
    blocking_tasks: List[str]
    at_risk_reasons: List[str]
    recommended_actions: List[str]


@dataclass
class BlockerAlert:
    """Alert for critical blockers"""
    task_id: str
    task_name: str
    severity: BlockerSeverity
    blocked_since: datetime
    days_blocked: int
    tasks_impacted: int
    milestones_impacted: List[str]
    root_causes: List[str]
    resolution_paths: List[str]


class MilestoneBlockerDetector:
    """Detects and alerts on milestones at risk and critical blockers"""
    
    def __init__(self, progress_tracker: SmartProgressTracker):
        self.tracker = progress_tracker
        self.boss_notifier = BossNotifier()
        
        # Configurable thresholds
        self.risk_thresholds = {
            "days_before_at_risk": 7,      # Days before deadline to flag as at-risk
            "days_before_high_risk": 3,     # Days before deadline to flag as high-risk
            "completion_rate_threshold": 0.1,  # Min daily progress rate expected
            "blocker_duration_medium": 3,    # Days blocked to be medium severity
            "blocker_duration_high": 7,      # Days blocked to be high severity
        }
        
        # Cache for performance
        self._last_check_time = None
        self._alert_history: Dict[str, datetime] = {}
    
    def detect_milestone_risks(self, 
                              target_dates: Optional[Dict[str, datetime]] = None) -> List[MilestoneAlert]:
        """
        Detect milestones at risk of missing their deadlines.
        
        Args:
            target_dates: Optional dict of milestone_id -> target completion date
            
        Returns:
            List of milestone alerts sorted by risk level
        """
        alerts = []
        
        for milestone_id in self.tracker.milestones:
            task = self.tracker.task_progress.get(milestone_id)
            if not task:
                continue
            
            # Skip completed milestones
            if task.status == TaskStatus.COMPLETED:
                continue
            
            alert = self._analyze_milestone_risk(
                milestone_id, 
                task,
                target_dates.get(milestone_id) if target_dates else None
            )
            
            if alert:
                alerts.append(alert)
        
        # Sort by risk level (highest risk first)
        risk_order = {MilestoneRisk.MISSED: 0, MilestoneRisk.HIGH_RISK: 1, 
                     MilestoneRisk.AT_RISK: 2, MilestoneRisk.ON_TRACK: 3}
        alerts.sort(key=lambda a: risk_order[a.risk_level])
        
        return alerts
    
    def _analyze_milestone_risk(self, 
                               milestone_id: str,
                               task: TaskProgress,
                               target_date: Optional[datetime]) -> Optional[MilestoneAlert]:
        """Analyze risk level for a specific milestone"""
        risk_level = MilestoneRisk.ON_TRACK
        at_risk_reasons = []
        recommended_actions = []
        
        # Calculate estimated completion date
        estimated_completion = self._estimate_completion_date(milestone_id, task)
        
        # Check against target date if provided
        days_remaining = None
        if target_date:
            now = datetime.now()
            if now > target_date:
                risk_level = MilestoneRisk.MISSED
                at_risk_reasons.append("Target date has passed")
                recommended_actions.append("Escalate to management immediately")
            else:
                days_remaining = (target_date - now).days
                
                if estimated_completion and estimated_completion > target_date:
                    days_late = (estimated_completion - target_date).days
                    
                    if days_late > self.risk_thresholds["days_before_high_risk"]:
                        risk_level = MilestoneRisk.HIGH_RISK
                        at_risk_reasons.append(f"Estimated to be {days_late} days late")
                        recommended_actions.append("Consider scope reduction or resource reallocation")
                    else:
                        risk_level = MilestoneRisk.AT_RISK
                        at_risk_reasons.append(f"May be {days_late} days late")
                        recommended_actions.append("Increase focus on critical path tasks")
        
        # Check progress velocity
        velocity = self._calculate_velocity(milestone_id, task)
        if velocity < self.risk_thresholds["completion_rate_threshold"]:
            if risk_level == MilestoneRisk.ON_TRACK:
                risk_level = MilestoneRisk.AT_RISK
            at_risk_reasons.append(f"Low progress velocity: {velocity:.1%} per day")
            recommended_actions.append("Review and remove impediments")
        
        # Check for blocking tasks
        blocking_tasks = self._find_blocking_tasks(milestone_id)
        if blocking_tasks:
            if risk_level == MilestoneRisk.ON_TRACK:
                risk_level = MilestoneRisk.AT_RISK
            at_risk_reasons.append(f"{len(blocking_tasks)} tasks blocking progress")
            recommended_actions.append("Prioritize unblocking tasks")
        
        # Only create alert if there's a risk
        if risk_level != MilestoneRisk.ON_TRACK or at_risk_reasons:
            return MilestoneAlert(
                milestone_id=milestone_id,
                milestone_name=milestone_id,  # Could be enhanced with actual names
                risk_level=risk_level,
                completion_percentage=task.completion_percentage * 100,
                estimated_completion_date=estimated_completion,
                target_date=target_date,
                days_remaining=days_remaining,
                blocking_tasks=blocking_tasks,
                at_risk_reasons=at_risk_reasons,
                recommended_actions=recommended_actions
            )
        
        return None
    
    def _estimate_completion_date(self, 
                                 task_id: str,
                                 task: TaskProgress) -> Optional[datetime]:
        """Estimate when a task will complete based on current velocity"""
        if task.completion_percentage >= 1.0:
            return task.completed_at
        
        if not task.started_at or task.completion_percentage == 0:
            return None
        
        # Calculate velocity
        elapsed_days = (datetime.now() - task.started_at).days + 1
        daily_velocity = task.completion_percentage / elapsed_days
        
        if daily_velocity > 0:
            remaining_percentage = 1.0 - task.completion_percentage
            days_to_complete = remaining_percentage / daily_velocity
            return datetime.now() + timedelta(days=days_to_complete)
        
        return None
    
    def _calculate_velocity(self, task_id: str, task: TaskProgress) -> float:
        """Calculate daily progress velocity"""
        if not task.started_at:
            return 0.0
        
        elapsed_days = max(1, (datetime.now() - task.started_at).days)
        return task.completion_percentage / elapsed_days
    
    def _find_blocking_tasks(self, milestone_id: str) -> List[str]:
        """Find all tasks blocking a milestone"""
        blocking_tasks = []
        
        # Direct blockers
        milestone_task = self.tracker.task_progress.get(milestone_id)
        if milestone_task and milestone_task.blocked_by:
            blocking_tasks.extend(milestone_task.blocked_by)
        
        # Check all children recursively
        def check_children(task_id: str):
            for child_id in self.tracker.task_hierarchy.get(task_id, []):
                child = self.tracker.task_progress.get(child_id)
                if child:
                    if child.status == TaskStatus.BLOCKED:
                        blocking_tasks.append(child_id)
                    elif child.status not in [TaskStatus.COMPLETED, TaskStatus.ARCHIVED]:
                        # Check child's children
                        check_children(child_id)
        
        check_children(milestone_id)
        
        return list(set(blocking_tasks))  # Remove duplicates
    
    def detect_critical_blockers(self) -> List[BlockerAlert]:
        """
        Detect blockers that need immediate attention.
        
        Returns:
            List of blocker alerts sorted by severity
        """
        alerts = []
        
        # Find all blocked tasks
        for task_id, task in self.tracker.task_progress.items():
            if task.status != TaskStatus.BLOCKED:
                continue
            
            alert = self._analyze_blocker(task_id, task)
            if alert:
                alerts.append(alert)
        
        # Sort by severity (highest first)
        severity_order = {BlockerSeverity.CRITICAL: 0, BlockerSeverity.HIGH: 1,
                         BlockerSeverity.MEDIUM: 2, BlockerSeverity.LOW: 3}
        alerts.sort(key=lambda a: (severity_order[a.severity], -a.days_blocked))
        
        return alerts
    
    def _analyze_blocker(self, task_id: str, task: TaskProgress) -> Optional[BlockerAlert]:
        """Analyze a specific blocker"""
        # Calculate how long it's been blocked
        blocked_duration = self.tracker._calculate_blocked_duration(task)
        
        # Calculate impact
        tasks_impacted = self.tracker._calculate_blocker_impact(task_id)
        
        # Find impacted milestones
        milestones_impacted = self._find_impacted_milestones(task_id)
        
        # Determine severity
        severity = self._calculate_blocker_severity(
            tasks_impacted,
            len(milestones_impacted),
            blocked_duration
        )
        
        # Analyze root causes
        root_causes = self._analyze_root_causes(task_id, task)
        
        # Suggest resolution paths
        resolution_paths = self._suggest_resolution_paths(task_id, task, root_causes)
        
        # Find when it was blocked
        blocked_since = datetime.now() - timedelta(days=blocked_duration)
        
        return BlockerAlert(
            task_id=task_id,
            task_name=task_id,  # Could be enhanced with actual names
            severity=severity,
            blocked_since=blocked_since,
            days_blocked=blocked_duration,
            tasks_impacted=tasks_impacted,
            milestones_impacted=milestones_impacted,
            root_causes=root_causes,
            resolution_paths=resolution_paths
        )
    
    def _find_impacted_milestones(self, blocked_task_id: str) -> List[str]:
        """Find milestones impacted by a blocked task"""
        impacted_milestones = []
        
        # Check if the blocked task itself is a milestone
        if blocked_task_id in self.tracker.milestones:
            impacted_milestones.append(blocked_task_id)
        
        # Traverse up the hierarchy to find milestone ancestors
        current_id = blocked_task_id
        while current_id in self.tracker.parent_map:
            parent_id = self.tracker.parent_map[current_id]
            if parent_id in self.tracker.milestones:
                impacted_milestones.append(parent_id)
            current_id = parent_id
        
        return list(set(impacted_milestones))
    
    def _calculate_blocker_severity(self,
                                   tasks_impacted: int,
                                   milestones_impacted: int,
                                   days_blocked: int) -> BlockerSeverity:
        """Calculate severity based on impact and duration"""
        # Critical if impacts milestones or many tasks
        if milestones_impacted > 0 or tasks_impacted > 10:
            return BlockerSeverity.CRITICAL
        
        # High if long duration or significant impact
        if days_blocked >= self.risk_thresholds["blocker_duration_high"] or tasks_impacted > 5:
            return BlockerSeverity.HIGH
        
        # Medium if moderate duration or impact
        if days_blocked >= self.risk_thresholds["blocker_duration_medium"] or tasks_impacted > 2:
            return BlockerSeverity.MEDIUM
        
        return BlockerSeverity.LOW
    
    def _analyze_root_causes(self, task_id: str, task: TaskProgress) -> List[str]:
        """Analyze potential root causes of the blocker"""
        root_causes = []
        
        # Check what's blocking it
        if task.blocked_by:
            for blocker_id in task.blocked_by:
                blocker_task = self.tracker.task_progress.get(blocker_id)
                if blocker_task:
                    if blocker_task.status == TaskStatus.BLOCKED:
                        root_causes.append(f"Cascading block from {blocker_id}")
                    elif blocker_task.status != TaskStatus.COMPLETED:
                        root_causes.append(f"Waiting for {blocker_id} to complete")
        
        # Check if it's been stuck in review/testing
        if task.completion_percentage > 0.8:
            root_causes.append("Possibly stuck in review or testing phase")
        
        # Check if no progress has been made
        if task.completion_percentage == 0 and task.started_at:
            root_causes.append("No progress since task was started")
        
        if not root_causes:
            root_causes.append("External dependency or resource constraint")
        
        return root_causes
    
    def _suggest_resolution_paths(self,
                                 task_id: str,
                                 task: TaskProgress,
                                 root_causes: List[str]) -> List[str]:
        """Suggest ways to resolve the blocker"""
        paths = []
        
        # Based on root causes
        for cause in root_causes:
            if "Cascading block" in cause:
                paths.append("Resolve upstream blockers first")
            elif "Waiting for" in cause:
                paths.append("Expedite completion of dependency tasks")
            elif "review or testing" in cause:
                paths.append("Schedule immediate review session")
            elif "No progress" in cause:
                paths.append("Reassign task or provide additional resources")
        
        # General suggestions based on severity
        tasks_impacted = self.tracker._calculate_blocker_impact(task_id)
        if tasks_impacted > 5:
            paths.append("Consider alternative implementation approach")
            paths.append("Break down into smaller, unblocked subtasks")
        
        # Time-based suggestions
        blocked_duration = self.tracker._calculate_blocked_duration(task)
        if blocked_duration > 7:
            paths.append("Escalate to senior management")
            paths.append("Consider removing from critical path")
        
        return paths
    
    def run_detection_cycle(self,
                           target_dates: Optional[Dict[str, datetime]] = None,
                           send_notifications: bool = True) -> Dict[str, Any]:
        """
        Run a complete detection cycle for milestones and blockers.
        
        Args:
            target_dates: Optional milestone target dates
            send_notifications: Whether to send boss notifications
            
        Returns:
            Summary of detected issues
        """
        # Detect milestone risks
        milestone_alerts = self.detect_milestone_risks(target_dates)
        
        # Detect critical blockers
        blocker_alerts = self.detect_critical_blockers()
        
        # Send notifications if requested
        if send_notifications:
            self._send_alert_notifications(milestone_alerts, blocker_alerts)
        
        # Update last check time
        self._last_check_time = datetime.now()
        
        return {
            "check_time": self._last_check_time,
            "milestone_alerts": len(milestone_alerts),
            "milestones_at_risk": sum(1 for a in milestone_alerts if a.risk_level != MilestoneRisk.ON_TRACK),
            "milestones_high_risk": sum(1 for a in milestone_alerts if a.risk_level == MilestoneRisk.HIGH_RISK),
            "blocker_alerts": len(blocker_alerts),
            "critical_blockers": sum(1 for a in blocker_alerts if a.severity == BlockerSeverity.CRITICAL),
            "details": {
                "milestones": milestone_alerts,
                "blockers": blocker_alerts
            }
        }
    
    def _send_alert_notifications(self,
                                 milestone_alerts: List[MilestoneAlert],
                                 blocker_alerts: List[BlockerAlert]):
        """Send notifications for critical alerts"""
        # Milestone notifications
        for alert in milestone_alerts:
            if alert.risk_level in [MilestoneRisk.HIGH_RISK, MilestoneRisk.MISSED]:
                # Only notify if we haven't recently
                alert_key = f"milestone_{alert.milestone_id}"
                if self._should_send_notification(alert_key):
                    self.boss_notifier.notify_milestone_risk(
                        milestone_id=alert.milestone_id,
                        milestone_name=alert.milestone_name,
                        risk_level=alert.risk_level.value,
                        completion_percentage=alert.completion_percentage,
                        days_remaining=alert.days_remaining,
                        at_risk_reasons=alert.at_risk_reasons,
                        recommended_actions=alert.recommended_actions
                    )
                    self._alert_history[alert_key] = datetime.now()
        
        # Blocker notifications
        for alert in blocker_alerts:
            if alert.severity in [BlockerSeverity.HIGH, BlockerSeverity.CRITICAL]:
                alert_key = f"blocker_{alert.task_id}"
                if self._should_send_notification(alert_key):
                    # Use the existing notify_blocker method
                    self.boss_notifier.notify_blocker(
                        task_id=alert.task_id,
                        task_name=alert.task_name,
                        blocker_description=f"Blocked for {alert.days_blocked} days, impacting {alert.tasks_impacted} tasks",
                        blocker_type="critical" if alert.severity == BlockerSeverity.CRITICAL else "high",
                        suggested_solutions=alert.resolution_paths
                    )
                    self._alert_history[alert_key] = datetime.now()
    
    def _should_send_notification(self, alert_key: str, hours: int = 24) -> bool:
        """Check if we should send a notification (avoid spam)"""
        if alert_key not in self._alert_history:
            return True
        
        last_sent = self._alert_history[alert_key]
        time_since = datetime.now() - last_sent
        
        return time_since.total_seconds() > (hours * 3600)
    
    def get_dashboard_summary(self) -> Dict[str, Any]:
        """Get a dashboard-friendly summary of milestones and blockers"""
        # Run detection without notifications
        results = self.run_detection_cycle(send_notifications=False)
        
        # Build summary
        summary = {
            "overview": {
                "total_milestones": len(self.tracker.milestones),
                "milestones_at_risk": results["milestones_at_risk"],
                "critical_blockers": results["critical_blockers"],
                "last_check": results["check_time"].isoformat()
            },
            "milestones": {
                "on_track": [],
                "at_risk": [],
                "high_risk": [],
                "missed": []
            },
            "blockers": {
                "critical": [],
                "high": [],
                "medium": [],
                "low": []
            }
        }
        
        # Categorize milestones
        for alert in results["details"]["milestones"]:
            category = alert.risk_level.value
            summary["milestones"][category].append({
                "id": alert.milestone_id,
                "completion": f"{alert.completion_percentage:.0f}%",
                "days_remaining": alert.days_remaining,
                "blocking_tasks": len(alert.blocking_tasks)
            })
        
        # Categorize blockers
        for alert in results["details"]["blockers"]:
            category = alert.severity.value
            summary["blockers"][category].append({
                "id": alert.task_id,
                "days_blocked": alert.days_blocked,
                "tasks_impacted": alert.tasks_impacted,
                "milestones_impacted": len(alert.milestones_impacted)
            })
        
        return summary