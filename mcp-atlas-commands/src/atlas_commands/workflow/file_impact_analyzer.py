"""
File Impact Analyzer for Task Complexity and Dependencies

Analyzes which files a task will likely impact and uses this for:
1. More accurate complexity estimation (more files = more complex)
2. Better dependency detection (tasks touching same files are related)
3. Learning from predicted vs actual file modifications
"""

import os
import re
from typing import List, Dict, Set, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import json
from datetime import datetime


class FileOperation(Enum):
    """Types of file operations"""
    READ = "read"          # Just needs to read/analyze
    MODIFY = "modify"      # Will change the file
    CREATE = "create"      # Will create new file
    DELETE = "delete"      # Will remove file
    REFACTOR = "refactor"  # Major restructuring


class FileImpactConfidence(Enum):
    """Confidence in file impact prediction"""
    CERTAIN = "certain"        # Explicitly mentioned in task
    LIKELY = "likely"          # Pattern suggests this file
    POSSIBLE = "possible"      # Might be affected
    UNLIKELY = "unlikely"      # Probably not affected


@dataclass
class FileImpact:
    """Predicted impact on a specific file"""
    file_path: str
    operation: FileOperation
    confidence: FileImpactConfidence
    reasoning: str
    related_patterns: List[str]  # Patterns that suggested this file


@dataclass
class TaskFileAnalysis:
    """Complete file impact analysis for a task"""
    task_id: str
    predicted_files: List[FileImpact]
    estimated_complexity: float
    file_based_dependencies: Dict[str, List[str]]  # task_id -> shared files
    confidence_score: float
    analysis_timestamp: datetime


@dataclass
class FileImpactFeedback:
    """Feedback on actual vs predicted file impact"""
    task_id: str
    predicted_files: Set[str]
    actual_files: Set[str]
    prediction_accuracy: float
    missed_files: Set[str]
    extra_files: Set[str]
    patterns_learned: List[str]


class FileImpactAnalyzer:
    """Analyzes and predicts file impacts for tasks"""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.file_index = self._build_file_index()
        self.historical_impacts: List[FileImpactFeedback] = []
        self.pattern_accuracy: Dict[str, float] = {}
        self._load_historical_data()
    
    def _build_file_index(self) -> Dict[str, List[str]]:
        """Build index of files by various categories"""
        index = {
            "by_extension": {},
            "by_directory": {},
            "by_name_pattern": {},
            "by_import": {}  # Files that import each other
        }
        
        for file_path in self.project_root.rglob("*"):
            if file_path.is_file() and not any(part.startswith('.') for part in file_path.parts):
                rel_path = str(file_path.relative_to(self.project_root))
                
                # By extension
                ext = file_path.suffix
                if ext not in index["by_extension"]:
                    index["by_extension"][ext] = []
                index["by_extension"][ext].append(rel_path)
                
                # By directory
                dir_path = str(file_path.parent.relative_to(self.project_root))
                if dir_path not in index["by_directory"]:
                    index["by_directory"][dir_path] = []
                index["by_directory"][dir_path].append(rel_path)
                
                # By name pattern
                name_parts = file_path.stem.split('_')
                for part in name_parts:
                    if len(part) > 3:  # Skip short parts
                        if part not in index["by_name_pattern"]:
                            index["by_name_pattern"][part] = []
                        index["by_name_pattern"][part].append(rel_path)
        
        return index
    
    def analyze_task_impact(self, 
                           task_name: str,
                           task_description: str,
                           domain: str,
                           existing_tasks: Optional[List[Dict[str, Any]]] = None) -> TaskFileAnalysis:
        """
        Analyze which files a task will likely impact.
        
        Args:
            task_name: Name of the task
            task_description: Full task description
            domain: Task domain (refactoring, feature, bugfix, etc.)
            existing_tasks: Other tasks to check for dependencies
            
        Returns:
            Complete file impact analysis
        """
        # Extract file references from task description
        explicit_files = self._extract_explicit_files(task_name, task_description)
        
        # Predict additional files based on patterns
        pattern_files = self._predict_files_from_patterns(task_name, task_description, domain)
        
        # Predict files based on domain and keywords
        domain_files = self._predict_files_from_domain(domain, task_description)
        
        # Combine all predictions
        all_impacts = self._combine_predictions(explicit_files, pattern_files, domain_files)
        
        # Calculate complexity based on file impacts
        complexity = self._calculate_file_based_complexity(all_impacts)
        
        # Find dependencies with other tasks
        dependencies = {}
        if existing_tasks:
            dependencies = self._find_file_based_dependencies(all_impacts, existing_tasks)
        
        # Calculate overall confidence
        confidence = self._calculate_confidence(all_impacts)
        
        return TaskFileAnalysis(
            task_id=self._generate_task_id(task_name),
            predicted_files=all_impacts,
            estimated_complexity=complexity,
            file_based_dependencies=dependencies,
            confidence_score=confidence,
            analysis_timestamp=datetime.now()
        )
    
    def _extract_explicit_files(self, task_name: str, description: str) -> List[FileImpact]:
        """Extract explicitly mentioned files from task description"""
        impacts = []
        text = f"{task_name} {description}".lower()
        
        # Look for file paths
        file_patterns = [
            r'`([^`]+\.[a-z]+)`',  # Backtick quoted files
            r'"([^"]+\.[a-z]+)"',   # Double quoted files
            r'\'([^\']+\.[a-z]+)\'', # Single quoted files
            r'\b(\w+/\w+\.[a-z]+)\b', # Path-like patterns
            r'\b(\w+\.[a-z]+)\b'    # Simple filenames
        ]
        
        found_files = set()
        for pattern in file_patterns:
            matches = re.findall(pattern, text)
            found_files.update(matches)
        
        # Check which files actually exist
        for file_ref in found_files:
            matching_files = self._find_matching_files(file_ref)
            for file_path in matching_files:
                # Determine operation type
                operation = self._determine_operation(text, file_ref)
                
                impacts.append(FileImpact(
                    file_path=file_path,
                    operation=operation,
                    confidence=FileImpactConfidence.CERTAIN,
                    reasoning=f"Explicitly mentioned: '{file_ref}'",
                    related_patterns=[file_ref]
                ))
        
        return impacts
    
    def _predict_files_from_patterns(self, task_name: str, description: str, domain: str) -> List[FileImpact]:
        """Predict files based on learned patterns"""
        impacts = []
        text = f"{task_name} {description}".lower()
        
        # Common patterns that suggest file modifications
        patterns = {
            "controller": {
                "keywords": ["controller", "endpoint", "route", "api"],
                "likely_files": ["**/controllers/*.py", "**/routes/*.py", "**/api/*.py"],
                "operation": FileOperation.MODIFY
            },
            "model": {
                "keywords": ["model", "schema", "database", "entity"],
                "likely_files": ["**/models/*.py", "**/schemas/*.py", "**/entities/*.py"],
                "operation": FileOperation.MODIFY
            },
            "test": {
                "keywords": ["test", "spec", "unit test", "integration test"],
                "likely_files": ["**/test_*.py", "**/*_test.py", "**/tests/*.py"],
                "operation": FileOperation.CREATE if "new" in text or "add" in text else FileOperation.MODIFY
            },
            "config": {
                "keywords": ["config", "configuration", "settings", "environment"],
                "likely_files": ["**/*.json", "**/*.yaml", "**/*.env", "**/config.py"],
                "operation": FileOperation.MODIFY
            },
            "frontend": {
                "keywords": ["ui", "component", "view", "template", "style"],
                "likely_files": ["**/*.jsx", "**/*.tsx", "**/*.vue", "**/*.css"],
                "operation": FileOperation.MODIFY
            },
            "documentation": {
                "keywords": ["docs", "documentation", "readme", "api docs"],
                "likely_files": ["**/*.md", "**/docs/*.rst", "README.md"],
                "operation": FileOperation.MODIFY
            }
        }
        
        # Check which patterns match
        for pattern_name, pattern_config in patterns.items():
            if any(keyword in text for keyword in pattern_config["keywords"]):
                # Find files matching the pattern
                for file_pattern in pattern_config["likely_files"]:
                    matching_files = self._find_files_by_pattern(file_pattern)
                    
                    # Use historical accuracy to adjust confidence
                    pattern_key = f"{pattern_name}_{domain}"
                    historical_accuracy = self.pattern_accuracy.get(pattern_key, 0.5)
                    
                    if historical_accuracy > 0.7:
                        confidence = FileImpactConfidence.LIKELY
                    elif historical_accuracy > 0.4:
                        confidence = FileImpactConfidence.POSSIBLE
                    else:
                        confidence = FileImpactConfidence.UNLIKELY
                    
                    for file_path in matching_files[:5]:  # Limit to top 5 matches
                        impacts.append(FileImpact(
                            file_path=file_path,
                            operation=pattern_config["operation"],
                            confidence=confidence,
                            reasoning=f"Pattern '{pattern_name}' suggests this file (accuracy: {historical_accuracy:.2f})",
                            related_patterns=pattern_config["keywords"]
                        ))
        
        return impacts
    
    def _predict_files_from_domain(self, domain: str, description: str) -> List[FileImpact]:
        """Predict files based on task domain"""
        impacts = []
        
        domain_patterns = {
            "refactoring": {
                "focus": ["high complexity files", "duplicated code", "large files"],
                "operation": FileOperation.REFACTOR
            },
            "bugfix": {
                "focus": ["recent changes", "error logs", "test failures"],
                "operation": FileOperation.MODIFY
            },
            "feature": {
                "focus": ["related features", "integration points", "new files"],
                "operation": FileOperation.CREATE
            },
            "optimization": {
                "focus": ["performance bottlenecks", "large operations", "queries"],
                "operation": FileOperation.MODIFY
            },
            "testing": {
                "focus": ["untested code", "low coverage", "critical paths"],
                "operation": FileOperation.CREATE
            }
        }
        
        if domain in domain_patterns:
            pattern = domain_patterns[domain]
            
            # Find files based on domain focus
            if "high complexity" in pattern["focus"]:
                # In real implementation, would analyze cyclomatic complexity
                # For now, use file size as proxy
                large_files = self._find_large_files()
                for file_path in large_files[:3]:
                    impacts.append(FileImpact(
                        file_path=file_path,
                        operation=pattern["operation"],
                        confidence=FileImpactConfidence.POSSIBLE,
                        reasoning=f"Domain '{domain}' typically affects large/complex files",
                        related_patterns=[domain]
                    ))
        
        return impacts
    
    def _combine_predictions(self, 
                            explicit: List[FileImpact],
                            pattern: List[FileImpact],
                            domain: List[FileImpact]) -> List[FileImpact]:
        """Combine predictions from different sources, avoiding duplicates"""
        # Use dict to track best prediction for each file
        file_impacts: Dict[str, FileImpact] = {}
        
        # Priority: explicit > pattern > domain
        for impact in explicit + pattern + domain:
            if impact.file_path not in file_impacts:
                file_impacts[impact.file_path] = impact
            else:
                # Keep higher confidence prediction
                current = file_impacts[impact.file_path]
                if self._confidence_priority(impact.confidence) > self._confidence_priority(current.confidence):
                    file_impacts[impact.file_path] = impact
        
        return list(file_impacts.values())
    
    def _confidence_priority(self, confidence: FileImpactConfidence) -> int:
        """Get priority value for confidence level"""
        priorities = {
            FileImpactConfidence.CERTAIN: 4,
            FileImpactConfidence.LIKELY: 3,
            FileImpactConfidence.POSSIBLE: 2,
            FileImpactConfidence.UNLIKELY: 1
        }
        return priorities.get(confidence, 0)
    
    def _calculate_file_based_complexity(self, impacts: List[FileImpact]) -> float:
        """Calculate task complexity based on file impacts"""
        base_complexity = len(impacts) * 2.0  # Base 2 hours per file
        
        # Adjust for operation types
        operation_multipliers = {
            FileOperation.READ: 0.5,
            FileOperation.MODIFY: 1.0,
            FileOperation.CREATE: 1.5,
            FileOperation.DELETE: 0.3,
            FileOperation.REFACTOR: 2.0
        }
        
        total_multiplier = 0
        for impact in impacts:
            multiplier = operation_multipliers.get(impact.operation, 1.0)
            
            # Adjust for confidence
            if impact.confidence == FileImpactConfidence.CERTAIN:
                multiplier *= 1.0
            elif impact.confidence == FileImpactConfidence.LIKELY:
                multiplier *= 0.8
            elif impact.confidence == FileImpactConfidence.POSSIBLE:
                multiplier *= 0.5
            else:
                multiplier *= 0.3
            
            total_multiplier += multiplier
        
        # Calculate final complexity
        complexity = base_complexity * (total_multiplier / len(impacts) if impacts else 1.0)
        
        # Add complexity for cross-cutting concerns
        unique_dirs = set(Path(impact.file_path).parent for impact in impacts)
        if len(unique_dirs) > 3:
            complexity *= 1.2  # Multiple directories = more complex
        
        return round(complexity, 1)
    
    def _find_file_based_dependencies(self, 
                                     impacts: List[FileImpact],
                                     existing_tasks: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """Find dependencies based on shared file impacts"""
        dependencies = {}
        my_files = {impact.file_path for impact in impacts}
        
        for task in existing_tasks:
            task_id = task.get("task_id", "")
            # Get task's predicted files if available
            task_files = set()
            
            if "predicted_files" in task:
                task_files = {f for f in task["predicted_files"]}
            elif "file_impacts" in task:
                task_files = {impact["file_path"] for impact in task["file_impacts"]}
            
            # Find shared files
            shared_files = my_files & task_files
            if shared_files:
                dependencies[task_id] = list(shared_files)
        
        return dependencies
    
    def record_actual_impact(self, 
                            task_id: str,
                            predicted_analysis: TaskFileAnalysis,
                            actual_files_modified: List[str]) -> FileImpactFeedback:
        """
        Record actual file modifications and learn from prediction accuracy.
        
        Args:
            task_id: Task identifier
            predicted_analysis: Original prediction
            actual_files_modified: Files that were actually modified
            
        Returns:
            Feedback on prediction accuracy
        """
        predicted_set = {impact.file_path for impact in predicted_analysis.predicted_files}
        actual_set = set(actual_files_modified)
        
        # Calculate accuracy
        if not predicted_set and not actual_set:
            accuracy = 1.0
        elif not predicted_set or not actual_set:
            accuracy = 0.0
        else:
            intersection = predicted_set & actual_set
            union = predicted_set | actual_set
            accuracy = len(intersection) / len(union) if union else 0.0
        
        # Find missed and extra predictions
        missed = actual_set - predicted_set
        extra = predicted_set - actual_set
        
        # Learn patterns from misses
        patterns_learned = []
        if missed:
            # Analyze what patterns we missed
            for missed_file in missed:
                # Check what patterns could have predicted this
                for impact in predicted_analysis.predicted_files:
                    if any(pattern in missed_file for pattern in impact.related_patterns):
                        patterns_learned.append(f"Pattern '{pattern}' should include {missed_file}")
        
        feedback = FileImpactFeedback(
            task_id=task_id,
            predicted_files=predicted_set,
            actual_files=actual_set,
            prediction_accuracy=accuracy,
            missed_files=missed,
            extra_files=extra,
            patterns_learned=patterns_learned
        )
        
        # Update historical data
        self.historical_impacts.append(feedback)
        self._update_pattern_accuracy(predicted_analysis, feedback)
        self._save_historical_data()
        
        return feedback
    
    def _update_pattern_accuracy(self, analysis: TaskFileAnalysis, feedback: FileImpactFeedback):
        """Update accuracy scores for patterns based on feedback"""
        # Group impacts by pattern
        pattern_results = {}
        
        for impact in analysis.predicted_files:
            for pattern in impact.related_patterns:
                if pattern not in pattern_results:
                    pattern_results[pattern] = {"correct": 0, "total": 0}
                
                pattern_results[pattern]["total"] += 1
                if impact.file_path in feedback.actual_files:
                    pattern_results[pattern]["correct"] += 1
        
        # Update accuracy scores with weighted average
        for pattern, results in pattern_results.items():
            if results["total"] > 0:
                new_accuracy = results["correct"] / results["total"]
                
                if pattern in self.pattern_accuracy:
                    # Weighted update (80% old, 20% new)
                    self.pattern_accuracy[pattern] = (
                        self.pattern_accuracy[pattern] * 0.8 + new_accuracy * 0.2
                    )
                else:
                    self.pattern_accuracy[pattern] = new_accuracy
    
    def get_complexity_adjustment_factor(self, predicted_files: int, actual_files: int) -> float:
        """
        Calculate complexity adjustment based on file prediction accuracy.
        
        Returns multiplier for future estimates.
        """
        if predicted_files == 0:
            return 1.5 if actual_files > 0 else 1.0
        
        ratio = actual_files / predicted_files
        
        # Bound the adjustment factor
        return max(0.5, min(2.0, ratio))
    
    def _find_matching_files(self, file_ref: str) -> List[str]:
        """Find actual files matching a file reference"""
        matches = []
        
        # Direct path match
        full_path = self.project_root / file_ref
        if full_path.exists():
            matches.append(str(full_path.relative_to(self.project_root)))
        
        # Search by filename
        filename = Path(file_ref).name
        for ext_files in self.file_index["by_extension"].values():
            for file_path in ext_files:
                if Path(file_path).name == filename:
                    matches.append(file_path)
        
        return matches
    
    def _find_files_by_pattern(self, pattern: str) -> List[str]:
        """Find files matching a glob pattern"""
        matches = []
        try:
            for path in self.project_root.glob(pattern):
                if path.is_file():
                    matches.append(str(path.relative_to(self.project_root)))
        except:
            pass
        return matches
    
    def _find_large_files(self, min_lines: int = 500) -> List[str]:
        """Find files with many lines (proxy for complexity)"""
        large_files = []
        
        for ext in [".py", ".js", ".ts", ".java"]:
            if ext in self.file_index["by_extension"]:
                for file_path in self.file_index["by_extension"][ext]:
                    try:
                        full_path = self.project_root / file_path
                        with open(full_path, 'r') as f:
                            line_count = sum(1 for _ in f)
                        if line_count > min_lines:
                            large_files.append(file_path)
                    except:
                        pass
        
        return sorted(large_files, key=lambda f: -len(f))[:10]  # Top 10 largest
    
    def _determine_operation(self, text: str, file_ref: str) -> FileOperation:
        """Determine the likely operation on a file based on context"""
        text_lower = text.lower()
        
        # Check for operation keywords
        if any(word in text_lower for word in ["create", "add new", "generate"]):
            return FileOperation.CREATE
        elif any(word in text_lower for word in ["delete", "remove", "clean up"]):
            return FileOperation.DELETE
        elif any(word in text_lower for word in ["refactor", "restructure", "reorganize"]):
            return FileOperation.REFACTOR
        elif any(word in text_lower for word in ["read", "analyze", "check", "review"]):
            return FileOperation.READ
        else:
            return FileOperation.MODIFY
    
    def _calculate_confidence(self, impacts: List[FileImpact]) -> float:
        """Calculate overall confidence score"""
        if not impacts:
            return 0.0
        
        confidence_scores = {
            FileImpactConfidence.CERTAIN: 1.0,
            FileImpactConfidence.LIKELY: 0.75,
            FileImpactConfidence.POSSIBLE: 0.5,
            FileImpactConfidence.UNLIKELY: 0.25
        }
        
        total_score = sum(confidence_scores.get(impact.confidence, 0) for impact in impacts)
        return total_score / len(impacts)
    
    def _generate_task_id(self, task_name: str) -> str:
        """Generate a task ID from task name"""
        return task_name.lower().replace(' ', '_').replace('-', '_')
    
    def _save_historical_data(self):
        """Save historical impact data to file"""
        data = {
            "pattern_accuracy": self.pattern_accuracy,
            "historical_impacts": [
                {
                    "task_id": feedback.task_id,
                    "predicted_files": list(feedback.predicted_files),
                    "actual_files": list(feedback.actual_files),
                    "prediction_accuracy": feedback.prediction_accuracy,
                    "missed_files": list(feedback.missed_files),
                    "extra_files": list(feedback.extra_files),
                    "patterns_learned": feedback.patterns_learned
                }
                for feedback in self.historical_impacts[-100:]  # Keep last 100
            ]
        }
        
        history_file = self.project_root / ".atlas" / "file_impact_history.json"
        history_file.parent.mkdir(exist_ok=True)
        
        with open(history_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _load_historical_data(self):
        """Load historical impact data from file"""
        history_file = self.project_root / ".atlas" / "file_impact_history.json"
        
        if history_file.exists():
            try:
                with open(history_file, 'r') as f:
                    data = json.load(f)
                
                self.pattern_accuracy = data.get("pattern_accuracy", {})
                
                # Reconstruct feedback objects
                for impact_data in data.get("historical_impacts", []):
                    feedback = FileImpactFeedback(
                        task_id=impact_data["task_id"],
                        predicted_files=set(impact_data["predicted_files"]),
                        actual_files=set(impact_data["actual_files"]),
                        prediction_accuracy=impact_data["prediction_accuracy"],
                        missed_files=set(impact_data["missed_files"]),
                        extra_files=set(impact_data["extra_files"]),
                        patterns_learned=impact_data["patterns_learned"]
                    )
                    self.historical_impacts.append(feedback)
            except Exception as e:
                print(f"Could not load historical data: {e}")
    
    def get_learning_insights(self) -> Dict[str, Any]:
        """Get insights about prediction accuracy and patterns"""
        if not self.historical_impacts:
            return {"status": "no_data"}
        
        total_predictions = len(self.historical_impacts)
        avg_accuracy = sum(f.prediction_accuracy for f in self.historical_impacts) / total_predictions
        
        # Find most commonly missed file patterns
        all_missed = []
        for feedback in self.historical_impacts:
            all_missed.extend(feedback.missed_files)
        
        missed_patterns = {}
        for file_path in all_missed:
            dir_name = str(Path(file_path).parent)
            missed_patterns[dir_name] = missed_patterns.get(dir_name, 0) + 1
        
        # Find most accurate patterns
        accurate_patterns = sorted(
            self.pattern_accuracy.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        return {
            "total_predictions": total_predictions,
            "average_accuracy": avg_accuracy,
            "most_missed_directories": sorted(
                missed_patterns.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5],
            "most_accurate_patterns": accurate_patterns,
            "recommendation": self._generate_recommendation(avg_accuracy)
        }
    
    def _generate_recommendation(self, avg_accuracy: float) -> str:
        """Generate recommendation based on accuracy"""
        if avg_accuracy > 0.8:
            return "File predictions are highly accurate. Continue using for estimation."
        elif avg_accuracy > 0.6:
            return "File predictions are reasonably accurate. Consider domain-specific improvements."
        elif avg_accuracy > 0.4:
            return "File predictions need improvement. Analyze missed patterns."
        else:
            return "File predictions are poor. Need more historical data or pattern refinement."