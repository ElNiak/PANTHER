"""
Automatic conversion between PluginManifest and PluginMetadata.

This module uses reflection to automatically discover and map fields between
the two structures, preventing field loss and reducing maintenance burden.
"""

import logging
from dataclasses import fields, is_dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Type, TypeVar, Union, get_type_hints

from panther.plugins.core.structures.plugin_manifest import PluginManifest
from panther.plugins.core.structures.plugin_metadata import PluginMetadata
from panther.plugins.core.structures.plugin_type import PluginType

T = TypeVar("T")
U = TypeVar("U")


class FieldConverter:
    """Handles conversion of specific field types."""

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.FieldConverter")
        self.type_converters: Dict[str, Callable] = {
            # Handle PluginType enum conversions
            "PluginType_to_str": lambda x: x.value if hasattr(x, "value") else str(x),
            "str_to_PluginType": self._safe_plugin_type_conversion,
            # Handle Path conversions
            "Path_to_str": lambda x: str(x) if x else None,
            "str_to_Path": lambda x: Path(x) if x else None,
            # Handle list conversions
            "list_normalize": lambda x: x or [],
            # Handle dict conversions
            "dict_normalize": lambda x: x or {},
        }

    def _safe_plugin_type_conversion(self, value: Any) -> Union[PluginType, str]:
        """Safely convert string to PluginType enum."""
        if isinstance(value, str):
            try:
                # Try direct conversion first
                return PluginType(value)
            except ValueError:
                # Try uppercase conversion
                try:
                    return PluginType(value.upper())
                except ValueError:
                    self.logger.warning(
                        f"Could not convert '{value}' to PluginType, keeping as string"
                    )
                    return value
        return value

    def convert_value(
        self, value: Any, source_type: Type, target_type: Type, field_name: str
    ) -> Any:
        """Convert value from source type to target type."""
        if value is None:
            return None

        # Handle identical types
        if source_type == target_type:
            return value

        # Handle PluginType conversions
        if source_type == PluginType and target_type == str:
            return self.type_converters["PluginType_to_str"](value)
        elif source_type == str and target_type == PluginType:
            return self.type_converters["str_to_PluginType"](value)

        # Handle Path conversions
        elif source_type == Path and target_type == str:
            return self.type_converters["Path_to_str"](value)
        elif source_type == str and target_type == Path:
            return self.type_converters["str_to_Path"](value)

        # Handle collections
        elif hasattr(target_type, "__origin__"):
            if target_type.__origin__ == list:
                return self.type_converters["list_normalize"](value)
            elif target_type.__origin__ == dict:
                return self.type_converters["dict_normalize"](value)

        # Default: return as-is
        self.logger.debug(
            f"No specific converter for {field_name}: {source_type} -> {target_type}"
        )
        return value


class PluginStructureConverter:
    """
    Automatically converts between PluginManifest and PluginMetadata
    using reflection to discover common fields.
    """

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.PluginStructureConverter")
        self.field_converter = FieldConverter()
        self._manifest_fields = None
        self._metadata_fields = None
        self._manifest_type_hints = None
        self._metadata_type_hints = None

    @property
    def manifest_fields(self) -> Dict[str, Any]:
        """Get PluginManifest dataclass fields."""
        if self._manifest_fields is None:
            self._manifest_fields = {f.name: f for f in fields(PluginManifest)}
        return self._manifest_fields

    @property
    def metadata_fields(self) -> Dict[str, Any]:
        """Get PluginMetadata dataclass fields."""
        if self._metadata_fields is None:
            self._metadata_fields = {f.name: f for f in fields(PluginMetadata)}
        return self._metadata_fields

    @property
    def manifest_type_hints(self) -> Dict[str, Type]:
        """Get PluginManifest type hints."""
        if self._manifest_type_hints is None:
            self._manifest_type_hints = get_type_hints(PluginManifest)
        return self._manifest_type_hints

    @property
    def metadata_type_hints(self) -> Dict[str, Type]:
        """Get PluginMetadata type hints."""
        if self._metadata_type_hints is None:
            self._metadata_type_hints = get_type_hints(PluginMetadata)
        return self._metadata_type_hints

    def manifest_to_metadata(self, manifest: PluginManifest) -> PluginMetadata:
        """Convert PluginManifest to PluginMetadata with auto field mapping."""

        self.logger.debug(f"Converting manifest to metadata: {manifest.name}")

        # Find common fields between both structures
        common_fields = set(self.manifest_fields.keys()) & set(
            self.metadata_fields.keys()
        )
        conversion_data = {}

        for field_name in common_fields:
            manifest_value = getattr(manifest, field_name, None)

            # Get type information
            source_type = self.manifest_type_hints.get(field_name, type(manifest_value))
            target_type = self.metadata_type_hints.get(field_name, type(manifest_value))

            # Convert value to appropriate type for metadata
            converted_value = self.field_converter.convert_value(
                manifest_value,
                source_type,
                target_type,
                f"manifest->metadata: {field_name}",
            )
            conversion_data[field_name] = converted_value

            self.logger.debug(
                f"Mapped field {field_name}: {type(manifest_value)} -> {type(converted_value)}"
            )

        # Handle special mappings for fields that don't match exactly
        self._apply_special_mappings_to_metadata(manifest, conversion_data)

        # Validate we're not missing critical fields
        self._validate_metadata_conversion(conversion_data, manifest.name)

        self.logger.debug(
            f"Successfully converted manifest {manifest.name} to metadata"
        )
        return PluginMetadata(**conversion_data)

    def metadata_to_manifest(self, metadata: PluginMetadata) -> PluginManifest:
        """Convert PluginMetadata to PluginManifest with auto field mapping."""

        self.logger.debug(f"Converting metadata to manifest: {metadata.name}")

        # Find common fields
        common_fields = set(self.manifest_fields.keys()) & set(
            self.metadata_fields.keys()
        )
        conversion_data = {}

        for field_name in common_fields:
            metadata_value = getattr(metadata, field_name, None)

            # Get type information
            source_type = self.metadata_type_hints.get(field_name, type(metadata_value))
            target_type = self.manifest_type_hints.get(field_name, type(metadata_value))

            # Convert value to appropriate type for manifest
            converted_value = self.field_converter.convert_value(
                metadata_value,
                source_type,
                target_type,
                f"metadata->manifest: {field_name}",
            )
            conversion_data[field_name] = converted_value

            self.logger.debug(
                f"Mapped field {field_name}: {type(metadata_value)} -> {type(converted_value)}"
            )

        # Handle special mappings and required fields for manifest
        self._apply_special_mappings_to_manifest(metadata, conversion_data)

        # Validate conversion
        self._validate_manifest_conversion(conversion_data, metadata.name)

        self.logger.debug(
            f"Successfully converted metadata {metadata.name} to manifest"
        )
        return PluginManifest(**conversion_data)

    def _apply_special_mappings_to_metadata(
        self, manifest: PluginManifest, data: Dict[str, Any]
    ):
        """Handle special field mappings when converting to metadata."""

        # Handle dependencies conversion (PluginDependency objects to strings)
        if hasattr(manifest, "dependencies") and manifest.dependencies:
            deps = []
            for dep in manifest.dependencies:
                if hasattr(dep, "name"):
                    deps.append(dep.name)
                else:
                    deps.append(str(dep))
            data["dependencies"] = deps
            self.logger.debug(f"Converted {len(deps)} dependencies to strings")

        # Ensure path is Path object (metadata uses 'path', manifest uses 'file_path')
        # Read from manifest directly since file_path/path name mismatch means
        # the common-fields loop never adds file_path to data.
        if hasattr(manifest, "file_path") and manifest.file_path:
            data["path"] = (
                Path(manifest.file_path)
                if isinstance(manifest.file_path, str)
                else manifest.file_path
            )
            data.pop("file_path", None)
            self.logger.debug("Converted file_path to path for metadata")
        elif "file_path" in data and data["file_path"]:
            data["path"] = (
                Path(data["file_path"])
                if isinstance(data["file_path"], str)
                else data["file_path"]
            )
            data.pop("file_path", None)
            self.logger.debug("Converted file_path to path for metadata (from data)")

        # Ensure runtime_mode is preserved from manifest to metadata
        if hasattr(manifest, "runtime_mode") and manifest.runtime_mode:
            data["runtime_mode"] = manifest.runtime_mode
            self.logger.debug(
                f"Preserved runtime_mode '{manifest.runtime_mode}' in metadata conversion"
            )

    def _apply_special_mappings_to_manifest(
        self, metadata: PluginMetadata, data: Dict[str, Any]
    ):
        """Handle special field mappings when converting to manifest."""

        # Convert string dependencies to PluginDependency objects
        if hasattr(metadata, "dependencies") and metadata.dependencies:
            from panther.plugins.core.structures.plugin_dependency import (
                PluginDependency,
            )

            deps = []
            for dep in metadata.dependencies:
                if isinstance(dep, str):
                    deps.append(PluginDependency(name=dep, version_spec="*"))
                else:
                    deps.append(dep)
            data["dependencies"] = deps
            self.logger.debug(
                f"Converted {len(deps)} dependencies to PluginDependency objects"
            )

        # Convert path to file_path string (manifest uses 'file_path', metadata uses 'path')
        if hasattr(metadata, "path") and metadata.path:
            data["file_path"] = str(metadata.path)
            # Remove path as manifest doesn't have this field with that name
            if "path" in data and "file_path" in self.manifest_fields:
                data.pop("path", None)
                self.logger.debug("Converted path to file_path for manifest")

        # Ensure runtime_mode is preserved from metadata to manifest
        if hasattr(metadata, "runtime_mode") and metadata.runtime_mode:
            data["runtime_mode"] = metadata.runtime_mode
            self.logger.debug(
                f"Preserved runtime_mode '{metadata.runtime_mode}' in manifest conversion"
            )

        # Ensure required fields have defaults
        data.setdefault("config_schema", {})
        data.setdefault("default_config", {})
        data.setdefault("dependencies", [])
        data.setdefault("supported_protocols", [])
        data.setdefault("capabilities", [])
        data.setdefault("tags", [])
        data.setdefault("external_dependencies", [])

        self.logger.debug("Applied default values for required manifest fields")

    def _validate_metadata_conversion(self, data: Dict[str, Any], plugin_name: str):
        """Validate that metadata conversion includes required fields."""
        required_fields = {"name", "type", "version"}
        missing = required_fields - set(data.keys())
        if missing:
            raise ValueError(
                f"Missing required fields for PluginMetadata ({plugin_name}): {missing}"
            )

        # Validate types
        if "name" in data and not isinstance(data["name"], str):
            raise ValueError(
                f"Invalid type for 'name' in PluginMetadata ({plugin_name}): expected str, got {type(data['name'])}"
            )

        self.logger.debug(f"Validated metadata conversion for {plugin_name}")

    def _validate_manifest_conversion(self, data: Dict[str, Any], plugin_name: str):
        """Validate that manifest conversion includes required fields."""
        required_fields = {"name", "type", "version"}
        if missing := required_fields - set(data.keys()):
            raise ValueError(
                f"Missing required fields for PluginManifest ({plugin_name}): {missing}"
            )

        # Validate types
        if "name" in data and not isinstance(data["name"], str):
            raise ValueError(
                f"Invalid type for 'name' in PluginManifest ({plugin_name}): expected str, got {type(data['name'])}"
            )

        # Ensure type is PluginType enum for manifest
        if "type" in data and isinstance(data["type"], str):
            try:
                data["type"] = PluginType(data["type"])
            except ValueError:
                data["type"] = PluginType(data["type"].upper())

        self.logger.debug(f"Validated manifest conversion for {plugin_name}")

    def get_field_mapping_report(self) -> Dict[str, Any]:
        """Generate a report of field mappings between the two structures."""
        manifest_fields = set(self.manifest_fields.keys())
        metadata_fields = set(self.metadata_fields.keys())

        common_fields = manifest_fields & metadata_fields
        manifest_only = manifest_fields - metadata_fields
        metadata_only = metadata_fields - manifest_fields

        report = {
            "common_fields": sorted(common_fields),
            "manifest_only_fields": sorted(manifest_only),
            "metadata_only_fields": sorted(metadata_only),
            "field_count": {
                "manifest": len(manifest_fields),
                "metadata": len(metadata_fields),
                "common": len(common_fields),
            },
            "coverage": {
                "manifest_coverage": len(common_fields) / len(manifest_fields)
                if manifest_fields
                else 0,
                "metadata_coverage": len(common_fields) / len(metadata_fields)
                if metadata_fields
                else 0,
            },
        }

        return report


# Global converter instance
_converter = PluginStructureConverter()


def auto_convert_manifest_to_metadata(manifest: PluginManifest) -> PluginMetadata:
    """Convenience function for automatic manifest to metadata conversion."""
    return _converter.manifest_to_metadata(manifest)


def auto_convert_metadata_to_manifest(metadata: PluginMetadata) -> PluginManifest:
    """Convenience function for automatic metadata to manifest conversion."""
    return _converter.metadata_to_manifest(metadata)


def get_field_mapping_report() -> Dict[str, Any]:
    """Get a report of field mappings between PluginManifest and PluginMetadata."""
    return _converter.get_field_mapping_report()
