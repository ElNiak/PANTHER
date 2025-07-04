"""Test automatic parent rollup functionality in SmartProgressTracker"""

import pytest
from datetime import datetime
from atlas_commands.workflow.progress_tracker import (
    SmartProgressTracker, TaskStatus, ProgressCalculationMethod
)


class TestParentRollup:
    """Test automatic parent task completion when children complete"""
    
    def test_simple_parent_rollup(self):
        """Test parent completes when all children complete"""
        tracker = SmartProgressTracker("test_project")
        
        # Create parent and children
        parent = tracker.register_task("parent_task", estimated_hours=10)
        child1 = tracker.register_task("child_1", parent_id="parent_task", estimated_hours=3)
        child2 = tracker.register_task("child_2", parent_id="parent_task", estimated_hours=2)
        
        # Start parent
        tracker.update_task_progress("parent_task", status=TaskStatus.IN_PROGRESS)
        
        # Complete first child
        update1 = tracker.update_task_progress("child_1", 
                                               completion_percentage=1.0,
                                               status=TaskStatus.COMPLETED)
        
        # Parent should still be in progress
        parent_task = tracker.task_progress["parent_task"]
        assert parent_task.status == TaskStatus.IN_PROGRESS
        assert parent_task.completion_percentage < 1.0
        
        # Complete second child
        update2 = tracker.update_task_progress("child_2",
                                               completion_percentage=1.0,
                                               status=TaskStatus.COMPLETED)
        
        # Parent should now be complete
        parent_task = tracker.task_progress["parent_task"]
        assert parent_task.status == TaskStatus.COMPLETED
        assert parent_task.completion_percentage == 1.0
        assert parent_task.completed_at is not None
        
        # Check parent was included in updates
        assert any(p[0] == "parent_task" for p in update2.parent_updates)
    
    def test_multi_level_rollup(self):
        """Test rollup propagates through multiple levels"""
        tracker = SmartProgressTracker("test_project")
        
        # Create 3-level hierarchy
        grandparent = tracker.register_task("grandparent", estimated_hours=20)
        parent1 = tracker.register_task("parent_1", parent_id="grandparent", estimated_hours=10)
        parent2 = tracker.register_task("parent_2", parent_id="grandparent", estimated_hours=10)
        child1_1 = tracker.register_task("child_1_1", parent_id="parent_1", estimated_hours=5)
        child1_2 = tracker.register_task("child_1_2", parent_id="parent_1", estimated_hours=5)
        child2_1 = tracker.register_task("child_2_1", parent_id="parent_2", estimated_hours=5)
        
        # Start tasks
        tracker.update_task_progress("grandparent", status=TaskStatus.IN_PROGRESS)
        tracker.update_task_progress("parent_1", status=TaskStatus.IN_PROGRESS)
        tracker.update_task_progress("parent_2", status=TaskStatus.IN_PROGRESS)
        
        # Complete all children of parent_1
        tracker.update_task_progress("child_1_1", status=TaskStatus.COMPLETED)
        tracker.update_task_progress("child_1_2", status=TaskStatus.COMPLETED)
        
        # Parent_1 should be complete
        assert tracker.task_progress["parent_1"].status == TaskStatus.COMPLETED
        # Grandparent should still be in progress
        assert tracker.task_progress["grandparent"].status == TaskStatus.IN_PROGRESS
        
        # Complete child of parent_2
        tracker.update_task_progress("child_2_1", status=TaskStatus.COMPLETED)
        
        # Parent_2 should be complete
        assert tracker.task_progress["parent_2"].status == TaskStatus.COMPLETED
        # Grandparent should now be complete
        assert tracker.task_progress["grandparent"].status == TaskStatus.COMPLETED
    
    def test_blocked_parent_unblocks_on_completion(self):
        """Test blocked parent unblocks when all children complete"""
        tracker = SmartProgressTracker("test_project")
        
        # Create parent and children
        parent = tracker.register_task("blocked_parent", estimated_hours=10)
        child1 = tracker.register_task("blocker_child", parent_id="blocked_parent", estimated_hours=5)
        child2 = tracker.register_task("normal_child", parent_id="blocked_parent", estimated_hours=5)
        
        # Mark parent as blocked
        tracker.mark_task_blocked("blocked_parent", ["blocker_child"], "Waiting for child")
        
        # Complete first child
        tracker.update_task_progress("blocker_child", status=TaskStatus.COMPLETED)
        
        # Parent should still be blocked (not all children complete)
        assert tracker.task_progress["blocked_parent"].status == TaskStatus.BLOCKED
        
        # Complete second child
        tracker.update_task_progress("normal_child", status=TaskStatus.COMPLETED)
        
        # Parent should now be unblocked and complete
        parent_task = tracker.task_progress["blocked_parent"]
        assert parent_task.status == TaskStatus.COMPLETED
        assert parent_task.blocked_by == []
        assert parent_task.completion_percentage == 1.0
    
    def test_manual_parent_completion_check(self):
        """Test manual check for parent completion"""
        tracker = SmartProgressTracker("test_project")
        
        # Create parent and children
        parent = tracker.register_task("manual_parent", estimated_hours=10)
        child1 = tracker.register_task("child_1", parent_id="manual_parent", estimated_hours=5)
        child2 = tracker.register_task("child_2", parent_id="manual_parent", estimated_hours=5)
        
        # Complete children without updating parent
        tracker.task_progress["child_1"].status = TaskStatus.COMPLETED
        tracker.task_progress["child_1"].completion_percentage = 1.0
        tracker.task_progress["child_2"].status = TaskStatus.COMPLETED
        tracker.task_progress["child_2"].completion_percentage = 1.0
        
        # Parent should still be pending
        assert tracker.task_progress["manual_parent"].status == TaskStatus.PENDING
        
        # Manually check and update parent
        updated = tracker.check_and_update_parent_completion("manual_parent")
        
        assert updated is True
        assert tracker.task_progress["manual_parent"].status == TaskStatus.COMPLETED
        assert tracker.task_progress["manual_parent"].completion_percentage == 1.0
    
    def test_batch_parent_completion_check(self):
        """Test batch checking all parents for completion"""
        tracker = SmartProgressTracker("test_project")
        
        # Create multiple parent-child relationships
        parent1 = tracker.register_task("parent_1", estimated_hours=10)
        child1_1 = tracker.register_task("child_1_1", parent_id="parent_1", estimated_hours=5)
        child1_2 = tracker.register_task("child_1_2", parent_id="parent_1", estimated_hours=5)
        
        parent2 = tracker.register_task("parent_2", estimated_hours=10)
        child2_1 = tracker.register_task("child_2_1", parent_id="parent_2", estimated_hours=5)
        
        # Complete all children of parent_1
        tracker.task_progress["child_1_1"].status = TaskStatus.COMPLETED
        tracker.task_progress["child_1_1"].completion_percentage = 1.0
        tracker.task_progress["child_1_2"].status = TaskStatus.COMPLETED
        tracker.task_progress["child_1_2"].completion_percentage = 1.0
        
        # Complete child of parent_2
        tracker.task_progress["child_2_1"].status = TaskStatus.COMPLETED
        tracker.task_progress["child_2_1"].completion_percentage = 1.0
        
        # Batch check all parents
        updated_parents = tracker.batch_check_parent_completions()
        
        assert len(updated_parents) == 2
        assert "parent_1" in updated_parents
        assert "parent_2" in updated_parents
        assert tracker.task_progress["parent_1"].status == TaskStatus.COMPLETED
        assert tracker.task_progress["parent_2"].status == TaskStatus.COMPLETED
    
    def test_parent_with_mixed_children_statuses(self):
        """Test parent doesn't complete if any child is incomplete"""
        tracker = SmartProgressTracker("test_project")
        
        parent = tracker.register_task("mixed_parent", estimated_hours=15)
        child1 = tracker.register_task("complete_child", parent_id="mixed_parent", estimated_hours=5)
        child2 = tracker.register_task("progress_child", parent_id="mixed_parent", estimated_hours=5)
        child3 = tracker.register_task("blocked_child", parent_id="mixed_parent", estimated_hours=5)
        
        # Set different statuses
        tracker.update_task_progress("complete_child", status=TaskStatus.COMPLETED)
        tracker.update_task_progress("progress_child", 
                                    status=TaskStatus.IN_PROGRESS,
                                    completion_percentage=0.5)
        tracker.mark_task_blocked("blocked_child", ["external_dep"], "External dependency")
        
        # Parent should not be complete
        parent_task = tracker.task_progress["mixed_parent"]
        assert parent_task.status != TaskStatus.COMPLETED
        assert parent_task.completion_percentage < 1.0
        
        # Complete remaining children
        tracker.update_task_progress("progress_child", status=TaskStatus.COMPLETED)
        tracker.unblock_task("blocked_child")
        tracker.update_task_progress("blocked_child", status=TaskStatus.COMPLETED)
        
        # Now parent should be complete
        parent_task = tracker.task_progress["mixed_parent"]
        assert parent_task.status == TaskStatus.COMPLETED
        assert parent_task.completion_percentage == 1.0
    
    def test_milestone_parent_completion(self):
        """Test milestone parent completion triggers special notification"""
        tracker = SmartProgressTracker("test_project")
        
        # Create milestone parent
        parent = tracker.register_task("milestone_parent", 
                                      estimated_hours=20,
                                      is_milestone=True)
        child1 = tracker.register_task("child_1", parent_id="milestone_parent", estimated_hours=10)
        child2 = tracker.register_task("child_2", parent_id="milestone_parent", estimated_hours=10)
        
        # Complete children
        tracker.update_task_progress("child_1", status=TaskStatus.COMPLETED)
        update = tracker.update_task_progress("child_2", status=TaskStatus.COMPLETED)
        
        # Verify milestone parent is complete
        parent_task = tracker.task_progress["milestone_parent"]
        assert parent_task.status == TaskStatus.COMPLETED
        assert parent_task.is_milestone is True
        
        # Check milestone appears in milestone status
        milestones = tracker.get_milestone_status()
        milestone_status = next((m for m in milestones if m["task_id"] == "milestone_parent"), None)
        assert milestone_status is not None
        assert milestone_status["status"] == "completed"
        assert milestone_status["completion"] == 100.0
    
    def test_parent_progress_calculation_methods(self):
        """Test different progress calculation methods affect rollup"""
        tracker = SmartProgressTracker("test_project")
        
        parent = tracker.register_task("weighted_parent", estimated_hours=30)
        # Heavy task (20 hours)
        heavy_child = tracker.register_task("heavy_child", 
                                           parent_id="weighted_parent",
                                           estimated_hours=20)
        # Light task (10 hours)
        light_child = tracker.register_task("light_child",
                                           parent_id="weighted_parent", 
                                           estimated_hours=10)
        
        # Complete light task first
        tracker.update_task_progress("light_child", status=TaskStatus.COMPLETED)
        
        # With weighted calculation, parent should be ~33% complete (10/30 hours)
        parent_progress = tracker._calculate_parent_progress("weighted_parent",
                                                           ProgressCalculationMethod.WEIGHTED)
        assert 0.3 < parent_progress < 0.4
        
        # With simple calculation, parent should be 50% complete (1/2 tasks)
        simple_progress = tracker._calculate_parent_progress("weighted_parent",
                                                           ProgressCalculationMethod.SIMPLE)
        assert simple_progress == 0.5
        
        # Complete heavy task
        tracker.update_task_progress("heavy_child", status=TaskStatus.COMPLETED)
        
        # Parent should be complete regardless of calculation method
        assert tracker.task_progress["weighted_parent"].status == TaskStatus.COMPLETED