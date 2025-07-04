"""
Task Auto Generator Module
Provides automatic task generation and complexity analysis for ATLAS MCP coordination.
"""

import asyncio
import json
import logging
import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict


class TaskComplexity(Enum):
    """Task complexity levels for automatic generation."""
    TRIVIAL = "trivial"      # < 1 hour
    SIMPLE = "simple"        # 1-4 hours
    MODERATE = "moderate"    # 4-16 hours
    COMPLEX = "complex"      # 16-40 hours
    EPIC = "epic"           # > 40 hours


class TaskType(Enum):
    """Types of tasks that can be automatically generated."""
    IMPLEMENTATION = "implementation"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    REFACTORING = "refactoring"
    ANALYSIS = "analysis"
    DEBUGGING = "debugging"
    DEPLOYMENT = "deployment"
    MAINTENANCE = "maintenance"


class TaskPriority(Enum):
    """Task priority levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class GeneratedTask:
    """Represents a generated task with metadata."""
    id: str
    title: str
    description: str
    complexity: TaskComplexity
    task_type: TaskType
    priority: TaskPriority
    estimated_hours: float
    dependencies: List[str]
    prerequisites: List[str]
    success_criteria: List[str]
    subtasks: List[str]
    domain: str
    context: Dict[str, Any]
    creation_timestamp: str


@dataclass
class TaskTemplate:
    """Template for task generation."""
    name: str
    description_pattern: str
    complexity_range: Tuple[TaskComplexity, TaskComplexity]
    task_type: TaskType
    default_priority: TaskPriority
    common_dependencies: List[str]
    success_criteria_patterns: List[str]


class TaskAutoGenerator:
    """
    Automatically generates tasks based on context analysis and patterns.
    
    Provides intelligent task decomposition and complexity analysis for ATLAS coordination.
    """
    
    def __init__(self, storage_path: Optional[str] = None):
        """Initialize the task auto generator."""
        
        self.logger = logging.getLogger(__name__)
        self.storage_path = storage_path
        
        # Task generation templates
        self.task_templates = self._initialize_task_templates()
        
        # Complexity analysis patterns
        self.complexity_indicators = {
            "trivial": ["fix typo", "update comment", "add log", "simple change"],
            "simple": ["add method", "update config", "fix bug", "small feature"],
            "moderate": ["implement feature", "refactor module", "add tests", "integrate"],
            "complex": ["design system", "migrate data", "major refactor", "performance"],
            "epic": ["architecture", "complete rewrite", "full migration", "new platform"]
        }
        
        # Domain-specific complexity multipliers
        self.domain_multipliers = {
            "security": 1.5,
            "performance": 1.3,
            "integration": 1.4,
            "data_migration": 1.6,
            "legacy_systems": 1.4,
            "distributed_systems": 1.5,
            "machine_learning": 1.3,
            "frontend": 1.1,
            "backend": 1.2,
            "database": 1.3
        }
        
        # Task generation history
        self.generation_history = []
        self.task_registry = {}
        
        self.logger.info("TaskAutoGenerator initialized")
    
    def analyze_complexity(self, 
                          task_description: str,
                          domain: str = "general",
                          context: Dict[str, Any] = None) -> Tuple[TaskComplexity, Dict[str, Any]]:
        """
        Analyze the complexity of a task description.
        
        Args:
            task_description: Description of the task
            domain: Domain context
            context: Additional context information
            
        Returns:
            Tuple of (complexity_level, analysis_details)
        """
        
        context = context or {}
        description_lower = task_description.lower()
        
        # Base complexity scoring
        base_score = 0
        indicators_found = []
        
        # Check complexity indicators
        for complexity_level, indicators in self.complexity_indicators.items():
            for indicator in indicators:
                if indicator in description_lower:
                    if complexity_level == "epic":
                        base_score += 50
                    elif complexity_level == "complex":
                        base_score += 30
                    elif complexity_level == "moderate":
                        base_score += 20
                    elif complexity_level == "simple":
                        base_score += 10
                    else:  # trivial
                        base_score += 5
                    
                    indicators_found.append(f"{complexity_level}: {indicator}")
        
        # Apply domain multiplier
        domain_multiplier = self.domain_multipliers.get(domain, 1.0)
        adjusted_score = base_score * domain_multiplier
        
        # Additional complexity factors
        if "multiple" in description_lower or "several" in description_lower:
            adjusted_score *= 1.2
        
        if "integrate" in description_lower or "connect" in description_lower:
            adjusted_score *= 1.3
        
        if "test" in description_lower:
            adjusted_score *= 1.1
        
        # Estimate hours based on score
        if adjusted_score < 10:
            complexity = TaskComplexity.TRIVIAL
            estimated_hours = 0.5
        elif adjusted_score < 25:
            complexity = TaskComplexity.SIMPLE
            estimated_hours = 2.0
        elif adjusted_score < 50:
            complexity = TaskComplexity.MODERATE
            estimated_hours = 8.0
        elif adjusted_score < 80:
            complexity = TaskComplexity.COMPLEX
            estimated_hours = 24.0
        else:
            complexity = TaskComplexity.EPIC
            estimated_hours = 60.0
        
        analysis_details = {
            "base_score": base_score,
            "domain_multiplier": domain_multiplier,
            "adjusted_score": adjusted_score,
            "estimated_hours": estimated_hours,
            "indicators_found": indicators_found,
            "domain": domain,
            "analysis_timestamp": datetime.now().isoformat()
        }
        
        return complexity, analysis_details
    
    def generate_task_breakdown(self,
                               main_task_description: str,
                               domain: str = "general",
                               max_subtasks: int = 8,
                               context: Dict[str, Any] = None) -> List[GeneratedTask]:
        """
        Generate a breakdown of subtasks for a main task.
        
        Args:
            main_task_description: Description of the main task
            domain: Domain context
            max_subtasks: Maximum number of subtasks to generate
            context: Additional context
            
        Returns:
            List of generated subtasks
        """
        
        context = context or {}
        
        # Analyze main task complexity
        main_complexity, complexity_analysis = self.analyze_complexity(
            main_task_description, domain, context
        )
        
        # Generate subtasks based on complexity and patterns
        subtasks = []
        
        if main_complexity in [TaskComplexity.COMPLEX, TaskComplexity.EPIC]:
            # Break down complex tasks into phases
            subtasks.extend(self._generate_phase_based_subtasks(
                main_task_description, domain, context
            ))
        elif main_complexity == TaskComplexity.MODERATE:
            # Break down moderate tasks into functional components
            subtasks.extend(self._generate_component_based_subtasks(
                main_task_description, domain, context
            ))
        else:
            # Simple tasks may not need breakdown, but provide completion steps
            subtasks.extend(self._generate_completion_steps(
                main_task_description, domain, context
            ))
        
        # Limit subtasks to max_subtasks
        subtasks = subtasks[:max_subtasks]
        
        # Update generation history
        generation_record = {
            "main_task": main_task_description,
            "domain": domain,
            "complexity": main_complexity.value,
            "subtask_count": len(subtasks),
            "timestamp": datetime.now().isoformat()
        }
        self.generation_history.append(generation_record)
        
        return subtasks
    
    def suggest_task_optimizations(self,
                                  task_description: str,
                                  domain: str = "general",
                                  context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Suggest optimizations for a task based on patterns and best practices.
        
        Args:
            task_description: Description of the task
            domain: Domain context
            context: Additional context
            
        Returns:
            Dictionary of optimization suggestions
        """
        
        context = context or {}
        description_lower = task_description.lower()
        
        suggestions = {
            "automation_opportunities": [],
            "parallel_execution": [],
            "risk_mitigation": [],
            "efficiency_improvements": [],
            "tool_recommendations": []
        }
        
        # Automation opportunities
        if "test" in description_lower:
            suggestions["automation_opportunities"].append("Implement automated testing")
        
        if "deploy" in description_lower:
            suggestions["automation_opportunities"].append("Use CI/CD pipeline")
        
        if "document" in description_lower:
            suggestions["automation_opportunities"].append("Generate docs automatically")
        
        # Parallel execution opportunities
        if "test" in description_lower and "implement" in description_lower:
            suggestions["parallel_execution"].append("Run tests in parallel with implementation")
        
        if "multiple" in description_lower:
            suggestions["parallel_execution"].append("Process multiple items concurrently")
        
        # Risk mitigation
        if "refactor" in description_lower or "migrate" in description_lower:
            suggestions["risk_mitigation"].extend([
                "Create comprehensive backup",
                "Implement rollback mechanism",
                "Test in staging environment first"
            ])
        
        if "production" in description_lower or "live" in description_lower:
            suggestions["risk_mitigation"].extend([
                "Use blue-green deployment",
                "Monitor system metrics closely",
                "Have incident response plan ready"
            ])
        
        # Efficiency improvements
        if "analyze" in description_lower:
            suggestions["efficiency_improvements"].append("Use incremental analysis")
        
        if "process" in description_lower:
            suggestions["efficiency_improvements"].append("Implement batch processing")
        
        # Tool recommendations based on domain
        domain_tools = {
            "frontend": ["webpack", "jest", "cypress"],
            "backend": ["docker", "kubernetes", "monitoring"],
            "database": ["migration tools", "backup tools", "performance monitoring"],
            "security": ["static analysis", "dependency scanning", "penetration testing"]
        }
        
        if domain in domain_tools:
            suggestions["tool_recommendations"] = domain_tools[domain]
        
        return suggestions
    
    def estimate_task_duration(self,
                              task_description: str,
                              domain: str = "general",
                              team_size: int = 1,
                              context: Dict[str, Any] = None) -> Dict[str, float]:
        """
        Estimate task duration with different scenarios.
        
        Args:
            task_description: Description of the task
            domain: Domain context
            team_size: Size of the team working on the task
            context: Additional context
            
        Returns:
            Dictionary with different duration estimates
        """
        
        complexity, analysis = self.analyze_complexity(task_description, domain, context)
        base_hours = analysis["estimated_hours"]
        
        # Adjust for team size (with diminishing returns)
        if team_size > 1:
            # Brooks' Law: Adding people to a late project makes it later
            # But some tasks can benefit from parallelization
            team_efficiency = 1.0 + (team_size - 1) * 0.7  # 70% efficiency per additional person
            parallel_adjusted_hours = base_hours / team_efficiency
        else:
            parallel_adjusted_hours = base_hours
        
        # Different scenario estimates
        estimates = {
            "optimistic": parallel_adjusted_hours * 0.7,  # Everything goes well
            "realistic": parallel_adjusted_hours,          # Expected case
            "pessimistic": parallel_adjusted_hours * 1.5,  # Some issues arise
            "with_testing": parallel_adjusted_hours * 1.3, # Including comprehensive testing
            "with_documentation": parallel_adjusted_hours * 1.2, # Including documentation
            "full_pipeline": parallel_adjusted_hours * 1.6 # Including testing, docs, deployment
        }
        
        return estimates
    
    def get_task_dependencies(self,
                             task_description: str,
                             domain: str = "general",
                             context: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Identify potential dependencies for a task.
        
        Args:
            task_description: Description of the task
            domain: Domain context
            context: Additional context
            
        Returns:
            List of dependency descriptions
        """
        
        description_lower = task_description.lower()
        dependencies = []
        
        # Implementation dependencies
        if "test" in description_lower:
            dependencies.append({
                "type": "prerequisite",
                "description": "Implementation must be complete",
                "critical": True
            })
        
        if "deploy" in description_lower:
            dependencies.append({
                "type": "prerequisite", 
                "description": "Testing must be complete",
                "critical": True
            })
        
        if "integrate" in description_lower:
            dependencies.append({
                "type": "external",
                "description": "External system availability",
                "critical": True
            })
        
        # Documentation dependencies
        if "document" in description_lower:
            dependencies.append({
                "type": "prerequisite",
                "description": "Feature implementation must be stable",
                "critical": False
            })
        
        # Domain-specific dependencies
        if domain == "database":
            dependencies.append({
                "type": "resource",
                "description": "Database backup and migration scripts",
                "critical": True
            })
        
        if domain == "security":
            dependencies.append({
                "type": "review",
                "description": "Security review and approval",
                "critical": True
            })
        
        return dependencies
    
    def generate_success_criteria(self,
                                 task_description: str,
                                 domain: str = "general",
                                 context: Dict[str, Any] = None) -> List[str]:
        """
        Generate success criteria for a task.
        
        Args:
            task_description: Description of the task
            domain: Domain context
            context: Additional context
            
        Returns:
            List of success criteria
        """
        
        description_lower = task_description.lower()
        criteria = []
        
        # Basic completion criteria
        criteria.append("Task implementation is complete")
        
        # Quality criteria
        if "implement" in description_lower or "develop" in description_lower:
            criteria.extend([
                "Code passes all existing tests",
                "Code follows project coding standards",
                "Implementation meets functional requirements"
            ])
        
        # Testing criteria
        if "test" in description_lower:
            criteria.extend([
                "All test cases pass",
                "Code coverage meets project standards",
                "No critical bugs identified"
            ])
        
        # Performance criteria
        if "performance" in description_lower or "optimize" in description_lower:
            criteria.extend([
                "Performance benchmarks are met",
                "No performance regressions introduced",
                "Resource usage is within acceptable limits"
            ])
        
        # Deployment criteria
        if "deploy" in description_lower:
            criteria.extend([
                "Deployment process completes successfully",
                "System health checks pass",
                "Rollback plan is tested and ready"
            ])
        
        # Documentation criteria
        if "document" in description_lower:
            criteria.extend([
                "Documentation is complete and accurate",
                "Examples and usage patterns are provided",
                "Documentation passes review"
            ])
        
        return criteria
    
    def _initialize_task_templates(self) -> Dict[str, TaskTemplate]:
        """Initialize task generation templates."""
        
        templates = {}
        
        # Implementation templates
        templates["feature_implementation"] = TaskTemplate(
            name="Feature Implementation",
            description_pattern="Implement {feature_name} with {requirements}",
            complexity_range=(TaskComplexity.MODERATE, TaskComplexity.COMPLEX),
            task_type=TaskType.IMPLEMENTATION,
            default_priority=TaskPriority.HIGH,
            common_dependencies=["design_approval", "requirements_complete"],
            success_criteria_patterns=["feature_works", "tests_pass", "code_reviewed"]
        )
        
        templates["bug_fix"] = TaskTemplate(
            name="Bug Fix",
            description_pattern="Fix {bug_description} in {component}",
            complexity_range=(TaskComplexity.SIMPLE, TaskComplexity.MODERATE),
            task_type=TaskType.DEBUGGING,
            default_priority=TaskPriority.HIGH,
            common_dependencies=["bug_reproduced", "root_cause_identified"],
            success_criteria_patterns=["bug_fixed", "regression_tests_added"]
        )
        
        templates["refactoring"] = TaskTemplate(
            name="Code Refactoring",
            description_pattern="Refactor {component} to {improvement}",
            complexity_range=(TaskComplexity.MODERATE, TaskComplexity.COMPLEX),
            task_type=TaskType.REFACTORING,
            default_priority=TaskPriority.MEDIUM,
            common_dependencies=["test_coverage_adequate", "refactor_plan_approved"],
            success_criteria_patterns=["code_improved", "functionality_preserved", "tests_pass"]
        )
        
        # Testing templates
        templates["test_implementation"] = TaskTemplate(
            name="Test Implementation",
            description_pattern="Implement tests for {component}",
            complexity_range=(TaskComplexity.SIMPLE, TaskComplexity.MODERATE),
            task_type=TaskType.TESTING,
            default_priority=TaskPriority.MEDIUM,
            common_dependencies=["implementation_complete"],
            success_criteria_patterns=["tests_comprehensive", "coverage_adequate"]
        )
        
        return templates
    
    def _generate_phase_based_subtasks(self,
                                      main_task: str,
                                      domain: str,
                                      context: Dict[str, Any]) -> List[GeneratedTask]:
        """Generate subtasks based on project phases."""
        
        subtasks = []
        base_id = self._generate_task_id(main_task)
        
        phases = [
            ("analysis", "Analyze requirements and current state"),
            ("design", "Design solution architecture"),
            ("implementation", "Implement core functionality"),
            ("testing", "Comprehensive testing"),
            ("documentation", "Create documentation"),
            ("deployment", "Deploy and validate")
        ]
        
        for i, (phase, description) in enumerate(phases):
            subtask = GeneratedTask(
                id=f"{base_id}_phase_{i+1}_{phase}",
                title=f"Phase {i+1}: {phase.title()}",
                description=f"{description} for {main_task}",
                complexity=TaskComplexity.MODERATE,
                task_type=self._map_phase_to_task_type(phase),
                priority=TaskPriority.HIGH if phase in ["implementation", "testing"] else TaskPriority.MEDIUM,
                estimated_hours=8.0,
                dependencies=[f"{base_id}_phase_{i}_{phases[i-1][0]}"] if i > 0 else [],
                prerequisites=[],
                success_criteria=[f"{phase.title()} phase completed successfully"],
                subtasks=[],
                domain=domain,
                context=context,
                creation_timestamp=datetime.now().isoformat()
            )
            subtasks.append(subtask)
        
        return subtasks
    
    def _generate_component_based_subtasks(self,
                                          main_task: str,
                                          domain: str,
                                          context: Dict[str, Any]) -> List[GeneratedTask]:
        """Generate subtasks based on functional components."""
        
        subtasks = []
        base_id = self._generate_task_id(main_task)
        
        components = [
            ("core_logic", "Implement core business logic"),
            ("data_layer", "Implement data access layer"),
            ("api_layer", "Implement API interfaces"),
            ("validation", "Add input validation and error handling"),
            ("testing", "Create comprehensive tests")
        ]
        
        for i, (component, description) in enumerate(components):
            subtask = GeneratedTask(
                id=f"{base_id}_comp_{i+1}_{component}",
                title=f"Component: {component.replace('_', ' ').title()}",
                description=f"{description} for {main_task}",
                complexity=TaskComplexity.SIMPLE,
                task_type=TaskType.IMPLEMENTATION,
                priority=TaskPriority.MEDIUM,
                estimated_hours=4.0,
                dependencies=[],
                prerequisites=[],
                success_criteria=[f"{component.replace('_', ' ').title()} implemented and tested"],
                subtasks=[],
                domain=domain,
                context=context,
                creation_timestamp=datetime.now().isoformat()
            )
            subtasks.append(subtask)
        
        return subtasks
    
    def _generate_completion_steps(self,
                                  main_task: str,
                                  domain: str,
                                  context: Dict[str, Any]) -> List[GeneratedTask]:
        """Generate completion steps for simple tasks."""
        
        subtasks = []
        base_id = self._generate_task_id(main_task)
        
        steps = [
            ("implement", "Complete the implementation"),
            ("test", "Test the implementation"),
            ("review", "Code review and approval")
        ]
        
        for i, (step, description) in enumerate(steps):
            subtask = GeneratedTask(
                id=f"{base_id}_step_{i+1}_{step}",
                title=f"Step {i+1}: {step.title()}",
                description=f"{description} for {main_task}",
                complexity=TaskComplexity.SIMPLE,
                task_type=self._map_step_to_task_type(step),
                priority=TaskPriority.MEDIUM,
                estimated_hours=2.0,
                dependencies=[f"{base_id}_step_{i}_{steps[i-1][0]}"] if i > 0 else [],
                prerequisites=[],
                success_criteria=[f"{step.title()} completed successfully"],
                subtasks=[],
                domain=domain,
                context=context,
                creation_timestamp=datetime.now().isoformat()
            )
            subtasks.append(subtask)
        
        return subtasks
    
    def _map_phase_to_task_type(self, phase: str) -> TaskType:
        """Map phase name to task type."""
        
        mapping = {
            "analysis": TaskType.ANALYSIS,
            "design": TaskType.ANALYSIS,
            "implementation": TaskType.IMPLEMENTATION,
            "testing": TaskType.TESTING,
            "documentation": TaskType.DOCUMENTATION,
            "deployment": TaskType.DEPLOYMENT
        }
        
        return mapping.get(phase, TaskType.IMPLEMENTATION)
    
    def _map_step_to_task_type(self, step: str) -> TaskType:
        """Map step name to task type."""
        
        mapping = {
            "implement": TaskType.IMPLEMENTATION,
            "test": TaskType.TESTING,
            "review": TaskType.TESTING,  # Code review is validation
            "deploy": TaskType.DEPLOYMENT,
            "document": TaskType.DOCUMENTATION
        }
        
        return mapping.get(step, TaskType.IMPLEMENTATION)
    
    def _generate_task_id(self, task_description: str) -> str:
        """Generate a unique task ID from description."""
        
        # Clean and normalize the description
        clean_desc = re.sub(r'[^a-zA-Z0-9\s]', '', task_description.lower())
        words = clean_desc.split()[:4]  # Take first 4 words
        
        # Create ID
        base_id = '_'.join(words)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        return f"task_{base_id}_{timestamp}"
    
    def get_generation_statistics(self) -> Dict[str, Any]:
        """Get statistics about task generation history."""
        
        if not self.generation_history:
            return {"total_generations": 0}
        
        # Analyze generation patterns
        total_generations = len(self.generation_history)
        
        complexity_counts = defaultdict(int)
        domain_counts = defaultdict(int)
        subtask_counts = []
        
        for record in self.generation_history:
            complexity_counts[record["complexity"]] += 1
            domain_counts[record["domain"]] += 1
            subtask_counts.append(record["subtask_count"])
        
        avg_subtasks = sum(subtask_counts) / len(subtask_counts) if subtask_counts else 0
        
        return {
            "total_generations": total_generations,
            "complexity_distribution": dict(complexity_counts),
            "domain_distribution": dict(domain_counts),
            "average_subtasks_per_generation": avg_subtasks,
            "max_subtasks_generated": max(subtask_counts) if subtask_counts else 0,
            "min_subtasks_generated": min(subtask_counts) if subtask_counts else 0
        }