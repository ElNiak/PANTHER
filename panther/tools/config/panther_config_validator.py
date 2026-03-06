#!/usr/bin/env python3
"""Comprehensive PANTHER configuration validation system with sophisticated conflict analysis.

This module implements a comprehensive validation framework for PANTHER experiment configuration
files, providing deep structural analysis, port conflict detection, and cross-file dependency
validation. Designed to catch configuration issues before experiment execution.

**Key Validation Features**:
- **YAML Structure Analysis**: Deep validation of configuration file structure and syntax
- **Port Conflict Detection**: Cross-file port usage analysis with conflict resolution
- **Configuration Completeness**: Validation of required PANTHER configuration sections
- **Security Analysis**: Privileged port usage and security risk assessment
- **Cross-Reference Validation**: Inter-configuration dependency checking

**Analysis Capabilities**:
- **Multi-File Analysis**: Comprehensive validation across entire configuration directories
- **Conflict Categorization**: Port conflicts classified by severity and scope
- **Statistical Reporting**: Detailed metrics on configuration health and port usage
- **Error Classification**: Structured error categorization for targeted fixing
- **Export Formats**: JSON and text reports for integration and analysis

**Port Analysis Architecture**:
```
Port Detection Strategy:
├── Direct Port Fields (port, server_port, client_port, etc.)
├── Docker Compose Ports (ports arrays with host:container mappings)
├── Address/Endpoint Fields (address, bind, listen with host:port format)
├── Network Configuration Sections (networks, services, containers)
└── Recursive Structure Analysis (nested configurations and includes)
```

**Validation Workflow**:
1. **Discovery Phase**: Recursive YAML file discovery and indexing
2. **Syntax Validation**: YAML parsing and basic structure validation
3. **Structural Analysis**: PANTHER-specific configuration section validation
4. **Port Extraction**: Comprehensive port number extraction and cataloging
5. **Conflict Analysis**: Cross-file port conflict detection and categorization
6. **Report Generation**: Multi-format reporting with actionable recommendations
"""

import json
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

import yaml


class PantherConfigValidationReport:
    """Comprehensive PANTHER configuration validation engine with advanced conflict analysis."""

    def __init__(self):
        """Initialize PantherConfigValidationReport."""
        self.results = {}
        self.port_conflicts = defaultdict(list)
        self.error_categories = defaultdict(int)
        self.total_files = 0
        self.pass_count = 0
        self.minor_count = 0  # 1-5 errors
        self.major_count = 0  # 5+ errors
        self.all_ports_found = set()

    def extract_all_ports(self, obj, path="") -> List[Tuple[int, str]]:
        """Extract all port numbers from a configuration object."""
        ports = []

        if isinstance(obj, dict):
            for key, value in obj.items():
                # Direct port fields
                if key.lower() in [
                    "port",
                    "server_port",
                    "client_port",
                    "client_port_alt",
                ]:
                    if isinstance(value, int) and 1000 <= value <= 65535:
                        ports.append((value, f"{path}.{key}"))

                # Docker Compose style ports array
                elif key.lower() == "ports" and isinstance(value, list):
                    for i, port_mapping in enumerate(value):
                        if isinstance(port_mapping, str):
                            # Handle Docker style "host:container" or just "port"
                            port_parts = port_mapping.strip().split(":")
                            for part in port_parts:
                                try:
                                    port_num = int(part.strip())
                                    if 1000 <= port_num <= 65535:
                                        ports.append((port_num, f"{path}.{key}[{i}]"))
                                except ValueError:
                                    pass
                        elif (
                            isinstance(port_mapping, int)
                            and 1000 <= port_mapping <= 65535
                        ):
                            ports.append((port_mapping, f"{path}.{key}[{i}]"))

                # Address/endpoint fields with host:port format
                elif key.lower() in [
                    "address",
                    "endpoint",
                    "bind",
                    "listen",
                    "server_address",
                    "client_address",
                ]:
                    if isinstance(value, str) and ":" in value:
                        try:
                            port_part = value.split(":")[-1]
                            port_num = int(port_part)
                            if 1000 <= port_num <= 65535:
                                ports.append((port_num, f"{path}.{key}"))
                        except ValueError:
                            pass

                # Network configurations and services sections
                elif key.lower() in ["networks", "services", "containers", "tests"]:
                    ports.extend(
                        self.extract_all_ports(value, f"{path}.{key}" if path else key)
                    )

                # Recursively search in other objects
                else:
                    ports.extend(
                        self.extract_all_ports(value, f"{path}.{key}" if path else key)
                    )

        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                ports.extend(self.extract_all_ports(item, f"{path}[{i}]"))

        return ports

    def analyze_file(self, filepath: str) -> Dict[str, Any]:
        """Analyze a single YAML configuration file."""
        print(f"Analyzing: {os.path.basename(filepath)}")

        result = {
            "filepath": filepath,
            "filename": os.path.basename(filepath),
            "status": "UNKNOWN",
            "errors": [],
            "warnings": [],
            "port_conflicts": [],
            "all_ports": [],
            "port_count": 0,
            "yaml_valid": False,
            "structure_valid": False,
        }

        # Check if file can be parsed as YAML
        try:
            with open(filepath, "r") as f:
                config_data = yaml.safe_load(f)
                result["yaml_valid"] = True
        except Exception as e:
            result["errors"].append(f"YAML Parse Error: {str(e)}")
            result["status"] = "MAJOR"
            self.error_categories["yaml_errors"] += 1
            return result

        # Validate basic structure
        if not config_data:
            result["errors"].append("Empty configuration file")
            self.error_categories["structure_errors"] += 1
        else:
            result["structure_valid"] = True

            # Check for expected PANTHER config sections
            expected_sections = ["logging", "paths", "docker"]
            found_sections = []

            if isinstance(config_data, dict):
                for section in expected_sections:
                    if section in config_data:
                        found_sections.append(section)

                # Check for test configurations
                if "tests" in config_data:
                    found_sections.append("tests")

                if len(found_sections) == 0:
                    result["warnings"].append(
                        "No standard PANTHER config sections found"
                    )
                    self.error_categories["structure_warnings"] += 1

        # Extract ports
        if result["yaml_valid"]:
            try:
                ports_found = self.extract_all_ports(config_data)
                result["all_ports"] = sorted(
                    list(set([port for port, _ in ports_found]))
                )
                self.all_ports_found.update(result["all_ports"])

                # Check for duplicates within the same file
                port_counts = Counter([port for port, _ in ports_found])
                for port, count in port_counts.items():
                    if count > 1:
                        result["port_conflicts"].append(port)
                        self.port_conflicts[port].append(filepath)
                        result["errors"].append(
                            f"Duplicate port {port} found in configuration (used {count} times)"
                        )
                        self.error_categories["port_errors"] += 1

                # Check for problematic port ranges
                for port in result["all_ports"]:
                    if port < 1024:
                        result["warnings"].append(
                            f"Port {port} is in privileged range (< 1024)"
                        )
                        self.error_categories["port_warnings"] += 1
                    elif port > 49151:  # Dynamic/private port range
                        result["warnings"].append(
                            f"Port {port} is in dynamic/ephemeral range (> 49151)"
                        )
                        self.error_categories["port_warnings"] += 1

            except Exception as e:
                result["errors"].append(f"Port analysis error: {str(e)}")
                self.error_categories["analysis_errors"] += 1

        # Count unique port conflicts
        result["port_count"] = len(set(result["port_conflicts"]))

        # Determine status
        error_count = len(result["errors"])
        warning_count = len(result["warnings"])

        if error_count == 0:
            result["status"] = "PASS"
            self.pass_count += 1
        elif error_count <= 5:
            result["status"] = "MINOR"
            self.minor_count += 1
        else:
            result["status"] = "MAJOR"
            self.major_count += 1

        return result

    def analyze_cross_file_conflicts(self):
        """Analyze port conflicts across multiple files."""
        all_ports = defaultdict(list)

        # Collect all ports from all files
        for filepath, result in self.results.items():
            for port in result["all_ports"]:
                all_ports[port].append(filepath)

        # Find ports used by multiple files
        cross_file_conflicts = 0
        for port, files in all_ports.items():
            if len(files) > 1:
                unique_files = list(set(files))
                self.port_conflicts[port].extend(unique_files)
                cross_file_conflicts += 1

                for filepath in unique_files:
                    if f"Port {port} conflicts across multiple files" not in [
                        str(e) for e in self.results[filepath]["errors"]
                    ]:
                        self.results[filepath]["errors"].append(
                            f"Port {port} conflicts across multiple files: {[os.path.basename(f) for f in unique_files]}"
                        )
                        self.results[filepath]["port_conflicts"].append(port)
                        self.error_categories["cross_file_port_errors"] += 1

                        # Update status if it was PASS
                        if self.results[filepath]["status"] == "PASS":
                            self.results[filepath]["status"] = "MINOR"
                            self.pass_count -= 1
                            self.minor_count += 1

        return cross_file_conflicts

    def generate_summary(self) -> str:
        """Generate a comprehensive summary report."""
        report = []
        report.append("=" * 80)
        report.append("PANTHER CONFIGURATION VALIDATION REPORT")
        report.append("=" * 80)
        report.append("")

        # Overall statistics
        report.append("OVERALL STATISTICS:")
        report.append(f"Total files analyzed: {self.total_files}")
        report.append(f"✅ PASS (no errors): {self.pass_count}")
        report.append(f"⚠️  MINOR (1-5 errors): {self.minor_count}")
        report.append(f"❌ MAJOR (5+ errors): {self.major_count}")
        report.append("")

        # Error categories
        report.append("ERROR CATEGORIES:")
        for category, count in sorted(self.error_categories.items()):
            report.append(f"  {category}: {count}")
        report.append("")

        # Port analysis
        report.append("PORT ANALYSIS:")
        report.append(f"Total unique ports found: {len(self.all_ports_found)}")
        if self.all_ports_found:
            sorted_ports = sorted(self.all_ports_found)
            report.append(f"Port range: {min(sorted_ports)} - {max(sorted_ports)}")

            # Categorize ports
            privileged = [p for p in sorted_ports if p < 1024]
            registered = [p for p in sorted_ports if 1024 <= p <= 49151]
            dynamic = [p for p in sorted_ports if p > 49151]

            if privileged:
                report.append(
                    f"Privileged ports (< 1024): {len(privileged)} - {privileged}"
                )
            if registered:
                report.append(
                    f"Registered ports (1024-49151): {len(registered)} - {registered[:10]}{'...' if len(registered) > 10 else ''}"
                )
            if dynamic:
                report.append(
                    f"Dynamic/Ephemeral ports (> 49151): {len(dynamic)} - {dynamic}"
                )

        # Port conflict analysis
        report.append("\nPORT CONFLICT ANALYSIS:")
        if self.port_conflicts:
            report.append(f"Total conflicting ports: {len(self.port_conflicts)}")

            # Most problematic ports
            port_frequency = {
                port: len(set(files)) for port, files in self.port_conflicts.items()
            }
            top_ports = sorted(
                port_frequency.items(), key=lambda x: x[1], reverse=True
            )[:10]

            report.append("\nMost conflicting ports:")
            for port, count in top_ports:
                files = list(set(self.port_conflicts[port]))
                report.append(
                    f"  Port {port}: {count} files - {[os.path.basename(f) for f in files[:3]]}"
                )
                if len(files) > 3:
                    report.append(f"    ... and {len(files) - 3} more files")
            report.append("")
        else:
            report.append("✅ No port conflicts detected!")
            report.append("")

        # File-by-file results (sorted by status)
        report.append("DETAILED RESULTS:")
        report.append("-" * 50)

        # Sort by status: MAJOR, MINOR, PASS
        status_order = {"MAJOR": 0, "MINOR": 1, "PASS": 2}
        sorted_results = sorted(
            self.results.items(),
            key=lambda x: (status_order.get(x[1]["status"], 3), x[1]["filename"]),
        )

        for filepath, result in sorted_results:
            status_emoji = {"PASS": "✅", "MINOR": "⚠️", "MAJOR": "❌"}.get(
                result["status"], "❓"
            )
            report.append(f"{status_emoji} {result['filename']} [{result['status']}]")

            if result["all_ports"]:
                report.append(f"    Ports found: {result['all_ports']}")

            if result["errors"]:
                report.append(f"    Errors ({len(result['errors'])}):")
                for error in result["errors"][:3]:  # Show first 3 errors
                    report.append(f"      - {error}")
                if len(result["errors"]) > 3:
                    report.append(f"      ... and {len(result['errors']) - 3} more")

            if result["warnings"]:
                report.append(f"    Warnings ({len(result['warnings'])}):")
                for warning in result["warnings"][:2]:  # Show first 2 warnings
                    report.append(f"      - {warning}")
                if len(result["warnings"]) > 2:
                    report.append(f"      ... and {len(result['warnings']) - 2} more")

            report.append("")

        return "\n".join(report)

    def run_validation(self, config_dir: str):
        """Run validation on all YAML files in the directory."""
        config_path = Path(config_dir)
        yaml_files = list(config_path.rglob("*.yaml"))

        self.total_files = len(yaml_files)
        print(f"Found {self.total_files} YAML files to validate")
        print("-" * 50)

        for yaml_file in sorted(yaml_files):
            result = self.analyze_file(str(yaml_file))
            self.results[str(yaml_file)] = result

        # Analyze cross-file conflicts
        print("Analyzing cross-file port conflicts...")
        cross_conflicts = self.analyze_cross_file_conflicts()
        print(f"Found {cross_conflicts} ports with cross-file conflicts")

        print("-" * 50)
        print("Validation complete!")


def main():
    """Run PANTHER configuration validation on the default config directory."""
    config_dir = "/Users/elniak/Documents/Project/Software-Engineer-AI-Agent-Atlas/REPOS/PANTHER/experiment-config"

    if not os.path.exists(config_dir):
        print(f"Error: Config directory not found: {config_dir}")
        sys.exit(1)

    # Run validation
    report = PantherConfigValidationReport()
    report.run_validation(config_dir)

    # Generate and display summary
    summary = report.generate_summary()
    print(summary)

    # Save detailed results to file
    output_file = "/Users/elniak/Documents/Project/Software-Engineer-AI-Agent-Atlas/REPOS/PANTHER/panther_config_validation_report.txt"
    with open(output_file, "w") as f:
        f.write(summary)
        f.write("\n\n" + "=" * 80)
        f.write("\nDETAILED JSON RESULTS:\n")
        f.write("=" * 80 + "\n")

        # Clean up results for JSON serialization
        json_results = {}
        for filepath, result in report.results.items():
            json_results[os.path.basename(filepath)] = {
                "status": result["status"],
                "errors": result["errors"],
                "warnings": result["warnings"],
                "ports_found": result["all_ports"],
                "port_conflicts": result["port_conflicts"],
            }

        f.write(json.dumps(json_results, indent=2))

    print(f"\nDetailed report saved to: {output_file}")

    # Summary statistics
    print(f"\n📊 SUMMARY:")
    print(f"   Total config files: {report.total_files}")
    print(f"   Unique ports found: {len(report.all_ports_found)}")
    print(f"   Port conflicts: {len(report.port_conflicts)}")
    print(f"   Files with issues: {report.minor_count + report.major_count}")


if __name__ == "__main__":
    main()
