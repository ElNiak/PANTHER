# Plugin Platform Declaration System Design

## Overview

Design for a comprehensive system allowing PANTHER plugins to declare supported platforms, build modes, and runtime configurations. This addresses the need for explicit platform compatibility declarations and validation before Docker builds.

## Current Platform Analysis

**From docker_builder.py analysis:**
- **Host Detection**: `linux/amd64`, `linux/arm64` (with fallback to amd64)
- **Target Platform**: Configurable via `global_config.docker.target_platform`
- **Build Mode Restrictions**: Advanced modes (`rel-lto`, `debug-asan`, `release-static-pgo`) require x86 architecture
- **Buildx Usage**: Automatic for cross-platform builds

## 1. Plugin Manifest Structure

```python
# plugin_manifest.py or plugin_config.yaml
PLUGIN_MANIFEST = {
    "name": "picoquic",
    "version": "1.0.0",
    "supported_platforms": {
        "linux/amd64": {
            "status": "fully_supported",
            "build_modes": ["", "debug-asan", "rel-lto", "release-static-pgo"],
            "runtime_modes": ["minimal", "debug", "profile"],
            "dockerfile": "Dockerfile",
            "requirements": {
                "min_memory": "512MB",
                "architecture_features": ["sse4.2"]
            }
        },
        "linux/arm64": {
            "status": "limited_support",
            "build_modes": [""],  # Only basic build mode
            "runtime_modes": ["minimal", "debug"],
            "dockerfile": "Dockerfile.arm64",
            "limitations": ["no_advanced_optimizations", "reduced_performance"],
            "requirements": {
                "min_memory": "1GB"  # May need more memory on ARM
            }
        },
        "darwin/amd64": {
            "status": "experimental",
            "build_modes": [""],
            "runtime_modes": ["minimal"],
            "dockerfile": "Dockerfile.macos",
            "warnings": ["not_tested_in_production"]
        }
    },
    "fallback_strategy": {
        "unsupported_platform": "error",  # or "warn", "emulate"
        "unsupported_build_mode": "fallback_to_basic",
        "unsupported_runtime_mode": "fallback_to_minimal"
    }
}
```

## 2. Platform Declaration Methods

### Option A: Declarative YAML/JSON
```yaml
# plugins/services/iut/picoquic/platform_support.yaml
platforms:
  linux/amd64:
    support_level: full
    build_modes: [debug-asan, rel-lto, release-static-pgo]
    dockerfile_variants:
      default: Dockerfile
      buildkit: Dockerfile.buildkit
  linux/arm64:
    support_level: basic
    build_modes: []
    dockerfile_variants:
      default: Dockerfile.arm64
    notes: "Limited optimization support"
```

### Option B: Python Class Protocol
```python
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from enum import Enum

class PlatformSupportLevel(Enum):
    FULLY_SUPPORTED = "fully_supported"
    LIMITED_SUPPORT = "limited_support"
    EXPERIMENTAL = "experimental"
    NOT_SUPPORTED = "not_supported"

class PlatformRequirements:
    def __init__(self,
                 min_memory: str = "512MB",
                 architecture_features: List[str] = None,
                 docker_version: str = "20.10+"):
        self.min_memory = min_memory
        self.architecture_features = architecture_features or []
        self.docker_version = docker_version

class PlatformSupportInfo:
    def __init__(self,
                 support_level: PlatformSupportLevel,
                 build_modes: List[str],
                 runtime_modes: List[str],
                 dockerfile: str = "Dockerfile",
                 requirements: Optional[PlatformRequirements] = None,
                 limitations: List[str] = None,
                 warnings: List[str] = None):
        self.support_level = support_level
        self.build_modes = build_modes
        self.runtime_modes = runtime_modes
        self.dockerfile = dockerfile
        self.requirements = requirements or PlatformRequirements()
        self.limitations = limitations or []
        self.warnings = warnings or []

class PlatformSupportMixin(ABC):
    @abstractmethod
    def get_supported_platforms(self) -> Dict[str, PlatformSupportInfo]:
        """Return dictionary of platform -> support info."""
        pass

    def is_platform_supported(self, platform: str) -> bool:
        """Check if platform is supported at any level."""
        platforms = self.get_supported_platforms()
        return platform in platforms and \
               platforms[platform].support_level != PlatformSupportLevel.NOT_SUPPORTED

    def get_platform_dockerfile(self, platform: str) -> Optional[str]:
        """Get appropriate Dockerfile for platform."""
        platforms = self.get_supported_platforms()
        if platform in platforms:
            return platforms[platform].dockerfile
        return None

    def validate_build_configuration(self, platform: str, build_mode: str, runtime_mode: str) -> Dict[str, any]:
        """Validate if build configuration is supported on platform."""
        platforms = self.get_supported_platforms()
        if platform not in platforms:
            return {
                "valid": False,
                "error": f"Platform {platform} not supported",
                "suggestions": list(platforms.keys())
            }

        platform_info = platforms[platform]

        # Check build mode support
        if build_mode and build_mode not in platform_info.build_modes:
            return {
                "valid": False,
                "error": f"Build mode '{build_mode}' not supported on {platform}",
                "suggestions": platform_info.build_modes,
                "fallback": "" if "" in platform_info.build_modes else None
            }

        # Check runtime mode support
        if runtime_mode not in platform_info.runtime_modes:
            return {
                "valid": False,
                "error": f"Runtime mode '{runtime_mode}' not supported on {platform}",
                "suggestions": platform_info.runtime_modes,
                "fallback": "minimal" if "minimal" in platform_info.runtime_modes else platform_info.runtime_modes[0]
            }

        return {
            "valid": True,
            "warnings": platform_info.warnings,
            "limitations": platform_info.limitations
        }
```

## 3. Integration with DockerBuilder

```python
# Enhancement to docker_builder.py
class DockerBuilder(DockerBuildCacheMixin, LoggerMixin, ErrorHandlerMixin):

    def validate_plugin_platform_support(self, plugin, target_platform: str, build_mode: str, runtime_mode: str):
        """Validate plugin supports the target platform and modes."""
        if not hasattr(plugin, 'get_supported_platforms'):
            self.logger.warning(f"Plugin {plugin.name} doesn't declare platform support - assuming basic compatibility")
            return {"valid": True, "warnings": ["platform_support_unknown"]}

        return plugin.validate_build_configuration(target_platform, build_mode, runtime_mode)

    def select_dockerfile_for_platform(self, plugin, target_platform: str) -> str:
        """Select appropriate Dockerfile variant for target platform."""
        if hasattr(plugin, 'get_platform_dockerfile'):
            dockerfile = plugin.get_platform_dockerfile(target_platform)
            if dockerfile:
                return dockerfile

        # Fallback to standard Dockerfile discovery
        return "Dockerfile"

    def build_image_with_platform_validation(self, impl_name: str, plugin, config: Dict[str, Any], **kwargs):
        """Enhanced build_image with platform validation."""
        target_platform = self._get_target_platform()
        build_mode = config.get("build_mode", "")
        runtime_mode = config.get("runtime_mode", "minimal")

        # Validate platform support
        validation_result = self.validate_plugin_platform_support(
            plugin, target_platform, build_mode, runtime_mode
        )

        if not validation_result["valid"]:
            # Handle fallback strategies
            if "fallback" in validation_result:
                self.logger.warning(f"Falling back: {validation_result['error']} -> using {validation_result['fallback']}")
                if "build_mode" in validation_result["error"]:
                    config["build_mode"] = validation_result["fallback"]
                elif "runtime_mode" in validation_result["error"]:
                    config["runtime_mode"] = validation_result["fallback"]
            else:
                raise PlatformNotSupportedException(
                    f"Plugin {impl_name}: {validation_result['error']}",
                    suggestions=validation_result.get("suggestions", [])
                )

        # Log warnings and limitations
        for warning in validation_result.get("warnings", []):
            self.logger.warning(f"Platform warning for {impl_name}: {warning}")

        for limitation in validation_result.get("limitations", []):
            self.logger.info(f"Platform limitation for {impl_name}: {limitation}")

        # Use platform-specific Dockerfile if available
        dockerfile_name = self.select_dockerfile_for_platform(plugin, target_platform)

        return self.build_image(impl_name, config=config, dockerfile_name=dockerfile_name, **kwargs)
```

## 4. Example Plugin Implementation

```python
class PicoquicPlugin(PlatformSupportMixin):
    def get_supported_platforms(self) -> Dict[str, PlatformSupportInfo]:
        return {
            "linux/amd64": PlatformSupportInfo(
                support_level=PlatformSupportLevel.FULLY_SUPPORTED,
                build_modes=["", "debug-asan", "rel-lto", "release-static-pgo"],
                runtime_modes=["minimal", "debug", "profile"],
                dockerfile="Dockerfile",
                requirements=PlatformRequirements(
                    min_memory="512MB",
                    architecture_features=["sse4.2"]
                )
            ),
            "linux/arm64": PlatformSupportInfo(
                support_level=PlatformSupportLevel.LIMITED_SUPPORT,
                build_modes=[""],  # Only basic build
                runtime_modes=["minimal", "debug"],
                dockerfile="Dockerfile.arm64",
                limitations=["no_lto_optimizations", "reduced_performance"],
                requirements=PlatformRequirements(min_memory="1GB")
            )
        }
```

## 5. Usage Examples

```python
# During plugin loading
plugin = PicoquicPlugin()
target_platform = "linux/arm64"
build_mode = "rel-lto"  # This would fail validation

validation = plugin.validate_build_configuration(target_platform, build_mode, "minimal")
# Returns: {"valid": False, "error": "Build mode 'rel-lto' not supported on linux/arm64", "fallback": ""}

# Docker builder usage
try:
    image_tag = docker_builder.build_image_with_platform_validation(
        impl_name="picoquic",
        plugin=plugin,
        config={"build_mode": "rel-lto", "runtime_mode": "minimal"}
    )
except PlatformNotSupportedException as e:
    print(f"Platform issue: {e}")
    print(f"Supported platforms: {e.suggestions}")
```

## 6. Discovery and Registry

```python
class PlatformSupportRegistry:
    def __init__(self):
        self.plugins = {}

    def register_plugin(self, plugin_name: str, plugin):
        """Register plugin and validate platform declarations."""
        if hasattr(plugin, 'get_supported_platforms'):
            platforms = plugin.get_supported_platforms()
            self.logger.info(f"Plugin {plugin_name} supports platforms: {list(platforms.keys())}")

        self.plugins[plugin_name] = plugin

    def get_plugins_for_platform(self, platform: str) -> List[str]:
        """Get list of plugins that support given platform."""
        compatible_plugins = []
        for name, plugin in self.plugins.items():
            if hasattr(plugin, 'is_platform_supported') and plugin.is_platform_supported(platform):
                compatible_plugins.append(name)
        return compatible_plugins

    def generate_platform_compatibility_report(self) -> Dict[str, any]:
        """Generate comprehensive platform support report."""
        report = {
            "supported_platforms": set(),
            "plugin_compatibility": {},
            "platform_coverage": {}
        }

        for plugin_name, plugin in self.plugins.items():
            if hasattr(plugin, 'get_supported_platforms'):
                platforms = plugin.get_supported_platforms()
                report["plugin_compatibility"][plugin_name] = {
                    platform: info.support_level.value
                    for platform, info in platforms.items()
                }
                report["supported_platforms"].update(platforms.keys())

        # Calculate which platforms have good coverage
        for platform in report["supported_platforms"]:
            supporting_plugins = self.get_plugins_for_platform(platform)
            report["platform_coverage"][platform] = {
                "plugin_count": len(supporting_plugins),
                "plugins": supporting_plugins
            }

        return report
```

## Implementation Benefits

This design provides:

1. **Declarative Support**: Plugins explicitly declare platform capabilities
2. **Validation**: Automatic validation before builds
3. **Graceful Fallbacks**: Configurable fallback strategies
4. **Discovery**: Easy way to find platform-compatible plugins
5. **Reporting**: Comprehensive platform compatibility overview
6. **Flexibility**: Support for experimental/limited platform support

## Implementation Phases

### Phase 1: Core Infrastructure
- Implement `PlatformSupportMixin` and related classes
- Add validation methods to `DockerBuilder`
- Create platform compatibility exceptions

### Phase 2: Plugin Integration
- Update existing plugins to declare platform support
- Implement platform-specific Dockerfile selection
- Add fallback strategy handling

### Phase 3: Discovery and Tooling
- Implement `PlatformSupportRegistry`
- Add CLI commands for platform compatibility reporting
- Create documentation generation tools

### Phase 4: Advanced Features
- Add automatic platform capability detection
- Implement cross-compilation support
- Add performance optimization recommendations per platform

## Future Considerations

- **Dynamic Platform Detection**: Automatically detect plugin capabilities
- **Performance Profiles**: Platform-specific performance characteristics
- **Resource Requirements**: Memory, CPU, and storage requirements per platform
- **Cross-Compilation**: Support for building on one platform for another
- **Cloud Platform Support**: Extensions for cloud-specific optimizations
