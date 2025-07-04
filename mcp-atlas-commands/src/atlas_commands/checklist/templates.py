"""Pre-defined checklist templates for common ATLAS command patterns."""

from typing import Dict, List, Any
from datetime import datetime


class ChecklistTemplates:
    """Collection of pre-defined checklist templates."""
    
    @staticmethod
    def planning_checklist(task_id: str, complexity: str = "medium") -> List[Dict[str, Any]]:
        """Generate planning phase checklist."""
        
        base_items = [
            {
                'id': 'problem-analysis',
                'description': 'Analyze problem scope and requirements',
                'priority': 'HIGH',
                'estimate': '20m' if complexity == 'complex' else '15m',
                'status': 'PENDING'
            },
            {
                'id': 'solution-approach',
                'description': 'Define solution approach and architecture',
                'priority': 'HIGH',
                'estimate': '25m' if complexity == 'complex' else '20m',
                'dependencies': ['problem-analysis'],
                'status': 'PENDING'
            },
            {
                'id': 'risk-assessment',
                'description': 'Identify and assess implementation risks',
                'priority': 'MEDIUM',
                'estimate': '15m',
                'dependencies': ['solution-approach'],
                'status': 'PENDING'
            },
            {
                'id': 'resource-planning',
                'description': 'Plan resource requirements and timeline',
                'priority': 'MEDIUM',
                'estimate': '10m',
                'dependencies': ['solution-approach'],
                'status': 'PENDING'
            }
        ]
        
        if complexity == 'complex':
            base_items.extend([
                {
                    'id': 'stakeholder-analysis',
                    'description': 'Analyze stakeholder impact and requirements',
                    'priority': 'MEDIUM',
                    'estimate': '15m',
                    'dependencies': ['problem-analysis'],
                    'status': 'PENDING'
                },
                {
                    'id': 'alternative-evaluation',
                    'description': 'Evaluate alternative solutions',
                    'priority': 'LOW',
                    'estimate': '20m',
                    'dependencies': ['solution-approach'],
                    'status': 'PENDING'
                }
            ])
        
        return base_items
    
    @staticmethod
    def execution_checklist(task_id: str, task_type: str = "feature") -> List[Dict[str, Any]]:
        """Generate execution phase checklist."""
        
        base_items = [
            {
                'id': 'setup-environment',
                'description': 'Setup development environment and tools',
                'priority': 'HIGH',
                'estimate': '10m',
                'status': 'PENDING'
            },
            {
                'id': 'implement-core',
                'description': 'Implement core functionality',
                'priority': 'HIGH',
                'estimate': '45m',
                'dependencies': ['setup-environment'],
                'status': 'PENDING'
            },
            {
                'id': 'unit-tests',
                'description': 'Write and run unit tests',
                'priority': 'HIGH',
                'estimate': '30m',
                'dependencies': ['implement-core'],
                'status': 'PENDING'
            },
            {
                'id': 'integration-tests',
                'description': 'Write and run integration tests',
                'priority': 'MEDIUM',
                'estimate': '25m',
                'dependencies': ['unit-tests'],
                'status': 'PENDING'
            },
            {
                'id': 'documentation',
                'description': 'Update documentation and examples',
                'priority': 'MEDIUM',
                'estimate': '20m',
                'dependencies': ['implement-core'],
                'status': 'PENDING'
            }
        ]
        
        if task_type == "refactor":
            base_items.extend([
                {
                    'id': 'backward-compatibility',
                    'description': 'Ensure backward compatibility',
                    'priority': 'HIGH',
                    'estimate': '15m',
                    'dependencies': ['implement-core'],
                    'status': 'PENDING'
                },
                {
                    'id': 'migration-testing',
                    'description': 'Test migration of existing code',
                    'priority': 'HIGH',
                    'estimate': '20m',
                    'dependencies': ['integration-tests'],
                    'status': 'PENDING'
                }
            ])
        elif task_type == "plugin":
            base_items.extend([
                {
                    'id': 'plugin-integration',
                    'description': 'Integrate with PANTHER plugin system',
                    'priority': 'HIGH',
                    'estimate': '20m',
                    'dependencies': ['implement-core'],
                    'status': 'PENDING'
                },
                {
                    'id': 'docker-setup',
                    'description': 'Setup Docker configuration',
                    'priority': 'MEDIUM',
                    'estimate': '15m',
                    'dependencies': ['plugin-integration'],
                    'status': 'PENDING'
                }
            ])
        
        return base_items
    
    @staticmethod
    def verification_checklist(task_id: str, verification_level: str = "standard") -> List[Dict[str, Any]]:
        """Generate verification phase checklist."""
        
        base_items = [
            {
                'id': 'functional-testing',
                'description': 'Run functional test suite',
                'priority': 'HIGH',
                'estimate': '15m',
                'status': 'PENDING'
            },
            {
                'id': 'code-quality',
                'description': 'Run code quality checks',
                'priority': 'HIGH',
                'estimate': '10m',
                'status': 'PENDING'
            },
            {
                'id': 'security-scan',
                'description': 'Run security vulnerability scan',
                'priority': 'HIGH',
                'estimate': '10m',
                'status': 'PENDING'
            },
            {
                'id': 'performance-check',
                'description': 'Verify performance requirements',
                'priority': 'MEDIUM',
                'estimate': '15m',
                'dependencies': ['functional-testing'],
                'status': 'PENDING'
            }
        ]
        
        if verification_level in ["thorough", "comprehensive"]:
            base_items.extend([
                {
                    'id': 'integration-verification',
                    'description': 'Verify all integration points',
                    'priority': 'HIGH',
                    'estimate': '20m',
                    'dependencies': ['functional-testing'],
                    'status': 'PENDING'
                },
                {
                    'id': 'edge-case-testing',
                    'description': 'Test edge cases and error conditions',
                    'priority': 'MEDIUM',
                    'estimate': '25m',
                    'dependencies': ['functional-testing'],
                    'status': 'PENDING'
                },
                {
                    'id': 'load-testing',
                    'description': 'Run load and stress tests',
                    'priority': 'MEDIUM',
                    'estimate': '20m',
                    'dependencies': ['performance-check'],
                    'status': 'PENDING'
                }
            ])
        
        if verification_level == "comprehensive":
            base_items.extend([
                {
                    'id': 'documentation-review',
                    'description': 'Review all documentation for accuracy',
                    'priority': 'MEDIUM',
                    'estimate': '15m',
                    'status': 'PENDING'
                },
                {
                    'id': 'user-acceptance',
                    'description': 'Validate user acceptance criteria',
                    'priority': 'HIGH',
                    'estimate': '20m',
                    'dependencies': ['integration-verification'],
                    'status': 'PENDING'
                }
            ])
        
        return base_items
    
    @staticmethod
    def completion_checklist(task_id: str, archive_level: str = "standard") -> List[Dict[str, Any]]:
        """Generate completion phase checklist."""
        
        base_items = [
            {
                'id': 'verification-validation',
                'description': 'Validate all verification requirements are met',
                'priority': 'HIGH',
                'estimate': '10m',
                'status': 'PENDING'
            },
            {
                'id': 'quality-gates-check',
                'description': 'Confirm all quality gates are satisfied',
                'priority': 'HIGH',
                'estimate': '5m',
                'dependencies': ['verification-validation'],
                'status': 'PENDING'
            },
            {
                'id': 'completion-summary',
                'description': 'Generate completion summary and status report',
                'priority': 'HIGH',
                'estimate': '15m',
                'dependencies': ['quality-gates-check'],
                'status': 'PENDING'
            },
            {
                'id': 'artifact-archival',
                'description': 'Archive task artifacts and documentation',
                'priority': 'MEDIUM',
                'estimate': '10m' if archive_level in ['comprehensive', 'release-ready'] else '5m',
                'dependencies': ['completion-summary'],
                'status': 'PENDING'
            },
            {
                'id': 'learning-capture',
                'description': 'Capture learnings and insights for future reference',
                'priority': 'MEDIUM',
                'estimate': '10m',
                'dependencies': ['completion-summary'],
                'status': 'PENDING'
            },
            {
                'id': 'status-update',
                'description': 'Update all tracking systems and close task',
                'priority': 'HIGH',
                'estimate': '5m',
                'dependencies': ['artifact-archival', 'learning-capture'],
                'status': 'PENDING'
            }
        ]
        
        if archive_level in ['comprehensive', 'release-ready']:
            base_items.extend([
                {
                    'id': 'documentation-generation',
                    'description': 'Generate comprehensive technical documentation',
                    'priority': 'MEDIUM',
                    'estimate': '20m',
                    'dependencies': ['completion-summary'],
                    'status': 'PENDING'
                },
                {
                    'id': 'metrics-analysis',
                    'description': 'Analyze performance and quality metrics',
                    'priority': 'MEDIUM',
                    'estimate': '15m',
                    'dependencies': ['quality-gates-check'],
                    'status': 'PENDING'
                }
            ])
        
        if archive_level == 'release-ready':
            base_items.extend([
                {
                    'id': 'release-notes',
                    'description': 'Generate release notes and changelog entries',
                    'priority': 'MEDIUM',
                    'estimate': '25m',
                    'dependencies': ['documentation-generation'],
                    'status': 'PENDING'
                },
                {
                    'id': 'deployment-guides',
                    'description': 'Create deployment and migration documentation',
                    'priority': 'MEDIUM',
                    'estimate': '20m',
                    'dependencies': ['documentation-generation'],
                    'status': 'PENDING'
                }
            ])
        
        return base_items
    
    @staticmethod
    def quick_fix_checklist(task_id: str) -> List[Dict[str, Any]]:
        """Generate quick fix checklist."""
        
        return [
            {
                'id': 'identify-issue',
                'description': 'Identify and isolate the issue',
                'priority': 'HIGH',
                'estimate': '5m',
                'status': 'PENDING'
            },
            {
                'id': 'apply-fix',
                'description': 'Apply the fix with minimal changes',
                'priority': 'HIGH',
                'estimate': '10m',
                'dependencies': ['identify-issue'],
                'status': 'PENDING'
            },
            {
                'id': 'quick-test',
                'description': 'Run quick validation tests',
                'priority': 'HIGH',
                'estimate': '5m',
                'dependencies': ['apply-fix'],
                'status': 'PENDING'
            },
            {
                'id': 'safety-check',
                'description': 'Verify no regressions introduced',
                'priority': 'HIGH',
                'estimate': '5m',
                'dependencies': ['quick-test'],
                'status': 'PENDING'
            }
        ]
    
    @staticmethod
    def get_template_by_command(command_name: str, **kwargs) -> List[Dict[str, Any]]:
        """Get checklist template based on command name."""
        
        template_map = {
            'plan': ChecklistTemplates.planning_checklist,
            'execute': ChecklistTemplates.execution_checklist,
            'verify': ChecklistTemplates.verification_checklist,
            'complete': ChecklistTemplates.completion_checklist,
            'quick-fix': ChecklistTemplates.quick_fix_checklist
        }
        
        if command_name in template_map:
            return template_map[command_name](**kwargs)
        else:
            # Default generic checklist
            return [
                {
                    'id': 'task-setup',
                    'description': f'Setup for {command_name} command',
                    'priority': 'HIGH',
                    'estimate': '10m',
                    'status': 'PENDING'
                },
                {
                    'id': 'task-execution',
                    'description': f'Execute {command_name} command',
                    'priority': 'HIGH',
                    'estimate': '30m',
                    'dependencies': ['task-setup'],
                    'status': 'PENDING'
                },
                {
                    'id': 'task-validation',
                    'description': f'Validate {command_name} results',
                    'priority': 'HIGH',
                    'estimate': '15m',
                    'dependencies': ['task-execution'],
                    'status': 'PENDING'
                }
            ]