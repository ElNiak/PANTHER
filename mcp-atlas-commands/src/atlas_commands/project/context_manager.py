"""
Project Context Manager for ATLAS MCP Multi-Project Support

This module provides lightweight project isolation by extending the existing
ATLAS task management system with project-scoped operations while maintaining
DRY, SOLID, and KISS principles.

Key Design Decisions:
- Reuse existing TaskStorageManager, MemoryGraphManager, etc.
- Add project scoping through composition, not inheritance
- Minimal changes to existing MCP tool handlers
- Backward compatible with single-project setups
"""

import os
import hashlib
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass

# Import Phase 2 cache intelligence components
try:
    from ..caching.hierarchical_cache_manager import HierarchicalCacheManager
    from ..caching.content_hash_validator import ContentHashValidator, SmartCacheInvalidator
    from ..caching.language_aware_cache import LanguageAwareSymbolCache
    from ..caching.performance_analytics import CachePerformanceDashboard
except ImportError:
    HierarchicalCacheManager = None
    ContentHashValidator = None
    SmartCacheInvalidator = None
    LanguageAwareSymbolCache = None
    CachePerformanceDashboard = None

# Import Phase 3 cross-project intelligence components
try:
    from ..caching.cross_project_intelligence import CrossProjectIntelligenceOrchestrator
except ImportError:
    CrossProjectIntelligenceOrchestrator = None

# Import Phase 4 ML-powered components
try:
    from ..caching.ml_powered_analytics import MLPatternRecognition
    from ..caching.anomaly_detection import AnomalyDetectionOrchestrator, AnomalyDetectionConfig
    from ..caching.predictive_analytics import PredictiveAnalyticsOrchestrator
    from ..caching.self_optimizing_cache import SelfOptimizingCacheOrchestrator, AutoOptimizationConfig
except ImportError:
    MLPatternRecognition = None
    AnomalyDetectionOrchestrator = None
    AnomalyDetectionConfig = None
    PredictiveAnalyticsOrchestrator = None
    SelfOptimizingCacheOrchestrator = None
    AutoOptimizationConfig = None


@dataclass
class ProjectContext:
    """Project context information"""
    project_id: str
    project_root: Path
    cache_root: Path
    project_fingerprint: str
    workspace_isolation: bool
    created_at: str


class ProjectContextManager:
    """
    Manages project identification and scoped storage paths.
    
    Design: Composition over inheritance - wraps existing storage paths
    with project-specific prefixes while preserving all existing functionality.
    """
    
    def __init__(self):
        self.project_id = self._get_project_id()
        self.project_root = Path(os.environ.get('ATLAS_PROJECT_ROOT', '/app/workspace'))
        self.cache_root = Path(os.environ.get('ATLAS_CACHE_ROOT', '/app/cache'))
        self.workspace_isolation = os.environ.get('ATLAS_WORKSPACE_ISOLATION', 'false').lower() == 'true'
        
        self.project_fingerprint = self._generate_project_fingerprint()
        self.context = self._create_context()
        
        # Initialize Phase 2 cache intelligence components
        self.cache_manager = None
        self.content_validator = None
        self.smart_invalidator = None
        self.symbol_cache = None
        self.performance_dashboard = None
        
        # Initialize Phase 3 cross-project intelligence
        self.cross_project_intelligence = None
        
        # Initialize Phase 4 ML-powered components
        self.ml_pattern_recognition = None
        self.anomaly_detector = None
        self.predictive_analytics = None
        self.self_optimizing_cache = None
        
        if HierarchicalCacheManager:
            try:
                self.cache_manager = HierarchicalCacheManager(self.project_id)
                
                # Initialize Phase 2 intelligence components
                if ContentHashValidator:
                    self.content_validator = ContentHashValidator(self.cache_manager)
                    self.smart_invalidator = SmartCacheInvalidator(self.cache_manager)
                
                if LanguageAwareSymbolCache:
                    self.symbol_cache = LanguageAwareSymbolCache(
                        self.cache_manager, 
                        self.content_validator
                    )
                
                if CachePerformanceDashboard:
                    self.performance_dashboard = CachePerformanceDashboard(
                        self.cache_manager,
                        self.content_validator,
                        self.symbol_cache
                    )
                
                # Initialize Phase 3 cross-project intelligence
                if (CrossProjectIntelligenceOrchestrator and 
                    self.content_validator and self.symbol_cache and self.performance_dashboard):
                    self.cross_project_intelligence = CrossProjectIntelligenceOrchestrator(
                        self.cache_manager,
                        self.content_validator,
                        self.symbol_cache,
                        self.performance_dashboard
                    )
                
                # Initialize Phase 4 ML-powered components
                if (MLPatternRecognition and self.symbol_cache):
                    self.ml_pattern_recognition = MLPatternRecognition(
                        self.cache_manager,
                        self.symbol_cache
                    )
                
                if (AnomalyDetectionOrchestrator and self.symbol_cache and self.performance_dashboard):
                    anomaly_config = AnomalyDetectionConfig() if AnomalyDetectionConfig else None
                    if anomaly_config:
                        self.anomaly_detector = AnomalyDetectionOrchestrator(
                            self.cache_manager,
                            self.symbol_cache,
                            self.performance_dashboard,
                            anomaly_config
                        )
                
                if (PredictiveAnalyticsOrchestrator and self.performance_dashboard):
                    self.predictive_analytics = PredictiveAnalyticsOrchestrator(
                        self.cache_manager,
                        self.performance_dashboard
                    )
                
                if (SelfOptimizingCacheOrchestrator and self.symbol_cache and self.performance_dashboard):
                    auto_config = AutoOptimizationConfig() if AutoOptimizationConfig else None
                    if auto_config:
                        self.self_optimizing_cache = SelfOptimizingCacheOrchestrator(
                            self.cache_manager,
                            self.symbol_cache,
                            self.performance_dashboard,
                            auto_config
                        )
                    
            except Exception as e:
                print(f"Warning: Failed to initialize cache intelligence: {e}")
        
        self._ensure_project_directories()
    
    def _get_project_id(self) -> str:
        """Get project ID from environment or derive from path"""
        project_id = os.environ.get('ATLAS_PROJECT_ID')
        if project_id:
            return project_id
            
        # Fallback: derive from project root path
        project_root = os.environ.get('ATLAS_PROJECT_ROOT', '/app/workspace')
        return Path(project_root).name or 'default'
    
    def _generate_project_fingerprint(self) -> str:
        """Generate unique project fingerprint based on key files"""
        key_files = [
            'package.json', 'pyproject.toml', 'Cargo.toml', 
            'pom.xml', 'build.gradle', 'composer.json',
            'requirements.txt', 'Pipfile', 'poetry.lock',
            'go.mod', 'Gemfile', 'CMakeLists.txt'
        ]
        
        fingerprint_data = [f"project_id:{self.project_id}"]
        
        for file in key_files:
            file_path = self.project_root / file
            if file_path.exists() and file_path.is_file():
                try:
                    content_hash = hashlib.md5(file_path.read_bytes()).hexdigest()[:8]
                    fingerprint_data.append(f"{file}:{content_hash}")
                except (OSError, PermissionError):
                    # Skip files we can't read
                    continue
        
        # Include project root in fingerprint for uniqueness
        fingerprint_data.append(f"path:{str(self.project_root)}")
        
        return hashlib.md5('|'.join(fingerprint_data).encode()).hexdigest()[:16]
    
    def _create_context(self) -> ProjectContext:
        """Create comprehensive project context"""
        return ProjectContext(
            project_id=self.project_id,
            project_root=self.project_root,
            cache_root=self.cache_root,
            project_fingerprint=self.project_fingerprint,
            workspace_isolation=self.workspace_isolation,
            created_at=datetime.utcnow().isoformat()
        )
    
    def _ensure_project_directories(self):
        """Create project-specific directories if they don't exist"""
        if not self.workspace_isolation:
            return
            
        directories = [
            self.cache_root,
            self.get_project_scoped_path('tasks'),
            self.get_project_scoped_path('memory'),
            self.get_project_scoped_path('cache'),
            self.get_project_scoped_path('logs'),
            self.get_project_scoped_path('artifacts'),
            self.get_project_scoped_path('backups')
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    def get_project_scoped_path(self, resource_type: str, filename: str = None) -> Path:
        """
        Get project-scoped path for different resource types.
        
        This preserves the existing ATLAS directory structure while adding
        project isolation through path prefixes.
        """
        if self.workspace_isolation:
            # Project-isolated mode: separate directories per project
            base_path = self.cache_root / resource_type
        else:
            # Backward compatibility mode: use existing paths with project prefixes
            base_path = self.cache_root / resource_type
        
        base_path.mkdir(parents=True, exist_ok=True)
        
        if filename:
            if self.workspace_isolation or self.project_id != 'default':
                # Add project prefix to filename for isolation
                scoped_filename = f"{self.project_id}_{filename}"
            else:
                # Backward compatibility: no prefix for default project
                scoped_filename = filename
            return base_path / scoped_filename
        
        return base_path
    
    def validate_file_access(self, file_path: str) -> bool:
        """
        Validate file path is within project boundaries.
        
        Only enforced when workspace_isolation is enabled.
        """
        if not self.workspace_isolation:
            return True
            
        try:
            abs_file_path = Path(file_path).resolve()
            abs_project_root = self.project_root.resolve()
            
            # Check if file is within project root or cache
            valid_paths = [abs_project_root, self.cache_root.resolve()]
            
            for valid_path in valid_paths:
                if valid_path in abs_file_path.parents or abs_file_path == valid_path:
                    return True
                    
            return False
        except (OSError, ValueError):
            return False
    
    def scope_task_id(self, task_id: str) -> str:
        """Add project scope to task ID if not already scoped"""
        if self.project_id == 'default' and not self.workspace_isolation:
            # Backward compatibility: no scoping for default project
            return task_id
            
        if not task_id.startswith(f"{self.project_id}:"):
            return f"{self.project_id}:{task_id}"
        return task_id
    
    def scope_entity_id(self, entity_name: str) -> str:
        """Add project scope to entity ID if not already scoped"""
        if self.project_id == 'default' and not self.workspace_isolation:
            # Backward compatibility: no scoping for default project
            return entity_name
            
        if not entity_name.startswith(f"{self.project_id}:"):
            return f"{self.project_id}:{entity_name}"
        return entity_name
    
    def validate_task_belongs_to_project(self, task_id: str) -> bool:
        """Check if task belongs to current project"""
        if self.project_id == 'default' and not self.workspace_isolation:
            # Backward compatibility: all tasks belong to default project
            return True
            
        return task_id.startswith(f"{self.project_id}:")
    
    def validate_entity_belongs_to_project(self, entity_id: str) -> bool:
        """Check if entity belongs to current project"""
        if self.project_id == 'default' and not self.workspace_isolation:
            # Backward compatibility: all entities belong to default project
            return True
            
        return entity_id.startswith(f"{self.project_id}:")
    
    def get_project_context_dict(self) -> Dict[str, Any]:
        """Get project context as dictionary for storage in metadata"""
        return {
            'project_id': self.project_id,
            'project_root': str(self.project_root),
            'project_fingerprint': self.project_fingerprint,
            'workspace_isolation': self.workspace_isolation,
            'cache_root': str(self.cache_root),
            'created_at': self.context.created_at
        }
    
    def is_compatible_with_context(self, stored_context: Dict[str, Any]) -> bool:
        """Check if stored context is compatible with current project"""
        if not stored_context:
            return True  # No context stored, assume compatible
            
        stored_project_id = stored_context.get('project_id')
        stored_fingerprint = stored_context.get('project_fingerprint')
        
        # Check project ID match
        if stored_project_id and stored_project_id != self.project_id:
            return False
            
        # Check fingerprint match (if both exist)
        if stored_fingerprint and stored_fingerprint != self.project_fingerprint:
            return False
            
        return True
    
    def get_cache_path(self, cache_type: str, cache_level: str = "project") -> Path:
        """Get cache path using hierarchical cache manager if available"""
        if self.cache_manager:
            return self.cache_manager.get_cache_path(cache_type, cache_level)
        
        # Fallback to legacy path structure
        return self.get_project_scoped_path('cache') / cache_type
    
    def cache_data(self, cache_type: str, key: str, data: Any, 
                   cache_level: str = "project", content_hash: str = None) -> bool:
        """Cache data using hierarchical cache manager if available"""
        if self.cache_manager:
            return self.cache_manager.set_cache(cache_type, key, data, cache_level, content_hash)
        
        # Fallback: basic file cache
        try:
            cache_path = self.get_cache_path(cache_type, cache_level)
            cache_path.mkdir(parents=True, exist_ok=True)
            cache_file = cache_path / f"{key}.json"
            with open(cache_file, 'w') as f:
                json.dump(data, f, default=str)
            return True
        except Exception:
            return False
    
    def get_cached_data(self, cache_type: str, key: str, cache_level: str = "project") -> Optional[Any]:
        """Get cached data using hierarchical cache manager if available"""
        if self.cache_manager:
            return self.cache_manager.get_cache(cache_type, key, cache_level)
        
        # Fallback: basic file cache
        try:
            cache_path = self.get_cache_path(cache_type, cache_level)
            cache_file = cache_path / f"{key}.json"
            if cache_file.exists():
                with open(cache_file, 'r') as f:
                    return json.load(f)
            return None
        except Exception:
            return None
    
    def invalidate_cache(self, cache_type: str, key: str = None, cache_level: str = "project"):
        """Invalidate cache using hierarchical cache manager if available"""
        if self.cache_manager:
            self.cache_manager.invalidate_cache(cache_type, key, cache_level)
        else:
            # Fallback: remove cache files
            try:
                cache_path = self.get_cache_path(cache_type, cache_level)
                if key:
                    cache_file = cache_path / f"{key}.json"
                    if cache_file.exists():
                        cache_file.unlink()
                else:
                    if cache_path.exists():
                        for cache_file in cache_path.glob("*.json"):
                            cache_file.unlink()
            except Exception:
                pass
    
    def get_cache_performance_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        if self.cache_manager:
            return self.cache_manager.get_performance_stats()
        
        return {
            "project_id": self.project_id,
            "cache_manager": "legacy",
            "hit_rate_percent": 0,
            "message": "Hierarchical cache not available"
        }
    
    def optimize_cache(self):
        """Optimize cache if hierarchical cache manager is available"""
        if self.cache_manager:
            self.cache_manager.optimize_cache()
    
    # Phase 2 Intelligence Methods
    
    def analyze_file_symbols(self, file_path: str, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
        """Analyze symbols in a file using language-aware cache"""
        if not self.symbol_cache:
            return None
        
        symbol_map = self.symbol_cache.analyze_file(file_path, force_refresh)
        if symbol_map:
            # Record analytics
            if self.performance_dashboard:
                self.performance_dashboard.record_cache_operation(
                    "symbol_analysis", "symbols", "project", file_path
                )
            return {
                "file_path": symbol_map.file_path,
                "language": symbol_map.language.value,
                "symbols": [{"name": s.name, "type": s.symbol_type, "line": s.line_start} 
                           for s in symbol_map.symbols],
                "imports": [{"module": imp.module, "names": imp.imported_names} 
                           for imp in symbol_map.imports],
                "exports": symbol_map.exports
            }
        return None
    
    def find_symbol_in_file(self, file_path: str, symbol_name: str) -> Optional[Dict[str, Any]]:
        """Find a specific symbol in a file"""
        if not self.symbol_cache:
            return None
        
        symbol = self.symbol_cache.find_symbol_by_name(file_path, symbol_name)
        if symbol:
            return {
                "name": symbol.name,
                "type": symbol.symbol_type,
                "line_start": symbol.line_start,
                "line_end": symbol.line_end,
                "parameters": symbol.parameters,
                "docstring": symbol.docstring,
                "visibility": symbol.visibility
            }
        return None
    
    def track_file_dependency(self, file_path: str, cache_type: str, cache_key: str, 
                             dependency_type: str = "reference"):
        """Track a file as dependency for smart invalidation"""
        if self.smart_invalidator:
            self.smart_invalidator.track_file_dependency(
                file_path, cache_type, cache_key, dependency_type
            )
    
    def validate_file_caches(self, file_path: str) -> bool:
        """Check if file changed and invalidate dependent caches"""
        if self.smart_invalidator:
            return self.smart_invalidator.invalidate_if_changed(file_path)
        return False
    
    def validate_all_caches(self) -> Dict[str, Any]:
        """Validate all cached data against file dependencies"""
        if self.smart_invalidator:
            return self.smart_invalidator.validate_all_caches()
        return {"error": "Smart invalidation not available"}
    
    def get_cache_health_report(self) -> Dict[str, Any]:
        """Get comprehensive cache health report"""
        if self.smart_invalidator:
            return self.smart_invalidator.get_cache_health_report()
        return {"error": "Cache health monitoring not available"}
    
    def get_performance_dashboard(self, report_type: str = "comprehensive") -> Dict[str, Any]:
        """Get performance analytics dashboard report"""
        if self.performance_dashboard:
            return self.performance_dashboard.generate_report(report_type)
        return {"error": "Performance dashboard not available"}
    
    def get_real_time_cache_stats(self) -> Dict[str, Any]:
        """Get real-time cache performance statistics"""
        if self.performance_dashboard:
            return self.performance_dashboard.get_real_time_stats()
        return {"error": "Real-time stats not available"}
    
    def analyze_project_symbols(self, file_paths: List[str]) -> Dict[str, Any]:
        """Analyze symbol relationships across multiple files"""
        if not self.symbol_cache:
            return {"error": "Symbol cache not available"}
        
        return self.symbol_cache.analyze_symbol_relationships(file_paths)
    
    def get_language_distribution(self, file_paths: List[str]) -> Dict[str, int]:
        """Get programming language distribution in project"""
        if not self.symbol_cache:
            return {}
        
        return self.symbol_cache.get_language_distribution(file_paths)
    
    def save_analytics_snapshot(self) -> str:
        """Save current analytics state to disk"""
        if self.performance_dashboard:
            return self.performance_dashboard.save_analytics_snapshot()
        return ""
    
    # Phase 3 Cross-Project Intelligence Methods
    
    def analyze_cross_project_insights(self, file_paths: List[str]) -> Dict[str, Any]:
        """Analyze project for cross-project insights and patterns"""
        if not self.cross_project_intelligence:
            return {"error": "Cross-project intelligence not available"}
        
        return self.cross_project_intelligence.analyze_project_for_cross_insights(
            self.project_id, file_paths
        )
    
    def discover_project_patterns(self, file_paths: List[str]) -> Dict[str, Any]:
        """Discover patterns in the current project"""
        if not self.cross_project_intelligence:
            return {"error": "Cross-project intelligence not available"}
        
        return self.cross_project_intelligence.pattern_discovery.analyze_project_patterns(
            self.project_id, file_paths
        )
    
    def get_relevant_patterns_from_other_projects(self) -> List[Dict[str, Any]]:
        """Get patterns from other projects that might be relevant"""
        if not self.cross_project_intelligence:
            return []
        
        patterns = self.cross_project_intelligence.pattern_discovery.get_patterns_for_project(
            self.project_id
        )
        return [{"name": p.pattern_name, "confidence": p.confidence_score, 
                "projects": p.projects, "signature": p.pattern_signature} for p in patterns]
    
    def add_error_solution(self, error_pattern: str, error_type: str, language: str,
                          solution_steps: List[str], code_examples: List[str]) -> str:
        """Add an error solution to the shared database"""
        if not self.cross_project_intelligence:
            return ""
        
        from ..caching.language_aware_cache import LanguageType
        lang_type = LanguageType(language) if language in [l.value for l in LanguageType] else LanguageType.UNKNOWN
        
        return self.cross_project_intelligence.error_solutions.add_error_solution(
            error_pattern, error_type, lang_type, solution_steps, code_examples, self.project_id
        )
    
    def search_error_solutions(self, error_pattern: str, language: str = None) -> List[Dict[str, Any]]:
        """Search for solutions to an error pattern"""
        if not self.cross_project_intelligence:
            return []
        
        from ..caching.language_aware_cache import LanguageType
        lang_type = None
        if language:
            lang_type = LanguageType(language) if language in [l.value for l in LanguageType] else LanguageType.UNKNOWN
        
        solutions = self.cross_project_intelligence.error_solutions.search_solutions(
            error_pattern, lang_type
        )
        
        return [{
            "error_id": s.error_id,
            "error_pattern": s.error_pattern,
            "solution_steps": s.solution_steps,
            "code_examples": s.code_examples,
            "success_rate": s.success_rate,
            "projects_affected": s.projects_affected
        } for s in solutions]
    
    def compare_performance_with_similar_projects(self, language: str = "python") -> Dict[str, Any]:
        """Compare current project performance with similar projects"""
        if not self.cross_project_intelligence:
            return {"error": "Cross-project intelligence not available"}
        
        from ..caching.language_aware_cache import LanguageType
        lang_type = LanguageType(language) if language in [l.value for l in LanguageType] else LanguageType.PYTHON
        
        return self.cross_project_intelligence.baseline_manager.compare_with_baselines(
            self.project_id, lang_type
        )
    
    def generate_cache_preload_suggestions(self) -> List[Dict[str, Any]]:
        """Generate intelligent cache preload suggestions"""
        if not self.cross_project_intelligence:
            return []
        
        suggestions = self.cross_project_intelligence.cache_preloader.generate_preload_suggestions(
            self.project_id
        )
        
        return [{
            "suggestion_id": s.suggestion_id,
            "cache_type": s.cache_type,
            "priority": s.priority,
            "confidence": s.confidence,
            "estimated_benefit": s.estimated_benefit,
            "pattern_source": s.pattern_source
        } for s in suggestions]
    
    def execute_cache_preload_suggestions(self, suggestion_ids: List[str] = None) -> Dict[str, Any]:
        """Execute cache preload suggestions"""
        if not self.cross_project_intelligence:
            return {"error": "Cross-project intelligence not available"}
        
        return self.cross_project_intelligence.cache_preloader.execute_preload_suggestions(
            self.project_id, suggestion_ids
        )
    
    def get_global_optimization_report(self) -> Dict[str, Any]:
        """Get global optimization report across all projects"""
        if not self.cross_project_intelligence:
            return {"error": "Cross-project intelligence not available"}
        
        return self.cross_project_intelligence.get_global_optimization_report()
    
    def discover_cross_project_patterns(self, projects: List[str]) -> List[Dict[str, Any]]:
        """Discover patterns that appear across multiple projects"""
        if not self.cross_project_intelligence:
            return []
        
        patterns = self.cross_project_intelligence.pattern_discovery.discover_cross_project_patterns(
            projects
        )
        
        return [{
            "pattern_id": p.pattern_id,
            "pattern_name": p.pattern_name,
            "pattern_type": p.pattern_type,
            "frequency": p.frequency,
            "projects": p.projects,
            "confidence_score": p.confidence_score,
            "pattern_signature": p.pattern_signature
        } for p in patterns]
    
    # Global Cache Optimization Methods
    
    def analyze_global_cache_state(self) -> Dict[str, Any]:
        """Analyze global cache state for optimization opportunities"""
        if not self.cross_project_intelligence:
            return {"error": "Cross-project intelligence not available"}
        
        # Initialize global optimizer if needed
        if not hasattr(self.cross_project_intelligence, 'global_optimizer') or not self.cross_project_intelligence.global_optimizer:
            try:
                from ..caching.global_optimization import GlobalCacheOptimizer
                self.cross_project_intelligence.global_optimizer = GlobalCacheOptimizer(self.cross_project_intelligence)
            except ImportError:
                return {"error": "Global optimization not available"}
        
        return self.cross_project_intelligence.global_optimizer.analyze_global_cache_state()
    
    def get_optimization_recommendations(self) -> List[Dict[str, Any]]:
        """Get prioritized cache optimization recommendations"""
        if not self.cross_project_intelligence:
            return []
        
        # Initialize global optimizer if needed
        if not hasattr(self.cross_project_intelligence, 'global_optimizer') or not self.cross_project_intelligence.global_optimizer:
            try:
                from ..caching.global_optimization import GlobalCacheOptimizer
                self.cross_project_intelligence.global_optimizer = GlobalCacheOptimizer(self.cross_project_intelligence)
            except ImportError:
                return []
        
        return self.cross_project_intelligence.global_optimizer.get_optimization_recommendations()
    
    def apply_optimization_strategy(self, strategy_id: str) -> Dict[str, Any]:
        """Apply a specific optimization strategy"""
        if not self.cross_project_intelligence:
            return {"error": "Cross-project intelligence not available"}
        
        # Initialize global optimizer if needed
        if not hasattr(self.cross_project_intelligence, 'global_optimizer') or not self.cross_project_intelligence.global_optimizer:
            try:
                from ..caching.global_optimization import GlobalCacheOptimizer
                self.cross_project_intelligence.global_optimizer = GlobalCacheOptimizer(self.cross_project_intelligence)
            except ImportError:
                return {"error": "Global optimization not available"}
        
        try:
            result = self.cross_project_intelligence.global_optimizer.apply_optimization_strategy(strategy_id)
            return {
                "strategy_id": result.strategy_id,
                "applied_at": result.applied_at,
                "projects_affected": result.projects_affected,
                "actual_improvements": result.actual_improvements,
                "success_rate": result.success_rate,
                "notes": result.notes
            }
        except Exception as e:
            return {"error": f"Failed to apply optimization strategy: {str(e)}"}
    
    def monitor_optimization_effectiveness(self) -> Dict[str, Any]:
        """Monitor the effectiveness of applied optimizations"""
        if not self.cross_project_intelligence:
            return {"error": "Cross-project intelligence not available"}
        
        # Initialize global optimizer if needed
        if not hasattr(self.cross_project_intelligence, 'global_optimizer') or not self.cross_project_intelligence.global_optimizer:
            try:
                from ..caching.global_optimization import GlobalCacheOptimizer
                self.cross_project_intelligence.global_optimizer = GlobalCacheOptimizer(self.cross_project_intelligence)
            except ImportError:
                return {"error": "Global optimization not available"}
        
        return self.cross_project_intelligence.global_optimizer.monitor_optimization_effectiveness()


class ProjectMismatchError(Exception):
    """Raised when operation targets wrong project"""
    
    def __init__(self, message: str, expected_project: str, actual_project: str):
        super().__init__(message)
        self.expected_project = expected_project
        self.actual_project = actual_project


class ContextViolationError(Exception):
    """Raised when operation violates context safety"""
    
    def __init__(self, message: str, file_path: str = None, project_root: str = None):
        super().__init__(message)
        self.file_path = file_path
        self.project_root = project_root


class ProjectContextValidator:
    """
    Validates operations against project context.
    
    Design: Single responsibility - only validates, doesn't modify behavior.
    """
    
    def __init__(self, context_manager: ProjectContextManager):
        self.context_manager = context_manager
    
    def validate_operation(self, operation: str, data: Dict[str, Any]) -> bool:
        """
        Validate operation is safe within project context.
        
        Returns True if valid, raises exception if invalid.
        """
        try:
            self._validate_project_id(data)
            self._validate_file_paths(data)
            self._validate_task_scope(data)
            self._validate_entity_scope(data)
            return True
        except (ProjectMismatchError, ContextViolationError):
            raise
    
    def _validate_project_id(self, data: Dict[str, Any]):
        """Ensure operation targets correct project"""
        if 'project_name' in data:
            if data['project_name'] != self.context_manager.project_id:
                raise ProjectMismatchError(
                    f"Operation for project '{data['project_name']}' attempted on project '{self.context_manager.project_id}'",
                    expected_project=self.context_manager.project_id,
                    actual_project=data['project_name']
                )
    
    def _validate_file_paths(self, data: Dict[str, Any]):
        """Ensure file paths are within project boundaries"""
        path_fields = ['file_path', 'directory', 'workspace_path', 'relative_path', 'path']
        
        for field in path_fields:
            if field in data:
                file_path = data[field]
                if not self.context_manager.validate_file_access(file_path):
                    raise ContextViolationError(
                        f"File path '{file_path}' is outside project boundaries",
                        file_path=file_path,
                        project_root=str(self.context_manager.project_root)
                    )
    
    def _validate_task_scope(self, data: Dict[str, Any]):
        """Validate task operations are project-scoped"""
        task_id_fields = ['task_id', 'parent_task_id']
        
        for field in task_id_fields:
            if field in data and data[field]:
                task_id = data[field]
                if not self.context_manager.validate_task_belongs_to_project(task_id):
                    raise ProjectMismatchError(
                        f"Task '{task_id}' does not belong to project '{self.context_manager.project_id}'",
                        expected_project=self.context_manager.project_id,
                        actual_project=task_id.split(':')[0] if ':' in task_id else 'unknown'
                    )
    
    def _validate_entity_scope(self, data: Dict[str, Any]):
        """Validate memory entity operations are project-scoped"""
        entity_fields = ['entity_id', 'entity_name', 'from_entity', 'to_entity']
        
        for field in entity_fields:
            if field in data and data[field]:
                entity_id = data[field]
                if not self.context_manager.validate_entity_belongs_to_project(entity_id):
                    raise ProjectMismatchError(
                        f"Entity '{entity_id}' does not belong to project '{self.context_manager.project_id}'",
                        expected_project=self.context_manager.project_id,
                        actual_project=entity_id.split(':')[0] if ':' in entity_id else 'unknown'
                    )


# Global project context manager instance
# This follows the existing ATLAS pattern of global manager instances
_project_context_manager: Optional[ProjectContextManager] = None


def get_project_context_manager() -> ProjectContextManager:
    """Get global project context manager instance"""
    global _project_context_manager
    if _project_context_manager is None:
        _project_context_manager = ProjectContextManager()
    return _project_context_manager


def reset_project_context_manager():
    """Reset global project context manager (for testing)"""
    global _project_context_manager
    _project_context_manager = None