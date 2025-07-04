"""Integration tests for AdaptiveCommandSelector with other ATLAS components."""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
import json
import tempfile
from pathlib import Path
from datetime import datetime

from atlas_commands.workflow.adaptive_command_selector import (
    AdaptiveCommandSelector,
    ContextType
)
from atlas_commands.server import EnhancedAtlasCommandsServer as EnhancedAtlasCommandsServer
from atlas_commands.storage.task_storage_manager import TaskStorageManager
from atlas_commands.memory.graph_manager import MemoryGraphManager
from atlas_commands.workflow.pattern_analyzer import WorkflowPatternAnalyzer
from atlas_commands.workflow.task_auto_generator import TaskAutoGenerator
from atlas_commands.workflow.enforcer import WorkflowEnforcer


class TestAdaptiveCommandServerIntegration:
    """Test integration between AdaptiveCommandSelector and MCP server."""
    
    @pytest.fixture
    async def server(self):
        """Create test server instance."""
        server = EnhancedAtlasCommandsServer()
        # Initialize with test configuration
        await server.initialize()
        return server
    
    @pytest.mark.asyncio
    async def test_adaptive_command_tool_registration(self, server):
        """Test that adaptive command selection tool is properly registered."""
        tools = await server.list_tools()
        
        # Find adaptive command tool
        adaptive_tool = next(
            (t for t in tools if t.name == "adaptive_command_selection"),
            None
        )
        
        assert adaptive_tool is not None
        assert "task_description" in adaptive_tool.inputSchema["properties"]
        assert "domain" in adaptive_tool.inputSchema["properties"]
    
    @pytest.mark.asyncio
    async def test_adaptive_command_execution_via_server(self, server):
        """Test executing adaptive command selection through server."""
        # Call the tool through server
        result = await server.call_tool(
            "adaptive_command_selection",
            {
                "task_description": "Build API authentication",
                "domain": "security",
                "current_phase": "planning"
            }
        )
        
        assert result is not None
        assert "recommendations" in result
        recommendations = result["recommendations"]
        assert len(recommendations) > 0
        assert all("command" in r for r in recommendations)
        assert all("confidence" in r for r in recommendations)
    
    @pytest.mark.asyncio 
    async def test_server_handles_adaptive_errors(self, server):
        """Test server error handling for adaptive command selection."""
        # Test with invalid parameters
        with pytest.raises(Exception):
            await server.call_tool(
                "adaptive_command_selection",
                {
                    # Missing required task_description
                    "domain": "testing"
                }
            )


class TestAdaptiveWorkflowIntegration:
    """Test integration with workflow components."""
    
    @pytest.fixture
    def integrated_system(self, tmp_path):
        """Create integrated system with real components."""
        # Create temporary directories
        task_dir = tmp_path / "tasks"
        task_dir.mkdir()
        
        # Initialize components
        task_manager = TaskStorageManager(str(task_dir))
        memory_manager = MemoryGraphManager()
        pattern_analyzer = WorkflowPatternAnalyzer()
        task_generator = TaskAutoGenerator()
        
        # Create selector - it creates its own dependencies
        selector = AdaptiveCommandSelector()
        
        # Override with real components
        selector.task_generator = task_generator
        selector.memory_manager = memory_manager
        selector.pattern_analyzer = pattern_analyzer
        
        # Create workflow enforcer
        enforcer = WorkflowEnforcer(task_manager, memory_manager)
        
        return {
            'selector': selector,
            'task_manager': task_manager,
            'memory_manager': memory_manager,
            'pattern_analyzer': pattern_analyzer,
            'enforcer': enforcer
        }
    
    def test_adaptive_selector_with_task_manager(self, integrated_system):
        """Test adaptive selector working with task manager."""
        selector = integrated_system['selector']
        task_manager = integrated_system['task_manager']
        
        # Create a task
        task_id = "test-task-001"
        task_manager.create_task_metadata(
            project_name="TEST",
            task_id=task_id,
            task_type="feature",
            description="Build authentication system",
            command="plan"
        )
        
        # Get recommendations for the task
        context = selector.analyze_context(
            task_description="Build authentication system",
            domain="security",
            current_phase="planning"
        )
        recommendations = selector.recommend_commands(context)
        
        assert len(recommendations) > 0
        
        # Update task with selected command
        selected = recommendations[0]
        task_manager.add_task_artifact(
            project_name="TEST",
            task_id=task_id,
            artifact_type="command_selection",
            content=json.dumps({
                'selected_command': selected.command,
                'confidence': selected.confidence,
                'rationale': selected.rationale
            }),
            filename="adaptive_selection.json"
        )
        
        # Verify artifact was created
        context = task_manager.get_task_context("TEST", task_id)
        assert any(a['type'] == 'command_selection' for a in context['artifacts'])
    
    def test_adaptive_learning_with_memory_graph(self, integrated_system):
        """Test adaptive learning integration with memory graph."""
        selector = integrated_system['selector']
        memory = integrated_system['memory_manager']
        
        # Create initial task entity
        memory.create_entities([{
            'name': 'AuthenticationTask',
            'entityType': 'Task',
            'observations': ['Building OAuth2 authentication']
        }])
        
        # Learn from task execution
        selector.learn_from_outcome(
            command='explore',
            context=ContextType.GREENFIELD,
            domain='security',
            success=True,
            duration=3600,
            task_description="Build OAuth2 authentication"
        )
        
        # Create relation for learning
        memory.create_relations([{
            'from': 'AuthenticationTask',
            'to': 'AdaptiveCommandSelection',
            'relationType': 'learned_pattern'
        }])
        
        # Add observation about learning
        memory.add_observations([{
            'entityName': 'AuthenticationTask',
            'contents': ['Explore command succeeded with high confidence']
        }])
        
        # Verify memory integration
        graph = memory.read_graph()
        auth_node = next((n for n in graph['nodes'] if n['name'] == 'AuthenticationTask'), None)
        assert auth_node is not None
        assert any('Explore command' in obs for obs in auth_node['observations'])
    
    def test_workflow_enforcer_uses_adaptive_recommendations(self, integrated_system):
        """Test workflow enforcer leveraging adaptive recommendations."""
        selector = integrated_system['selector']
        enforcer = integrated_system['enforcer']
        task_manager = integrated_system['task_manager']
        
        # Create workflow task
        task_id = "workflow-test-001"
        task_manager.create_task_metadata(
            project_name="TEST",
            task_id=task_id,
            task_type="workflow",
            description="Complete feature implementation"
        )
        
        # Get adaptive recommendations
        context = selector.analyze_context(
            task_description="Complete feature implementation",
            domain="feature",
            current_phase="planning"
        )
        recommendations = selector.recommend_commands(context)
        
        # Simulate workflow enforcement with recommendations
        workflow_state = {
            'current_phase': 'planning',
            'completed_commands': [],
            'recommendations': [r.__dict__ for r in recommendations[:3]]
        }
        
        # Save workflow state
        task_manager.add_task_artifact(
            project_name="TEST",
            task_id=task_id,
            artifact_type="workflow_state",
            content=json.dumps(workflow_state),
            filename="workflow_state.json"
        )
        
        # Verify integration
        context = task_manager.get_task_context("TEST", task_id)
        assert len(context['artifacts']) > 0
    
    def test_pattern_analyzer_feedback_loop(self, integrated_system):
        """Test pattern analyzer receiving feedback from adaptive selector."""
        selector = integrated_system['selector']
        analyzer = integrated_system['pattern_analyzer']
        
        # Simulate multiple task executions
        task_patterns = [
            ("Build REST API", "backend", ['explore', 'plan', 'execute'], True),
            ("Create GraphQL API", "backend", ['explore', 'design', 'implement'], True),
            ("Fix API bug", "backend", ['debug', 'fix', 'test'], True),
            ("Optimize API performance", "backend", ['analyze', 'optimize', 'verify'], False)
        ]
        
        for task_desc, domain, commands, success in task_patterns:
            # Get recommendations
            for i, cmd in enumerate(commands):
                context = selector.analyze_context(
                    task_description=task_desc,
                    domain=domain,
                    previous_commands=commands[:i]
                )
                selector.recommend_commands(context)
                
                # Learn from execution
                selector.learn_from_outcome(
                    command=cmd,
                    context=selector._classify_context_type(context),
                    domain=domain,
                    success=success,
                    duration=1800,
                    task_description=task_desc
                )
        
        # Verify patterns were learned
        assert len(selector.learning_cache) >= len(task_patterns) * 2
    
    def test_complex_workflow_with_adaptations(self, integrated_system):
        """Test complex workflow that adapts based on outcomes."""
        selector = integrated_system['selector']
        task_manager = integrated_system['task_manager']
        
        task_id = "complex-workflow-001"
        task_manager.create_task_metadata(
            project_name="TEST",
            task_id=task_id,
            task_type="epic",
            description="Migrate legacy system to microservices"
        )
        
        # Simulate workflow with adaptations
        workflow_log = []
        current_commands = []
        
        # Phase 1: Initial exploration fails
        context = selector.analyze_context(
            task_description="Migrate legacy system to microservices",
            domain="architecture",
            current_phase="exploration"
        )
        rec1 = selector.recommend_commands(context)
        
        selected_cmd = rec1[0].command
        current_commands.append(selected_cmd)
        workflow_log.append({
            'phase': 'exploration',
            'command': selected_cmd,
            'success': False,
            'reason': 'Legacy system too complex'
        })
        
        # Learn from failure
        selector.learn_from_outcome(
            command=selected_cmd,
            context=ContextType.MIGRATION,
            domain='architecture',
            success=False,
            duration=7200,
            task_description="Migrate legacy system"
        )
        
        # Phase 2: Adapt strategy based on failure
        context = selector.analyze_context(
            task_description="Migrate legacy system - need deeper analysis",
            domain="architecture",
            current_phase="exploration",
            previous_commands=current_commands
        )
        rec2 = selector.recommend_commands(context)
        
        # Should recommend different approach
        assert rec2[0].command != selected_cmd or rec2[0].confidence < rec1[0].confidence
        
        # Continue workflow
        selected_cmd2 = rec2[0].command
        current_commands.append(selected_cmd2)
        workflow_log.append({
            'phase': 'deep_analysis',
            'command': selected_cmd2,
            'success': True,
            'adaptation': 'Changed approach after initial failure'
        })
        
        # Save workflow log
        task_manager.add_task_artifact(
            project_name="TEST",
            task_id=task_id,
            artifact_type="adaptive_workflow_log",
            content=json.dumps(workflow_log, indent=2),
            filename="adaptive_workflow.json"
        )
        
        # Verify adaptation was recorded
        context = task_manager.get_task_context("TEST", task_id)
        assert len(context['artifacts']) > 0
        
        # Check that learning affected recommendations
        assert len(selector.learning_cache) >= 1


class TestMemoryPersistenceIntegration:
    """Test learning persistence across sessions."""
    
    @pytest.fixture
    def persistent_selector(self, tmp_path):
        """Create selector with persistent storage."""
        cache_file = tmp_path / "adaptive_learning.json"
        
        # Create selector
        selector = AdaptiveCommandSelector()
        
        # Mock dependencies
        selector.task_generator = Mock(spec=TaskAutoGenerator)
        selector.task_generator.analyze_complexity.return_value = "moderate"
        
        selector.memory_manager = Mock(spec=MemoryGraphManager)
        selector.memory_manager.query_patterns.return_value = []
        
        selector.pattern_analyzer = Mock(spec=WorkflowPatternAnalyzer)
        selector.pattern_analyzer.get_historical_sequences.return_value = []
        selector.cache_file = cache_file
        return selector, cache_file
    
    def test_learning_persistence_across_sessions(self, persistent_selector):
        """Test that learning persists across selector instances."""
        selector1, cache_file = persistent_selector
        
        # Session 1: Learn patterns
        patterns_to_learn = [
            ("API development", "backend", "explore", True),
            ("API testing", "backend", "test", True),
            ("API deployment", "backend", "deploy", False)
        ]
        
        for task, domain, command, success in patterns_to_learn:
            selector1.learn_from_outcome(
                command=command,
                context=ContextType.GREENFIELD,
                domain=domain,
                success=success,
                duration=1800,
                task_description=task
            )
        
        # Simulate saving (would normally happen on shutdown)
        selector1._save_learning_cache()
        
        # Session 2: Create new selector with same cache file
        selector2 = AdaptiveCommandSelector()
        selector2.task_generator = selector1.task_generator
        selector2.memory_manager = selector1.memory_manager
        selector2.pattern_analyzer = selector1.pattern_analyzer
        selector2.cache_file = cache_file
        selector2._load_learning_cache()
        
        # Verify patterns were loaded
        assert len(selector2.learning_cache) == len(patterns_to_learn)
        
        # Test that learned patterns affect recommendations
        context = selector2.analyze_context(
            task_description="API feature development",
            domain="backend"
        )
        recs = selector2.recommend_commands(context)
        
        # Should favor 'explore' due to successful pattern
        explore_rec = next((r for r in recs if r.command == 'explore'), None)
        assert explore_rec is not None
        
        # Should penalize 'deploy' due to failure
        deploy_rec = next((r for r in recs if r.command == 'deploy'), None)
        if deploy_rec:
            assert deploy_rec.confidence < 0.5


class TestEdgeCaseIntegration:
    """Test edge cases in integrated environment."""
    
    @pytest.fixture
    def edge_case_system(self):
        """Create system for edge case testing."""
        selector = AdaptiveCommandSelector()
        selector.task_generator = TaskAutoGenerator()
        selector.memory_manager = Mock(spec=MemoryGraphManager)
        selector.memory_manager.query_patterns.return_value = []
        selector.pattern_analyzer = Mock(spec=WorkflowPatternAnalyzer)
        selector.pattern_analyzer.get_historical_sequences.return_value = []
        
        return {'selector': selector}
    
    def test_malformed_task_descriptions(self, edge_case_system):
        """Test handling of malformed or unusual task descriptions."""
        selector = edge_case_system['selector']
        
        edge_cases = [
            "",  # Empty
            "   ",  # Whitespace only
            "🚀 Unicode task! 测试 🎯",  # Unicode
            "A" * 1000,  # Very long
            "CREATE TABLE users (id INT PRIMARY KEY);",  # SQL injection attempt
            "<script>alert('xss')</script>",  # XSS attempt
            "../../etc/passwd",  # Path traversal
            None  # None value
        ]
        
        for task_desc in edge_cases:
            if task_desc is None:
                with pytest.raises(Exception):
                    selector.get_adaptive_recommendations(
                        task_description=task_desc,
                        domain="testing"
                    )
            else:
                # Should handle gracefully
                context = selector.analyze_context(
                    task_description=task_desc,
                    domain="testing"
                )
                recs = selector.recommend_commands(context)
                assert len(recs) > 0
                assert all(isinstance(r.command, str) for r in recs)
    
    def test_concurrent_access_patterns(self, edge_case_system):
        """Test concurrent access to adaptive selector."""
        selector = edge_case_system['selector']
        
        import threading
        import time
        
        results = []
        errors = []
        
        def get_recommendations(task_id):
            try:
                context = selector.analyze_context(
                    task_description=f"Concurrent task {task_id}",
                    domain="concurrent"
                )
                recs = selector.recommend_commands(context)
                results.append((task_id, len(recs)))
            except Exception as e:
                errors.append((task_id, str(e)))
        
        # Launch concurrent requests
        threads = []
        for i in range(20):
            t = threading.Thread(target=get_recommendations, args=(i,))
            threads.append(t)
            t.start()
        
        # Wait for completion
        for t in threads:
            t.join(timeout=5)
        
        # Verify results
        assert len(errors) == 0, f"Concurrent access errors: {errors}"
        assert len(results) == 20
        assert all(count > 0 for _, count in results)
    
    def test_memory_pressure_handling(self, edge_case_system):
        """Test behavior under memory pressure with large cache."""
        selector = edge_case_system['selector']
        
        # Fill cache with many patterns
        for i in range(10000):
            selector.learn_from_outcome(
                command=f"cmd_{i % 20}",
                context=list(ContextType)[i % len(ContextType)],
                domain=f"domain_{i % 5}",
                success=i % 3 != 0,
                duration=1000 + i,
                task_description=f"Task number {i}"
            )
        
        # Should still function
        context = selector.analyze_context(
            task_description="New task after memory pressure",
            domain="testing"
        )
        recs = selector.recommend_commands(context)
        
        assert len(recs) > 0
        # Cache should be bounded
        assert len(selector.learning_cache) <= 1000  # Reasonable limit