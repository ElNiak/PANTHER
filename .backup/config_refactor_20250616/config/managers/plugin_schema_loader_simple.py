"""Plugin schema loading functionality without pydantic dependency."""

import importlib
import importlib.util
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Type, Union

from panther.core.exceptions.error_handler_mixin import ErrorHandlerMixin


class SchemaInfo:
    """Container for schema information."""

    def __init__(self, name: str, schema_class: Any, source_file: Path):
        """Initialize schema info.

        Args:
            name: Schema name
            schema_class: Schema class
            source_file: Source file path
        """
        self.name = name
        self.schema_class = schema_class
        self.source_file = source_file
        self.version = getattr(schema_class, "__version__", "unknown")
        self.description = schema_class.__doc__ or ""
        self.json_schema = None
        self.fields_info = {}


class PluginSchemaLoader(ErrorHandlerMixin):
    """Loads and caches plugin schemas without external dependencies."""

    def __init__(self, plugin_dir: Optional[Path] = None):
        """Initialize the schema loader.

        Args:
            plugin_dir: Optional plugin directory to add to search paths
        """
        super().__init__()
        self._schema_cache: Dict[str, SchemaInfo] = {}
        self._load_paths: List[Path] = []

        if plugin_dir:
            self.add_schema_path(plugin_dir)

    def add_schema_path(self, path: Union[str, Path]) -> None:
        """Add a path to search for schemas.

        Args:
            path: Directory path to search for schema files
        """
        path_obj = Path(path)
        if path_obj.exists() and path_obj.is_dir():
            self._load_paths.append(path_obj)

    def load_schema(
        self, name: str, force_reload: bool = False
    ) -> Optional[SchemaInfo]:
        """Load a schema by name.

        Args:
            name: Name of the schema to load
            force_reload: Whether to force reload cached schemas

        Returns:
            SchemaInfo object if found, None otherwise
        """
        if not force_reload and name in self._schema_cache:
            return self._schema_cache[name]

        # Try to find and load the schema
        for path in self._load_paths:
            schema_file = path / f"{name}.py"
            if schema_file.exists():
                try:
                    module_name = f"schema_{name}"
                    spec = importlib.util.spec_from_file_location(
                        module_name, schema_file
                    )
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)

                        # Look for schema classes in the module
                        for attr_name in dir(module):
                            attr = getattr(module, attr_name)
                            if isinstance(attr, type) and attr_name.endswith("Schema"):
                                schema_info = SchemaInfo(name, attr, schema_file)
                                self._schema_cache[name] = schema_info
                                return schema_info

                except Exception as e:
                    self._handle_error(f"Failed to load schema {name}: {e}")

        return None

    def get_cached_schemas(self) -> Dict[str, SchemaInfo]:
        """Get all cached schemas.

        Returns:
            Dictionary of cached schema info objects
        """
        return self._schema_cache.copy()

    def validate_data(
        self, schema_name: str, data: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        """Validate data against a schema.

        Args:
            schema_name: Name of the schema to validate against
            data: Data to validate

        Returns:
            Tuple of (is_valid, errors)
        """
        schema_info = self.load_schema(schema_name)
        if not schema_info:
            return False, [f"Schema {schema_name} not found"]

        try:
            # Simple validation - just check if schema class can process the data
            if hasattr(schema_info.schema_class, "validate"):
                result = schema_info.schema_class.validate(data)
                return True, []
            else:
                # If no validate method, assume valid
                return True, []
        except Exception as e:
            return False, [str(e)]

    def clear_cache(self) -> None:
        """Clear the schema cache."""
        self._schema_cache.clear()
