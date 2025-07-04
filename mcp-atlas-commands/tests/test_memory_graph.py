"""Tests for Memory Graph Manager module."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from atlas_commands.memory.graph_manager import MemoryGraphManager, PatternTracker


class TestMemoryGraphManager:
    """Test suite for MemoryGraphManager."""
    
    def test_create_workflow_entity(self):
        """Test creating workflow entity in memory graph."""
        manager = MemoryGraphManager()
        
        result = manager.create_workflow_entity(
            command_type="plan",
            target="authentication-system",
            step="initial",
            observations=["Analyzed requirements", "Identified 3 components"]
        )
        
        assert result["entity_name"] == "workflow_plan_authentication-system_initial"
        assert result["command_type"] == "plan"
        assert result["target"] == "authentication-system"
        assert result["observation_count"] == 2
    
    def test_add_workflow_relation(self):
        """Test adding relation between workflow entities."""
        manager = MemoryGraphManager()
        
        # Create two entities
        entity1 = manager.create_workflow_entity(
            command_type="plan",
            target="feature",
            step="planning"
        )
        
        entity2 = manager.create_workflow_entity(
            command_type="execute",
            target="feature",
            step="implementation"
        )
        
        # Add relation
        result = manager.add_workflow_relation(
            from_entity=entity1["entity_name"],
            to_entity=entity2["entity_name"],
            relation_type="precedes"
        )
        
        assert result["success"] is True
        assert result["from"] == entity1["entity_name"]
        assert result["to"] == entity2["entity_name"]
        assert result["relation_type"] == "precedes"
    
    def test_search_workflow_patterns(self):
        """Test searching for workflow patterns."""
        manager = MemoryGraphManager()
        
        # Create entities with pattern
        for i in range(3):
            manager.create_workflow_entity(
                command_type="refactor",
                target="legacy-code",
                step=f"phase-{i}",
                observations=[f"Refactored module {i}"]
            )
        
        # Search for pattern
        results = manager.search_workflow_patterns("refactor", "legacy-code")
        
        assert len(results) == 3
        assert all("refactor_legacy-code" in r["entity_name"] for r in results)
    
    def test_compact_old_entities(self):
        """Test compacting old entities."""
        manager = MemoryGraphManager()
        
        # Create old and new entities
        with patch('atlas_commands.memory.graph_manager.datetime') as mock_datetime:
            # Old entity (30 days ago)
            mock_datetime.now.return_value = datetime.now() - timedelta(days=30)
            old_entity = manager.create_workflow_entity(
                command_type="analyze",
                target="old-feature",
                step="analysis"
            )
            
            # Recent entity
            mock_datetime.now.return_value = datetime.now()
            recent_entity = manager.create_workflow_entity(
                command_type="analyze",
                target="new-feature",
                step="analysis"
            )
        
        # Compact entities older than 7 days
        result = manager.compact_old_entities(days_old=7)
        
        assert result["compacted_count"] >= 1
        assert "summary" in result
    
    def test_get_command_statistics(self):
        """Test getting command usage statistics."""
        manager = MemoryGraphManager()
        
        # Create entities for different commands
        commands = ["plan", "execute", "plan", "verify", "execute", "execute"]
        
        for i, cmd in enumerate(commands):
            manager.create_workflow_entity(
                command_type=cmd,
                target=f"feature-{i}",
                step="main"
            )
        
        stats = manager.get_command_statistics()
        
        assert stats["plan"] == 2
        assert stats["execute"] == 3
        assert stats["verify"] == 1
    
    def test_extract_high_value_observations(self):
        """Test extraction of high-value observations."""
        manager = MemoryGraphManager()
        
        observations = [
            "Fixed critical bug in authentication",
            "Updated documentation",
            "Discovered race condition in worker threads",
            "Added comments to code",
            "Performance improved by 300%",
            "Refactored variable names"
        ]
        
        high_value = manager._extract_high_value_observations(observations)
        
        # Should extract surprising/important observations
        assert "critical bug" in " ".join(high_value)
        assert "race condition" in " ".join(high_value)
        assert "300%" in " ".join(high_value)
        
        # Should filter routine observations
        assert not any("comments" in obs for obs in high_value)
        assert not any("variable names" in obs for obs in high_value)


class TestPatternTracker:
    """Test suite for PatternTracker."""
    
    def test_track_command_pattern(self):
        """Test tracking command execution patterns."""
        tracker = PatternTracker()
        
        # Track multiple command executions
        tracker.track_pattern(
            command="plan",
            target="feature-auth",
            outcome="success",
            duration=120.5,
            observations=["Created 5 subtasks", "Identified dependencies"]
        )
        
        tracker.track_pattern(
            command="plan",
            target="feature-payment",
            outcome="success",
            duration=95.0,
            observations=["Created 3 subtasks"]
        )
        
        tracker.track_pattern(
            command="plan",
            target="feature-broken",
            outcome="failure",
            duration=30.0,
            observations=["Missing requirements"]
        )
        
        stats = tracker.get_pattern_statistics("plan")
        
        assert stats["total_executions"] == 3
        assert stats["success_rate"] == pytest.approx(0.667, 0.01)
        assert stats["average_duration"] == pytest.approx(81.83, 0.01)
    
    def test_get_successful_patterns(self):
        """Test retrieving successful command patterns."""
        tracker = PatternTracker()
        
        # Track patterns
        for i in range(5):
            tracker.track_pattern(
                command="execute",
                target=f"task-{i}",
                outcome="success" if i < 3 else "failure",
                duration=60.0 + i * 10
            )
        
        successful = tracker.get_successful_patterns("execute", limit=2)
        
        assert len(successful) == 2
        assert all(p["outcome"] == "success" for p in successful)
        assert successful[0]["duration"] < successful[1]["duration"]  # Sorted by duration
    
    def test_identify_problematic_patterns(self):
        """Test identifying problematic patterns."""
        tracker = PatternTracker()
        
        # Track patterns with failures
        targets = ["complex-refactor", "complex-refactor", "simple-fix", "complex-refactor"]
        outcomes = ["failure", "failure", "success", "failure"]
        
        for target, outcome in zip(targets, outcomes):
            tracker.track_pattern(
                command="execute",
                target=target,
                outcome=outcome,
                duration=100.0
            )
        
        problems = tracker.identify_problematic_patterns()
        
        assert len(problems) > 0
        assert any("complex-refactor" in str(p) for p in problems)
    
    def test_pattern_memory_integration(self):
        """Test pattern tracking with memory integration."""
        tracker = PatternTracker()
        manager = MemoryGraphManager()
        
        # Track pattern and create memory entity
        tracker.track_pattern(
            command="analyze",
            target="performance-issue",
            outcome="success",
            duration=300.0,
            observations=["Found memory leak", "Identified optimization opportunity"]
        )
        
        # Create corresponding memory entity
        entity = manager.create_workflow_entity(
            command_type="analyze",
            target="performance-issue",
            step="complete",
            observations=["Found memory leak", "Identified optimization opportunity"]
        )
        
        # Verify consistency
        patterns = tracker.get_successful_patterns("analyze")
        assert len(patterns) == 1
        assert patterns[0]["target"] == "performance-issue"
        assert entity["target"] == "performance-issue"