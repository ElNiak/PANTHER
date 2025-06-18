"""State management mixin for ConfigurationManager."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from panther.core.utils.logging_mixin import LoggerMixin


class HealthReport:
    """Configuration health check report."""
    
    def __init__(self):
        self.is_healthy = True
        self.issues: List[str] = []
        self.warnings: List[str] = []
        self.checks_passed: List[str] = []
    
    def add_issue(self, issue: str):
        """Add a health issue."""
        self.issues.append(issue)
        self.is_healthy = False
    
    def add_warning(self, warning: str):
        """Add a health warning."""
        self.warnings.append(warning)
    
    def add_passed(self, check: str):
        """Add a passed check."""
        self.checks_passed.append(check)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "is_healthy": self.is_healthy,
            "issues": self.issues,
            "warnings": self.warnings,
            "checks_passed": self.checks_passed,
            "summary": f"{len(self.checks_passed)} passed, {len(self.issues)} issues, {len(self.warnings)} warnings"
        }


class StateManagementMixin(LoggerMixin):
    """Handles configuration state and reporting."""
    
    def get_configuration_summary(self) -> Dict[str, Any]:
        """Get comprehensive configuration summary.
        
        Returns:
            Dictionary with configuration summary
        """
        summary = {
            "manager_state": {
                "experiment_file": getattr(self, 'experiment_file', None),
                "output_dir": getattr(self, 'output_dir', None),
                "debug_override": getattr(self, 'debug_override', False),
                "auto_fix_configs": getattr(self, 'auto_fix_configs', True),
                "enable_cache": getattr(self, 'enable_cache', True),
            },
            "loaded_configs": {
                "current_experiment": self.current_experiment_config is not None,
                "current_global": self.current_global_config is not None,
                "cached_experiments": len(getattr(self, '_loaded_experiments', {})),
            },
            "validation": {
                "last_validation_errors": len(getattr(self, '_validation_errors', [])),
                "strict_mode": getattr(self, '_strict_mode', False),
                "custom_validators": len(getattr(self, '_custom_validators', [])),
            },
            "plugins": self._get_plugin_summary(),
            "overrides": len(getattr(self, '_config_overrides', {})),
        }
        
        # Add cache statistics if available
        if hasattr(self, 'get_cache_statistics'):
            summary["cache"] = self.get_cache_statistics()
        
        return summary
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get detailed statistics about configuration manager.
        
        Returns:
            Dictionary with statistics
        """
        stats = {
            "configurations": {
                "experiments_loaded": len(getattr(self, '_loaded_experiments', {})),
                "validations_cached": len(getattr(self, '_validation_cache', {})),
                "total_validations": getattr(self, '_total_validations', 0),
                "validation_failures": getattr(self, '_validation_failures', 0),
            },
            "plugins": {
                "discovered": len(self.discover_plugins()) if hasattr(self, 'discover_plugins') else 0,
                "schemas_loaded": len(getattr(self, '_schema_cache', {})) if hasattr(self, '_schema_cache') else 0,
                "versions_discovered": len(getattr(self, '_version_cache', {})),
            },
            "performance": {
                "cache_enabled": getattr(self, 'enable_cache', True),
                "auto_fix_enabled": getattr(self, 'auto_fix_configs', True),
            }
        }
        
        # Add timing information if available
        if hasattr(self, '_timing_stats'):
            stats["timing"] = self._timing_stats
        
        return stats
    
    def get_validation_report(self) -> Dict[str, Any]:
        """Get detailed validation report.
        
        Returns:
            Validation report dictionary
        """
        report = {
            "validation_mode": "strict" if getattr(self, '_strict_mode', False) else "lenient",
            "last_validation": None,
            "validation_history": [],
            "common_errors": {},
            "auto_fixes_applied": getattr(self, '_auto_fixes_applied', 0),
        }
        
        # Add last validation result
        if hasattr(self, 'validation_results'):
            for config_name, result in self.validation_results.items():
                entry = {
                    "config": config_name,
                    "is_valid": result.is_valid,
                    "errors": len(result.errors),
                    "warnings": len(result.warnings),
                }
                report["validation_history"].append(entry)
                
                # Track common errors
                for error in result.errors:
                    error_type = error.field.split('.')[0] if '.' in error.field else error.field
                    report["common_errors"][error_type] = report["common_errors"].get(error_type, 0) + 1
        
        return report
    
    def export_configuration(self, format: str = "yaml") -> str:
        """Export current configuration state.
        
        Args:
            format: Export format ('yaml' or 'json')
            
        Returns:
            Exported configuration string
        """
        # Gather all configuration data
        export_data = {
            "manager_config": self.get_configuration_summary(),
            "global_config": None,
            "experiment_config": None,
        }
        
        # Add current configurations
        if hasattr(self, 'current_global_config') and self.current_global_config:
            export_data["global_config"] = self.current_global_config.to_dict()
        
        if hasattr(self, 'current_experiment_config') and self.current_experiment_config:
            export_data["experiment_config"] = self.current_experiment_config.to_dict()
        
        # Export in requested format
        if format == "yaml":
            return yaml.dump(export_data, default_flow_style=False, sort_keys=False)
        elif format == "json":
            return json.dumps(export_data, indent=2)
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def dump_configuration_state(self, output_dir: Path) -> None:
        """Dump complete configuration state to directory.
        
        Args:
            output_dir: Directory to dump state to
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger.info(f"Dumping configuration state to {output_dir}")
        
        # Export manager state
        (output_dir / "manager_state.yaml").write_text(
            yaml.dump(self.get_configuration_summary(), default_flow_style=False)
        )
        
        # Export statistics
        (output_dir / "statistics.json").write_text(
            json.dumps(self.get_statistics(), indent=2)
        )
        
        # Export validation report
        (output_dir / "validation_report.json").write_text(
            json.dumps(self.get_validation_report(), indent=2)
        )
        
        # Export current configurations
        if hasattr(self, 'current_global_config') and self.current_global_config:
            self.current_global_config.save(output_dir / "global_config.yaml")
        
        if hasattr(self, 'current_experiment_config') and self.current_experiment_config:
            self.current_experiment_config.save(output_dir / "experiment_config.yaml")
        
        # Export plugin information
        if hasattr(self, 'discover_plugins'):
            plugins = self.discover_plugins()
            plugin_data = {
                name: {
                    "type": meta.type,
                    "path": str(meta.path),
                    "protocol": meta.protocol,
                    "version": meta.version,
                    "description": meta.description,
                }
                for name, meta in plugins.items()
            }
            (output_dir / "plugins.yaml").write_text(
                yaml.dump(plugin_data, default_flow_style=False)
            )
        
        self.logger.info(f"Configuration state dumped successfully")
    
    def validate_all_plugins(self) -> Dict[str, 'ValidationResult']:
        """Validate all discovered plugins.
        
        Returns:
            Dictionary mapping plugin names to validation results
        """
        self.logger.info("Validating all plugins")
        
        results = {}
        
        if hasattr(self, 'discover_plugins'):
            plugins = self.discover_plugins()
            
            for plugin_name, metadata in plugins.items():
                try:
                    # Create minimal config for validation
                    test_config = {
                        "implementation": {
                            "name": plugin_name,
                            "type": metadata.type
                        }
                    }
                    
                    # Validate
                    result = self.validate_plugin_config(plugin_name, test_config)
                    results[plugin_name] = result
                except Exception as e:
                    from ..mixins.plugin_management import ValidationResult
                    result = ValidationResult(is_valid=False)
                    result.errors = [str(e)]
                    results[plugin_name] = result
        
        return results
    
    def check_configuration_health(self) -> HealthReport:
        """Perform comprehensive health check.
        
        Returns:
            Health report with issues and warnings
        """
        self.logger.info("Performing configuration health check")
        
        report = HealthReport()
        
        # Check required directories
        plugin_dir = getattr(self, 'panther_dir', Path.cwd()) / "panther" / "plugins"
        if not plugin_dir.exists():
            report.add_issue(f"Plugin directory not found: {plugin_dir}")
        else:
            report.add_passed("Plugin directory exists")
        
        # Check configuration files
        if hasattr(self, 'experiment_file') and self.experiment_file:
            if not Path(self.experiment_file).exists():
                report.add_issue(f"Experiment file not found: {self.experiment_file}")
            else:
                report.add_passed("Experiment file exists")
        
        # Check plugin discovery
        try:
            if hasattr(self, 'discover_plugins'):
                plugins = self.discover_plugins()
                if not plugins:
                    report.add_warning("No plugins discovered")
                else:
                    report.add_passed(f"Discovered {len(plugins)} plugins")
        except Exception as e:
            report.add_issue(f"Plugin discovery failed: {e}")
        
        # Check cache health
        if hasattr(self, 'get_cache_statistics'):
            cache_stats = self.get_cache_statistics()
            hit_rate = float(cache_stats['hit_rate'].rstrip('%'))
            if hit_rate < 50:
                report.add_warning(f"Low cache hit rate: {hit_rate}%")
            else:
                report.add_passed(f"Good cache hit rate: {hit_rate}%")
        
        # Check validation status
        if hasattr(self, 'validation_results'):
            failed_validations = sum(
                1 for result in self.validation_results.values()
                if not result.is_valid
            )
            if failed_validations > 0:
                report.add_warning(f"{failed_validations} configurations failed validation")
            else:
                report.add_passed("All configurations validated successfully")
        
        return report
    
    def _get_plugin_summary(self) -> Dict[str, Any]:
        """Get plugin summary for configuration summary.
        
        Returns:
            Plugin summary dictionary
        """
        summary = {
            "discovered": 0,
            "by_type": {},
            "with_schemas": 0,
        }
        
        if hasattr(self, 'discover_plugins'):
            try:
                plugins = self.discover_plugins()
                summary["discovered"] = len(plugins)
                
                # Count by type
                for plugin in plugins.values():
                    plugin_type = plugin.type
                    summary["by_type"][plugin_type] = summary["by_type"].get(plugin_type, 0) + 1
                
                # Count with schemas
                if hasattr(self, 'load_plugin_schemas'):
                    schemas = self.load_plugin_schemas()
                    summary["with_schemas"] = len(schemas)
            except Exception as e:
                self.logger.warning(f"Failed to get plugin summary: {e}")
        
        return summary