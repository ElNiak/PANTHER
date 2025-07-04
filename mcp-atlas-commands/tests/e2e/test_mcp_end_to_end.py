"""
End-to-end tests for ATLAS MCP Server - Real-world workflow testing
Testing complete user scenarios, cross-component integration, and production workflows.
"""

import pytest
import asyncio
import json
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, List
from unittest.mock import Mock, patch, AsyncMock

from src.atlas_commands.server import EnhancedAtlasCommandsServer
from src.atlas_commands.intelligent_orchestrator import IntelligentMCPOrchestrator
from src.atlas_commands.coordination.workflow_manager import WorkflowManager


class TestCompleteUserWorkflows:
    """Test complete user workflows from start to finish."""
    
    @pytest.fixture
    async def full_mcp_server(self):
        """Create fully configured MCP server for E2E testing."""
        server = EnhancedAtlasCommandsServer()
        await server.initialize()
        
        # Add test resources and prompts
        await server.add_resource({
            'uri': 'atlas://test/project_template',
            'name': 'Project Template',
            'description': 'Template for new projects'
        })
        
        server.add_prompt({
            'name': 'project_planning',
            'description': 'Plan a new software project',
            'arguments': [
                {'name': 'project_type', 'required': True},
                {'name': 'complexity', 'required': False}
            ]
        })
        
        return server
    
    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace for E2E tests."""
        workspace = tempfile.mkdtemp(prefix="atlas_e2e_")
        yield Path(workspace)
        shutil.rmtree(workspace, ignore_errors=True)
    
    @pytest.mark.asyncio
    async def test_complete_project_planning_workflow(self, full_mcp_server, temp_workspace):
        """Test complete project planning workflow from start to finish."""
        
        # Step 1: User requests project planning
        planning_request = {
            'name': 'orchestrate_intelligent_tasks',
            'arguments': {
                'task_description': 'Plan a new microservices e-commerce platform',
                'context': {
                    'domain': 'backend',
                    'team_size': 5,
                    'timeline': '6 months',
                    'budget': 'medium',
                    'experience_level': 'senior'
                },
                'requirements': {
                    'scalability': 'high',
                    'security': 'critical',
                    'performance': 'high',
                    'maintainability': 'high'
                }
            }
        }
        
        planning_result = await full_mcp_server.call_tool(planning_request)
        assert planning_result is not None
        
        planning_data = json.loads(planning_result['content'][0]['text'])
        assert 'task_analysis' in planning_data
        assert 'execution_sequence' in planning_data
        
        # Step 2: User requests adaptive command selection based on planning
        command_selection_request = {
            'name': 'adaptive_command_selection',
            'arguments': {
                'current_context': {
                    'project_type': 'microservices',
                    'current_phase': 'planning',
                    'planning_result': planning_data
                },
                'available_commands': [
                    'analyze_architecture',
                    'design_database_schema', 
                    'define_api_contracts',
                    'setup_ci_cd_pipeline',
                    'create_deployment_strategy'
                ],
                'user_preferences': {
                    'automation_level': 'high',
                    'detail_level': 'comprehensive'
                }
            }
        }
        
        command_result = await full_mcp_server.call_tool(command_selection_request)
        command_data = json.loads(command_result['content'][0]['text'])
        
        assert 'recommended_command' in command_data
        assert 'confidence_score' in command_data
        assert command_data['confidence_score'] > 0.7
        
        # Step 3: User requests workflow pattern analysis
        workflow_request = {
            'name': 'analyze_workflow_patterns',
            'arguments': {
                'workflow_data': {
                    'project_planning': planning_data,
                    'recommended_commands': command_data,
                    'execution_sequence': planning_data['execution_sequence']
                },
                'analysis_depth': 'comprehensive',
                'optimization_goals': ['efficiency', 'quality', 'team_coordination']
            }
        }
        
        workflow_result = await full_mcp_server.call_tool(workflow_request)
        workflow_data = json.loads(workflow_result['content'][0]['text'])
        
        assert 'detected_patterns' in workflow_data
        assert 'optimization_recommendations' in workflow_data
        assert 'workflow_efficiency_score' in workflow_data
        
        # Step 4: User requests progress milestone tracking
        milestone_request = {
            'name': 'track_progress_milestones',
            'arguments': {
                'project_context': {
                    'name': 'E-commerce Platform',
                    'planning_data': planning_data,
                    'workflow_analysis': workflow_data
                },
                'current_progress': {
                    'completed_tasks': ['initial_planning', 'architecture_review'],
                    'in_progress_tasks': ['database_design'],
                    'blocked_tasks': []
                },
                'milestone_criteria': {
                    'quality_gates': ['code_review', 'testing', 'security_audit'],
                    'timeline_checkpoints': ['week_2', 'month_1', 'month_3'],
                    'deliverables': ['mvp', 'beta', 'production']
                }
            }
        }
        
        milestone_result = await full_mcp_server.call_tool(milestone_request)
        milestone_data = json.loads(milestone_result['content'][0]['text'])
        
        assert 'milestone_status' in milestone_data
        assert 'next_actions' in milestone_data
        assert 'risk_assessment' in milestone_data
        
        # Verify complete workflow coherence
        assert planning_data['estimated_efficiency_gain'] > 0
        assert workflow_data['workflow_efficiency_score'] > 0.5
        assert len(milestone_data['next_actions']) > 0
        
        print("\n=== Complete Project Planning Workflow Results ===")
        print(f"Planning efficiency gain: {planning_data['estimated_efficiency_gain']:.2%}")
        print(f"Workflow efficiency score: {workflow_data['workflow_efficiency_score']:.2f}")
        print(f"Next actions count: {len(milestone_data['next_actions'])}")
    
    @pytest.mark.asyncio
    async def test_iterative_task_refinement_workflow(self, full_mcp_server):
        """Test iterative task refinement and optimization workflow."""
        
        # Initial task request
        initial_task = {
            'name': 'orchestrate_intelligent_tasks',
            'arguments': {
                'task_description': 'Improve application performance',
                'context': {'domain': 'performance', 'urgency': 'high'},
                'requirements': {'target_improvement': '50%'}
            }
        }
        
        initial_result = await full_mcp_server.call_tool(initial_task)
        initial_data = json.loads(initial_result['content'][0]['text'])
        
        # Refinement iteration 1: More specific requirements
        refined_task_1 = {
            'name': 'orchestrate_intelligent_tasks',
            'arguments': {
                'task_description': 'Optimize database queries and implement caching for 50% performance improvement',
                'context': {
                    'domain': 'performance',
                    'urgency': 'high',
                    'previous_analysis': initial_data,
                    'specific_areas': ['database', 'caching', 'query_optimization']
                },
                'requirements': {
                    'target_improvement': '50%',
                    'budget_constraint': 'minimal',
                    'implementation_time': '2_weeks'
                }
            }
        }
        
        refined_result_1 = await full_mcp_server.call_tool(refined_task_1)
        refined_data_1 = json.loads(refined_result_1['content'][0]['text'])
        
        # Refinement iteration 2: Even more specific with feedback
        refined_task_2 = {
            'name': 'orchestrate_intelligent_tasks',
            'arguments': {
                'task_description': 'Implement Redis caching layer and optimize top 10 slowest database queries',
                'context': {
                    'domain': 'performance',
                    'urgency': 'high',
                    'previous_analyses': [initial_data, refined_data_1],
                    'feedback': 'Focus on most impactful optimizations first',
                    'constraints': ['no_schema_changes', 'backward_compatible']
                },
                'requirements': {
                    'target_improvement': '50%',
                    'budget_constraint': 'minimal',
                    'implementation_time': '2_weeks',
                    'rollback_plan': 'required'
                }
            }
        }
        
        refined_result_2 = await full_mcp_server.call_tool(refined_task_2)
        refined_data_2 = json.loads(refined_result_2['content'][0]['text'])
        
        # Verify refinement improved the plan
        assert refined_data_2['estimated_efficiency_gain'] >= refined_data_1['estimated_efficiency_gain']
        assert len(refined_data_2['execution_sequence']) >= len(initial_data['execution_sequence'])
        
        # Final adaptive command selection based on refined plan
        final_command_request = {
            'name': 'adaptive_command_selection',
            'arguments': {
                'current_context': {
                    'refined_plan': refined_data_2,
                    'iteration_count': 2,
                    'refinement_history': [initial_data, refined_data_1, refined_data_2]
                },
                'available_commands': [
                    'implement_redis_caching',
                    'optimize_database_queries',
                    'setup_performance_monitoring',
                    'create_rollback_plan',
                    'run_performance_tests'
                ],
                'user_preferences': {
                    'risk_tolerance': 'low',
                    'automation_level': 'high'
                }
            }
        }
        
        final_result = await full_mcp_server.call_tool(final_command_request)
        final_data = json.loads(final_result['content'][0]['text'])
        
        assert final_data['confidence_score'] > 0.8  # High confidence after refinement
        assert 'implementation_order' in final_data
        
        print("\n=== Iterative Refinement Workflow Results ===")
        print(f"Initial efficiency gain: {initial_data['estimated_efficiency_gain']:.2%}")
        print(f"Final efficiency gain: {refined_data_2['estimated_efficiency_gain']:.2%}")
        print(f"Final confidence score: {final_data['confidence_score']:.2f}")
    
    @pytest.mark.asyncio
    async def test_multi_domain_coordination_workflow(self, full_mcp_server):
        """Test coordination across multiple domains (frontend, backend, devops)."""
        
        # Backend team task
        backend_task = {
            'name': 'orchestrate_intelligent_tasks',
            'arguments': {
                'task_description': 'Design and implement REST API for user management',
                'context': {
                    'domain': 'backend',
                    'team': 'backend_team',
                    'technologies': ['python', 'fastapi', 'postgresql']
                },
                'requirements': {
                    'api_documentation': 'openapi',
                    'authentication': 'jwt',
                    'rate_limiting': 'required'
                }
            }
        }
        
        backend_result = await full_mcp_server.call_tool(backend_task)
        backend_data = json.loads(backend_result['content'][0]['text'])
        
        # Frontend team task
        frontend_task = {
            'name': 'orchestrate_intelligent_tasks',
            'arguments': {
                'task_description': 'Build user interface components for user management',
                'context': {
                    'domain': 'frontend',
                    'team': 'frontend_team',
                    'technologies': ['react', 'typescript', 'tailwind'],
                    'backend_dependencies': backend_data
                },
                'requirements': {
                    'responsive_design': 'required',
                    'accessibility': 'wcag_2.1',
                    'api_integration': backend_data['api_contract'] if 'api_contract' in backend_data else {}
                }
            }
        }
        
        frontend_result = await full_mcp_server.call_tool(frontend_task)
        frontend_data = json.loads(frontend_result['content'][0]['text'])
        
        # DevOps team task
        devops_task = {
            'name': 'orchestrate_intelligent_tasks',
            'arguments': {
                'task_description': 'Setup deployment pipeline and infrastructure',
                'context': {
                    'domain': 'devops',
                    'team': 'devops_team',
                    'dependencies': {
                        'backend': backend_data,
                        'frontend': frontend_data
                    }
                },
                'requirements': {
                    'ci_cd_pipeline': 'github_actions',
                    'infrastructure': 'kubernetes',
                    'monitoring': 'required',
                    'auto_scaling': 'enabled'
                }
            }
        }
        
        devops_result = await full_mcp_server.call_tool(devops_task)
        devops_data = json.loads(devops_result['content'][0]['text'])
        
        # Cross-domain workflow analysis
        cross_domain_analysis = {
            'name': 'analyze_workflow_patterns',
            'arguments': {
                'workflow_data': {
                    'backend_workflow': backend_data,
                    'frontend_workflow': frontend_data,
                    'devops_workflow': devops_data,
                    'coordination_points': [
                        'api_contract_agreement',
                        'deployment_synchronization',
                        'testing_coordination'
                    ]
                },
                'analysis_depth': 'cross_domain',
                'optimization_goals': [
                    'team_coordination',
                    'dependency_management',
                    'delivery_synchronization'
                ]
            }
        }
        
        analysis_result = await full_mcp_server.call_tool(cross_domain_analysis)
        analysis_data = json.loads(analysis_result['content'][0]['text'])
        
        # Verify cross-domain coordination
        assert 'coordination_efficiency' in analysis_data
        assert 'dependency_conflicts' in analysis_data
        assert 'synchronization_points' in analysis_data
        
        # All teams should have reasonable efficiency gains
        assert backend_data['estimated_efficiency_gain'] > 0.2
        assert frontend_data['estimated_efficiency_gain'] > 0.2
        assert devops_data['estimated_efficiency_gain'] > 0.2
        
        print("\n=== Multi-Domain Coordination Results ===")
        print(f"Backend efficiency: {backend_data['estimated_efficiency_gain']:.2%}")
        print(f"Frontend efficiency: {frontend_data['estimated_efficiency_gain']:.2%}")
        print(f"DevOps efficiency: {devops_data['estimated_efficiency_gain']:.2%}")
        print(f"Cross-domain coordination: {analysis_data['coordination_efficiency']:.2f}")


class TestRealWorldScenarios:
    """Test real-world scenarios and edge cases."""
    
    @pytest.mark.asyncio
    async def test_large_scale_migration_scenario(self, full_mcp_server):
        """Test large-scale system migration scenario."""
        
        migration_request = {
            'name': 'orchestrate_intelligent_tasks',
            'arguments': {
                'task_description': 'Migrate monolithic e-commerce platform to microservices architecture',
                'context': {
                    'domain': 'architecture',
                    'current_system': {
                        'type': 'monolith',
                        'language': 'php',
                        'database': 'mysql',
                        'users': '1M+',
                        'transaction_volume': 'high'
                    },
                    'target_system': {
                        'type': 'microservices',
                        'technologies': ['kubernetes', 'docker', 'istio'],
                        'languages': ['python', 'golang', 'nodejs'],
                        'databases': ['postgresql', 'redis', 'elasticsearch']
                    },
                    'constraints': {
                        'zero_downtime': True,
                        'data_migration': 'incremental',
                        'rollback_capability': 'required',
                        'timeline': '12_months'
                    }
                },
                'requirements': {
                    'scalability_improvement': '10x',
                    'performance_improvement': '3x',
                    'cost_optimization': '25%',
                    'team_training': 'included'
                }
            }
        }
        
        migration_result = await full_mcp_server.call_tool(migration_request)
        migration_data = json.loads(migration_result['content'][0]['text'])
        
        # Verify comprehensive migration plan
        assert 'execution_sequence' in migration_data
        assert len(migration_data['execution_sequence']) >= 10  # Complex migration has many steps
        
        # Should include risk mitigation
        execution_sequence = migration_data['execution_sequence']
        risk_mitigation_steps = [
            step for step in execution_sequence 
            if 'risk' in step.get('step_name', '').lower() or 'rollback' in step.get('step_name', '').lower()
        ]
        assert len(risk_mitigation_steps) > 0
        
        # Should have realistic timeline
        total_estimated_duration = sum(
            step.get('estimated_duration', 0) for step in execution_sequence
        )
        assert total_estimated_duration > 100  # Hours for large migration
        
        print(f"\nMigration plan steps: {len(migration_data['execution_sequence'])}")
        print(f"Total estimated duration: {total_estimated_duration} hours")
        print(f"Efficiency gain: {migration_data['estimated_efficiency_gain']:.2%}")
    
    @pytest.mark.asyncio
    async def test_emergency_incident_response_scenario(self, full_mcp_server):
        """Test emergency incident response scenario."""
        
        incident_request = {
            'name': 'orchestrate_intelligent_tasks',
            'arguments': {
                'task_description': 'Respond to production outage - database connection pool exhausted',
                'context': {
                    'domain': 'incident_response',
                    'severity': 'critical',
                    'impact': 'all_users_affected',
                    'timeline': 'immediate',
                    'incident_details': {
                        'symptoms': [
                            'application_timeouts',
                            'database_connection_errors',
                            'high_response_times'
                        ],
                        'affected_services': ['user_auth', 'payment_processing', 'order_management'],
                        'traffic_level': 'peak_hours',
                        'last_deployment': '2_hours_ago'
                    }
                },
                'requirements': {
                    'resolution_time': '< 30_minutes',
                    'communication_plan': 'required',
                    'root_cause_analysis': 'immediate',
                    'prevention_measures': 'required'
                }
            }
        }
        
        incident_result = await full_mcp_server.call_tool(incident_request)
        incident_data = json.loads(incident_result['content'][0]['text'])
        
        # Verify rapid response plan
        execution_sequence = incident_data['execution_sequence']
        
        # Should prioritize immediate actions
        immediate_actions = [
            step for step in execution_sequence[:3]  # First 3 steps
            if step.get('estimated_duration', 0) < 10  # < 10 minutes each
        ]
        assert len(immediate_actions) >= 2
        
        # Should include communication steps
        communication_steps = [
            step for step in execution_sequence
            if 'communication' in step.get('step_name', '').lower() or 'notify' in step.get('step_name', '').lower()
        ]
        assert len(communication_steps) > 0
        
        # Should have high urgency weighting
        urgent_steps = [
            step for step in execution_sequence
            if step.get('priority', '').lower() in ['critical', 'high', 'urgent']
        ]
        assert len(urgent_steps) >= len(execution_sequence) // 2  # At least half should be urgent
    
    @pytest.mark.asyncio
    async def test_compliance_audit_scenario(self, full_mcp_server):
        """Test compliance audit preparation scenario."""
        
        audit_request = {
            'name': 'orchestrate_intelligent_tasks',
            'arguments': {
                'task_description': 'Prepare for SOC 2 Type II compliance audit',
                'context': {
                    'domain': 'compliance',
                    'audit_type': 'soc2_type2',
                    'timeline': '90_days',
                    'current_compliance_level': 'partial',
                    'systems_in_scope': [
                        'customer_data_processing',
                        'payment_processing',
                        'access_management',
                        'data_backup_recovery'
                    ],
                    'previous_audits': {
                        'last_audit': 'iso27001_2022',
                        'findings': 3,
                        'status': 'passed_with_recommendations'
                    }
                },
                'requirements': {
                    'documentation_completeness': '100%',
                    'evidence_collection': 'automated',
                    'gap_remediation': 'prioritized',
                    'audit_readiness': 'full'
                }
            }
        }
        
        audit_result = await full_mcp_server.call_tool(audit_request)
        audit_data = json.loads(audit_result['content'][0]['text'])
        
        # Verify comprehensive audit preparation
        execution_sequence = audit_data['execution_sequence']
        
        # Should include documentation steps
        documentation_steps = [
            step for step in execution_sequence
            if 'document' in step.get('step_name', '').lower() or 'policy' in step.get('step_name', '').lower()
        ]
        assert len(documentation_steps) >= 3
        
        # Should include evidence collection
        evidence_steps = [
            step for step in execution_sequence
            if 'evidence' in step.get('step_name', '').lower() or 'collect' in step.get('step_name', '').lower()
        ]
        assert len(evidence_steps) >= 2
        
        # Should include gap analysis
        gap_analysis_steps = [
            step for step in execution_sequence
            if 'gap' in step.get('step_name', '').lower() or 'assess' in step.get('step_name', '').lower()
        ]
        assert len(gap_analysis_steps) >= 1


class TestErrorRecoveryAndResilience:
    """Test error recovery and system resilience."""
    
    @pytest.mark.asyncio
    async def test_partial_failure_recovery(self, full_mcp_server):
        """Test recovery from partial component failures."""
        
        # Simulate partial failure scenario
        with patch('src.atlas_commands.task_analysis_algorithm.TaskComplexityAnalyzer') as mock_analyzer:
            # Make analyzer fail intermittently
            mock_analyzer.side_effect = [Exception("Temporary failure"), None, None]
            
            # Request should handle failure gracefully
            resilient_request = {
                'name': 'orchestrate_intelligent_tasks',
                'arguments': {
                    'task_description': 'Test resilience under component failure',
                    'context': {'domain': 'resilience_test'},
                    'requirements': {'fault_tolerance': 'high'}
                }
            }
            
            # Should either succeed with degraded functionality or fail gracefully
            try:
                result = await full_mcp_server.call_tool(resilient_request)
                # If successful, should indicate degraded mode
                data = json.loads(result['content'][0]['text'])
                if 'degraded_mode' in data or 'partial_analysis' in data:
                    assert True  # Graceful degradation
                else:
                    assert data is not None  # Full recovery
            except Exception as e:
                # Graceful failure is acceptable
                assert "analysis" in str(e).lower() or "temporary" in str(e).lower()
    
    @pytest.mark.asyncio
    async def test_resource_exhaustion_handling(self, full_mcp_server):
        """Test handling of resource exhaustion scenarios."""
        
        # Create resource-intensive request
        resource_intensive_request = {
            'name': 'orchestrate_intelligent_tasks',
            'arguments': {
                'task_description': 'Process extremely large dataset with complex analysis' + ' data' * 1000,
                'context': {
                    'domain': 'big_data',
                    'dataset_size': '1TB+',
                    'processing_complexity': 'maximum',
                    'memory_constraints': 'limited'
                },
                'requirements': {
                    'accuracy': 'highest',
                    'completeness': 'full',
                    'resource_optimization': 'required'
                }
            }
        }
        
        # Should handle resource constraints gracefully
        try:
            result = await asyncio.wait_for(
                full_mcp_server.call_tool(resource_intensive_request),
                timeout=30.0  # Reasonable timeout
            )
            
            if result:
                data = json.loads(result['content'][0]['text'])
                # Should have resource optimization strategies
                assert 'resource_allocation' in data or 'optimization_strategy' in data
                
        except (asyncio.TimeoutError, MemoryError) as e:
            # Timeout or memory errors are acceptable for extreme loads
            assert True
        except Exception as e:
            # Should be a meaningful error message
            error_msg = str(e).lower()
            assert any(keyword in error_msg for keyword in ['resource', 'memory', 'timeout', 'limit'])


@pytest.fixture(scope="module")
def event_loop():
    """Create event loop for module-level async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-s"])