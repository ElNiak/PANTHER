"""Test milestone and blocker detection system"""

import pytest
from datetime import datetime, timedelta
from atlas_commands.workflow.progress_tracker import SmartProgressTracker, TaskStatus
from atlas_commands.workflow.milestone_blocker_detector import (
    MilestoneBlockerDetector, MilestoneRisk, BlockerSeverity,
    MilestoneAlert, BlockerAlert
)


class TestMilestoneBlockerDetector:
    """Test milestone risk detection and blocker analysis"""
    
    def test_milestone_on_track_detection(self):
        """Test detection of milestones that are on track"""
        tracker = SmartProgressTracker("test_project")
        detector = MilestoneBlockerDetector(tracker)
        
        # Create milestone with good progress
        milestone = tracker.register_task("milestone_1", estimated_hours=40, is_milestone=True)
        tracker.update_task_progress("milestone_1", 
                                    status=TaskStatus.IN_PROGRESS,
                                    completion_percentage=0.6)
        
        # Set target date 30 days from now
        target_dates = {"milestone_1": datetime.now() + timedelta(days=30)}
        
        alerts = detector.detect_milestone_risks(target_dates)
        
        # Should have no alerts for on-track milestone
        assert len(alerts) == 0
    
    def test_milestone_at_risk_detection(self):
        """Test detection of milestones at risk"""
        tracker = SmartProgressTracker("test_project")
        detector = MilestoneBlockerDetector(tracker)
        
        # Create milestone with slow progress
        milestone = tracker.register_task("milestone_risky", estimated_hours=40, is_milestone=True)
        
        # Simulate it started 10 days ago with only 10% progress
        task = tracker.task_progress["milestone_risky"]
        task.started_at = datetime.now() - timedelta(days=10)
        task.completion_percentage = 0.1
        task.status = TaskStatus.IN_PROGRESS
        
        # Target date is 5 days from now (needs 90% in 5 days!)
        target_dates = {"milestone_risky": datetime.now() + timedelta(days=5)}
        
        alerts = detector.detect_milestone_risks(target_dates)
        
        assert len(alerts) == 1
        alert = alerts[0]
        assert alert.milestone_id == "milestone_risky"
        assert alert.risk_level in [MilestoneRisk.AT_RISK, MilestoneRisk.HIGH_RISK]
        assert "Low progress velocity" in str(alert.at_risk_reasons)
    
    def test_milestone_high_risk_detection(self):
        """Test detection of high-risk milestones"""
        tracker = SmartProgressTracker("test_project")
        detector = MilestoneBlockerDetector(tracker)
        
        # Create milestone that will miss deadline
        milestone = tracker.register_task("milestone_critical", estimated_hours=100, is_milestone=True)
        
        # Started 20 days ago, only 20% complete
        task = tracker.task_progress["milestone_critical"]
        task.started_at = datetime.now() - timedelta(days=20)
        task.completion_percentage = 0.2
        task.status = TaskStatus.IN_PROGRESS
        
        # Target date is tomorrow!
        target_dates = {"milestone_critical": datetime.now() + timedelta(days=1)}
        
        alerts = detector.detect_milestone_risks(target_dates)
        
        assert len(alerts) == 1
        alert = alerts[0]
        assert alert.risk_level == MilestoneRisk.HIGH_RISK
        assert alert.days_remaining is not None and alert.days_remaining <= 1
        assert "scope reduction" in str(alert.recommended_actions).lower()
    
    def test_milestone_with_blockers(self):
        """Test milestone risk detection with blocking tasks"""
        tracker = SmartProgressTracker("test_project")
        detector = MilestoneBlockerDetector(tracker)
        
        # Create milestone with subtasks
        milestone = tracker.register_task("milestone_blocked", estimated_hours=50, is_milestone=True)
        subtask1 = tracker.register_task("subtask_1", parent_id="milestone_blocked", estimated_hours=20)
        subtask2 = tracker.register_task("subtask_2", parent_id="milestone_blocked", estimated_hours=30)
        
        # Block one subtask
        tracker.mark_task_blocked("subtask_2", ["external_api"], "API unavailable")
        
        alerts = detector.detect_milestone_risks()
        
        # Should detect the milestone has blocking tasks
        milestone_alerts = [a for a in alerts if a.milestone_id == "milestone_blocked"]
        assert len(milestone_alerts) == 1
        alert = milestone_alerts[0]
        assert len(alert.blocking_tasks) == 1
        assert "subtask_2" in alert.blocking_tasks
        assert "Prioritize unblocking tasks" in alert.recommended_actions
    
    def test_blocker_severity_calculation(self):
        """Test blocker severity is calculated correctly"""
        tracker = SmartProgressTracker("test_project")
        detector = MilestoneBlockerDetector(tracker)
        
        # Create task hierarchy
        parent = tracker.register_task("parent_task", estimated_hours=40)
        child1 = tracker.register_task("child_1", parent_id="parent_task", estimated_hours=10)
        child2 = tracker.register_task("child_2", parent_id="parent_task", estimated_hours=10)
        child3 = tracker.register_task("child_3", parent_id="parent_task", estimated_hours=10)
        
        # Create a blocker that affects multiple tasks
        blocker = tracker.register_task("blocker_task", estimated_hours=5)
        tracker.mark_task_blocked("blocker_task", ["external_dependency"], "Waiting for vendor")
        
        # Block children with the blocker
        tracker.mark_task_blocked("child_1", ["blocker_task"], "Blocked by blocker")
        tracker.mark_task_blocked("child_2", ["blocker_task"], "Blocked by blocker")
        tracker.mark_task_blocked("child_3", ["blocker_task"], "Blocked by blocker")
        
        alerts = detector.detect_critical_blockers()
        
        # Should detect the main blocker
        blocker_alerts = [a for a in alerts if a.task_id == "blocker_task"]
        assert len(blocker_alerts) == 1
        alert = blocker_alerts[0]
        assert alert.tasks_impacted >= 4  # blocker + 3 children
        assert alert.severity in [BlockerSeverity.MEDIUM, BlockerSeverity.HIGH]
    
    def test_milestone_impact_from_blockers(self):
        """Test detection of milestones impacted by blockers"""
        tracker = SmartProgressTracker("test_project")
        detector = MilestoneBlockerDetector(tracker)
        
        # Create milestone with critical path task
        milestone = tracker.register_task("release_milestone", estimated_hours=100, is_milestone=True)
        critical_task = tracker.register_task("critical_feature", 
                                             parent_id="release_milestone",
                                             estimated_hours=40)
        
        # Block the critical task for many days
        task = tracker.task_progress["critical_feature"]
        task.started_at = datetime.now() - timedelta(days=10)
        tracker.mark_task_blocked("critical_feature", ["technical_issue"], "Architecture problem")
        
        alerts = detector.detect_critical_blockers()
        
        # Find the critical feature alert
        critical_alerts = [a for a in alerts if a.task_id == "critical_feature"]
        assert len(critical_alerts) == 1
        alert = critical_alerts[0]
        assert "release_milestone" in alert.milestones_impacted
        assert alert.severity in [BlockerSeverity.HIGH, BlockerSeverity.CRITICAL]
    
    def test_blocker_root_cause_analysis(self):
        """Test root cause analysis for blockers"""
        tracker = SmartProgressTracker("test_project")
        detector = MilestoneBlockerDetector(tracker)
        
        # Create cascading blockers
        task_a = tracker.register_task("task_a", estimated_hours=10)
        task_b = tracker.register_task("task_b", estimated_hours=10)
        task_c = tracker.register_task("task_c", estimated_hours=10)
        
        # C blocked by B, B blocked by A
        tracker.mark_task_blocked("task_a", ["external"], "External dependency")
        tracker.mark_task_blocked("task_b", ["task_a"], "Waiting for task A")
        tracker.mark_task_blocked("task_c", ["task_b"], "Waiting for task B")
        
        alerts = detector.detect_critical_blockers()
        
        # Check root cause analysis for task C
        task_c_alerts = [a for a in alerts if a.task_id == "task_c"]
        assert len(task_c_alerts) == 1
        alert = task_c_alerts[0]
        assert any("Cascading block" in cause for cause in alert.root_causes)
        assert "Resolve upstream blockers first" in alert.resolution_paths
    
    def test_detection_cycle_summary(self):
        """Test full detection cycle with summary"""
        tracker = SmartProgressTracker("test_project")
        detector = MilestoneBlockerDetector(tracker)
        
        # Create mixed scenario
        milestone1 = tracker.register_task("milestone_good", estimated_hours=40, is_milestone=True)
        milestone2 = tracker.register_task("milestone_risky", estimated_hours=40, is_milestone=True)
        
        # Set up risky milestone
        task = tracker.task_progress["milestone_risky"]
        task.started_at = datetime.now() - timedelta(days=10)
        task.completion_percentage = 0.1
        task.status = TaskStatus.IN_PROGRESS
        
        # Create some blockers
        blocker1 = tracker.register_task("blocker_1", estimated_hours=10)
        tracker.mark_task_blocked("blocker_1", ["issue"], "Technical issue")
        
        # Run detection cycle
        target_dates = {
            "milestone_good": datetime.now() + timedelta(days=30),
            "milestone_risky": datetime.now() + timedelta(days=5)
        }
        
        summary = detector.run_detection_cycle(target_dates, send_notifications=False)
        
        assert summary["milestone_alerts"] >= 1
        assert summary["milestones_at_risk"] >= 1
        assert summary["blocker_alerts"] >= 1
        assert "details" in summary
        assert isinstance(summary["check_time"], datetime)
    
    def test_dashboard_summary_format(self):
        """Test dashboard summary generation"""
        tracker = SmartProgressTracker("test_project")
        detector = MilestoneBlockerDetector(tracker)
        
        # Create a milestone
        milestone = tracker.register_task("dashboard_milestone", estimated_hours=40, is_milestone=True)
        tracker.update_task_progress("dashboard_milestone", 
                                    status=TaskStatus.IN_PROGRESS,
                                    completion_percentage=0.5)
        
        dashboard = detector.get_dashboard_summary()
        
        # Check structure
        assert "overview" in dashboard
        assert "milestones" in dashboard
        assert "blockers" in dashboard
        
        # Check milestone categories
        assert "on_track" in dashboard["milestones"]
        assert "at_risk" in dashboard["milestones"]
        assert "high_risk" in dashboard["milestones"]
        assert "missed" in dashboard["milestones"]
        
        # Check blocker categories
        assert "critical" in dashboard["blockers"]
        assert "high" in dashboard["blockers"]
        assert "medium" in dashboard["blockers"]
        assert "low" in dashboard["blockers"]
        
        # Check overview metrics
        assert dashboard["overview"]["total_milestones"] == 1
    
    def test_notification_throttling(self):
        """Test that notifications are throttled to avoid spam"""
        tracker = SmartProgressTracker("test_project")
        detector = MilestoneBlockerDetector(tracker)
        
        # Create high-risk milestone
        milestone = tracker.register_task("spam_milestone", estimated_hours=40, is_milestone=True)
        task = tracker.task_progress["spam_milestone"]
        task.started_at = datetime.now() - timedelta(days=20)
        task.completion_percentage = 0.1
        task.status = TaskStatus.IN_PROGRESS
        
        target_dates = {"spam_milestone": datetime.now() + timedelta(days=1)}
        
        # First detection should send notification
        summary1 = detector.run_detection_cycle(target_dates, send_notifications=True)
        
        # Mark that notification was sent
        detector._alert_history[f"milestone_spam_milestone"] = datetime.now()
        
        # Second detection should not send (too soon)
        should_send = detector._should_send_notification(f"milestone_spam_milestone", hours=24)
        assert not should_send
        
        # Simulate time passing
        detector._alert_history[f"milestone_spam_milestone"] = datetime.now() - timedelta(hours=25)
        
        # Now it should send again
        should_send = detector._should_send_notification(f"milestone_spam_milestone", hours=24)
        assert should_send