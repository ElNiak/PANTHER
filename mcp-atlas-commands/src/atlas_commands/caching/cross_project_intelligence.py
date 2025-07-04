"""
Cross-Project Intelligence System
Phase 3 implementation of ATLAS Hierarchical Cache Architecture
Discovers patterns, shares solutions, and optimizes across multiple projects
"""

import json
import time
import statistics
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict, Counter
import threading
import hashlib

from .hierarchical_cache_manager import HierarchicalCacheManager
from .content_hash_validator import ContentHashValidator
from .language_aware_cache import LanguageAwareSymbolCache, LanguageType
from .performance_analytics import CachePerformanceDashboard


@dataclass
class CodePattern:
    """Represents a code pattern discovered across projects"""
    pattern_id: str
    pattern_type: str  # 'function', 'class', 'import', 'error_handling'
    pattern_name: str
    pattern_signature: str
    language: LanguageType
    frequency: int
    projects: List[str]
    files: List[str]
    confidence_score: float  # 0-1
    first_seen: float
    last_seen: float
    example_usage: str = ""


@dataclass
class ErrorSolution:
    """Represents a solution to a common error"""
    error_id: str
    error_pattern: str
    error_type: str  # 'syntax', 'runtime', 'logic', 'performance'
    language: LanguageType
    solution_steps: List[str]
    code_examples: List[str]
    projects_affected: List[str]
    success_rate: float  # 0-1
    created_at: float
    updated_at: float
    usage_count: int = 0


@dataclass
class PerformanceBaseline:
    """Performance baseline data for cross-project comparison"""
    baseline_id: str
    project_id: str
    language: LanguageType
    operation_type: str  # 'cache_hit', 'symbol_analysis', 'file_parse'
    average_time_ms: float
    median_time_ms: float
    p95_time_ms: float
    sample_count: int
    cache_hit_rate: float
    measured_at: float
    environment_info: Dict[str, Any]


@dataclass
class CachePreloadSuggestion:
    """Suggestion for cache preloading based on patterns"""
    suggestion_id: str
    target_project: str
    cache_type: str
    cache_keys: List[str]
    priority: str  # 'high', 'medium', 'low'
    confidence: float  # 0-1
    estimated_benefit: str
    pattern_source: str  # Which pattern triggered this suggestion
    created_at: float


class CrossProjectPatternDiscovery:
    """Discovers common patterns across multiple projects"""
    
    def __init__(self, cache_manager: HierarchicalCacheManager,
                 symbol_cache: LanguageAwareSymbolCache):
        self.cache_manager = cache_manager
        self.symbol_cache = symbol_cache
        self.patterns_cache_type = "cross_project_patterns"
        self.global_patterns: Dict[str, CodePattern] = {}
        self._lock = threading.Lock()
    
    def analyze_project_patterns(self, project_id: str, file_paths: List[str]) -> Dict[str, Any]:
        """Analyze patterns in a specific project"""
        project_patterns = {
            "function_patterns": {},
            "import_patterns": {},
            "class_patterns": {},
            "error_patterns": {}
        }
        
        for file_path in file_paths:
            symbol_map = self.symbol_cache.analyze_file(file_path)
            if not symbol_map:
                continue
            
            # Analyze function patterns
            for symbol in symbol_map.symbols:
                if symbol.symbol_type == "function":
                    pattern_key = self._generate_function_pattern_key(symbol)
                    if pattern_key not in project_patterns["function_patterns"]:
                        project_patterns["function_patterns"][pattern_key] = {
                            "count": 0,
                            "files": [],
                            "signature": f"{symbol.name}({', '.join(symbol.parameters)})"
                        }
                    project_patterns["function_patterns"][pattern_key]["count"] += 1
                    project_patterns["function_patterns"][pattern_key]["files"].append(file_path)
                
                elif symbol.symbol_type == "class":
                    pattern_key = f"class_{symbol.name}_{len(symbol.parameters)}"
                    if pattern_key not in project_patterns["class_patterns"]:
                        project_patterns["class_patterns"][pattern_key] = {
                            "count": 0,
                            "files": [],
                            "signature": symbol.name
                        }
                    project_patterns["class_patterns"][pattern_key]["count"] += 1
                    project_patterns["class_patterns"][pattern_key]["files"].append(file_path)
            
            # Analyze import patterns
            for import_stmt in symbol_map.imports:
                pattern_key = f"import_{import_stmt.module}"
                if pattern_key not in project_patterns["import_patterns"]:
                    project_patterns["import_patterns"][pattern_key] = {
                        "count": 0,
                        "files": [],
                        "module": import_stmt.module
                    }
                project_patterns["import_patterns"][pattern_key]["count"] += 1
                project_patterns["import_patterns"][pattern_key]["files"].append(file_path)
        
        # Store project patterns
        cache_key = f"project_patterns_{project_id}"
        self.cache_manager.set_cache(
            self.patterns_cache_type,
            cache_key,
            project_patterns,
            cache_level="global"
        )
        
        return project_patterns
    
    def discover_cross_project_patterns(self, projects: List[str]) -> List[CodePattern]:
        """Discover patterns that appear across multiple projects"""
        all_patterns = defaultdict(lambda: {
            "projects": set(),
            "files": [],
            "count": 0,
            "signatures": set()
        })
        
        # Collect patterns from all projects
        for project_id in projects:
            cache_key = f"project_patterns_{project_id}"
            project_patterns = self.cache_manager.get_cache(
                self.patterns_cache_type, cache_key, cache_level="global"
            )
            
            if not project_patterns:
                continue
            
            # Process each pattern type
            for pattern_type, patterns in project_patterns.items():
                for pattern_key, pattern_data in patterns.items():
                    if pattern_data["count"] >= 2:  # Pattern appears multiple times
                        full_key = f"{pattern_type}_{pattern_key}"
                        all_patterns[full_key]["projects"].add(project_id)
                        all_patterns[full_key]["files"].extend(pattern_data["files"])
                        all_patterns[full_key]["count"] += pattern_data["count"]
                        all_patterns[full_key]["signatures"].add(pattern_data.get("signature", ""))
        
        # Filter for cross-project patterns
        cross_project_patterns = []
        current_time = time.time()
        
        for pattern_key, pattern_data in all_patterns.items():
            if len(pattern_data["projects"]) >= 2:  # Appears in 2+ projects
                pattern_type, pattern_name = pattern_key.split("_", 1)
                
                # Calculate confidence score
                confidence = min(1.0, (len(pattern_data["projects"]) * 0.3) + 
                               (pattern_data["count"] * 0.1))
                
                pattern = CodePattern(
                    pattern_id=self._generate_pattern_id(pattern_key),
                    pattern_type=pattern_type,
                    pattern_name=pattern_name,
                    pattern_signature=list(pattern_data["signatures"])[0],
                    language=LanguageType.UNKNOWN,  # Would need language detection
                    frequency=pattern_data["count"],
                    projects=list(pattern_data["projects"]),
                    files=pattern_data["files"],
                    confidence_score=confidence,
                    first_seen=current_time,
                    last_seen=current_time
                )
                
                cross_project_patterns.append(pattern)
        
        # Cache discovered patterns
        self._store_discovered_patterns(cross_project_patterns)
        
        return cross_project_patterns
    
    def get_patterns_for_project(self, project_id: str) -> List[CodePattern]:
        """Get patterns that might be relevant for a specific project"""
        all_patterns = self._load_discovered_patterns()
        relevant_patterns = []
        
        for pattern in all_patterns:
            if project_id not in pattern.projects:
                # Pattern from other projects might be relevant
                if pattern.confidence_score > 0.7:  # High confidence patterns
                    relevant_patterns.append(pattern)
        
        return relevant_patterns
    
    def _generate_function_pattern_key(self, symbol) -> str:
        """Generate a pattern key for a function symbol"""
        param_count = len(symbol.parameters)
        name_type = "async" if symbol.is_async else "sync"
        return f"{name_type}_func_{param_count}params"
    
    def _generate_pattern_id(self, pattern_key: str) -> str:
        """Generate unique pattern ID"""
        return hashlib.md5(pattern_key.encode()).hexdigest()[:12]
    
    def _store_discovered_patterns(self, patterns: List[CodePattern]):
        """Store discovered patterns in global cache"""
        patterns_data = [asdict(pattern) for pattern in patterns]
        self.cache_manager.set_cache(
            self.patterns_cache_type,
            "discovered_patterns",
            patterns_data,
            cache_level="global"
        )
    
    def _load_discovered_patterns(self) -> List[CodePattern]:
        """Load discovered patterns from global cache"""
        patterns_data = self.cache_manager.get_cache(
            self.patterns_cache_type,
            "discovered_patterns",
            cache_level="global"
        )
        
        if not patterns_data:
            return []
        
        patterns = []
        for data in patterns_data:
            # Convert projects back to list if it's a set
            if isinstance(data.get("projects"), set):
                data["projects"] = list(data["projects"])
            patterns.append(CodePattern(**data))
        
        return patterns


class SharedErrorSolutionsDatabase:
    """Database of error solutions shared across projects"""
    
    def __init__(self, cache_manager: HierarchicalCacheManager):
        self.cache_manager = cache_manager
        self.solutions_cache_type = "error_solutions"
        self._lock = threading.Lock()
    
    def add_error_solution(self, error_pattern: str, error_type: str,
                          language: LanguageType, solution_steps: List[str],
                          code_examples: List[str], project_id: str) -> str:
        """Add a new error solution to the database"""
        error_id = self._generate_error_id(error_pattern, language)
        
        # Check if solution already exists
        existing_solution = self.get_error_solution(error_id)
        
        if existing_solution:
            # Update existing solution
            with self._lock:
                existing_solution.solution_steps.extend(solution_steps)
                existing_solution.code_examples.extend(code_examples)
                existing_solution.projects_affected.append(project_id)
                existing_solution.updated_at = time.time()
                existing_solution.usage_count += 1
                
                self._store_solution(existing_solution)
        else:
            # Create new solution
            solution = ErrorSolution(
                error_id=error_id,
                error_pattern=error_pattern,
                error_type=error_type,
                language=language,
                solution_steps=solution_steps,
                code_examples=code_examples,
                projects_affected=[project_id],
                success_rate=1.0,  # Start with perfect score
                created_at=time.time(),
                updated_at=time.time(),
                usage_count=1
            )
            
            self._store_solution(solution)
        
        return error_id
    
    def get_error_solution(self, error_id: str) -> Optional[ErrorSolution]:
        """Get an error solution by ID"""
        solution_data = self.cache_manager.get_cache(
            self.solutions_cache_type,
            error_id,
            cache_level="global"
        )
        
        if solution_data:
            return ErrorSolution(**solution_data)
        return None
    
    def search_solutions(self, error_pattern: str, language: LanguageType = None) -> List[ErrorSolution]:
        """Search for solutions matching an error pattern"""
        # This would implement fuzzy matching against stored error patterns
        # For now, return exact matches
        error_id = self._generate_error_id(error_pattern, language or LanguageType.UNKNOWN)
        solution = self.get_error_solution(error_id)
        return [solution] if solution else []
    
    def get_popular_solutions(self, limit: int = 10) -> List[ErrorSolution]:
        """Get the most popular error solutions"""
        # This would require indexing all solutions by usage count
        # For now, return empty list as placeholder
        return []
    
    def update_solution_success_rate(self, error_id: str, success: bool):
        """Update the success rate of a solution based on feedback"""
        solution = self.get_error_solution(error_id)
        if solution:
            with self._lock:
                # Simple success rate calculation
                total_uses = solution.usage_count
                current_successes = solution.success_rate * total_uses
                
                if success:
                    current_successes += 1
                
                solution.success_rate = current_successes / (total_uses + 1)
                solution.usage_count += 1
                solution.updated_at = time.time()
                
                self._store_solution(solution)
    
    def _generate_error_id(self, error_pattern: str, language: LanguageType) -> str:
        """Generate unique error ID"""
        combined = f"{error_pattern}_{language.value}"
        return hashlib.md5(combined.encode()).hexdigest()[:12]
    
    def _store_solution(self, solution: ErrorSolution):
        """Store error solution in global cache"""
        self.cache_manager.set_cache(
            self.solutions_cache_type,
            solution.error_id,
            asdict(solution),
            cache_level="global"
        )


class PerformanceBaselineManager:
    """Manages performance baselines across projects"""
    
    def __init__(self, cache_manager: HierarchicalCacheManager,
                 performance_dashboard: CachePerformanceDashboard):
        self.cache_manager = cache_manager
        self.performance_dashboard = performance_dashboard
        self.baselines_cache_type = "performance_baselines"
    
    def create_baseline(self, project_id: str, language: LanguageType,
                       operation_type: str) -> PerformanceBaseline:
        """Create performance baseline for a project"""
        # Get recent performance metrics
        metrics = self.performance_dashboard.performance_tracker.calculate_metrics(
            time.time() - 86400,  # Last 24 hours
            time.time()
        )
        
        # Calculate detailed statistics
        recent_ops = self.performance_dashboard.performance_tracker.get_recent_operations(1440)  # 24 hours
        response_times = [op.duration_ms for op in recent_ops if op.operation_type in ['hit', 'miss']]
        
        if response_times:
            median_time = statistics.median(response_times)
            p95_time = statistics.quantiles(response_times, n=20)[18] if len(response_times) > 20 else max(response_times)
        else:
            median_time = 0
            p95_time = 0
        
        baseline = PerformanceBaseline(
            baseline_id=self._generate_baseline_id(project_id, language, operation_type),
            project_id=project_id,
            language=language,
            operation_type=operation_type,
            average_time_ms=metrics.average_response_time_ms,
            median_time_ms=median_time,
            p95_time_ms=p95_time,
            sample_count=metrics.total_operations,
            cache_hit_rate=metrics.hit_rate_percent,
            measured_at=time.time(),
            environment_info={
                "cache_size_mb": metrics.total_cache_size_mb,
                "efficiency_score": metrics.cache_efficiency_score
            }
        )
        
        # Store baseline
        self.cache_manager.set_cache(
            self.baselines_cache_type,
            baseline.baseline_id,
            asdict(baseline),
            cache_level="global"
        )
        
        return baseline
    
    def compare_with_baselines(self, project_id: str, language: LanguageType) -> Dict[str, Any]:
        """Compare current project performance with baselines from other projects"""
        current_baseline = self.create_baseline(project_id, language, "cache_operations")
        
        # Get baselines from other projects
        similar_baselines = self._get_similar_baselines(language, exclude_project=project_id)
        
        if not similar_baselines:
            return {"message": "No similar baselines found for comparison"}
        
        # Calculate comparisons
        comparisons = []
        for baseline in similar_baselines:
            comparison = {
                "project": baseline.project_id,
                "performance_ratio": current_baseline.average_time_ms / max(baseline.average_time_ms, 1),
                "hit_rate_diff": current_baseline.cache_hit_rate - baseline.cache_hit_rate,
                "efficiency_diff": (current_baseline.environment_info.get("efficiency_score", 0) - 
                                  baseline.environment_info.get("efficiency_score", 0))
            }
            comparisons.append(comparison)
        
        # Generate insights
        avg_performance_ratio = statistics.mean([c["performance_ratio"] for c in comparisons])
        insights = []
        
        if avg_performance_ratio > 1.2:
            insights.append("Performance is 20% slower than similar projects")
        elif avg_performance_ratio < 0.8:
            insights.append("Performance is 20% faster than similar projects")
        
        avg_hit_rate_diff = statistics.mean([c["hit_rate_diff"] for c in comparisons])
        if avg_hit_rate_diff < -10:
            insights.append("Cache hit rate is significantly lower than similar projects")
        elif avg_hit_rate_diff > 10:
            insights.append("Cache hit rate is significantly higher than similar projects")
        
        return {
            "current_baseline": asdict(current_baseline),
            "comparisons": comparisons,
            "insights": insights,
            "recommendations": self._generate_performance_recommendations(comparisons)
        }
    
    def _get_similar_baselines(self, language: LanguageType, 
                              exclude_project: str = None) -> List[PerformanceBaseline]:
        """Get baselines for similar projects (same language)"""
        # This would require indexing baselines by language
        # For now, return empty list as placeholder
        return []
    
    def _generate_baseline_id(self, project_id: str, language: LanguageType, operation_type: str) -> str:
        """Generate unique baseline ID"""
        combined = f"{project_id}_{language.value}_{operation_type}"
        return hashlib.md5(combined.encode()).hexdigest()[:12]
    
    def _generate_performance_recommendations(self, comparisons: List[Dict]) -> List[str]:
        """Generate performance recommendations based on comparisons"""
        recommendations = []
        
        slow_ratios = [c["performance_ratio"] for c in comparisons if c["performance_ratio"] > 1.1]
        if len(slow_ratios) > len(comparisons) / 2:
            recommendations.append("Consider optimizing cache lookup algorithms")
            recommendations.append("Review cache data structures for efficiency")
        
        low_hit_rates = [c["hit_rate_diff"] for c in comparisons if c["hit_rate_diff"] < -5]
        if len(low_hit_rates) > len(comparisons) / 2:
            recommendations.append("Implement more aggressive caching strategies")
            recommendations.append("Analyze cache invalidation patterns")
        
        return recommendations


class IntelligentCachePreloader:
    """Intelligently preloads cache based on cross-project patterns"""
    
    def __init__(self, cache_manager: HierarchicalCacheManager,
                 pattern_discovery: CrossProjectPatternDiscovery):
        self.cache_manager = cache_manager
        self.pattern_discovery = pattern_discovery
        self.suggestions_cache_type = "preload_suggestions"
    
    def generate_preload_suggestions(self, project_id: str) -> List[CachePreloadSuggestion]:
        """Generate cache preload suggestions for a project"""
        suggestions = []
        
        # Get patterns from other projects
        relevant_patterns = self.pattern_discovery.get_patterns_for_project(project_id)
        
        for pattern in relevant_patterns:
            if pattern.confidence_score > 0.6:  # High confidence patterns only
                suggestion = CachePreloadSuggestion(
                    suggestion_id=self._generate_suggestion_id(project_id, pattern.pattern_id),
                    target_project=project_id,
                    cache_type="symbols",
                    cache_keys=[f"pattern_{pattern.pattern_name}"],
                    priority="high" if pattern.confidence_score > 0.8 else "medium",
                    confidence=pattern.confidence_score,
                    estimated_benefit=f"Potential {int(pattern.frequency * 0.1)}ms improvement",
                    pattern_source=pattern.pattern_id,
                    created_at=time.time()
                )
                suggestions.append(suggestion)
        
        # Store suggestions
        self._store_suggestions(project_id, suggestions)
        
        return suggestions
    
    def execute_preload_suggestions(self, project_id: str, 
                                  suggestion_ids: List[str] = None) -> Dict[str, Any]:
        """Execute cache preload suggestions"""
        suggestions = self._load_suggestions(project_id)
        
        if suggestion_ids:
            suggestions = [s for s in suggestions if s.suggestion_id in suggestion_ids]
        
        results = {
            "preloaded_items": 0,
            "skipped_items": 0,
            "errors": []
        }
        
        for suggestion in suggestions:
            try:
                # Preload cache entries based on suggestion
                for cache_key in suggestion.cache_keys:
                    # This would implement actual preloading logic
                    # For now, just record the attempt
                    results["preloaded_items"] += 1
                    
            except Exception as e:
                results["errors"].append(f"Failed to preload {suggestion.suggestion_id}: {str(e)}")
                results["skipped_items"] += 1
        
        return results
    
    def _generate_suggestion_id(self, project_id: str, pattern_id: str) -> str:
        """Generate unique suggestion ID"""
        combined = f"{project_id}_{pattern_id}_{int(time.time())}"
        return hashlib.md5(combined.encode()).hexdigest()[:12]
    
    def _store_suggestions(self, project_id: str, suggestions: List[CachePreloadSuggestion]):
        """Store preload suggestions"""
        suggestions_data = [asdict(s) for s in suggestions]
        cache_key = f"suggestions_{project_id}"
        self.cache_manager.set_cache(
            self.suggestions_cache_type,
            cache_key,
            suggestions_data,
            cache_level="global"
        )
    
    def _load_suggestions(self, project_id: str) -> List[CachePreloadSuggestion]:
        """Load preload suggestions for a project"""
        cache_key = f"suggestions_{project_id}"
        suggestions_data = self.cache_manager.get_cache(
            self.suggestions_cache_type,
            cache_key,
            cache_level="global"
        )
        
        if not suggestions_data:
            return []
        
        return [CachePreloadSuggestion(**data) for data in suggestions_data]


class CrossProjectIntelligenceOrchestrator:
    """Orchestrates all cross-project intelligence features"""
    
    def __init__(self, cache_manager: HierarchicalCacheManager,
                 content_validator: ContentHashValidator,
                 symbol_cache: LanguageAwareSymbolCache,
                 performance_dashboard: CachePerformanceDashboard):
        
        self.cache_manager = cache_manager
        self.content_validator = content_validator
        self.symbol_cache = symbol_cache
        self.performance_dashboard = performance_dashboard
        
        # Initialize sub-components
        self.pattern_discovery = CrossProjectPatternDiscovery(cache_manager, symbol_cache)
        self.error_solutions = SharedErrorSolutionsDatabase(cache_manager)
        self.baseline_manager = PerformanceBaselineManager(cache_manager, performance_dashboard)
        self.cache_preloader = IntelligentCachePreloader(cache_manager, self.pattern_discovery)
        
        # Initialize global optimization (lazy loading to avoid circular imports)
        self.global_optimizer = None
    
    def analyze_project_for_cross_insights(self, project_id: str, 
                                         file_paths: List[str]) -> Dict[str, Any]:
        """Comprehensive cross-project analysis for a project"""
        
        # Discover patterns
        project_patterns = self.pattern_discovery.analyze_project_patterns(project_id, file_paths)
        
        # Get relevant patterns from other projects
        relevant_patterns = self.pattern_discovery.get_patterns_for_project(project_id)
        
        # Generate performance baseline
        baseline = self.baseline_manager.create_baseline(
            project_id, LanguageType.PYTHON, "cache_operations"
        )
        
        # Get performance comparison
        performance_comparison = self.baseline_manager.compare_with_baselines(
            project_id, LanguageType.PYTHON
        )
        
        # Generate preload suggestions
        preload_suggestions = self.cache_preloader.generate_preload_suggestions(project_id)
        
        return {
            "project_id": project_id,
            "analysis_timestamp": datetime.now().isoformat(),
            "discovered_patterns": {
                "project_specific": project_patterns,
                "cross_project_relevant": [asdict(p) for p in relevant_patterns]
            },
            "performance_analysis": {
                "baseline": asdict(baseline),
                "comparison": performance_comparison
            },
            "optimization_suggestions": {
                "cache_preload": [asdict(s) for s in preload_suggestions],
                "pattern_adoption": self._generate_pattern_adoption_suggestions(relevant_patterns)
            },
            "cross_project_insights": {
                "similar_projects": self._find_similar_projects(project_patterns),
                "knowledge_sharing_opportunities": self._identify_knowledge_sharing_opportunities(project_id)
            }
        }
    
    def get_global_optimization_report(self) -> Dict[str, Any]:
        """Generate global optimization report across all projects"""
        
        # Initialize global optimizer if needed
        if not self.global_optimizer:
            try:
                from .global_optimization import GlobalCacheOptimizer
                self.global_optimizer = GlobalCacheOptimizer(self)
            except ImportError:
                pass
        
        base_report = {
            "report_type": "global_optimization",
            "generated_at": datetime.now().isoformat(),
            "cross_project_patterns": {
                "total_patterns_discovered": len(self.pattern_discovery._load_discovered_patterns()),
                "high_confidence_patterns": len([p for p in self.pattern_discovery._load_discovered_patterns() 
                                               if p.confidence_score > 0.8])
            },
            "error_solutions_database": {
                "total_solutions": 0,  # Would count all stored solutions
                "most_popular_solutions": []  # Would get top solutions
            },
            "performance_insights": {
                "projects_analyzed": 0,  # Would count baselines
                "optimization_opportunities": []
            },
            "cache_optimization": {
                "global_cache_efficiency": self._calculate_global_cache_efficiency(),
                "storage_savings_mb": self._calculate_storage_savings(),
                "preload_success_rate": self._calculate_preload_success_rate()
            }
        }
        
        # Add global optimization insights if available
        if self.global_optimizer:
            try:
                optimization_analysis = self.global_optimizer.analyze_global_cache_state()
                optimization_recommendations = self.global_optimizer.get_optimization_recommendations()
                optimization_monitoring = self.global_optimizer.monitor_optimization_effectiveness()
                
                base_report["global_optimization"] = {
                    "current_state": optimization_analysis,
                    "recommendations": optimization_recommendations,
                    "effectiveness_monitoring": optimization_monitoring
                }
            except Exception as e:
                base_report["global_optimization"] = {"error": f"Failed to generate optimization insights: {str(e)}"}
        
        return base_report
    
    def _generate_pattern_adoption_suggestions(self, patterns: List[CodePattern]) -> List[Dict[str, Any]]:
        """Generate suggestions for adopting patterns from other projects"""
        suggestions = []
        
        for pattern in patterns:
            if pattern.confidence_score > 0.7:
                suggestions.append({
                    "pattern_name": pattern.pattern_name,
                    "suggestion": f"Consider adopting {pattern.pattern_signature} pattern",
                    "benefit": f"Used successfully in {len(pattern.projects)} projects",
                    "confidence": pattern.confidence_score
                })
        
        return suggestions
    
    def _find_similar_projects(self, project_patterns: Dict[str, Any]) -> List[str]:
        """Find projects with similar patterns"""
        # This would implement similarity matching
        return []
    
    def _identify_knowledge_sharing_opportunities(self, project_id: str) -> List[Dict[str, Any]]:
        """Identify opportunities for knowledge sharing"""
        return [
            {
                "opportunity": "Error solution sharing",
                "description": "Share common error solutions with similar projects"
            },
            {
                "opportunity": "Performance optimization",
                "description": "Learn from high-performing projects with similar patterns"
            }
        ]
    
    def _calculate_global_cache_efficiency(self) -> float:
        """Calculate global cache efficiency score"""
        cache_stats = self.cache_manager.get_performance_stats()
        return cache_stats.get("hit_rate_percent", 0)
    
    def _calculate_storage_savings(self) -> float:
        """Calculate storage savings from cross-project optimization"""
        cache_size_info = self.cache_manager.get_cache_size_info()
        return cache_size_info.get("global_cache_mb", 0)
    
    def _calculate_preload_success_rate(self) -> float:
        """Calculate success rate of cache preloading"""
        # This would track preload success/failure rates
        return 0.85  # Placeholder