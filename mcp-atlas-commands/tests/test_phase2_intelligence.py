"""
Comprehensive Test Suite for Phase 2 Intelligence Features
Tests smart invalidation, language-aware caching, and performance analytics
"""

import os
import tempfile
import shutil
import pytest
import time
import json
from pathlib import Path
from unittest.mock import patch

from src.atlas_commands.caching.hierarchical_cache_manager import HierarchicalCacheManager
from src.atlas_commands.caching.content_hash_validator import ContentHashValidator, SmartCacheInvalidator
from src.atlas_commands.caching.language_aware_cache import (
    LanguageAwareSymbolCache, LanguageDetector, LanguageType, 
    PythonSymbolExtractor, TypeScriptSymbolExtractor, RustSymbolExtractor
)
from src.atlas_commands.caching.performance_analytics import (
    CachePerformanceDashboard, PerformanceTracker, CacheAnalyzer
)
from src.atlas_commands.project.context_manager import ProjectContextManager


class TestContentHashValidator:
    """Test smart cache invalidation with file dependency tracking"""
    
    @pytest.fixture
    def temp_atlas_dir(self):
        """Create temporary .atlas directory for testing"""
        temp_dir = tempfile.mkdtemp()
        atlas_dir = Path(temp_dir) / ".atlas"
        atlas_dir.mkdir(parents=True, exist_ok=True)
        
        with patch.object(Path, 'home', return_value=Path(temp_dir)):
            yield atlas_dir
        
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def cache_manager(self, temp_atlas_dir):
        """Create cache manager instance"""
        with patch.object(Path, 'home', return_value=temp_atlas_dir.parent):
            return HierarchicalCacheManager("test-project")
    
    @pytest.fixture
    def content_validator(self, cache_manager):
        """Create content validator instance"""
        return ContentHashValidator(cache_manager)
    
    @pytest.fixture
    def test_file(self, temp_atlas_dir):
        """Create a test file for dependency tracking"""
        test_file = temp_atlas_dir / "test_file.py"
        test_file.write_text("def hello(): return 'world'")
        return str(test_file)
    
    def test_file_hash_calculation(self, content_validator, test_file):
        """Test file content hash calculation"""
        hash1 = content_validator.get_file_hash(test_file)
        hash2 = content_validator.get_file_hash(test_file)
        
        assert hash1 == hash2
        assert len(hash1) == 16
        
        # Modify file and verify hash changes
        Path(test_file).write_text("def hello(): return 'modified'")
        hash3 = content_validator.get_file_hash(test_file)
        assert hash3 != hash1
    
    def test_dependency_registration(self, content_validator, test_file):
        """Test file dependency registration"""
        cache_type = "symbols"
        cache_key = "test_symbols"
        
        content_validator.register_file_dependency(
            test_file, cache_type, cache_key, "import"
        )
        
        # Verify dependency was registered
        dependent_caches = content_validator.find_dependent_caches(test_file)
        assert f"{cache_type}:{cache_key}" in dependent_caches
        
        # Verify dependency data
        abs_file_path = str(Path(test_file).resolve())
        assert abs_file_path in content_validator.dependencies
        dep = content_validator.dependencies[abs_file_path]
        assert dep.dependency_type == "import"
        assert f"{cache_type}:{cache_key}" in dep.dependent_caches
    
    def test_dependency_invalidation(self, content_validator, cache_manager, test_file):
        """Test cache invalidation when file changes"""
        cache_type = "symbols"
        cache_key = "test_symbols"
        test_data = {"symbols": ["hello"]}
        
        # Cache some data
        cache_manager.set_cache(cache_type, cache_key, test_data)
        assert cache_manager.get_cache(cache_type, cache_key) == test_data
        
        # Register dependency
        content_validator.register_file_dependency(test_file, cache_type, cache_key)
        
        # Modify file
        Path(test_file).write_text("def goodbye(): return 'world'")
        
        # Invalidate dependent caches
        invalidation_stats = content_validator.invalidate_dependent_caches(test_file)
        assert invalidation_stats["invalidated"] == 1
        assert invalidation_stats["errors"] == 0
        
        # Verify cache was invalidated
        assert cache_manager.get_cache(cache_type, cache_key) is None
    
    def test_validation_all_dependencies(self, content_validator, cache_manager, test_file):
        """Test validation of all file dependencies"""
        # Register multiple dependencies
        for i in range(3):
            content_validator.register_file_dependency(
                test_file, "symbols", f"key_{i}", "reference"
            )
            cache_manager.set_cache("symbols", f"key_{i}", {"data": i})
        
        # Modify file
        Path(test_file).write_text("def modified(): pass")
        
        # Validate all dependencies
        validation_stats = content_validator.validate_all_dependencies()
        
        assert validation_stats["files_checked"] == 1
        assert validation_stats["files_changed"] == 1
        assert validation_stats["caches_invalidated"] == 3
        assert validation_stats["errors"] == 0
    
    def test_smart_cache_invalidator(self, cache_manager, test_file):
        """Test high-level smart cache invalidator interface"""
        invalidator = SmartCacheInvalidator(cache_manager)
        
        cache_type = "analysis"
        cache_key = "complexity"
        test_data = {"complexity_score": 5.2}
        
        # Cache data
        cache_manager.set_cache(cache_type, cache_key, test_data)
        
        # Track dependency
        invalidator.track_file_dependency(test_file, cache_type, cache_key)
        
        # Modify file and check invalidation
        Path(test_file).write_text("def complex_function(): pass")
        invalidated = invalidator.invalidate_if_changed(test_file)
        
        assert invalidated is True
        assert cache_manager.get_cache(cache_type, cache_key) is None


class TestLanguageAwareSymbolCache:
    """Test language-specific symbol caching"""
    
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
    def symbol_cache(self, cache_manager):
        """Create symbol cache"""
        return LanguageAwareSymbolCache(cache_manager)
    
    @pytest.fixture
    def python_test_file(self, temp_atlas_dir):
        """Create Python test file"""
        python_file = temp_atlas_dir / "test.py"
        python_content = '''
import os
from typing import List

class TestClass:
    """A test class for symbol extraction"""
    
    def __init__(self, name: str):
        self.name = name
    
    @staticmethod
    def static_method() -> str:
        return "static"
    
    async def async_method(self) -> None:
        pass

def global_function(param: int) -> List[str]:
    """Global function with parameters"""
    return ["result"]

GLOBAL_VAR = "constant"
'''
        python_file.write_text(python_content)
        return str(python_file)
    
    @pytest.fixture
    def typescript_test_file(self, temp_atlas_dir):
        """Create TypeScript test file"""
        ts_file = temp_atlas_dir / "test.ts"
        ts_content = '''
import { Component } from 'react';
import * as utils from './utils';

export interface User {
    id: number;
    name: string;
}

export class UserComponent extends Component {
    constructor(props: any) {
        super(props);
    }
    
    async fetchUser(id: number): Promise<User> {
        return { id, name: 'test' };
    }
}

export const formatUser = (user: User): string => {
    return `${user.name} (${user.id})`;
};
'''
        ts_file.write_text(ts_content)
        return str(ts_file)
    
    @pytest.fixture
    def rust_test_file(self, temp_atlas_dir):
        """Create Rust test file"""
        rust_file = temp_atlas_dir / "test.rs"
        rust_content = '''
use std::collections::HashMap;
use crate::utils::Helper;

pub struct User {
    id: u32,
    name: String,
}

pub enum Status {
    Active,
    Inactive,
}

impl User {
    pub fn new(id: u32, name: String) -> Self {
        User { id, name }
    }
    
    pub async fn save(&self) -> Result<(), Error> {
        Ok(())
    }
}

pub fn create_user(name: &str) -> User {
    User::new(1, name.to_string())
}
'''
        rust_file.write_text(rust_content)
        return str(rust_file)
    
    def test_language_detection(self, python_test_file, typescript_test_file, rust_test_file):
        """Test programming language detection"""
        # Test by extension
        assert LanguageDetector.detect_language(python_test_file) == LanguageType.PYTHON
        assert LanguageDetector.detect_language(typescript_test_file) == LanguageType.TYPESCRIPT
        assert LanguageDetector.detect_language(rust_test_file) == LanguageType.RUST
        
        # Test with content
        with open(python_test_file, 'r') as f:
            py_content = f.read()
        assert LanguageDetector.detect_language("unknown.txt", py_content) == LanguageType.PYTHON
    
    def test_python_symbol_extraction(self, python_test_file):
        """Test Python symbol extraction"""
        extractor = PythonSymbolExtractor()
        with open(python_test_file, 'r') as f:
            content = f.read()
        
        symbol_map = extractor.extract_symbols(content, python_test_file)
        
        # Check symbols
        symbol_names = [s.name for s in symbol_map.symbols]
        assert "TestClass" in symbol_names
        assert "global_function" in symbol_names
        assert "__init__" in symbol_names
        assert "static_method" in symbol_names
        assert "async_method" in symbol_names
        
        # Check symbol types
        class_symbol = next(s for s in symbol_map.symbols if s.name == "TestClass")
        assert class_symbol.symbol_type == "class"
        
        func_symbol = next(s for s in symbol_map.symbols if s.name == "global_function")
        assert func_symbol.symbol_type == "function"
        assert len(func_symbol.parameters) == 1
        assert func_symbol.parameters[0] == "param"
        
        async_symbol = next(s for s in symbol_map.symbols if s.name == "async_method")
        assert async_symbol.is_async is True
        
        # Check imports
        import_modules = [imp.module for imp in symbol_map.imports]
        assert "os" in import_modules
        assert "typing" in import_modules
    
    def test_typescript_symbol_extraction(self, typescript_test_file):
        """Test TypeScript symbol extraction"""
        extractor = TypeScriptSymbolExtractor()
        with open(typescript_test_file, 'r') as f:
            content = f.read()
        
        symbol_map = extractor.extract_symbols(content, typescript_test_file)
        
        # Check symbols
        symbol_names = [s.name for s in symbol_map.symbols]
        assert "User" in symbol_names  # Interface
        assert "UserComponent" in symbol_names  # Class
        assert "formatUser" in symbol_names  # Function
        
        # Check symbol types
        interface_symbol = next(s for s in symbol_map.symbols if s.name == "User")
        assert interface_symbol.symbol_type == "interface"
        
        class_symbol = next(s for s in symbol_map.symbols if s.name == "UserComponent")
        assert class_symbol.symbol_type == "class"
        
        # Check imports
        import_modules = [imp.module for imp in symbol_map.imports]
        assert "react" in import_modules
        assert "./utils" in import_modules
    
    def test_rust_symbol_extraction(self, rust_test_file):
        """Test Rust symbol extraction"""
        extractor = RustSymbolExtractor()
        with open(rust_test_file, 'r') as f:
            content = f.read()
        
        symbol_map = extractor.extract_symbols(content, rust_test_file)
        
        # Check symbols
        symbol_names = [s.name for s in symbol_map.symbols]
        assert "User" in symbol_names  # Struct
        assert "Status" in symbol_names  # Enum
        assert "new" in symbol_names  # Function
        assert "create_user" in symbol_names  # Function
        
        # Check visibility
        user_struct = next(s for s in symbol_map.symbols if s.name == "User")
        assert user_struct.symbol_type == "struct"
        assert user_struct.visibility == "public"
        
        create_func = next(s for s in symbol_map.symbols if s.name == "create_user")
        assert create_func.symbol_type == "function"
        assert create_func.visibility == "public"
    
    def test_symbol_cache_operations(self, symbol_cache, python_test_file):
        """Test symbol caching operations"""
        # Analyze file
        symbol_map = symbol_cache.analyze_file(python_test_file)
        assert symbol_map is not None
        assert symbol_map.language == LanguageType.PYTHON
        assert len(symbol_map.symbols) > 0
        
        # Test caching (second call should use cache)
        symbol_map_2 = symbol_cache.analyze_file(python_test_file)
        assert symbol_map_2.content_hash == symbol_map.content_hash
        
        # Find specific symbol
        class_symbols = symbol_cache.get_symbols_by_type(python_test_file, "class")
        assert len(class_symbols) == 1
        assert class_symbols[0].name == "TestClass"
        
        # Find symbol by name
        symbol = symbol_cache.find_symbol_by_name(python_test_file, "global_function")
        assert symbol is not None
        assert symbol.symbol_type == "function"
        
        # Get imports
        imports = symbol_cache.get_file_imports(python_test_file)
        assert len(imports) > 0
        import_modules = [imp.module for imp in imports]
        assert "os" in import_modules
    
    def test_symbol_relationships(self, symbol_cache, python_test_file, typescript_test_file):
        """Test symbol relationship analysis"""
        file_paths = [python_test_file, typescript_test_file]
        relationships = symbol_cache.analyze_symbol_relationships(file_paths)
        
        assert "imports" in relationships
        assert "exports" in relationships
        assert "usage_graph" in relationships
        
        # Check imports tracking
        assert python_test_file in relationships["imports"]
        assert typescript_test_file in relationships["imports"]
        
        # Check usage graph
        assert len(relationships["usage_graph"]) > 0
    
    def test_language_distribution(self, symbol_cache, python_test_file, typescript_test_file, rust_test_file):
        """Test language distribution analysis"""
        file_paths = [python_test_file, typescript_test_file, rust_test_file]
        distribution = symbol_cache.get_language_distribution(file_paths)
        
        assert distribution.get("python", 0) == 1
        assert distribution.get("typescript", 0) == 1
        assert distribution.get("rust", 0) == 1


class TestPerformanceAnalytics:
    """Test performance analytics and dashboard"""
    
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
    def performance_dashboard(self, cache_manager):
        """Create performance dashboard"""
        return CachePerformanceDashboard(cache_manager)
    
    def test_performance_tracking(self, performance_dashboard):
        """Test performance operation tracking"""
        # Record cache operations
        performance_dashboard.record_cache_operation(
            "hit", "symbols", "project", "test_key", 15.5, 1024
        )
        performance_dashboard.record_cache_operation(
            "miss", "symbols", "project", "missing_key", 25.0
        )
        performance_dashboard.record_cache_operation(
            "set", "symbols", "project", "new_key", 10.0, 2048
        )
        
        # Get recent operations
        recent_ops = performance_dashboard.performance_tracker.get_recent_operations(60)
        assert len(recent_ops) == 3
        
        # Check operation types
        op_types = [op.operation_type for op in recent_ops]
        assert "hit" in op_types
        assert "miss" in op_types
        assert "set" in op_types
    
    def test_performance_metrics_calculation(self, performance_dashboard):
        """Test performance metrics calculation"""
        tracker = performance_dashboard.performance_tracker
        
        # Record operations with known timing
        start_time = time.time()
        for i in range(10):
            op_type = "hit" if i % 2 == 0 else "miss"
            tracker.record_operation(
                tracker.operations.__class__.__bases__[0](
                    timestamp=start_time + i,
                    operation_type=op_type,
                    cache_type="test",
                    cache_level="project",
                    key=f"key_{i}",
                    duration_ms=10.0 + i,
                    size_bytes=1024 * (i + 1)
                )
            )
        
        # Calculate metrics
        end_time = start_time + 10
        metrics = tracker.calculate_metrics(start_time, end_time)
        
        assert metrics.total_operations == 10
        assert metrics.hit_count == 5
        assert metrics.miss_count == 5
        assert metrics.hit_rate_percent == 50.0
        assert metrics.average_response_time_ms > 10.0
        assert metrics.cache_efficiency_score > 0
    
    def test_cache_analysis(self, performance_dashboard):
        """Test cache pattern analysis"""
        # Record diverse operations
        for i in range(20):
            cache_type = ["symbols", "analysis", "models"][i % 3]
            op_type = ["hit", "miss"][i % 2]
            
            performance_dashboard.record_cache_operation(
                op_type, cache_type, "project", f"key_{i}", 15.0, 1024
            )
        
        # Analyze patterns
        analyzer = performance_dashboard.analyzer
        patterns = analyzer.analyze_cache_patterns(1)  # Last 1 hour
        
        assert "cache_type_performance" in patterns
        assert "most_active_cache_types" in patterns
        assert len(patterns["cache_type_performance"]) == 3  # 3 cache types
        
        # Check cache type stats
        for cache_type, stats in patterns["cache_type_performance"].items():
            assert "hit_rate" in stats
            assert "hits" in stats
            assert "misses" in stats
    
    def test_recommendations_generation(self, performance_dashboard):
        """Test cache optimization recommendations"""
        tracker = performance_dashboard.performance_tracker
        
        # Simulate poor performance
        for i in range(100):
            tracker.record_operation(
                tracker.operations.__class__.__bases__[0](
                    timestamp=time.time(),
                    operation_type="miss",  # All misses = poor hit rate
                    cache_type="symbols",
                    cache_level="project",
                    key=f"key_{i}",
                    duration_ms=100.0,  # High response time
                    size_bytes=1024
                )
            )
        
        # Generate recommendations
        recommendations = performance_dashboard.analyzer.generate_recommendations()
        
        assert len(recommendations) > 0
        
        # Should recommend hit rate improvement
        hit_rate_rec = next(
            (rec for rec in recommendations if rec.recommendation_type == "hit_rate_optimization"),
            None
        )
        assert hit_rate_rec is not None
        assert hit_rate_rec.priority == "high"
    
    def test_comprehensive_report_generation(self, performance_dashboard):
        """Test comprehensive report generation"""
        # Record some operations
        for i in range(10):
            performance_dashboard.record_cache_operation(
                "hit", "symbols", "project", f"key_{i}", 10.0, 1024
            )
        
        # Generate different report types
        comprehensive_report = performance_dashboard.generate_report("comprehensive")
        performance_report = performance_dashboard.generate_report("performance")
        
        assert comprehensive_report["report_type"] == "comprehensive"
        assert "performance_metrics" in comprehensive_report
        assert "cache_patterns" in comprehensive_report
        assert "recommendations" in comprehensive_report
        
        assert performance_report["report_type"] == "performance"
        assert "performance_metrics" in performance_report
    
    def test_real_time_stats(self, performance_dashboard):
        """Test real-time statistics"""
        # Record recent operations
        for i in range(5):
            performance_dashboard.record_cache_operation(
                "hit", "symbols", "project", f"key_{i}", 15.0, 1024
            )
        
        # Get real-time stats
        real_time = performance_dashboard.get_real_time_stats()
        
        assert real_time["status"] == "active"
        assert real_time["last_5_minutes"]["operations"] == 5
        assert real_time["last_5_minutes"]["hit_rate"] == 100.0
        assert "cache_health" in real_time
    
    def test_analytics_snapshot_saving(self, performance_dashboard):
        """Test analytics snapshot saving"""
        # Record operations
        performance_dashboard.record_cache_operation(
            "hit", "symbols", "project", "test_key", 10.0, 1024
        )
        
        # Save snapshot
        snapshot_file = performance_dashboard.save_analytics_snapshot()
        
        if snapshot_file:  # Only if saving succeeded
            assert Path(snapshot_file).exists()
            
            # Verify snapshot content
            with open(snapshot_file, 'r') as f:
                snapshot = json.load(f)
            
            assert "timestamp" in snapshot
            assert "performance_report" in snapshot
            assert "recent_operations" in snapshot


class TestPhase2Integration:
    """Test Phase 2 integration with ProjectContextManager"""
    
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
        """Create project context manager with Phase 2 features"""
        with patch.dict(os.environ, {
            'ATLAS_PROJECT_ID': 'test-project',
            'ATLAS_PROJECT_ROOT': str(temp_dirs["project_root"]),
            'ATLAS_CACHE_ROOT': str(temp_dirs["cache_root"]),
            'ATLAS_WORKSPACE_ISOLATION': 'true'
        }):
            with patch.object(Path, 'home', return_value=temp_dirs["atlas_root"].parent):
                return ProjectContextManager()
    
    @pytest.fixture
    def test_python_file(self, temp_dirs):
        """Create test Python file"""
        test_file = temp_dirs["project_root"] / "example.py"
        test_content = '''
def calculate(x, y):
    """Calculate sum of two numbers"""
    return x + y

class Calculator:
    def multiply(self, a, b):
        return a * b
'''
        test_file.write_text(test_content)
        return str(test_file)
    
    def test_phase2_initialization(self, context_manager):
        """Test Phase 2 components are initialized"""
        assert context_manager.cache_manager is not None
        assert context_manager.content_validator is not None
        assert context_manager.smart_invalidator is not None
        assert context_manager.symbol_cache is not None
        assert context_manager.performance_dashboard is not None
    
    def test_symbol_analysis_integration(self, context_manager, test_python_file):
        """Test symbol analysis through context manager"""
        # Analyze file symbols
        result = context_manager.analyze_file_symbols(test_python_file)
        
        assert result is not None
        assert result["language"] == "python"
        assert len(result["symbols"]) > 0
        
        # Check specific symbols
        symbol_names = [s["name"] for s in result["symbols"]]
        assert "calculate" in symbol_names
        assert "Calculator" in symbol_names
        
        # Find specific symbol
        calc_symbol = context_manager.find_symbol_in_file(test_python_file, "calculate")
        assert calc_symbol is not None
        assert calc_symbol["type"] == "function"
        assert len(calc_symbol["parameters"]) == 2
    
    def test_dependency_tracking_integration(self, context_manager, test_python_file):
        """Test dependency tracking integration"""
        cache_type = "analysis"
        cache_key = "complexity"
        
        # Cache some data
        context_manager.cache_data(cache_type, cache_key, {"score": 3.5})
        
        # Track file dependency
        context_manager.track_file_dependency(test_python_file, cache_type, cache_key)
        
        # Modify file
        Path(test_python_file).write_text("def new_function(): pass")
        
        # Validate and check invalidation
        invalidated = context_manager.validate_file_caches(test_python_file)
        assert invalidated is True
        
        # Verify cache was invalidated
        cached_data = context_manager.get_cached_data(cache_type, cache_key)
        assert cached_data is None
    
    def test_performance_analytics_integration(self, context_manager):
        """Test performance analytics integration"""
        # Get dashboard report
        report = context_manager.get_performance_dashboard("performance")
        assert "cache_manager_stats" in report
        assert "performance_metrics" in report
        
        # Get real-time stats
        real_time = context_manager.get_real_time_cache_stats()
        assert "status" in real_time
        
        # Get cache health report
        health = context_manager.get_cache_health_report()
        assert "dependency_tracking" in health
    
    def test_project_symbol_analysis(self, context_manager, test_python_file, temp_dirs):
        """Test project-wide symbol analysis"""
        # Create additional test file
        test_js_file = temp_dirs["project_root"] / "example.js"
        test_js_file.write_text('''
function greet(name) {
    return `Hello, ${name}!`;
}

class Greeter {
    constructor(prefix) {
        this.prefix = prefix;
    }
}
''')
        
        # Analyze symbols across files
        file_paths = [test_python_file, str(test_js_file)]
        relationships = context_manager.analyze_project_symbols(file_paths)
        
        assert "imports" in relationships
        assert "exports" in relationships
        assert "usage_graph" in relationships
        
        # Get language distribution
        distribution = context_manager.get_language_distribution(file_paths)
        assert distribution.get("python", 0) >= 1
        assert distribution.get("javascript", 0) >= 1
    
    def test_analytics_snapshot(self, context_manager):
        """Test analytics snapshot functionality"""
        # Perform some operations to generate analytics
        context_manager.cache_data("test", "key1", {"data": "value1"})
        context_manager.get_cached_data("test", "key1")
        
        # Save analytics snapshot
        snapshot_file = context_manager.save_analytics_snapshot()
        
        if snapshot_file:  # Only if saving succeeded
            assert Path(snapshot_file).exists()


if __name__ == "__main__":
    pytest.main([__file__])