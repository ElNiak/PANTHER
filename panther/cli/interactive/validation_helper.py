"""
Enhanced validation helper for PANTHER configurations.

Provides detailed error messages and suggestions for fixing common issues.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml
from omegaconf import DictConfig, OmegaConf, ValidationError


class ValidationHelper:
    """Provides enhanced validation with helpful error messages."""

    # Common validation errors and their solutions
    ERROR_SOLUTIONS = {
        "Plugin not found": {
            "cause": "The specified plugin does not exist or is not installed",
            "solutions": [
                "Check the plugin name spelling",
                "Use 'panther plugins list' to see available plugins",
                "Ensure the plugin is in the correct directory",
                "Check if the plugin type is correct (iut vs testers)",
            ],
        },
        "Invalid parameter": {
            "cause": "A parameter provided is not valid for this plugin",
            "solutions": [
                "Use 'panther plugins params <plugin_name>' to see valid parameters",
                "Check the parameter name spelling",
                "Verify the parameter type (string, number, boolean)",
                "Remove any extra parameters not supported by the plugin",
            ],
        },
        "Missing required field": {
            "cause": "A required configuration field is missing",
            "solutions": [
                "Add the missing field to your configuration",
                "Check the schema documentation for required fields",
                "Use a template as a starting point",
            ],
        },
        "Port conflict": {
            "cause": "Multiple services are trying to use the same port",
            "solutions": [
                "Use different port mappings for each service",
                "Check that host ports don't conflict",
                "Consider using automatic port assignment",
            ],
        },
        "Service target not found": {
            "cause": "A client service references a server that doesn't exist",
            "solutions": [
                "Check the target service name spelling",
                "Ensure the target service is defined before the client",
                "Verify the service names match exactly",
            ],
        },
        "Invalid role": {
            "cause": "The service role is not valid for the protocol",
            "solutions": [
                "Use 'client' or 'server' as the role",
                "For client services, specify a 'target' server",
                "Check protocol-specific role requirements",
            ],
        },
    }

    @staticmethod
    def get_available_plugins(plugin_type: str, base_path: Path) -> List[str]:
        """Get list of available plugins for a given type."""
        plugins = []

        if plugin_type == "network_environment":
            plugin_dir = base_path / "plugins" / "environments" / "network_environment"
        elif plugin_type == "execution_environment":
            plugin_dir = (
                base_path / "plugins" / "environments" / "execution_environment"
            )
        elif plugin_type == "iut":
            plugin_dir = base_path / "plugins" / "services" / "iut"
        elif plugin_type == "testers":
            plugin_dir = base_path / "plugins" / "services" / "testers"
        else:
            return plugins

        if plugin_dir.exists():
            for item in plugin_dir.iterdir():
                if item.is_dir() and not item.name.startswith("__"):
                    # For protocol-specific services, check subdirectories
                    if plugin_type in ["iut", "testers"] and item.name in [
                        "quic",
                        "http",
                        "minip",
                    ]:
                        for sub_item in item.iterdir():
                            if sub_item.is_dir() and not sub_item.name.startswith("__"):
                                plugins.append(f"{item.name}/{sub_item.name}")
                    else:
                        plugins.append(item.name)

        return sorted(plugins)

    @staticmethod
    def validate_service_relationships(services: Dict[str, Any]) -> List[str]:
        """Validate service relationships and dependencies."""
        errors = []

        # Check for client-server relationships
        for service_name, service_config in services.items():
            if service_config.get("protocol", {}).get("role") == "client":
                target = service_config.get("protocol", {}).get("target")
                if not target:
                    errors.append(
                        f"Client service '{service_name}' missing 'target' field"
                    )
                elif target not in services:
                    errors.append(
                        f"Client service '{service_name}' targets non-existent service '{target}'"
                    )
                    errors.append(f"  Available services: {', '.join(services.keys())}")

        # Check for port conflicts
        used_ports = {}
        for service_name, service_config in services.items():
            if "ports" in service_config:
                for port_mapping in service_config["ports"]:
                    if ":" in port_mapping:
                        host_port = port_mapping.split(":")[0]
                        if host_port in used_ports:
                            errors.append(
                                f"Port conflict: {host_port} used by both '{used_ports[host_port]}' and '{service_name}'"
                            )
                        else:
                            used_ports[host_port] = service_name

        return errors

    @staticmethod
    def explain_validation_error(error: ValidationError) -> str:
        """Convert validation error to user-friendly explanation."""
        error_str = str(error)
        explanation = [f"❌ Validation Error: {error_str}"]

        # Try to match known error patterns
        for error_type, info in ValidationHelper.ERROR_SOLUTIONS.items():
            if error_type.lower() in error_str.lower():
                explanation.append(f"\n🔍 Cause: {info['cause']}")
                explanation.append("\n💡 Solutions:")
                for solution in info["solutions"]:
                    explanation.append(f"   • {solution}")
                break
        else:
            # Generic advice if no specific pattern matches
            explanation.append("\n💡 General solutions:")
            explanation.append("   • Check the YAML syntax is valid")
            explanation.append("   • Verify all required fields are present")
            explanation.append(
                "   • Use 'panther config schema' to see the expected structure"
            )
            explanation.append(
                "   • Start with a working template using 'panther config generate'"
            )

        return "\n".join(explanation)

    @staticmethod
    def suggest_fixes(config_dict: dict, error: Exception) -> List[str]:
        """Suggest specific fixes based on the configuration and error."""
        suggestions = []
        error_str = str(error).lower()

        # Plugin-related suggestions
        if "plugin" in error_str and "not found" in error_str:
            # Try to extract plugin name from error
            import re

            match = re.search(r"plugin['\"]?\s*:\s*['\"]?(\w+)", error_str)
            if match:
                plugin_name = match.group(1)
                suggestions.append(f"Did you mean one of these plugins?")
                # This would need actual plugin discovery
                suggestions.append("  • picoquic (C-based QUIC implementation)")
                suggestions.append("  • aioquic (Python async QUIC implementation)")
                suggestions.append("  • panther_ivy (Formal protocol tester)")

        # Missing field suggestions
        if "missing" in error_str or "required" in error_str:
            suggestions.append("Add the missing required fields to your configuration")
            suggestions.append("Example minimal service configuration:")
            suggestions.append("  services:")
            suggestions.append("    server:")
            suggestions.append("      implementation:")
            suggestions.append("        name: picoquic")
            suggestions.append("        type: iut")
            suggestions.append("      protocol:")
            suggestions.append("        name: quic")
            suggestions.append("        version: rfc9000")
            suggestions.append("        role: server")

        return suggestions

    @staticmethod
    def validate_with_explanation(config_path: Path) -> Tuple[bool, List[str]]:
        """Validate configuration and return detailed explanations."""
        explanations = []

        try:
            # Load YAML
            with open(config_path, "r") as f:
                config_dict = yaml.safe_load(f)

            # Basic structure validation
            if not config_dict:
                explanations.append("❌ Configuration file is empty")
                return False, explanations

            if "tests" not in config_dict:
                explanations.append("❌ Missing 'tests' section - this is required")
                explanations.append("💡 Add at least one test configuration:")
                explanations.append("   tests:")
                explanations.append("     - name: 'My Test'")
                explanations.append("       services: {}")
                return False, explanations

            # Validate each test
            for i, test in enumerate(config_dict.get("tests", [])):
                test_name = test.get("name", f"Test {i+1}")

                # Check services
                if "services" not in test:
                    explanations.append(
                        f"⚠️  Test '{test_name}' has no services defined"
                    )
                else:
                    service_errors = ValidationHelper.validate_service_relationships(
                        test["services"]
                    )
                    if service_errors:
                        explanations.append(
                            f"❌ Service configuration errors in test '{test_name}':"
                        )
                        for error in service_errors:
                            explanations.append(f"   • {error}")

            if not explanations:
                explanations.append("✅ Basic structure validation passed")
                return True, explanations

        except yaml.YAMLError as e:
            explanations.append(f"❌ YAML syntax error: {e}")
            explanations.append("💡 Check for:")
            explanations.append("   • Proper indentation (use spaces, not tabs)")
            explanations.append("   • Matching quotes")
            explanations.append("   • Valid YAML structure")
            return False, explanations
        except Exception as e:
            explanations.append(f"❌ Error loading configuration: {e}")
            return False, explanations

        return len([e for e in explanations if e.startswith("❌")]) == 0, explanations
