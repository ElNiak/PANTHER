"""Plugin schema loading and caching functionality."""

import importlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, Union

from pydantic import BaseModel, ValidationError

from panther.core.exceptions.error_handler_mixin import ErrorHandlerMixin


class SchemaInfo:
    """Container for schema information."""

    def __init__(self, name: str, schema_class: Type[BaseModel], source_file: Path):
        """Initialize schema info.

        Args:
            name: Schema name
            schema_class: Pydantic model class
            source_file: Source file path
        """
        self.name = name
        self.schema_class = schema_class
        self.source_file = source_file
        self.version = getattr(schema_class, "__version__", "unknown")
        self.description = schema_class.__doc__ or ""
        self.json_schema = None
        self.fields_info = {}

        # Extract schema and field information
        self._extract_schema_info()

    def _extract_schema_info(self) -> None:
        """Extract schema and field information."""
        try:
            # Get JSON schema
            self.json_schema = self.schema_class.schema()

            # Extract field information
            if hasattr(self.schema_class, "__fields__"):
                for field_name, field in self.schema_class.__fields__.items():
                    self.fields_info[field_name] = {
                        "type": str(field.type_),
                        "required": field.required,
                        "default": field.default if field.default is not ... else None,
                        "description": field.field_info.description or "",
                        "alias": field.alias,
                    }
        except Exception as e:
            # If schema extraction fails, continue with empty info
            pass

    def to_dict(self) -> Dict[str, Any]:
        """Convert schema info to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "source_file": str(self.source_file),
            "json_schema": self.json_schema,
            "fields_info": self.fields_info,
        }

    def validate_data(self, data: Dict[str, Any]) -> Union[BaseModel, ValidationError]:
        """Validate data against this schema.

        Args:
            data: Data to validate

        Returns:
            Validated model instance or ValidationError
        """
        try:
            return self.schema_class(**data)
        except ValidationError as e:
            return e


class PluginSchemaLoader(ErrorHandlerMixin):
    """Handles loading and caching of plugin schemas."""

    def __init__(self, plugins_base_dir: Path):
        """Initialize schema loader.

        Args:
            plugins_base_dir: Base directory containing plugins
        """
        super().__init__()
        self.plugins_base_dir = plugins_base_dir
        self.loaded_schemas: Dict[str, SchemaInfo] = {}
        self.schema_cache_file = plugins_base_dir / ".schema_cache.json"
        self.import_cache: Dict[str, Any] = {}

    def load_all_schemas(self, force_refresh: bool = False) -> Dict[str, SchemaInfo]:
        """Load all plugin schemas.

        Args:
            force_refresh: Whether to force refresh from source files

        Returns:
            Dictionary mapping schema names to SchemaInfo objects
        """
        if not force_refresh and self._load_from_cache():
            self.logger.info(f"Loaded {len(self.loaded_schemas)} schemas from cache")
            return self.loaded_schemas

        self.logger.info("Loading plugin schemas...")

        # Discover and load schema files
        schema_files = self._discover_schema_files()

        for schema_file in schema_files:
            try:
                schemas = self._load_schemas_from_file(schema_file)
                for schema_name, schema_info in schemas.items():
                    self.loaded_schemas[schema_name] = schema_info
            except Exception as e:
                self.logger.error(f"Failed to load schemas from {schema_file}: {e}")

        # Save to cache
        self._save_to_cache()

        self.logger.info(
            f"Loaded {len(self.loaded_schemas)} schemas from {len(schema_files)} files"
        )
        return self.loaded_schemas

    def load_schema_for_plugin(
        self, plugin_name: str, plugin_type: str
    ) -> Optional[SchemaInfo]:
        """Load schema for a specific plugin.

        Args:
            plugin_name: Name of the plugin
            plugin_type: Type of the plugin

        Returns:
            SchemaInfo if found, None otherwise
        """
        # Try to find schema file for the plugin
        schema_file = self._find_schema_file_for_plugin(plugin_name, plugin_type)

        if not schema_file:
            self.logger.warning(f"No schema file found for plugin {plugin_name}")
            return None

        try:
            schemas = self._load_schemas_from_file(schema_file)

            # Look for a schema that matches the plugin
            for schema_name, schema_info in schemas.items():
                if self._is_schema_for_plugin(schema_name, plugin_name):
                    return schema_info

            # If no exact match, return the first schema found
            if schemas:
                return list(schemas.values())[0]

            return None

        except Exception as e:
            self.logger.error(f"Failed to load schema for plugin {plugin_name}: {e}")
            return None

    def get_schema(self, schema_name: str) -> Optional[SchemaInfo]:
        """Get a specific schema by name.

        Args:
            schema_name: Name of the schema

        Returns:
            SchemaInfo if found, None otherwise
        """
        return self.loaded_schemas.get(schema_name)

    def validate_plugin_config(
        self, plugin_name: str, config_data: Dict[str, Any]
    ) -> Union[BaseModel, ValidationError, None]:
        """Validate plugin configuration against its schema.

        Args:
            plugin_name: Name of the plugin
            config_data: Configuration data to validate

        Returns:
            Validated model, ValidationError, or None if no schema
        """
        # Try to find schema for the plugin
        schema_info = None
        for name, info in self.loaded_schemas.items():
            if self._is_schema_for_plugin(name, plugin_name):
                schema_info = info
                break

        if not schema_info:
            self.logger.warning(f"No schema found for plugin {plugin_name}")
            return None

        return schema_info.validate_data(config_data)

    def get_schema_json(self, schema_name: str) -> Optional[Dict[str, Any]]:
        """Get JSON schema for a specific schema.

        Args:
            schema_name: Name of the schema

        Returns:
            JSON schema dictionary if found, None otherwise
        """
        schema_info = self.get_schema(schema_name)
        return schema_info.json_schema if schema_info else None

    def get_schemas_by_type(self, schema_type: str) -> Dict[str, SchemaInfo]:
        """Get all schemas of a specific type.

        Args:
            schema_type: Type of schemas to retrieve

        Returns:
            Dictionary of matching schemas
        """
        # Determine schema type from name patterns
        type_patterns = {
            "service": ["ServiceConfig", "Service", "Manager"],
            "environment": ["EnvironmentConfig", "Environment"],
            "test": ["TestConfig", "Test"],
            "experiment": ["ExperimentConfig", "Experiment"],
            "global": ["GlobalConfig", "Global"],
        }

        patterns = type_patterns.get(schema_type, [])
        matching_schemas = {}

        for name, schema_info in self.loaded_schemas.items():
            if any(pattern in name for pattern in patterns):
                matching_schemas[name] = schema_info

        return matching_schemas

    def refresh_schema(self, schema_name: str) -> bool:
        """Refresh a specific schema from its source file.

        Args:
            schema_name: Name of the schema to refresh

        Returns:
            True if successfully refreshed, False otherwise
        """
        schema_info = self.get_schema(schema_name)
        if not schema_info:
            return False

        try:
            # Reload the schema from its source file
            schemas = self._load_schemas_from_file(schema_info.source_file)

            if schema_name in schemas:
                self.loaded_schemas[schema_name] = schemas[schema_name]
                self.logger.info(f"Refreshed schema: {schema_name}")
                return True

            return False

        except Exception as e:
            self.logger.error(f"Failed to refresh schema {schema_name}: {e}")
            return False

    def _discover_schema_files(self) -> List[Path]:
        """Discover all schema files in the plugins directory.

        Returns:
            List of schema file paths
        """
        schema_files = []

        # Look for config_schema.py files
        for schema_file in self.plugins_base_dir.rglob("config_schema.py"):
            schema_files.append(schema_file)

        # Look for schema.py files
        for schema_file in self.plugins_base_dir.rglob("schema.py"):
            schema_files.append(schema_file)

        # Also check in the main config directory
        config_dir = self.plugins_base_dir.parent / "config"
        if config_dir.exists():
            for schema_file in config_dir.rglob("*_schema.py"):
                schema_files.append(schema_file)

        return schema_files

    def _find_schema_file_for_plugin(
        self, plugin_name: str, plugin_type: str
    ) -> Optional[Path]:
        """Find schema file for a specific plugin.

        Args:
            plugin_name: Name of the plugin
            plugin_type: Type of the plugin

        Returns:
            Path to schema file if found, None otherwise
        """
        # Build possible paths based on plugin type and name
        possible_paths = []

        if plugin_type in ["iut", "tester"]:
            # For service plugins, schema might be in protocol subdirectory
            if "/" in plugin_name:
                protocol, impl_name = plugin_name.split("/", 1)
                possible_paths.extend(
                    [
                        self.plugins_base_dir
                        / "services"
                        / plugin_type
                        / protocol
                        / impl_name
                        / "config_schema.py",
                        self.plugins_base_dir
                        / "services"
                        / plugin_type
                        / protocol
                        / impl_name
                        / "schema.py",
                    ]
                )
            else:
                possible_paths.extend(
                    [
                        self.plugins_base_dir
                        / "services"
                        / plugin_type
                        / plugin_name
                        / "config_schema.py",
                        self.plugins_base_dir
                        / "services"
                        / plugin_type
                        / plugin_name
                        / "schema.py",
                    ]
                )
        else:
            # For environment and protocol plugins
            base_dir = (
                self.plugins_base_dir / "environments"
                if "environment" in plugin_type
                else self.plugins_base_dir / "protocols"
            )
            possible_paths.extend(
                [
                    base_dir / plugin_name / "config_schema.py",
                    base_dir / plugin_name / "schema.py",
                ]
            )

        # Find the first existing file
        for path in possible_paths:
            if path.exists():
                return path

        return None

    def _load_schemas_from_file(self, schema_file: Path) -> Dict[str, SchemaInfo]:
        """Load schemas from a Python file.

        Args:
            schema_file: Path to schema file

        Returns:
            Dictionary mapping schema names to SchemaInfo objects
        """
        schemas = {}

        try:
            # Create module name from file path
            relative_path = schema_file.relative_to(self.plugins_base_dir.parent)
            module_name = (
                str(relative_path).replace("/", ".").replace("\\", ".")[:-3]
            )  # Remove .py

            # Import the module
            if module_name in self.import_cache:
                module = self.import_cache[module_name]
            else:
                try:
                    module = importlib.import_module(module_name)
                    self.import_cache[module_name] = module
                except ModuleNotFoundError:
                    # Try alternative import method
                    import sys

                    spec = importlib.util.spec_from_file_location(
                        module_name, schema_file
                    )
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[module_name] = module
                    spec.loader.exec_module(module)
                    self.import_cache[module_name] = module

            # Find all BaseModel classes in the module
            for attr_name in dir(module):
                attr = getattr(module, attr_name)

                if (
                    isinstance(attr, type)
                    and issubclass(attr, BaseModel)
                    and attr != BaseModel
                ):

                    schema_info = SchemaInfo(attr_name, attr, schema_file)
                    schemas[attr_name] = schema_info

        except Exception as e:
            self.logger.error(f"Failed to load schemas from {schema_file}: {e}")
            raise

        return schemas

    def _is_schema_for_plugin(self, schema_name: str, plugin_name: str) -> bool:
        """Check if a schema is for a specific plugin.

        Args:
            schema_name: Name of the schema
            plugin_name: Name of the plugin

        Returns:
            True if schema is for the plugin, False otherwise
        """
        # Simple heuristic: check if plugin name is in schema name
        # Handle nested plugin names (protocol/implementation)
        if "/" in plugin_name:
            _, impl_name = plugin_name.split("/", 1)
            return impl_name.lower() in schema_name.lower()
        else:
            return plugin_name.lower() in schema_name.lower()

    def _load_from_cache(self) -> bool:
        """Load schemas from cache file.

        Returns:
            True if successfully loaded from cache, False otherwise
        """
        if not self.schema_cache_file.exists():
            return False

        try:
            with open(self.schema_cache_file, "r", encoding="utf-8") as f:
                cache_data = json.load(f)

            # Check cache timestamp
            cache_timestamp = cache_data.get("timestamp", 0)

            # Check if any schema files are newer than cache
            schema_files = self._discover_schema_files()
            for schema_file in schema_files:
                if schema_file.stat().st_mtime > cache_timestamp:
                    return False

            # Cache is still valid - but we can't easily recreate SchemaInfo
            # objects with actual classes from JSON, so we'll skip caching
            # for now and always load fresh
            return False

        except Exception as e:
            self.logger.warning(f"Failed to load schema cache: {e}")
            return False

    def _save_to_cache(self) -> None:
        """Save schemas to cache file.

        Note: Currently disabled as schemas contain class references
        that can't be easily serialized to JSON.
        """
        # Caching is currently disabled for schemas due to the complexity
        # of serializing Pydantic model classes
        pass

    def get_schema_summary(self) -> Dict[str, Any]:
        """Get a summary of loaded schemas.

        Returns:
            Summary dictionary with counts and information
        """
        total_schemas = len(self.loaded_schemas)

        by_type = {}
        for schema_name, schema_info in self.loaded_schemas.items():
            # Categorize by common patterns in schema names
            if "Config" in schema_name:
                schema_type = "config"
            elif "Test" in schema_name:
                schema_type = "test"
            elif "Experiment" in schema_name:
                schema_type = "experiment"
            elif "Service" in schema_name:
                schema_type = "service"
            elif "Environment" in schema_name:
                schema_type = "environment"
            else:
                schema_type = "other"

            if schema_type not in by_type:
                by_type[schema_type] = 0
            by_type[schema_type] += 1

        return {
            "total_schemas": total_schemas,
            "by_type": by_type,
            "schema_names": list(self.loaded_schemas.keys()),
        }
