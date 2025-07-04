"""
Comprehensive Test Suite for Phase 3 Cross-Project Intelligence Features
Tests pattern discovery, error solutions, performance baselines, and global optimization
"""

import os
import tempfile
import shutil
import pytest
import time
import json
from pathlib import Path
from unittest.mock import patch, Mock

from src.atlas_commands.caching.hierarchical_cache_manager import HierarchicalCacheManager
from src.atlas_commands.caching.content_hash_validator import ContentHashValidator
from src.atlas_commands.caching.language_aware_cache import LanguageAwareSymbolCache, LanguageType
from src.atlas_commands.caching.performance_analytics import CachePerformanceDashboard
from src.atlas_commands.caching.cross_project_intelligence import (
    CrossProjectIntelligenceOrchestrator, CrossProjectPatternDiscovery,
    SharedErrorSolutionsDatabase, PerformanceBaselineManager,
    IntelligentCachePreloader, CodePattern, ErrorSolution, PerformanceBaseline
)
from src.atlas_commands.caching.global_optimization import GlobalCacheOptimizer, OptimizationStrategy
from src.atlas_commands.project.context_manager import ProjectContextManager


class TestCrossProjectPatternDiscovery:
    """Test cross-project pattern discovery functionality"""
    
    @pytest.fixture
    def temp_atlas_dir(self):
        """Create temporary .atlas directory"""
        temp_dir = tempfile.mkdtemp()
        atlas_dir = Path(temp_dir) / ".atlas"
        atlas_dir.mkdir(parents=True, exist_ok=True)
        
        with patch.object(Path, 'home', return_value=Path(temp_dir)):
            yield atlas_dir
        
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def cache_manager(self, temp_atlas_dir):
        """Create cache manager"""
        with patch.object(Path, 'home', return_value=temp_atlas_dir.parent):
            return HierarchicalCacheManager("test-project")
    
    @pytest.fixture
    def symbol_cache(self, cache_manager, temp_atlas_dir):
        """Create symbol cache"""
        with patch.object(Path, 'home', return_value=temp_atlas_dir.parent):
            content_validator = ContentHashValidator(cache_manager)
            return LanguageAwareSymbolCache(cache_manager, content_validator)
    
    @pytest.fixture
    def pattern_discovery(self, cache_manager, symbol_cache):
        """Create pattern discovery instance"""
        return CrossProjectPatternDiscovery(cache_manager, symbol_cache)
    
    @pytest.fixture
    def sample_python_files(self, temp_atlas_dir):
        """Create sample Python files for testing"""
        files = []
        
        # File 1: Common utility functions
        file1 = temp_atlas_dir / "utils.py"
        file1.write_text('''
def process_data(data):
    """Process incoming data"""
    return data.strip().lower()

class DataProcessor:
    def __init__(self, config):
        self.config = config
    
    def validate(self, data):
        return len(data) > 0

def log_error(message):
    print(f"ERROR: {message}")
''')
        files.append(str(file1))
        
        # File 2: Similar patterns
        file2 = temp_atlas_dir / "helpers.py"
        file2.write_text('''
def process_input(input_data):
    """Process user input"""
    return input_data.strip().upper()

class InputProcessor:
    def __init__(self, settings):
        self.settings = settings
    
    def validate(self, input_data):
        return input_data is not None

def log_warning(message):
    print(f"WARN: {message}")
''')
        files.append(str(file2))
        
        return files
    
    def test_analyze_project_patterns(self, pattern_discovery, sample_python_files):
        """Test analyzing patterns in a project"""
        project_id = "test-project-1"
        patterns = pattern_discovery.analyze_project_patterns(project_id, sample_python_files)
        
        assert "function_patterns" in patterns
        assert "import_patterns" in patterns
        assert "class_patterns" in patterns
        
        # Check that common patterns are detected
        func_patterns = patterns["function_patterns"]
        assert len(func_patterns) > 0
        
        # Look for similar function patterns
        sync_func_patterns = [key for key in func_patterns.keys() if "sync_func" in key]
        assert len(sync_func_patterns) > 0
    
    def test_discover_cross_project_patterns(self, pattern_discovery, sample_python_files):
        """Test discovering patterns across multiple projects"""
        # Simulate patterns from multiple projects
        project1_patterns = {
            "function_patterns": {
                "sync_func_1params": {"count": 3, "files": ["file1.py"], "signature": "process_data(data)"},
                "sync_func_2params": {"count": 2, "files": ["file2.py"], "signature": "validate(self, data)"}
            },
            "class_patterns": {
                "class_DataProcessor_1": {"count": 1, "files": ["file1.py"], "signature": "DataProcessor"}
            }
        }
        
        project2_patterns = {
            "function_patterns": {
                "sync_func_1params": {"count": 2, "files": ["other1.py"], "signature": "process_input(input_data)"},
                "sync_func_2params": {"count": 1, "files": ["other2.py"], "signature": "validate(self, input_data)"}
            },
            "class_patterns": {
                "class_InputProcessor_1": {"count": 1, "files": ["other1.py"], "signature": "InputProcessor"}
            }
        }
        
        # Mock cache data
        cache_data = {
            "project_patterns_project1": project1_patterns,
            "project_patterns_project2": project2_patterns
        }
        
        with patch.object(pattern_discovery.cache_manager, 'get_cache', side_effect=lambda cache_type, key, **kwargs: cache_data.get(key)):
            cross_patterns = pattern_discovery.discover_cross_project_patterns(["project1", "project2"])
        
        assert len(cross_patterns) > 0
        
        # Check that cross-project patterns are identified
        pattern_names = [p.pattern_name for p in cross_patterns]
        assert any("sync_func_1params" in name for name in pattern_names)
    
    def test_get_patterns_for_project(self, pattern_discovery):
        """Test getting relevant patterns for a specific project"""
        # Mock discovered patterns
        mock_patterns = [
            CodePattern(
                pattern_id="test1",
                pattern_type="function",
                pattern_name="common_validator",
                pattern_signature="validate(data)",
                language=LanguageType.PYTHON,
                frequency=5,
                projects=["other-project"],
                files=["validator.py"],
                confidence_score=0.8,
                first_seen=time.time(),
                last_seen=time.time()
            )
        ]
        
        with patch.object(pattern_discovery, '_load_discovered_patterns', return_value=mock_patterns):
            relevant_patterns = pattern_discovery.get_patterns_for_project("new-project")
        
        assert len(relevant_patterns) == 1
        assert relevant_patterns[0].confidence_score > 0.7


class TestSharedErrorSolutionsDatabase:
    """Test shared error solutions database"""
    
    @pytest.fixture
    def temp_atlas_dir(self):
        """Create temporary .atlas directory"""
        temp_dir = tempfile.mkdtemp()
        atlas_dir = Path(temp_dir) / ".atlas"
        atlas_dir.mkdir(parents=True, exist_ok=True)
        
        with patch.object(Path, 'home', return_value=Path(temp_dir)):
            yield atlas_dir
        
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def cache_manager(self, temp_atlas_dir):
        """Create cache manager"""
        with patch.object(Path, 'home', return_value=temp_atlas_dir.parent):
            return HierarchicalCacheManager("test-project")
    
    @pytest.fixture
    def error_solutions_db(self, cache_manager):
        """Create error solutions database"""
        return SharedErrorSolutionsDatabase(cache_manager)
    
    def test_add_error_solution(self, error_solutions_db):
        """Test adding an error solution"""
        error_pattern = "AttributeError: 'NoneType' object has no attribute"
        error_type = "runtime"
        language = LanguageType.PYTHON
        solution_steps = [
            "Check if object is None before accessing attributes",
            "Add null checks or default values",
            "Use getattr() with default parameter"
        ]
        code_examples = [
            "if obj is not None:\n    obj.attribute",
            "getattr(obj, 'attribute', default_value)"
        ]
        
        error_id = error_solutions_db.add_error_solution(
            error_pattern, error_type, language, solution_steps, code_examples, "test-project"
        )
        
        assert error_id is not None
        assert len(error_id) > 0
        
        # Retrieve the solution
        solution = error_solutions_db.get_error_solution(error_id)
        assert solution is not None
        assert solution.error_pattern == error_pattern
        assert solution.language == language
        assert len(solution.solution_steps) == 3
        assert len(solution.code_examples) == 2
        assert "test-project" in solution.projects_affected
    
    def test_search_solutions(self, error_solutions_db):
        """Test searching for error solutions"""
        # Add a solution first
        error_pattern = "ImportError: No module named"
        error_id = error_solutions_db.add_error_solution(
            error_pattern, "import", LanguageType.PYTHON,
            ["Install the missing module", "Check import path"],
            ["pip install module_name"],
            "test-project"
        )
        
        # Search for solutions
        solutions = error_solutions_db.search_solutions(error_pattern, LanguageType.PYTHON)
        
        assert len(solutions) == 1
        assert solutions[0].error_pattern == error_pattern
    
    def test_update_solution_success_rate(self, error_solutions_db):
        """Test updating solution success rate"""
        # Add a solution
        error_id = error_solutions_db.add_error_solution(
            "ValueError: invalid literal", "runtime", LanguageType.PYTHON,
            ["Validate input before conversion"], ["try: int(value) except ValueError: ..."],
            "test-project"
        )
        
        # Update success rate
        error_solutions_db.update_solution_success_rate(error_id, True)
        error_solutions_db.update_solution_success_rate(error_id, False)
        
        solution = error_solutions_db.get_error_solution(error_id)
        assert solution.usage_count == 3  # Initial + 2 updates
        assert 0 < solution.success_rate < 1  # Should be between 0 and 1


class TestPerformanceBaselineManager:
    """Test performance baseline management"""
    
    @pytest.fixture
    def temp_atlas_dir(self):
        """Create temporary .atlas directory"""
        temp_dir = tempfile.mkdtemp()
        atlas_dir = Path(temp_dir) / ".atlas"
        atlas_dir.mkdir(parents=True, exist_ok=True)
        
        with patch.object(Path, 'home', return_value=Path(temp_dir)):
            yield atlas_dir
        
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def cache_manager(self, temp_atlas_dir):
        """Create cache manager"""
        with patch.object(Path, 'home', return_value=temp_atlas_dir.parent):
            return HierarchicalCacheManager("test-project")
    
    @pytest.fixture
    def performance_dashboard(self, cache_manager, temp_atlas_dir):
        """Create performance dashboard"""
        with patch.object(Path, 'home', return_value=temp_atlas_dir.parent):
            content_validator = ContentHashValidator(cache_manager)
            symbol_cache = LanguageAwareSymbolCache(cache_manager, content_validator)
            return CachePerformanceDashboard(cache_manager, content_validator, symbol_cache)
    
    @pytest.fixture
    def baseline_manager(self, cache_manager, performance_dashboard):
        """Create baseline manager"""
        return PerformanceBaselineManager(cache_manager, performance_dashboard)
    
    def test_create_baseline(self, baseline_manager):
        """Test creating a performance baseline"""
        project_id = "test-project"
        language = LanguageType.PYTHON
        operation_type = "cache_operations"
        
        baseline = baseline_manager.create_baseline(project_id, language, operation_type)
        
        assert baseline.project_id == project_id
        assert baseline.language == language
        assert baseline.operation_type == operation_type
        assert baseline.baseline_id is not None
        assert baseline.measured_at > 0
    
    def test_compare_with_baselines(self, baseline_manager):
        """Test comparing with other project baselines"""
        project_id = "test-project"
        language = LanguageType.PYTHON
        
        # Mock similar baselines
        mock_baselines = [
            PerformanceBaseline(
                baseline_id="baseline1",
                project_id="other-project",
                language=language,
                operation_type="cache_operations",
                average_time_ms=10.0,
                median_time_ms=8.0,
                p95_time_ms=20.0,
                sample_count=100,
                cache_hit_rate=85.0,
                measured_at=time.time(),
                environment_info={"efficiency_score": 80.0}
            )
        ]
        
        with patch.object(baseline_manager, '_get_similar_baselines', return_value=mock_baselines):
            comparison = baseline_manager.compare_with_baselines(project_id, language)
        
        assert "current_baseline" in comparison
        assert "comparisons" in comparison
        assert "insights" in comparison
        assert "recommendations" in comparison


class TestIntelligentCachePreloader:
    """Test intelligent cache preloading"""
    
    @pytest.fixture
    def temp_atlas_dir(self):
        """Create temporary .atlas directory"""
        temp_dir = tempfile.mkdtemp()
        atlas_dir = Path(temp_dir) / ".atlas"
        atlas_dir.mkdir(parents=True, exist_ok=True)
        
        with patch.object(Path, 'home', return_value=Path(temp_dir)):
            yield atlas_dir
        
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def cache_manager(self, temp_atlas_dir):
        """Create cache manager"""
        with patch.object(Path, 'home', return_value=temp_atlas_dir.parent):
            return HierarchicalCacheManager("test-project")
    
    @pytest.fixture
    def pattern_discovery(self, cache_manager):
        """Create pattern discovery mock"""
        with patch.object(Path, 'home', return_value=cache_manager.project_cache_root.parent):
            content_validator = ContentHashValidator(cache_manager)
            symbol_cache = LanguageAwareSymbolCache(cache_manager, content_validator)
            return CrossProjectPatternDiscovery(cache_manager, symbol_cache)
    
    @pytest.fixture
    def cache_preloader(self, cache_manager, pattern_discovery):
        """Create cache preloader"""
        return IntelligentCachePreloader(cache_manager, pattern_discovery)
    
    def test_generate_preload_suggestions(self, cache_preloader):
        """Test generating preload suggestions"""
        project_id = "test-project"
        
        # Mock relevant patterns
        mock_patterns = [
            CodePattern(
                pattern_id="pattern1",
                pattern_type="function",
                pattern_name="common_util",
                pattern_signature="process_data(data)",
                language=LanguageType.PYTHON,
                frequency=10,
                projects=["other-project"],
                files=["utils.py"],
                confidence_score=0.9,
                first_seen=time.time(),
                last_seen=time.time()
            )
        ]
        
        with patch.object(cache_preloader.pattern_discovery, 'get_patterns_for_project', return_value=mock_patterns):
            suggestions = cache_preloader.generate_preload_suggestions(project_id)
        
        assert len(suggestions) == 1
        assert suggestions[0].target_project == project_id
        assert suggestions[0].confidence == 0.9
        assert suggestions[0].priority == "high"
    
    def test_execute_preload_suggestions(self, cache_preloader):
        """Test executing preload suggestions"""
        project_id = "test-project"
        
        # Create mock suggestions
        mock_suggestions = [
            Mock(suggestion_id="sugg1", cache_keys=["key1", "key2"])
        ]
        
        with patch.object(cache_preloader, '_load_suggestions', return_value=mock_suggestions):
            results = cache_preloader.execute_preload_suggestions(project_id)
        
        assert "preloaded_items" in results
        assert "skipped_items" in results
        assert "errors" in results


class TestGlobalCacheOptimizer:
    """Test global cache optimization"""
    
    @pytest.fixture
    def temp_atlas_dir(self):
        """Create temporary .atlas directory"""
        temp_dir = tempfile.mkdtemp()
        atlas_dir = Path(temp_dir) / ".atlas"
        atlas_dir.mkdir(parents=True, exist_ok=True)
        
        with patch.object(Path, 'home', return_value=Path(temp_dir)):
            yield atlas_dir
        
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def cross_project_intelligence(self, temp_atlas_dir):
        """Create cross-project intelligence orchestrator"""
        with patch.object(Path, 'home', return_value=temp_atlas_dir.parent):
            cache_manager = HierarchicalCacheManager("test-project")
            content_validator = ContentHashValidator(cache_manager)
            symbol_cache = LanguageAwareSymbolCache(cache_manager, content_validator)
            performance_dashboard = CachePerformanceDashboard(cache_manager, content_validator, symbol_cache)
            
            return CrossProjectIntelligenceOrchestrator(
                cache_manager, content_validator, symbol_cache, performance_dashboard
            )
    
    @pytest.fixture
    def global_optimizer(self, cross_project_intelligence):
        """Create global cache optimizer"""
        return GlobalCacheOptimizer(cross_project_intelligence)
    
    def test_analyze_global_cache_state(self, global_optimizer):
        """Test analyzing global cache state"""
        analysis = global_optimizer.analyze_global_cache_state()
        
        assert "analysis_timestamp" in analysis
        assert "cache_size_info" in analysis
        assert "performance_overview" in analysis
        assert "storage_analysis" in analysis
        assert "access_patterns" in analysis
        assert "bottlenecks" in analysis
        assert "optimization_score" in analysis
    
    def test_generate_optimization_strategies(self, global_optimizer):
        """Test generating optimization strategies"""
        # Mock cache state that triggers optimization strategies
        mock_cache_info = {
            "total_cache_mb": 1500,  # Large cache
            "global_cache_mb": 300,
            "project_cache_mb": 1200
        }
        
        with patch.object(global_optimizer.cache_manager, 'get_cache_size_info', return_value=mock_cache_info):
            strategies = global_optimizer.generate_optimization_strategies()
        
        assert len(strategies) > 0
        
        # Check strategy types
        strategy_types = [s.strategy_type for s in strategies]
        assert "storage" in strategy_types
        assert "preload" in strategy_types
    
    def test_get_optimization_recommendations(self, global_optimizer):
        """Test getting optimization recommendations"""
        recommendations = global_optimizer.get_optimization_recommendations()
        
        assert isinstance(recommendations, list)
        
        if recommendations:
            rec = recommendations[0]
            assert "strategy_id" in rec
            assert "name" in rec
            assert "priority" in rec
            assert "estimated_improvement" in rec
            assert "implementation_steps" in rec
    
    def test_monitor_optimization_effectiveness(self, global_optimizer):
        """Test monitoring optimization effectiveness"""
        monitoring = global_optimizer.monitor_optimization_effectiveness()
        
        assert "monitoring_timestamp" in monitoring
        
        # Should handle case with no optimizations applied yet
        if "message" in monitoring:
            assert "No optimizations" in monitoring["message"]
        else:
            assert "overall_effectiveness" in monitoring


class TestCrossProjectIntelligenceIntegration:
    """Test full cross-project intelligence integration"""
    
    @pytest.fixture
    def temp_dirs(self):
        """Create temporary directories"""
        temp_dir = tempfile.mkdtemp()
        project_root = Path(temp_dir) / "project"
        cache_root = Path(temp_dir) / "cache"
        atlas_root = Path(temp_dir) / ".atlas"
        
        project_root.mkdir(parents=True, exist_ok=True)
        cache_root.mkdir(parents=True, exist_ok=True)
        atlas_root.mkdir(parents=True, exist_ok=True)
        
        yield {
            "temp_dir": temp_dir,
            "project_root": project_root,
            "cache_root": cache_root,
            "atlas_root": atlas_root
        }
        
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def context_manager(self, temp_dirs):
        """Create project context manager with Phase 3 features"""
        with patch.dict(os.environ, {
            'ATLAS_PROJECT_ID': 'test-project',
            'ATLAS_PROJECT_ROOT': str(temp_dirs["project_root"]),
            'ATLAS_CACHE_ROOT': str(temp_dirs["cache_root"]),
            'ATLAS_WORKSPACE_ISOLATION': 'true'
        }):
            with patch.object(Path, 'home', return_value=temp_dirs["atlas_root"].parent):
                return ProjectContextManager()
    
    @pytest.fixture
    def sample_files(self, temp_dirs):
        """Create sample files for testing"""
        files = []
        
        # Python file
        py_file = temp_dirs["project_root"] / "main.py"
        py_file.write_text('''
def main():
    print("Hello World")

class Application:
    def run(self):
        main()
''')
        files.append(str(py_file))
        
        # JavaScript file
        js_file = temp_dirs["project_root"] / "app.js"
        js_file.write_text('''
function greet(name) {
    return `Hello, ${name}!`;
}

class App {
    constructor() {
        this.name = "App";
    }
}
''')
        files.append(str(js_file))
        
        return files
    
    def test_phase3_initialization(self, context_manager):
        """Test Phase 3 components are initialized"""
        assert context_manager.cache_manager is not None
        assert context_manager.content_validator is not None
        assert context_manager.symbol_cache is not None
        assert context_manager.performance_dashboard is not None
        assert context_manager.cross_project_intelligence is not None
    
    def test_cross_project_analysis(self, context_manager, sample_files):
        """Test comprehensive cross-project analysis"""
        analysis = context_manager.analyze_cross_project_insights(sample_files)
        
        assert "project_id" in analysis
        assert "analysis_timestamp" in analysis
        assert "discovered_patterns" in analysis
        assert "performance_analysis" in analysis
        assert "optimization_suggestions" in analysis
        assert "cross_project_insights" in analysis
    
    def test_pattern_discovery_integration(self, context_manager, sample_files):
        """Test pattern discovery through context manager"""
        patterns = context_manager.discover_project_patterns(sample_files)
        
        assert "function_patterns" in patterns
        assert "class_patterns" in patterns
        assert "import_patterns" in patterns
    
    def test_error_solution_management(self, context_manager):
        """Test error solution management"""
        # Add an error solution
        error_id = context_manager.add_error_solution(
            "TypeError: unsupported operand type(s)",
            "runtime",
            "python",
            ["Check variable types before operations", "Use type conversion"],
            ["isinstance(x, int)", "int(x) if x.isdigit() else 0"]
        )
        
        assert error_id != ""
        
        # Search for solutions
        solutions = context_manager.search_error_solutions("TypeError", "python")
        assert len(solutions) > 0
    
    def test_performance_comparison(self, context_manager):
        """Test performance comparison with other projects"""
        comparison = context_manager.compare_performance_with_similar_projects()
        
        # Should handle case with no similar projects
        assert isinstance(comparison, dict)
    
    def test_cache_preload_suggestions(self, context_manager):
        """Test cache preload suggestions"""
        suggestions = context_manager.generate_cache_preload_suggestions()
        
        assert isinstance(suggestions, list)
        # New project may not have suggestions yet
    
    def test_global_optimization_features(self, context_manager):
        """Test global optimization features"""
        # Test cache state analysis
        state_analysis = context_manager.analyze_global_cache_state()
        assert isinstance(state_analysis, dict)
        
        # Test optimization recommendations
        recommendations = context_manager.get_optimization_recommendations()
        assert isinstance(recommendations, list)
        
        # Test optimization monitoring
        monitoring = context_manager.monitor_optimization_effectiveness()
        assert isinstance(monitoring, dict)
    
    def test_global_optimization_report(self, context_manager):
        """Test global optimization report generation"""
        report = context_manager.get_global_optimization_report()
        
        assert "report_type" in report
        assert report["report_type"] == "global_optimization"
        assert "generated_at" in report
        assert "cross_project_patterns" in report
        assert "cache_optimization" in report


if __name__ == "__main__":
    pytest.main([__file__])