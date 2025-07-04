"""
Historical Pattern Estimator Module

Analyzes historical task completion data to provide intelligent time estimates
for new tasks based on similar past work.
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import statistics
import re
from enum import Enum


class EstimationConfidence(Enum):
    """Confidence levels for estimates"""
    HIGH = "high"          # Based on many similar tasks
    MEDIUM = "medium"      # Based on some similar tasks
    LOW = "low"           # Based on few or loosely similar tasks
    GUESS = "guess"       # No historical data, using heuristics


@dataclass 
class TaskEstimate:
    """Represents a time estimate for a task"""
    estimated_hours: float
    confidence: EstimationConfidence
    min_hours: float
    max_hours: float
    based_on_tasks: List[str]  # IDs of similar historical tasks
    reasoning: str


@dataclass
class HistoricalTaskData:
    """Historical task data for pattern matching"""
    task_id: str
    task_name: str
    description: str
    domain: str
    estimated_hours: float
    actual_hours: float
    completion_date: datetime
    complexity_score: float
    team_size: int = 1


class HistoricalEstimator:
    """Estimates task duration based on historical patterns"""
    
    def __init__(self, project_root: Optional[str] = None):
        # In a real implementation, this would load from persistent storage
        self.historical_data: List[HistoricalTaskData] = []
        self.domain_multipliers: Dict[str, float] = {}
        self.complexity_patterns: Dict[str, float] = {}
        self.file_prediction_accuracy: Dict[str, float] = {}  # domain -> accuracy
        self._load_default_patterns()
        
        # Initialize file analyzer if available
        self.file_analyzer = None
        try:
            from .file_impact_analyzer import FileImpactAnalyzer
            if project_root:
                self.file_analyzer = FileImpactAnalyzer(project_root)
        except ImportError:
            pass
    
    def _load_default_patterns(self):
        """Load default estimation patterns"""
        # Domain multipliers based on typical complexity
        self.domain_multipliers = {
            "architecture": 1.5,
            "migration": 1.4,
            "integration": 1.3,
            "refactoring": 1.2,
            "feature": 1.0,
            "bugfix": 0.8,
            "testing": 0.9,
            "documentation": 0.7,
            "optimization": 1.1,
            "security": 1.3,
            "deployment": 0.9
        }
        
        # Complexity indicators and their impact
        self.complexity_patterns = {
            "simple": 0.5,
            "basic": 0.6,
            "standard": 1.0,
            "complex": 1.5,
            "advanced": 2.0,
            "critical": 1.3,
            "urgent": 0.8,  # Urgent tasks often get more resources
            "experimental": 1.6,
            "research": 2.0,
            "prototype": 1.2
        }
    
    def add_historical_data(self, task_data: HistoricalTaskData):
        """Add completed task data to historical record"""
        self.historical_data.append(task_data)
        # Update domain multipliers based on actual vs estimated
        if task_data.domain in self.domain_multipliers and task_data.estimated_hours > 0:
            actual_ratio = task_data.actual_hours / task_data.estimated_hours
            # Weighted update to avoid outliers having too much impact
            current = self.domain_multipliers[task_data.domain]
            self.domain_multipliers[task_data.domain] = (current * 0.8) + (actual_ratio * 0.2)
    
    def estimate_task(self, 
                     task_name: str,
                     description: str,
                     domain: str,
                     parent_estimated: Optional[float] = None) -> TaskEstimate:
        """
        Estimate task duration based on historical patterns.
        
        Args:
            task_name: Name of the task
            description: Task description
            domain: Task domain
            parent_estimated: Optional parent task estimate for proportion-based estimation
            
        Returns:
            TaskEstimate with duration and confidence
        """
        # Find similar historical tasks
        similar_tasks = self._find_similar_tasks(task_name, description, domain)
        
        if similar_tasks:
            # Calculate estimate based on similar tasks
            estimate = self._calculate_from_similar(similar_tasks, task_name, description, domain)
        else:
            # Use heuristic estimation
            estimate = self._heuristic_estimate(task_name, description, domain, parent_estimated)
        
        return estimate
    
    def _find_similar_tasks(self, task_name: str, description: str, domain: str) -> List[Tuple[HistoricalTaskData, float]]:
        """Find similar tasks in historical data with similarity scores"""
        similar = []
        
        task_tokens = self._tokenize(f"{task_name} {description}".lower())
        
        for historical in self.historical_data:
            # Skip if different domain (unless domains are related)
            if historical.domain != domain and not self._domains_related(historical.domain, domain):
                continue
            
            # Calculate similarity score
            hist_tokens = self._tokenize(f"{historical.task_name} {historical.description}".lower())
            similarity = self._calculate_similarity(task_tokens, hist_tokens)
            
            # Consider domain match
            if historical.domain == domain:
                similarity *= 1.2  # Boost same domain
            
            # Only include if similarity is significant
            if similarity > 0.3:
                similar.append((historical, similarity))
        
        # Sort by similarity and return top matches
        similar.sort(key=lambda x: x[1], reverse=True)
        return similar[:10]  # Top 10 most similar
    
    def _tokenize(self, text: str) -> Set[str]:
        """Tokenize text for similarity comparison"""
        # Remove common words and split
        stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by"}
        words = re.findall(r'\b\w+\b', text.lower())
        return {word for word in words if word not in stop_words and len(word) > 2}
    
    def _calculate_similarity(self, tokens1: Set[str], tokens2: Set[str]) -> float:
        """Calculate Jaccard similarity between token sets"""
        if not tokens1 or not tokens2:
            return 0.0
        
        intersection = len(tokens1 & tokens2)
        union = len(tokens1 | tokens2)
        
        return intersection / union if union > 0 else 0.0
    
    def _domains_related(self, domain1: str, domain2: str) -> bool:
        """Check if two domains are related"""
        related_groups = [
            {"frontend", "ui", "component", "design"},
            {"backend", "api", "service", "server"},
            {"testing", "test", "qa", "validation"},
            {"deployment", "devops", "infrastructure", "ci/cd"},
            {"database", "data", "migration", "schema"}
        ]
        
        for group in related_groups:
            if domain1 in group and domain2 in group:
                return True
        
        return False
    
    def _calculate_from_similar(self, similar_tasks: List[Tuple[HistoricalTaskData, float]], 
                               task_name: str, description: str, domain: str) -> TaskEstimate:
        """Calculate estimate from similar historical tasks"""
        if not similar_tasks:
            return self._heuristic_estimate(task_name, description, domain, None)
        
        # Weight actual hours by similarity
        weighted_hours = []
        weights = []
        task_ids = []
        
        for task, similarity in similar_tasks:
            weighted_hours.append(task.actual_hours * similarity)
            weights.append(similarity)
            task_ids.append(task.task_id)
        
        # Calculate weighted average
        if sum(weights) > 0:
            estimated_hours = sum(weighted_hours) / sum(weights)
        else:
            estimated_hours = statistics.mean([t[0].actual_hours for t in similar_tasks])
        
        # Apply domain multiplier
        domain_mult = self.domain_multipliers.get(domain, 1.0)
        estimated_hours *= domain_mult
        
        # Apply complexity adjustments
        complexity_mult = self._get_complexity_multiplier(task_name, description)
        estimated_hours *= complexity_mult
        
        # Calculate confidence based on number and similarity of matches
        avg_similarity = statistics.mean([s for _, s in similar_tasks])
        if len(similar_tasks) >= 5 and avg_similarity > 0.6:
            confidence = EstimationConfidence.HIGH
        elif len(similar_tasks) >= 3 and avg_similarity > 0.4:
            confidence = EstimationConfidence.MEDIUM
        else:
            confidence = EstimationConfidence.LOW
        
        # Calculate min/max based on historical variance
        if len(similar_tasks) > 1:
            actual_hours = [t[0].actual_hours for t in similar_tasks]
            std_dev = statistics.stdev(actual_hours)
            min_hours = max(1, estimated_hours - std_dev)
            max_hours = estimated_hours + std_dev
        else:
            min_hours = estimated_hours * 0.7
            max_hours = estimated_hours * 1.5
        
        reasoning = (
            f"Based on {len(similar_tasks)} similar historical tasks "
            f"with average similarity of {avg_similarity:.2f}. "
            f"Applied domain multiplier of {domain_mult:.2f} for '{domain}'."
        )
        
        return TaskEstimate(
            estimated_hours=round(estimated_hours, 1),
            confidence=confidence,
            min_hours=round(min_hours, 1),
            max_hours=round(max_hours, 1),
            based_on_tasks=task_ids[:5],  # Top 5 most similar
            reasoning=reasoning
        )
    
    def _heuristic_estimate(self, task_name: str, description: str, domain: str, 
                           parent_estimated: Optional[float]) -> TaskEstimate:
        """Estimate using heuristics when no historical data available"""
        base_hours = 4.0  # Default base
        
        # Adjust based on task name keywords
        task_lower = task_name.lower()
        if any(word in task_lower for word in ["simple", "basic", "minor", "small"]):
            base_hours = 2.0
        elif any(word in task_lower for word in ["complex", "major", "comprehensive", "full"]):
            base_hours = 8.0
        elif any(word in task_lower for word in ["epic", "large", "system", "architecture"]):
            base_hours = 16.0
        
        # Apply domain multiplier
        domain_mult = self.domain_multipliers.get(domain, 1.0)
        estimated_hours = base_hours * domain_mult
        
        # Apply complexity multiplier
        complexity_mult = self._get_complexity_multiplier(task_name, description)
        estimated_hours *= complexity_mult
        
        # If parent estimate provided, use it as a constraint
        if parent_estimated:
            # Subtask typically 20-40% of parent
            parent_proportion = 0.3
            parent_based = parent_estimated * parent_proportion
            # Average with heuristic estimate
            estimated_hours = (estimated_hours + parent_based) / 2
        
        # Wide range for guess
        min_hours = estimated_hours * 0.5
        max_hours = estimated_hours * 2.0
        
        reasoning = (
            f"Heuristic estimate based on task keywords and domain '{domain}'. "
            f"No similar historical tasks found. Consider this a rough approximation."
        )
        
        return TaskEstimate(
            estimated_hours=round(estimated_hours, 1),
            confidence=EstimationConfidence.GUESS,
            min_hours=round(min_hours, 1), 
            max_hours=round(max_hours, 1),
            based_on_tasks=[],
            reasoning=reasoning
        )
    
    def _get_complexity_multiplier(self, task_name: str, description: str) -> float:
        """Get complexity multiplier based on keywords"""
        text = f"{task_name} {description}".lower()
        
        multiplier = 1.0
        for pattern, mult in self.complexity_patterns.items():
            if pattern in text:
                # Use the highest multiplier found
                multiplier = max(multiplier, mult)
        
        return multiplier
    
    def get_estimation_insights(self) -> Dict[str, Any]:
        """Get insights about estimation accuracy"""
        if not self.historical_data:
            return {"status": "no_data", "insights": []}
        
        insights = {
            "total_tasks": len(self.historical_data),
            "domains": {},
            "accuracy_metrics": {},
            "recommendations": []
        }
        
        # Analyze by domain
        domain_data: Dict[str, List[float]] = {}
        for task in self.historical_data:
            if task.domain not in domain_data:
                domain_data[task.domain] = []
            if task.estimated_hours > 0:
                accuracy = task.actual_hours / task.estimated_hours
                domain_data[task.domain].append(accuracy)
        
        # Calculate domain statistics
        for domain, accuracies in domain_data.items():
            if accuracies:
                insights["domains"][domain] = {
                    "avg_accuracy": statistics.mean(accuracies),
                    "task_count": len(accuracies),
                    "overrun_rate": sum(1 for a in accuracies if a > 1.2) / len(accuracies)
                }
        
        # Overall accuracy
        all_accuracies = [a for accuracies in domain_data.values() for a in accuracies]
        if all_accuracies:
            insights["accuracy_metrics"] = {
                "mean_accuracy": statistics.mean(all_accuracies),
                "median_accuracy": statistics.median(all_accuracies),
                "std_dev": statistics.stdev(all_accuracies) if len(all_accuracies) > 1 else 0
            }
            
            # Recommendations based on patterns
            if insights["accuracy_metrics"]["mean_accuracy"] > 1.2:
                insights["recommendations"].append(
                    "Estimates tend to be too optimistic. Consider adding 20% buffer."
                )
            elif insights["accuracy_metrics"]["mean_accuracy"] < 0.8:
                insights["recommendations"].append(
                    "Estimates tend to be too pessimistic. Team may be improving efficiency."
                )
        
        return insights
    
    def learn_from_completion(self, task_id: str, actual_hours: float, task_metadata: Dict[str, Any]):
        """Update patterns based on task completion"""
        # Create historical record
        historical = HistoricalTaskData(
            task_id=task_id,
            task_name=task_metadata.get("task_name", ""),
            description=task_metadata.get("description", ""),
            domain=task_metadata.get("domain", "unknown"),
            estimated_hours=task_metadata.get("estimated_hours", 0),
            actual_hours=actual_hours,
            completion_date=datetime.now(),
            complexity_score=task_metadata.get("complexity_score", 1.0),
            team_size=task_metadata.get("team_size", 1)
        )
        
        self.add_historical_data(historical)
    
    def learn_from_file_prediction(self, 
                                  domain: str,
                                  predicted_file_count: int,
                                  actual_file_count: int,
                                  prediction_accuracy: float):
        """Update estimation patterns based on file prediction accuracy"""
        # Store file prediction accuracy by domain
        if domain not in self.file_prediction_accuracy:
            self.file_prediction_accuracy[domain] = prediction_accuracy
        else:
            # Weighted average update
            self.file_prediction_accuracy[domain] = (
                self.file_prediction_accuracy[domain] * 0.7 + prediction_accuracy * 0.3
            )
        
        # Adjust domain multiplier based on file prediction accuracy
        if actual_file_count > 0 and predicted_file_count > 0:
            file_ratio = actual_file_count / predicted_file_count
            
            # If we consistently underpredict files, increase domain multiplier
            if file_ratio > 1.2 and domain in self.domain_multipliers:
                self.domain_multipliers[domain] *= 1.05  # 5% increase
            elif file_ratio < 0.8 and domain in self.domain_multipliers:
                self.domain_multipliers[domain] *= 0.95  # 5% decrease
    
    def adjust_estimate_with_file_analysis(self,
                                          base_estimate: float,
                                          domain: str,
                                          predicted_files: int,
                                          file_confidence: float) -> float:
        """Adjust time estimate based on file analysis confidence"""
        # Get historical file prediction accuracy for this domain
        domain_accuracy = self.file_prediction_accuracy.get(domain, 0.5)
        
        # Calculate adjustment factor
        # High confidence + high historical accuracy = trust the file-based estimate more
        trust_factor = file_confidence * domain_accuracy
        
        if trust_factor > 0.7:
            # High trust - use file-based estimate heavily
            file_based_hours = predicted_files * 2.5  # Average hours per file
            return base_estimate * 0.3 + file_based_hours * 0.7
        elif trust_factor > 0.4:
            # Medium trust - blend estimates
            file_based_hours = predicted_files * 2.0
            return base_estimate * 0.6 + file_based_hours * 0.4
        else:
            # Low trust - mostly use base estimate
            return base_estimate * 0.9 + (predicted_files * 1.5) * 0.1