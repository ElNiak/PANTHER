"""
Language-Aware Symbol Caching System
Phase 2 implementation of ATLAS Hierarchical Cache Architecture
Supports Python, TypeScript, Rust, Go, Java and other languages
"""

import re
import ast
import json
import time
from pathlib import Path
from typing import Dict, List, Set, Optional, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum

from .hierarchical_cache_manager import HierarchicalCacheManager
from .content_hash_validator import ContentHashValidator


class LanguageType(Enum):
    """Supported programming languages"""
    PYTHON = "python"
    TYPESCRIPT = "typescript"
    JAVASCRIPT = "javascript"
    RUST = "rust"
    GO = "go"
    JAVA = "java"
    CSHARP = "csharp"
    CPP = "cpp"
    C = "c"
    UNKNOWN = "unknown"


@dataclass
class Symbol:
    """Represents a code symbol (function, class, variable, etc.)"""
    name: str
    symbol_type: str  # function, class, variable, interface, etc.
    line_start: int
    line_end: int
    column_start: int = 0
    column_end: int = 0
    parameters: List[str] = None
    return_type: str = ""
    visibility: str = "public"  # public, private, protected
    is_async: bool = False
    decorators: List[str] = None
    docstring: str = ""
    parent_symbol: str = ""  # For nested symbols
    
    def __post_init__(self):
        if self.parameters is None:
            self.parameters = []
        if self.decorators is None:
            self.decorators = []


@dataclass
class ImportStatement:
    """Represents an import/include statement"""
    module: str
    imported_names: List[str]
    alias: str = ""
    is_relative: bool = False
    line_number: int = 0


@dataclass
class SymbolMap:
    """Complete symbol map for a file"""
    file_path: str
    language: LanguageType
    symbols: List[Symbol]
    imports: List[ImportStatement]
    exports: List[str]  # For modules that export symbols
    content_hash: str
    last_analyzed: float
    analysis_version: str = "v2025-07-01"


class LanguageDetector:
    """Detects programming language from file extension and content"""
    
    EXTENSION_MAP = {
        '.py': LanguageType.PYTHON,
        '.ts': LanguageType.TYPESCRIPT,
        '.tsx': LanguageType.TYPESCRIPT,
        '.js': LanguageType.JAVASCRIPT,
        '.jsx': LanguageType.JAVASCRIPT,
        '.rs': LanguageType.RUST,
        '.go': LanguageType.GO,
        '.java': LanguageType.JAVA,
        '.cs': LanguageType.CSHARP,
        '.cpp': LanguageType.CPP,
        '.cc': LanguageType.CPP,
        '.cxx': LanguageType.CPP,
        '.c': LanguageType.C,
        '.h': LanguageType.C,
        '.hpp': LanguageType.CPP,
    }
    
    @classmethod
    def detect_language(cls, file_path: str, content: str = None) -> LanguageType:
        """Detect language from file extension and optionally content"""
        path_obj = Path(file_path)
        extension = path_obj.suffix.lower()
        
        # Primary detection by extension
        if extension in cls.EXTENSION_MAP:
            return cls.EXTENSION_MAP[extension]
        
        # Fallback to content analysis if available
        if content:
            return cls._detect_from_content(content)
        
        return LanguageType.UNKNOWN
    
    @classmethod
    def _detect_from_content(cls, content: str) -> LanguageType:
        """Detect language from file content patterns"""
        content_lower = content.lower()
        
        # Python patterns
        if any(pattern in content for pattern in ['def ', 'import ', 'from ', '__init__']):
            return LanguageType.PYTHON
        
        # TypeScript patterns
        if any(pattern in content for pattern in ['interface ', 'type ', ': string', ': number']):
            return LanguageType.TYPESCRIPT
        
        # Rust patterns
        if any(pattern in content for pattern in ['fn ', 'use ', 'mod ', 'struct ']):
            return LanguageType.RUST
        
        # Go patterns
        if any(pattern in content for pattern in ['func ', 'package ', 'import "', 'var ']):
            return LanguageType.GO
        
        # Java patterns
        if any(pattern in content for pattern in ['public class', 'import java', 'public static']):
            return LanguageType.JAVA
        
        return LanguageType.UNKNOWN


class PythonSymbolExtractor:
    """Extract symbols from Python code"""
    
    def extract_symbols(self, content: str, file_path: str) -> SymbolMap:
        """Extract Python symbols using AST"""
        symbols = []
        imports = []
        exports = []
        
        try:
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    symbols.append(self._extract_function(node))
                elif isinstance(node, ast.ClassDef):
                    symbols.append(self._extract_class(node))
                    # Extract methods within class
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            method = self._extract_function(item, parent=node.name)
                            symbols.append(method)
                elif isinstance(node, ast.Import):
                    imports.extend(self._extract_import(node))
                elif isinstance(node, ast.ImportFrom):
                    imports.extend(self._extract_import_from(node))
                elif isinstance(node, ast.Assign):
                    # Global variable assignments
                    if hasattr(node, 'targets'):
                        for target in node.targets:
                            if isinstance(target, ast.Name):
                                symbols.append(Symbol(
                                    name=target.id,
                                    symbol_type="variable",
                                    line_start=node.lineno,
                                    line_end=node.lineno
                                ))
            
            # Check for __all__ exports
            exports = self._find_exports(tree)
            
        except SyntaxError:
            # If parsing fails, return empty symbol map
            pass
        
        return SymbolMap(
            file_path=file_path,
            language=LanguageType.PYTHON,
            symbols=symbols,
            imports=imports,
            exports=exports,
            content_hash="",  # Will be set by caller
            last_analyzed=time.time()
        )
    
    def _extract_function(self, node: ast.FunctionDef, parent: str = "") -> Symbol:
        """Extract function symbol"""
        return Symbol(
            name=node.name,
            symbol_type="method" if parent else "function",
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            parameters=[arg.arg for arg in node.args.args],
            decorators=[self._get_decorator_name(d) for d in node.decorator_list],
            docstring=ast.get_docstring(node) or "",
            parent_symbol=parent,
            is_async=isinstance(node, ast.AsyncFunctionDef)
        )
    
    def _extract_class(self, node: ast.ClassDef) -> Symbol:
        """Extract class symbol"""
        return Symbol(
            name=node.name,
            symbol_type="class",
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            decorators=[self._get_decorator_name(d) for d in node.decorator_list],
            docstring=ast.get_docstring(node) or ""
        )
    
    def _extract_import(self, node: ast.Import) -> List[ImportStatement]:
        """Extract import statement"""
        imports = []
        for alias in node.names:
            imports.append(ImportStatement(
                module=alias.name,
                imported_names=[alias.name],
                alias=alias.asname or "",
                line_number=node.lineno
            ))
        return imports
    
    def _extract_import_from(self, node: ast.ImportFrom) -> List[ImportStatement]:
        """Extract from import statement"""
        module = node.module or ""
        imported_names = [alias.name for alias in node.names]
        
        return [ImportStatement(
            module=module,
            imported_names=imported_names,
            is_relative=node.level > 0,
            line_number=node.lineno
        )]
    
    def _get_decorator_name(self, decorator) -> str:
        """Get decorator name as string"""
        if isinstance(decorator, ast.Name):
            return decorator.id
        elif isinstance(decorator, ast.Attribute):
            return f"{decorator.value.id}.{decorator.attr}"
        return str(decorator)
    
    def _find_exports(self, tree: ast.AST) -> List[str]:
        """Find __all__ exports"""
        for node in ast.walk(tree):
            if (isinstance(node, ast.Assign) and 
                len(node.targets) == 1 and
                isinstance(node.targets[0], ast.Name) and
                node.targets[0].id == "__all__"):
                
                if isinstance(node.value, ast.List):
                    return [elt.s for elt in node.value.elts if isinstance(elt, ast.Str)]
        return []


class TypeScriptSymbolExtractor:
    """Extract symbols from TypeScript/JavaScript code using regex patterns"""
    
    def extract_symbols(self, content: str, file_path: str) -> SymbolMap:
        """Extract TypeScript symbols using regex patterns"""
        symbols = []
        imports = []
        exports = []
        
        # Function patterns
        func_patterns = [
            r'(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\([^)]*\)',
            r'(?:export\s+)?const\s+(\w+)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>',
            r'(\w+)\s*:\s*\([^)]*\)\s*=>'
        ]
        
        for pattern in func_patterns:
            for match in re.finditer(pattern, content, re.MULTILINE):
                line_num = content[:match.start()].count('\n') + 1
                symbols.append(Symbol(
                    name=match.group(1),
                    symbol_type="function",
                    line_start=line_num,
                    line_end=line_num,
                    is_async="async" in match.group(0)
                ))
        
        # Class patterns
        class_pattern = r'(?:export\s+)?class\s+(\w+)(?:\s+extends\s+\w+)?'
        for match in re.finditer(class_pattern, content):
            line_num = content[:match.start()].count('\n') + 1
            symbols.append(Symbol(
                name=match.group(1),
                symbol_type="class",
                line_start=line_num,
                line_end=line_num
            ))
        
        # Interface patterns
        interface_pattern = r'(?:export\s+)?interface\s+(\w+)'
        for match in re.finditer(interface_pattern, content):
            line_num = content[:match.start()].count('\n') + 1
            symbols.append(Symbol(
                name=match.group(1),
                symbol_type="interface",
                line_start=line_num,
                line_end=line_num
            ))
        
        # Import patterns
        import_patterns = [
            r'import\s+(\{[^}]+\}|\w+)\s+from\s+[\'"]([^\'"]+)[\'"]',
            r'import\s*\*\s*as\s+(\w+)\s+from\s+[\'"]([^\'"]+)[\'"]'
        ]
        
        for pattern in import_patterns:
            for match in re.finditer(pattern, content):
                line_num = content[:match.start()].count('\n') + 1
                imported_names = []
                
                import_spec = match.group(1)
                if import_spec.startswith('{'):
                    # Named imports
                    imported_names = [name.strip() for name in import_spec[1:-1].split(',')]
                else:
                    # Default import
                    imported_names = [import_spec]
                
                imports.append(ImportStatement(
                    module=match.group(2),
                    imported_names=imported_names,
                    line_number=line_num
                ))
        
        # Export patterns
        export_pattern = r'export\s+(?:default\s+)?(?:function|class|const|interface)\s+(\w+)'
        for match in re.finditer(export_pattern, content):
            exports.append(match.group(1))
        
        return SymbolMap(
            file_path=file_path,
            language=LanguageType.TYPESCRIPT,
            symbols=symbols,
            imports=imports,
            exports=exports,
            content_hash="",  # Will be set by caller
            last_analyzed=time.time()
        )


class RustSymbolExtractor:
    """Extract symbols from Rust code using regex patterns"""
    
    def extract_symbols(self, content: str, file_path: str) -> SymbolMap:
        """Extract Rust symbols using regex patterns"""
        symbols = []
        imports = []
        exports = []
        
        # Function patterns
        func_pattern = r'(?:pub\s+)?(?:async\s+)?fn\s+(\w+)\s*\([^)]*\)'
        for match in re.finditer(func_pattern, content):
            line_num = content[:match.start()].count('\n') + 1
            symbols.append(Symbol(
                name=match.group(1),
                symbol_type="function",
                line_start=line_num,
                line_end=line_num,
                visibility="public" if "pub" in match.group(0) else "private",
                is_async="async" in match.group(0)
            ))
        
        # Struct patterns
        struct_pattern = r'(?:pub\s+)?struct\s+(\w+)'
        for match in re.finditer(struct_pattern, content):
            line_num = content[:match.start()].count('\n') + 1
            symbols.append(Symbol(
                name=match.group(1),
                symbol_type="struct",
                line_start=line_num,
                line_end=line_num,
                visibility="public" if "pub" in match.group(0) else "private"
            ))
        
        # Enum patterns
        enum_pattern = r'(?:pub\s+)?enum\s+(\w+)'
        for match in re.finditer(enum_pattern, content):
            line_num = content[:match.start()].count('\n') + 1
            symbols.append(Symbol(
                name=match.group(1),
                symbol_type="enum",
                line_start=line_num,
                line_end=line_num,
                visibility="public" if "pub" in match.group(0) else "private"
            ))
        
        # Use statements (imports)
        use_pattern = r'use\s+([^;]+);'
        for match in re.finditer(use_pattern, content):
            line_num = content[:match.start()].count('\n') + 1
            use_statement = match.group(1).strip()
            
            # Parse use statement
            if '::' in use_statement:
                parts = use_statement.split('::')
                module = '::'.join(parts[:-1])
                imported = parts[-1]
                
                # Handle {item1, item2} syntax
                if imported.startswith('{') and imported.endswith('}'):
                    imported_names = [name.strip() for name in imported[1:-1].split(',')]
                else:
                    imported_names = [imported]
                
                imports.append(ImportStatement(
                    module=module,
                    imported_names=imported_names,
                    line_number=line_num
                ))
        
        return SymbolMap(
            file_path=file_path,
            language=LanguageType.RUST,
            symbols=symbols,
            imports=imports,
            exports=exports,  # Rust exports are handled differently
            content_hash="",  # Will be set by caller
            last_analyzed=time.time()
        )


class LanguageAwareSymbolCache:
    """Language-aware symbol caching system"""
    
    def __init__(self, cache_manager: HierarchicalCacheManager, 
                 content_validator: ContentHashValidator = None):
        self.cache_manager = cache_manager
        self.content_validator = content_validator
        
        # Initialize extractors
        self.extractors = {
            LanguageType.PYTHON: PythonSymbolExtractor(),
            LanguageType.TYPESCRIPT: TypeScriptSymbolExtractor(),
            LanguageType.JAVASCRIPT: TypeScriptSymbolExtractor(),  # Reuse TS extractor
            LanguageType.RUST: RustSymbolExtractor(),
        }
        
        # Cache for symbol maps
        self.symbol_cache_type = "symbols"
        self.relationship_cache_type = "symbol_relationships"
    
    def analyze_file(self, file_path: str, force_refresh: bool = False) -> Optional[SymbolMap]:
        """Analyze a file and cache its symbols"""
        path_obj = Path(file_path)
        if not path_obj.exists():
            return None
        
        # Read file content
        try:
            with open(path_obj, 'r', encoding='utf-8') as f:
                content = f.read()
        except (UnicodeDecodeError, IOError):
            return None
        
        # Calculate content hash
        content_hash = self._calculate_content_hash(content)
        
        # Check if cached version is still valid
        cache_key = self._get_cache_key(file_path)
        if not force_refresh:
            cached_symbols = self.cache_manager.get_cache(self.symbol_cache_type, cache_key)
            if (cached_symbols and 
                isinstance(cached_symbols, dict) and
                cached_symbols.get("content_hash") == content_hash):
                return self._deserialize_symbol_map(cached_symbols)
        
        # Detect language
        language = LanguageDetector.detect_language(file_path, content)
        if language not in self.extractors:
            return None
        
        # Extract symbols
        extractor = self.extractors[language]
        symbol_map = extractor.extract_symbols(content, file_path)
        symbol_map.content_hash = content_hash
        
        # Cache the symbol map
        serialized = self._serialize_symbol_map(symbol_map)
        self.cache_manager.set_cache(
            self.symbol_cache_type, 
            cache_key, 
            serialized,
            content_hash=content_hash
        )
        
        # Register file dependency for invalidation
        if self.content_validator:
            self.content_validator.register_file_dependency(
                file_path, self.symbol_cache_type, cache_key, "content"
            )
        
        return symbol_map
    
    def get_symbols_by_type(self, file_path: str, symbol_type: str) -> List[Symbol]:
        """Get symbols of specific type from a file"""
        symbol_map = self.analyze_file(file_path)
        if not symbol_map:
            return []
        
        return [s for s in symbol_map.symbols if s.symbol_type == symbol_type]
    
    def find_symbol_by_name(self, file_path: str, symbol_name: str) -> Optional[Symbol]:
        """Find a specific symbol by name in a file"""
        symbol_map = self.analyze_file(file_path)
        if not symbol_map:
            return None
        
        for symbol in symbol_map.symbols:
            if symbol.name == symbol_name:
                return symbol
        return None
    
    def get_file_imports(self, file_path: str) -> List[ImportStatement]:
        """Get all imports from a file"""
        symbol_map = self.analyze_file(file_path)
        return symbol_map.imports if symbol_map else []
    
    def analyze_symbol_relationships(self, file_paths: List[str]) -> Dict[str, Any]:
        """Analyze relationships between symbols across files"""
        relationships = {
            "imports": {},  # file -> list of imported modules
            "exports": {},  # file -> list of exported symbols
            "dependencies": {},  # file -> list of files it depends on
            "usage_graph": {}  # symbol -> list of files that use it
        }
        
        for file_path in file_paths:
            symbol_map = self.analyze_file(file_path)
            if not symbol_map:
                continue
            
            # Track imports
            relationships["imports"][file_path] = [
                imp.module for imp in symbol_map.imports
            ]
            
            # Track exports
            relationships["exports"][file_path] = symbol_map.exports
            
            # Track symbol usage
            for symbol in symbol_map.symbols:
                if symbol.name not in relationships["usage_graph"]:
                    relationships["usage_graph"][symbol.name] = []
                relationships["usage_graph"][symbol.name].append(file_path)
        
        # Cache relationships
        cache_key = "project_relationships"
        self.cache_manager.set_cache(
            self.relationship_cache_type,
            cache_key,
            relationships
        )
        
        return relationships
    
    def get_language_distribution(self, file_paths: List[str]) -> Dict[str, int]:
        """Get distribution of programming languages in project"""
        distribution = {}
        
        for file_path in file_paths:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                language = LanguageDetector.detect_language(file_path, content)
                lang_name = language.value
                distribution[lang_name] = distribution.get(lang_name, 0) + 1
            except (UnicodeDecodeError, IOError):
                continue
        
        return distribution
    
    def get_cache_statistics(self) -> Dict[str, Any]:
        """Get symbol cache statistics"""
        cache_stats = self.cache_manager.get_performance_stats()
        
        # Count cached symbols by language
        symbol_counts = {}
        # This would require iterating through cache entries
        # For now, return basic stats
        
        return {
            "cache_performance": cache_stats,
            "symbol_counts_by_language": symbol_counts,
            "supported_languages": [lang.value for lang in self.extractors.keys()]
        }
    
    def _get_cache_key(self, file_path: str) -> str:
        """Generate cache key for a file"""
        return f"file:{Path(file_path).name}:{abs(hash(file_path)) % 10000}"
    
    def _calculate_content_hash(self, content: str) -> str:
        """Calculate hash of file content"""
        import hashlib
        return hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]
    
    def _serialize_symbol_map(self, symbol_map: SymbolMap) -> Dict[str, Any]:
        """Serialize symbol map for caching"""
        return {
            "file_path": symbol_map.file_path,
            "language": symbol_map.language.value,
            "symbols": [asdict(symbol) for symbol in symbol_map.symbols],
            "imports": [asdict(imp) for imp in symbol_map.imports],
            "exports": symbol_map.exports,
            "content_hash": symbol_map.content_hash,
            "last_analyzed": symbol_map.last_analyzed,
            "analysis_version": symbol_map.analysis_version
        }
    
    def _deserialize_symbol_map(self, data: Dict[str, Any]) -> SymbolMap:
        """Deserialize symbol map from cache"""
        return SymbolMap(
            file_path=data["file_path"],
            language=LanguageType(data["language"]),
            symbols=[Symbol(**s) for s in data["symbols"]],
            imports=[ImportStatement(**imp) for imp in data["imports"]],
            exports=data["exports"],
            content_hash=data["content_hash"],
            last_analyzed=data["last_analyzed"],
            analysis_version=data.get("analysis_version", "v2025-07-01")
        )