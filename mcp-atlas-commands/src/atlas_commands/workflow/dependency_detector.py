"""
Intelligent Dependency Detection Module

Analyzes tasks to automatically detect and suggest dependencies between them
based on semantic understanding and historical patterns.
"""

from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass
from enum import Enum
import re
from datetime import datetime

# Import file impact analyzer if available
try:
    from .file_impact_analyzer import FileImpactAnalyzer
    FILE_ANALYZER_AVAILABLE = True
except ImportError:
    FILE_ANALYZER_AVAILABLE = False


class DependencyType(Enum):
    """Types of dependencies between tasks"""
    BLOCKS = "blocks"              # Must complete before
    BLOCKED_BY = "blocked_by"      # Cannot start until
    RELATED = "related"            # Can work in parallel with coordination
    PREREQUISITE = "prerequisite"  # Required knowledge/setup
    FOLLOWS = "follows"            # Natural sequence but not blocking


@dataclass
class DependencyRelation:
    """Represents a dependency between two tasks"""
    from_task_id: str
    to_task_id: str
    dependency_type: DependencyType
    confidence: float  # 0.0 to 1.0
    reasoning: str
    auto_detected: bool = True


class DependencyDetector:
    """Detects dependencies between tasks using semantic analysis"""
    
    # Keyword patterns that suggest dependencies
    DEPENDENCY_PATTERNS = {
        # Output/Input relationships
        "creates_consumes": {
            "creators": ["create", "generate", "build", "implement", "write", "design", "develop"],
            "consumers": ["use", "consume", "integrate", "test", "validate", "deploy", "verify"]
        },
        # Sequential flow
        "sequential": {
            "sequence": [
                ("analyze", "design"),
                ("design", "implement"),
                ("implement", "test"),
                ("test", "deploy"),
                ("plan", "execute"),
                ("research", "prototype"),
                ("prototype", "production")
            ]
        },
        # Prerequisite relationships
        "prerequisites": {
            "setup": ["setup", "initialize", "configure", "install"],
            "requires": ["migration", "integration", "deployment", "optimization"]
        },
        # Parallel work indicators
        "parallel": {
            "independent": ["frontend", "backend", "api", "ui", "database"],
            "similar": ["unit test", "integration test", "documentation", "review"]
        }
    }
    
    # Technical term associations
    TECHNICAL_ASSOCIATIONS = {
        "database": ["schema", "migration", "query", "model", "orm"],
        "api": ["endpoint", "rest", "graphql", "swagger", "authentication"],
        "frontend": ["ui", "component", "react", "vue", "angular", "css"],
        "backend": ["server", "service", "controller", "business logic"],
        "testing": ["test", "spec", "coverage", "assertion", "mock"],
        "deployment": ["deploy", "ci/cd", "docker", "kubernetes", "production"],
        "security": ["auth", "encryption", "validation", "sanitization", "audit"]
    }
    
    def __init__(self, project_root: Optional[str] = None):
        """Initialize dependency detector with optional file analyzer"""
        self.file_analyzer = None
        if FILE_ANALYZER_AVAILABLE and project_root:
            try:
                self.file_analyzer = FileImpactAnalyzer(project_root)
            except:
                pass
    
    def detect_dependencies(self, tasks: List[Dict[str, Any]], existing_dependencies: Optional[List[Dict]] = None) -> List[DependencyRelation]:
        """
        Detect dependencies between a list of tasks.
        
        Args:
            tasks: List of task dictionaries with at least 'task_id', 'task_name', 'description'
            existing_dependencies: Optional list of already defined dependencies to consider
            
        Returns:
            List of detected dependency relationships
        """
        dependencies = []
        existing = existing_dependencies or []
        
        # Create a map of existing dependencies to avoid duplicates
        existing_pairs = set()
        for dep in existing:
            pair = (dep.get("from_task_id", ""), dep.get("to_task_id", ""))
            existing_pairs.add(pair)
        
        # Analyze each pair of tasks
        for i, task1 in enumerate(tasks):
            for j, task2 in enumerate(tasks):
                if i >= j:  # Skip self and already processed pairs
                    continue
                
                # Skip if dependency already exists
                pair = (task1["task_id"], task2["task_id"])
                reverse_pair = (task2["task_id"], task1["task_id"])
                if pair in existing_pairs or reverse_pair in existing_pairs:
                    continue
                
                # Detect potential dependencies
                relations = self._analyze_task_pair(task1, task2)
                dependencies.extend(relations)
        
        # Post-process to resolve conflicts and optimize
        dependencies = self._optimize_dependencies(dependencies)
        
        return dependencies
    
    def _analyze_task_pair(self, task1: Dict[str, Any], task2: Dict[str, Any]) -> List[DependencyRelation]:
        """Analyze a pair of tasks for potential dependencies"""
        relations = []
        
        # Check output/input relationships
        output_input_rel = self._check_output_input_dependency(task1, task2)
        if output_input_rel:
            relations.append(output_input_rel)
        
        # Check sequential patterns
        sequential_rel = self._check_sequential_dependency(task1, task2)
        if sequential_rel:
            relations.append(sequential_rel)
        
        # Check prerequisite relationships
        prereq_rel = self._check_prerequisite_dependency(task1, task2)
        if prereq_rel:
            relations.append(prereq_rel)
        
        # Check for parallel work opportunities
        parallel_rel = self._check_parallel_relationship(task1, task2)
        if parallel_rel:
            relations.append(parallel_rel)
        
        # Check technical associations
        tech_rel = self._check_technical_associations(task1, task2)
        if tech_rel:
            relations.append(tech_rel)
        
        # Check file-based dependencies if analyzer available
        if self.file_analyzer:
            file_rel = self._check_file_based_dependency(task1, task2)
            if file_rel:
                relations.append(file_rel)
        
        return relations
    
    def _check_output_input_dependency(self, task1: Dict[str, Any], task2: Dict[str, Any]) -> Optional[DependencyRelation]:
        """Check if task1 creates something that task2 consumes"""
        task1_text = f"{task1.get('task_name', '')} {task1.get('description', '')}".lower()
        task2_text = f"{task2.get('task_name', '')} {task2.get('description', '')}".lower()
        
        patterns = self.DEPENDENCY_PATTERNS["creates_consumes"]
        
        # Check if task1 creates and task2 consumes
        task1_creates = any(creator in task1_text for creator in patterns["creators"])
        task2_consumes = any(consumer in task2_text for consumer in patterns["consumers"])
        
        if task1_creates and task2_consumes:
            # Look for shared nouns to increase confidence
            task1_nouns = set(re.findall(r'\b(?:api|service|component|module|feature|system|interface)\b', task1_text))
            task2_nouns = set(re.findall(r'\b(?:api|service|component|module|feature|system|interface)\b', task2_text))
            
            shared_nouns = task1_nouns & task2_nouns
            confidence = 0.7 if shared_nouns else 0.5
            
            return DependencyRelation(
                from_task_id=task1["task_id"],
                to_task_id=task2["task_id"],
                dependency_type=DependencyType.BLOCKS,
                confidence=confidence,
                reasoning=f"Task '{task1['task_name']}' appears to create outputs needed by '{task2['task_name']}'"
            )
        
        return None
    
    def _check_sequential_dependency(self, task1: Dict[str, Any], task2: Dict[str, Any]) -> Optional[DependencyRelation]:
        """Check if tasks follow a sequential pattern"""
        task1_name = task1.get('task_name', '').lower()
        task2_name = task2.get('task_name', '').lower()
        
        sequences = self.DEPENDENCY_PATTERNS["sequential"]["sequence"]
        
        for step1, step2 in sequences:
            if step1 in task1_name and step2 in task2_name:
                return DependencyRelation(
                    from_task_id=task1["task_id"],
                    to_task_id=task2["task_id"],
                    dependency_type=DependencyType.BLOCKS,
                    confidence=0.8,
                    reasoning=f"'{step1}' typically precedes '{step2}' in development workflow"
                )
        
        return None
    
    def _check_prerequisite_dependency(self, task1: Dict[str, Any], task2: Dict[str, Any]) -> Optional[DependencyRelation]:
        """Check if task1 is a prerequisite for task2"""
        task1_text = f"{task1.get('task_name', '')} {task1.get('description', '')}".lower()
        task2_text = f"{task2.get('task_name', '')} {task2.get('description', '')}".lower()
        
        patterns = self.DEPENDENCY_PATTERNS["prerequisites"]
        
        # Check if task1 is setup and task2 requires it
        is_setup = any(setup in task1_text for setup in patterns["setup"])
        requires_setup = any(req in task2_text for req in patterns["requires"])
        
        if is_setup and requires_setup:
            return DependencyRelation(
                from_task_id=task1["task_id"],
                to_task_id=task2["task_id"],
                dependency_type=DependencyType.PREREQUISITE,
                confidence=0.7,
                reasoning=f"Setup task '{task1['task_name']}' is prerequisite for '{task2['task_name']}'"
            )
        
        return None
    
    def _check_parallel_relationship(self, task1: Dict[str, Any], task2: Dict[str, Any]) -> Optional[DependencyRelation]:
        """Check if tasks can be done in parallel"""
        task1_text = f"{task1.get('task_name', '')} {task1.get('description', '')}".lower()
        task2_text = f"{task2.get('task_name', '')} {task2.get('description', '')}".lower()
        
        patterns = self.DEPENDENCY_PATTERNS["parallel"]
        
        # Check for independent components
        task1_components = [comp for comp in patterns["independent"] if comp in task1_text]
        task2_components = [comp for comp in patterns["independent"] if comp in task2_text]
        
        if task1_components and task2_components and task1_components != task2_components:
            return DependencyRelation(
                from_task_id=task1["task_id"],
                to_task_id=task2["task_id"],
                dependency_type=DependencyType.RELATED,
                confidence=0.6,
                reasoning=f"Tasks work on independent components ({', '.join(task1_components)} vs {', '.join(task2_components)})"
            )
        
        # Check for similar work types
        for similar_type in patterns["similar"]:
            if similar_type in task1_text and similar_type in task2_text:
                return DependencyRelation(
                    from_task_id=task1["task_id"],
                    to_task_id=task2["task_id"],
                    dependency_type=DependencyType.RELATED,
                    confidence=0.5,
                    reasoning=f"Both tasks involve {similar_type} and can be done in parallel"
                )
        
        return None
    
    def _check_technical_associations(self, task1: Dict[str, Any], task2: Dict[str, Any]) -> Optional[DependencyRelation]:
        """Check for technical domain relationships"""
        task1_text = f"{task1.get('task_name', '')} {task1.get('description', '')}".lower()
        task2_text = f"{task2.get('task_name', '')} {task2.get('description', '')}".lower()
        
        task1_domains = []
        task2_domains = []
        
        # Find technical domains in each task
        for domain, keywords in self.TECHNICAL_ASSOCIATIONS.items():
            if any(keyword in task1_text for keyword in keywords):
                task1_domains.append(domain)
            if any(keyword in task2_text for keyword in keywords):
                task2_domains.append(domain)
        
        # Check for common domains
        common_domains = set(task1_domains) & set(task2_domains)
        if common_domains:
            # Tasks in same technical domain might have dependencies
            # Check for more specific relationships
            if "testing" in common_domains and ("implement" in task1_text or "create" in task1_text):
                return DependencyRelation(
                    from_task_id=task1["task_id"],
                    to_task_id=task2["task_id"],
                    dependency_type=DependencyType.BLOCKS,
                    confidence=0.7,
                    reasoning=f"Implementation must complete before testing in {', '.join(common_domains)} domain"
                )
        
        return None
    
    def _optimize_dependencies(self, dependencies: List[DependencyRelation]) -> List[DependencyRelation]:
        """Optimize dependency list by removing redundant relationships and resolving conflicts"""
        # Group by task pairs
        task_pairs: Dict[Tuple[str, str], List[DependencyRelation]] = {}
        
        for dep in dependencies:
            pair = (dep.from_task_id, dep.to_task_id)
            if pair not in task_pairs:
                task_pairs[pair] = []
            task_pairs[pair].append(dep)
        
        # Select best dependency for each pair
        optimized = []
        for pair, deps in task_pairs.items():
            if len(deps) == 1:
                optimized.append(deps[0])
            else:
                # Select dependency with highest confidence
                best_dep = max(deps, key=lambda d: d.confidence)
                optimized.append(best_dep)
        
        # Remove transitive dependencies where possible
        optimized = self._remove_transitive_dependencies(optimized)
        
        return optimized
    
    def _remove_transitive_dependencies(self, dependencies: List[DependencyRelation]) -> List[DependencyRelation]:
        """Remove transitive dependencies (A->B->C implies A->C is redundant)"""
        # Build adjacency list for blocking dependencies only
        blocks_graph: Dict[str, Set[str]] = {}
        
        for dep in dependencies:
            if dep.dependency_type == DependencyType.BLOCKS:
                if dep.from_task_id not in blocks_graph:
                    blocks_graph[dep.from_task_id] = set()
                blocks_graph[dep.from_task_id].add(dep.to_task_id)
        
        # Find transitive relationships
        transitive_pairs = set()
        for start in blocks_graph:
            # Find all reachable nodes from start
            visited = set()
            stack = [start]
            
            while stack:
                current = stack.pop()
                if current in visited:
                    continue
                visited.add(current)
                
                if current in blocks_graph:
                    for next_node in blocks_graph[current]:
                        if next_node not in visited:
                            stack.append(next_node)
                            # If we can reach next_node from start through intermediate nodes
                            if current != start:
                                transitive_pairs.add((start, next_node))
        
        # Filter out transitive dependencies
        filtered = []
        for dep in dependencies:
            if dep.dependency_type == DependencyType.BLOCKS:
                pair = (dep.from_task_id, dep.to_task_id)
                if pair not in transitive_pairs:
                    filtered.append(dep)
            else:
                # Keep all non-blocking dependencies
                filtered.append(dep)
        
        return filtered
    
    def explain_dependencies(self, dependencies: List[DependencyRelation]) -> Dict[str, Any]:
        """Generate human-readable explanation of detected dependencies"""
        summary = {
            "total_dependencies": len(dependencies),
            "by_type": {},
            "high_confidence": [],
            "suggested_critical_path": []
        }
        
        # Count by type
        for dep in dependencies:
            dep_type = dep.dependency_type.value
            if dep_type not in summary["by_type"]:
                summary["by_type"][dep_type] = 0
            summary["by_type"][dep_type] += 1
            
            # Track high confidence dependencies
            if dep.confidence >= 0.7:
                summary["high_confidence"].append({
                    "from": dep.from_task_id,
                    "to": dep.to_task_id,
                    "type": dep_type,
                    "reason": dep.reasoning
                })
        
        # Suggest critical path (simplified - just blocking deps with high confidence)
        blocking_deps = [d for d in dependencies if d.dependency_type == DependencyType.BLOCKS and d.confidence >= 0.7]
        if blocking_deps:
            # Build a simple critical path
            task_order = []
            added = set()
            
            # Find tasks with no dependencies
            all_to_tasks = {d.to_task_id for d in blocking_deps}
            all_from_tasks = {d.from_task_id for d in blocking_deps}
            start_tasks = all_from_tasks - all_to_tasks
            
            # Simple topological sort
            for start in start_tasks:
                if start not in added:
                    task_order.append(start)
                    added.add(start)
            
            # Add remaining tasks
            for dep in blocking_deps:
                if dep.from_task_id not in added:
                    task_order.append(dep.from_task_id)
                    added.add(dep.from_task_id)
                if dep.to_task_id not in added:
                    task_order.append(dep.to_task_id)
                    added.add(dep.to_task_id)
            
            summary["suggested_critical_path"] = task_order
        
        return summary
    
    def _check_file_based_dependency(self, task1: Dict[str, Any], task2: Dict[str, Any]) -> Optional[DependencyRelation]:
        """Check for dependencies based on predicted file impacts"""
        if not self.file_analyzer:
            return None
        
        try:
            # Analyze file impacts for both tasks
            task1_analysis = self.file_analyzer.analyze_task_impact(
                task_name=task1.get('task_name', ''),
                task_description=task1.get('description', ''),
                domain=task1.get('domain', 'general')
            )
            
            task2_analysis = self.file_analyzer.analyze_task_impact(
                task_name=task2.get('task_name', ''),
                task_description=task2.get('description', ''),
                domain=task2.get('domain', 'general')
            )
            
            # Get file sets
            task1_files = {impact.file_path for impact in task1_analysis.predicted_files}
            task2_files = {impact.file_path for impact in task2_analysis.predicted_files}
            
            # Check for shared files
            shared_files = task1_files & task2_files
            
            if not shared_files:
                return None
            
            # Determine dependency type based on operations
            task1_creates = any(
                impact.operation.value in ["create", "refactor"] 
                for impact in task1_analysis.predicted_files
                if impact.file_path in shared_files
            )
            
            task2_modifies = any(
                impact.operation.value in ["modify", "refactor"]
                for impact in task2_analysis.predicted_files
                if impact.file_path in shared_files
            )
            
            # Calculate confidence based on file impact confidence
            avg_confidence = (task1_analysis.confidence_score + task2_analysis.confidence_score) / 2
            
            # Determine dependency type
            if task1_creates and task2_modifies:
                # Task1 creates files that task2 modifies - blocking dependency
                return DependencyRelation(
                    from_task_id=task1["task_id"],
                    to_task_id=task2["task_id"],
                    dependency_type=DependencyType.BLOCKS,
                    confidence=avg_confidence * 0.9,  # High confidence for file-based
                    reasoning=f"Tasks share {len(shared_files)} files, task1 creates what task2 modifies"
                )
            elif shared_files and len(shared_files) > 2:
                # Many shared files suggest coordination needed
                return DependencyRelation(
                    from_task_id=task1["task_id"],
                    to_task_id=task2["task_id"],
                    dependency_type=DependencyType.RELATED,
                    confidence=avg_confidence * 0.7,
                    reasoning=f"Tasks work on {len(shared_files)} common files, coordination recommended"
                )
            elif shared_files:
                # Few shared files, possible relationship
                return DependencyRelation(
                    from_task_id=task1["task_id"],
                    to_task_id=task2["task_id"],
                    dependency_type=DependencyType.RELATED,
                    confidence=avg_confidence * 0.5,
                    reasoning=f"Tasks share {len(shared_files)} files: {list(shared_files)[:2]}"
                )
            
        except Exception as e:
            # Silent fail - file analysis is supplementary
            pass
        
        return None