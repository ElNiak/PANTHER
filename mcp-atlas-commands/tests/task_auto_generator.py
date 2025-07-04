"""
Hierarchical Task Auto-Generation Module

Analyzes task complexity and automatically generates subtask/subsubtask structures
with intelligent decomposition based on task characteristics.
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import re
from .validator import ValidationLevel

# Import file impact analyzer if available
try:
    from .file_impact_analyzer import FileImpactAnalyzer, TaskFileAnalysis
    FILE_ANALYZER_AVAILABLE = True
except ImportError:
    FILE_ANALYZER_AVAILABLE = False
    TaskFileAnalysis = None


class TaskComplexity(Enum):
    """Task complexity levels for auto-decomposition"""
    SIMPLE = "simple"        # < 4 hours, single action
    MODERATE = "moderate"    # 4-16 hours, 2-4 subtasks
    COMPLEX = "complex"      # 16-40 hours, 4-8 subtasks
    EPIC = "epic"           # > 40 hours, 8+ subtasks with subsubtasks


@dataclass
class TaskDecomposition:
    """Represents a decomposed task structure"""
    subtasks: List[Dict[str, Any]]
    estimated_hours: float
    complexity: TaskComplexity
    suggested_dependencies: List[Dict[str, str]]
    rationale: str


class TaskAutoGenerator:
    """Generates hierarchical task structures based on complexity analysis"""
    
    # Keywords that suggest complexity
    COMPLEXITY_INDICATORS = {
        "implement": 2,
        "refactor": 3,
        "migrate": 4,
        "integrate": 3,
        "optimize": 3,
        "redesign": 4,
        "architect": 4,
        "framework": 3,
        "system": 3,
        "multiple": 2,
        "comprehensive": 3,
        "full": 2,
        "complete": 2,
        "all": 2,
        "entire": 3,
        "transform": 4,
        "overhaul": 4
    }
    
    # Domain patterns for task decomposition
    DOMAIN_PATTERNS = {
        "testing": ["unit tests", "integration tests", "e2e tests", "test documentation"],
        "refactoring": ["identify patterns", "extract components", "update dependencies", "verify behavior"],
        "feature": ["design", "implement core", "add tests", "integrate", "document"],
        "bugfix": ["reproduce", "diagnose", "implement fix", "add regression test"],
        "optimization": ["profile current", "identify bottlenecks", "implement improvements", "benchmark results"],
        "documentation": ["analyze current", "plan structure", "write content", "review and polish"],
        "migration": ["analyze current state", "plan migration", "implement changes", "validate results", "cleanup old code"],
        "integration": ["analyze APIs", "design integration", "implement connectors", "add error handling", "test end-to-end"]
    }
    
    def __init__(self, project_root: Optional[str] = None):
        """Initialize task auto-generator with optional file analyzer"""
        self.file_analyzer = None
        if FILE_ANALYZER_AVAILABLE and project_root:
            try:
                self.file_analyzer = FileImpactAnalyzer(project_root)
            except:
                pass
    
    def analyze_complexity(self, task_description: str, domain: str = None, task_name: str = None) -> Tuple[TaskComplexity, float]:
        """
        Analyze task description to determine complexity and estimate hours.
        
        Args:
            task_description: The task description to analyze
            domain: Optional domain hint for better analysis
            task_name: Optional task name for file-based analysis
            
        Returns:
            Tuple of (complexity level, estimated hours)
        """
        # First try file-based analysis if available
        if self.file_analyzer and task_name:
            try:
                file_analysis = self.file_analyzer.analyze_task_impact(
                    task_name=task_name,
                    task_description=task_description,
                    domain=domain or "general"
                )
                
                # Use file-based complexity if confident
                if file_analysis.confidence_score > 0.6:
                    file_hours = file_analysis.estimated_complexity
                    
                    # Map to complexity levels
                    if file_hours < 4:
                        return TaskComplexity.SIMPLE, file_hours
                    elif file_hours < 16:
                        return TaskComplexity.MODERATE, file_hours
                    elif file_hours < 40:
                        return TaskComplexity.COMPLEX, file_hours
                    else:
                        return TaskComplexity.EPIC, file_hours
            except:
                pass
        
        # Fallback to keyword-based analysis
        # Calculate complexity score based on keywords
        complexity_score = 0
        description_lower = task_description.lower()
        
        for keyword, weight in self.COMPLEXITY_INDICATORS.items():
            if keyword in description_lower:
                complexity_score += weight
        
        # Check for multiple systems/components mentioned
        component_indicators = ["service", "module", "component", "system", "layer", "api", "database"]
        component_count = sum(1 for indicator in component_indicators if indicator in description_lower)
        complexity_score += component_count * 2
        
        # Determine complexity level and base hours
        if complexity_score < 5:
            complexity = TaskComplexity.SIMPLE
            base_hours = 2
        elif complexity_score < 10:
            complexity = TaskComplexity.MODERATE
            base_hours = 8
        elif complexity_score < 20:
            complexity = TaskComplexity.COMPLEX
            base_hours = 24
        else:
            complexity = TaskComplexity.EPIC
            base_hours = 48
        
        # Adjust based on domain if provided
        if domain:
            if domain in ["architecture", "migration", "integration"]:
                base_hours *= 1.5
            elif domain in ["documentation", "testing"]:
                base_hours *= 0.8
        
        return complexity, base_hours
    
    def generate_subtasks(self, 
                         task_name: str,
                         task_description: str,
                         domain: str,
                         complexity: TaskComplexity) -> List[Dict[str, Any]]:
        """
        Generate subtasks based on task characteristics.
        
        Args:
            task_name: Name of the parent task
            task_description: Description of the parent task
            domain: Task domain for pattern matching
            complexity: Analyzed complexity level
            
        Returns:
            List of subtask definitions
        """
        subtasks = []
        
        # Get domain-specific patterns
        if domain in self.DOMAIN_PATTERNS:
            patterns = self.DOMAIN_PATTERNS[domain]
        else:
            # Generic patterns for unknown domains
            patterns = ["analyze requirements", "design solution", "implement", "test", "document"]
        
        # Adjust patterns based on complexity
        if complexity == TaskComplexity.SIMPLE:
            # Use only core patterns
            patterns = patterns[:3]
        elif complexity == TaskComplexity.EPIC:
            # Expand patterns with additional phases
            patterns = ["research and planning"] + patterns + ["deployment", "monitoring setup"]
        
        # Generate subtasks from patterns
        for i, pattern in enumerate(patterns):
            subtask = {
                "task_name": f"{pattern.replace(' ', '-')}",
                "description": f"{pattern.capitalize()} for {task_name}",
                "domain": domain,
                "priority": "high" if i < 2 else "medium",
                "estimated_hours": self._estimate_subtask_hours(complexity, i, len(patterns))
            }
            subtasks.append(subtask)
        
        return subtasks
    
    def _estimate_subtask_hours(self, complexity: TaskComplexity, index: int, total: int) -> float:
        """Estimate hours for a subtask based on parent complexity and position"""
        base_distribution = {
            TaskComplexity.SIMPLE: [1, 1, 0.5],
            TaskComplexity.MODERATE: [2, 3, 2, 1],
            TaskComplexity.COMPLEX: [4, 6, 6, 4, 2, 2],
            TaskComplexity.EPIC: [8, 12, 16, 12, 8, 4, 4, 4]
        }
        
        distribution = base_distribution.get(complexity, [2] * total)
        if index < len(distribution):
            return distribution[index]
        else:
            # For extra subtasks, use average of last two
            return sum(distribution[-2:]) / 2
    
    def suggest_dependencies(self, subtasks: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """
        Suggest dependencies between subtasks based on their names and order.
        
        Args:
            subtasks: List of subtask definitions
            
        Returns:
            List of dependency relationships
        """
        dependencies = []
        
        # Sequential dependencies for certain keywords
        sequential_keywords = ["analyze", "design", "implement", "test", "deploy"]
        
        for i in range(len(subtasks) - 1):
            current = subtasks[i]
            next_task = subtasks[i + 1]
            
            # Check if tasks should be sequential
            current_has_keyword = any(kw in current["task_name"] for kw in sequential_keywords)
            next_has_keyword = any(kw in next_task["task_name"] for kw in sequential_keywords)
            
            if current_has_keyword and next_has_keyword:
                # Find which keywords they have
                current_kw = next(kw for kw in sequential_keywords if kw in current["task_name"])
                next_kw = next(kw for kw in sequential_keywords if kw in next_task["task_name"])
                
                # If next keyword comes after current in our list, create dependency
                if sequential_keywords.index(next_kw) > sequential_keywords.index(current_kw):
                    dependencies.append({
                        "from_task": current["task_name"],
                        "to_task": next_task["task_name"],
                        "type": "blocks",
                        "description": f"{current_kw.capitalize()} must complete before {next_kw}"
                    })
        
        # Parallel work for similar tasks
        test_tasks = [st for st in subtasks if "test" in st["task_name"]]
        if len(test_tasks) > 1:
            for i in range(len(test_tasks) - 1):
                dependencies.append({
                    "from_task": test_tasks[i]["task_name"],
                    "to_task": test_tasks[i + 1]["task_name"],
                    "type": "related",
                    "description": "Testing tasks can be done in parallel"
                })
        
        return dependencies
    
    def decompose_task(self, 
                       task_name: str,
                       task_description: str,
                       domain: str,
                       parent_id: Optional[str] = None) -> TaskDecomposition:
        """
        Main method to decompose a task into subtasks with full analysis.
        
        Args:
            task_name: Name of the task to decompose
            task_description: Full description of the task
            domain: Task domain
            parent_id: Optional parent task ID for subsubtask generation
            
        Returns:
            Complete task decomposition with subtasks and metadata
        """
        # Validate inputs
        if not task_name or len(task_name) < 3 or len(task_name) > 100:
            raise ValueError("task_name must be between 3 and 100 characters")
        if not task_description or len(task_description) < 10 or len(task_description) > 1000:
            raise ValueError("task_description must be between 10 and 1000 characters")
        if not domain or len(domain) < 2 or len(domain) > 50:
            raise ValueError("domain must be between 2 and 50 characters")
        
        # Analyze complexity
        complexity, estimated_hours = self.analyze_complexity(task_description, domain, task_name)
        
        # Generate subtasks
        subtasks = self.generate_subtasks(task_name, task_description, domain, complexity)
        
        # Add parent_task_id to all subtasks if provided
        if parent_id:
            for subtask in subtasks:
                subtask["parent_task_id"] = parent_id
        
        # Suggest dependencies
        dependencies = self.suggest_dependencies(subtasks)
        
        # Generate rationale
        rationale = self._generate_rationale(task_name, complexity, len(subtasks))
        
        return TaskDecomposition(
            subtasks=subtasks,
            estimated_hours=estimated_hours,
            complexity=complexity,
            suggested_dependencies=dependencies,
            rationale=rationale
        )
    
    def _generate_rationale(self, task_name: str, complexity: TaskComplexity, subtask_count: int) -> str:
        """Generate explanation for the decomposition"""
        return (
            f"Task '{task_name}' has been classified as {complexity.value} complexity. "
            f"Generated {subtask_count} subtasks based on domain patterns and complexity analysis. "
            f"Dependencies have been suggested to ensure logical task flow and enable parallel work where possible."
        )
    
    def should_create_subsubtasks(self, subtask: Dict[str, Any], parent_complexity: TaskComplexity) -> bool:
        """
        Determine if a subtask should be further decomposed into subsubtasks.
        
        Args:
            subtask: The subtask to evaluate
            parent_complexity: Complexity of the parent task
            
        Returns:
            True if subsubtasks should be created
        """
        # Only create subsubtasks for complex/epic parent tasks
        if parent_complexity not in [TaskComplexity.COMPLEX, TaskComplexity.EPIC]:
            return False
        
        # Check if subtask is complex enough
        subtask_hours = subtask.get("estimated_hours", 0)
        if subtask_hours < 8:
            return False
        
        # Check for keywords suggesting further decomposition
        decompose_keywords = ["multiple", "all", "comprehensive", "full", "complete", "various"]
        description_lower = subtask.get("description", "").lower()
        
        return any(keyword in description_lower for keyword in decompose_keywords)