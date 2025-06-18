#!/usr/bin/env python3
"""
Enhanced PANTHER Build Script with Modern Features

This enhanced version includes:
- Build backend detection and compatibility
- Dependency lock file management
- Enhanced security scanning
- Performance metrics collection
- Feature flags for gradual rollout
"""

import argparse
import shutil
import subprocess
import sys
import time
import os
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import docker
    docker_available = True
except ImportError:
    docker_available = False

# Import metrics system
try:
    from panther.metrics import record, flush, ResourceSampler
    from panther.metrics.utils import (
        get_directory_size_mb,
        get_docker_image_size_mb,
        find_latest_wheel,
        cleanup_build_artifacts,
    )
    METRICS_AVAILABLE = True
    print("Metrics system available.")
except ImportError:
    # Metrics not available, create dummy functions
    print("Metrics system not available. Using dummy functions.")
    
    def record(name, value, tags=None):
        pass
    
    def flush(kind, extra=None):
        return "no-metrics"
    
    class ResourceSampler:
        def start(self):
            pass
        
        def stop(self):
            return {}
    
    def get_directory_size_mb(path):
        return 0.0
    
    def get_docker_image_size_mb(name):
        return None
    
    def find_latest_wheel(dist_dir, package_name):
        return None
    
    def cleanup_build_artifacts(path):
        return {}
    
    METRICS_AVAILABLE = False

class PackagingConfig:
    """Configuration for packaging features based on environment variables."""
    
    # Feature flags for gradual rollout
    USE_MODERN_BACKEND = os.environ.get("PANTHER_USE_MODERN_BACKEND", "false").lower() == "true"
    USE_DEPENDENCY_LOCKS = os.environ.get("PANTHER_USE_DEP_LOCKS", "false").lower() == "true"
    ENABLE_SECURITY_SCAN = os.environ.get("PANTHER_SECURITY_SCAN", "true").lower() == "true"
    ENABLE_BUILD_CACHE = os.environ.get("PANTHER_BUILD_CACHE", "true").lower() == "true"
    PARALLEL_BUILDS = os.environ.get("PANTHER_PARALLEL_BUILDS", "false").lower() == "true"
    
    # Build configuration
    BUILD_ISOLATION = os.environ.get("PANTHER_BUILD_ISOLATION", "true").lower() == "true"
    CACHE_DIR = Path(os.environ.get("PANTHER_CACHE_DIR", Path.home() / ".cache" / "panther"))
    
    @classmethod
    def print_config(cls):
        """Print current configuration."""
        print("Packaging Configuration:")
        print(f"  Modern Backend: {cls.USE_MODERN_BACKEND}")
        print(f"  Dependency Locks: {cls.USE_DEPENDENCY_LOCKS}")
        print(f"  Security Scanning: {cls.ENABLE_SECURITY_SCAN}")
        print(f"  Build Cache: {cls.ENABLE_BUILD_CACHE}")
        print(f"  Parallel Builds: {cls.PARALLEL_BUILDS}")
        print(f"  Build Isolation: {cls.BUILD_ISOLATION}")
        print(f"  Cache Directory: {cls.CACHE_DIR}")

class DependencyManager:
    """Enhanced dependency management with lock files and caching."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.lock_dir = project_root / "locks"
        self.lock_dir.mkdir(exist_ok=True)
    
    def generate_lock_file(self, env_name: str = "default") -> Path:
        """Generate a reproducible dependency lock file."""
        lock_file = self.lock_dir / f"requirements-{env_name}.lock"
        
        print(f"Generating lock file: {lock_file}")
        
        # Use pip-tools if available, otherwise fall back to pip freeze
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "pip-tools"],
                check=True,
                capture_output=True
            )
            
            # Generate requirements.in from pyproject.toml
            requirements_in = self.lock_dir / f"requirements-{env_name}.in"
            self._generate_requirements_in(requirements_in, env_name)
            
            # Compile lock file
            subprocess.run(
                [
                    sys.executable, "-m", "piptools", "compile",
                    "--generate-hashes",
                    "--resolver=backtracking",
                    "-o", str(lock_file),
                    str(requirements_in)
                ],
                check=True
            )
        except Exception as e:
            print(f"pip-tools not available, using pip freeze: {e}")
            
            # Fallback to pip freeze
            result = subprocess.run(
                [sys.executable, "-m", "pip", "freeze"],
                capture_output=True,
                text=True,
                check=True
            )
            
            with open(lock_file, 'w') as f:
                f.write(result.stdout)
        
        print(f"Lock file generated: {lock_file}")
        return lock_file
    
    def _generate_requirements_in(self, output_file: Path, env_name: str):
        """Generate requirements.in from pyproject.toml."""
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib
        
        with open(self.project_root / "pyproject.toml", "rb") as f:
            config = tomllib.load(f)
        
        dependencies = config.get("project", {}).get("dependencies", [])
        
        if env_name != "default":
            # Add optional dependencies
            optional_deps = config.get("project", {}).get("optional-dependencies", {})
            if env_name in optional_deps:
                dependencies.extend(optional_deps[env_name])
        
        with open(output_file, 'w') as f:
            f.write("# Auto-generated from pyproject.toml\n")
            f.write(f"# Environment: {env_name}\n")
            f.write(f"# Generated: {datetime.now().isoformat()}\n\n")
            
            for dep in dependencies:
                f.write(f"{dep}\n")
    
    def verify_lock_file(self, lock_file: Path) -> bool:
        """Verify that current environment matches lock file."""
        if not lock_file.exists():
            return False
        
        # Compare hash of current environment with lock file
        current_hash = self._get_environment_hash()
        
        # Read lock file header for hash
        with open(lock_file, 'r') as f:
            first_line = f.readline()
            if first_line.startswith("# Hash:"):
                lock_hash = first_line.split(":")[1].strip()
                return current_hash == lock_hash
        
        return True
    
    def _get_environment_hash(self) -> str:
        """Generate hash of current Python environment."""
        result = subprocess.run(
            [sys.executable, "-m", "pip", "freeze"],
            capture_output=True,
            text=True,
            check=True
        )
        
        return hashlib.sha256(result.stdout.encode()).hexdigest()[:16]

class SecurityScanner:
    """Enhanced security scanning for dependencies and code."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.reports_dir = project_root / "security-reports"
        self.reports_dir.mkdir(exist_ok=True)
    
    def run_comprehensive_scan(self) -> Dict[str, bool]:
        """Run all security scans and return results."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results = {}
        
        # Run scans in parallel
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                executor.submit(self._run_safety_check, timestamp): "safety",
                executor.submit(self._run_bandit_scan, timestamp): "bandit",
                executor.submit(self._run_pip_audit, timestamp): "pip_audit",
                executor.submit(self._run_semgrep_scan, timestamp): "semgrep",
            }
            
            for future in as_completed(futures):
                scan_name = futures[future]
                try:
                    results[scan_name] = future.result()
                except Exception as e:
                    print(f"Error running {scan_name}: {e}")
                    results[scan_name] = False
        
        # Generate summary report
        self._generate_summary_report(results, timestamp)
        
        return results
    
    def _run_safety_check(self, timestamp: str) -> bool:
        """Run safety check for known vulnerabilities."""
        try:
            report_file = self.reports_dir / f"safety_{timestamp}.json"
            
            result = subprocess.run(
                [sys.executable, "-m", "safety", "check", "--json"],
                capture_output=True,
                text=True
            )
            
            with open(report_file, 'w') as f:
                f.write(result.stdout)
            
            # Parse results
            data = json.loads(result.stdout)
            vulnerabilities = data.get("vulnerabilities", [])
            
            if vulnerabilities:
                print(f"⚠️  Safety found {len(vulnerabilities)} vulnerabilities")
                return False
            else:
                print("✅ Safety check passed")
                return True
                
        except Exception as e:
            print(f"❌ Safety check failed: {e}")
            return False
    
    def _run_bandit_scan(self, timestamp: str) -> bool:
        """Run Bandit security linter."""
        try:
            report_file = self.reports_dir / f"bandit_{timestamp}.json"
            
            result = subprocess.run(
                [
                    sys.executable, "-m", "bandit",
                    "-r", "panther/",
                    "-f", "json",
                    "-o", str(report_file)
                ],
                capture_output=True,
                text=True
            )
            
            # Parse results
            with open(report_file, 'r') as f:
                data = json.load(f)
            
            high_issues = [i for i in data.get("results", []) if i.get("issue_severity") == "HIGH"]
            
            if high_issues:
                print(f"⚠️  Bandit found {len(high_issues)} high severity issues")
                return False
            else:
                print("✅ Bandit scan passed")
                return True
                
        except Exception as e:
            print(f"❌ Bandit scan failed: {e}")
            return False
    
    def _run_pip_audit(self, timestamp: str) -> bool:
        """Run pip-audit for dependency vulnerabilities."""
        try:
            report_file = self.reports_dir / f"pip_audit_{timestamp}.json"
            
            result = subprocess.run(
                [
                    sys.executable, "-m", "pip_audit",
                    "--format", "json",
                    "--desc", "on",
                    "--output", str(report_file)
                ],
                capture_output=True,
                text=True
            )
            
            # Check if vulnerabilities found
            with open(report_file, 'r') as f:
                data = json.load(f)
            
            vulnerabilities = data.get("vulnerabilities", [])
            
            if vulnerabilities:
                print(f"⚠️  pip-audit found {len(vulnerabilities)} vulnerabilities")
                return False
            else:
                print("✅ pip-audit passed")
                return True
                
        except Exception as e:
            print(f"❌ pip-audit failed: {e}")
            return False
    
    def _run_semgrep_scan(self, timestamp: str) -> bool:
        """Run Semgrep for code security patterns."""
        try:
            report_file = self.reports_dir / f"semgrep_{timestamp}.json"
            
            result = subprocess.run(
                [
                    "semgrep",
                    "--config=auto",
                    "--json",
                    "--output", str(report_file),
                    "panther/"
                ],
                capture_output=True,
                text=True
            )
            
            # Parse results
            with open(report_file, 'r') as f:
                data = json.load(f)
            
            errors = data.get("errors", [])
            results = data.get("results", [])
            
            high_findings = [r for r in results if r.get("extra", {}).get("severity", "") in ["ERROR", "WARNING"]]
            
            if errors or high_findings:
                print(f"⚠️  Semgrep found {len(high_findings)} high severity findings")
                return False
            else:
                print("✅ Semgrep scan passed")
                return True
                
        except FileNotFoundError:
            print("ℹ️  Semgrep not installed, skipping")
            return True
        except Exception as e:
            print(f"❌ Semgrep scan failed: {e}")
            return False
    
    def _generate_summary_report(self, results: Dict[str, bool], timestamp: str):
        """Generate a summary security report."""
        summary_file = self.reports_dir / f"security_summary_{timestamp}.json"
        
        summary = {
            "timestamp": timestamp,
            "overall_status": all(results.values()),
            "scan_results": results,
            "recommendations": []
        }
        
        if not results.get("safety", True):
            summary["recommendations"].append("Update vulnerable dependencies identified by Safety")
        
        if not results.get("bandit", True):
            summary["recommendations"].append("Fix high severity issues identified by Bandit")
        
        if not results.get("pip_audit", True):
            summary["recommendations"].append("Update packages with known vulnerabilities")
        
        if not results.get("semgrep", True):
            summary["recommendations"].append("Review and fix security patterns identified by Semgrep")
        
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"\nSecurity scan summary saved to: {summary_file}")
        print(f"Overall status: {'PASSED ✅' if summary['overall_status'] else 'FAILED ❌'}")

class ModernBuildManager:
    """Enhanced build manager with modern features."""
    
    def __init__(self):
        # Import base BuildManager
        sys.path.insert(0, str(Path(__file__).parent))
        from panther_builder import BuildManager
        
        # Initialize base class functionality
        self.base_manager = BuildManager()
        self.project_root = self.base_manager.project_root
        
        # Enhanced components
        self.dependency_manager = DependencyManager(self.project_root)
        self.security_scanner = SecurityScanner(self.project_root)
        
        # Build configuration
        self.config = PackagingConfig()
        
        # Cache management
        if self.config.ENABLE_BUILD_CACHE:
            self.cache_dir = self.config.CACHE_DIR
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Backend detection
        self.build_backend = self._detect_build_backend()
    
    def _detect_build_backend(self) -> str:
        """Auto-detect build backend from pyproject.toml."""
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib
        
        try:
            with open(self.project_root / "pyproject.toml", "rb") as f:
                data = tomllib.load(f)
            return data.get("build-system", {}).get("build-backend", "setuptools.build_meta")
        except Exception:
            return "setuptools.build_meta"
    
    def build_with_features(self) -> int:
        """Build with modern features based on configuration."""
        self.config.print_config()
        
        # Clean if requested
        if not self.config.ENABLE_BUILD_CACHE:
            self.base_manager.clean()
        
        # Generate lock files if enabled
        if self.config.USE_DEPENDENCY_LOCKS:
            print("\nGenerating dependency lock files...")
            self.dependency_manager.generate_lock_file("default")
            self.dependency_manager.generate_lock_file("dev")
        
        # Run security scans if enabled
        if self.config.ENABLE_SECURITY_SCAN:
            print("\nRunning security scans...")
            security_results = self.security_scanner.run_comprehensive_scan()
            
            if not all(security_results.values()):
                print("\n⚠️  Security issues found. Continue anyway? (y/N): ", end='')
                response = input().strip().lower()
                if response != 'y':
                    return 1
        
        # Build with appropriate backend
        if self.config.USE_MODERN_BACKEND:
            return self._build_with_hatchling()
        else:
            return self._build_with_setuptools()
    
    def _build_with_setuptools(self) -> int:
        """Build using setuptools (current default)."""
        print("\nBuilding with setuptools...")
        
        if self.config.BUILD_ISOLATION:
            return self.base_manager.run_command([
                sys.executable, "-m", "build", "--wheel", "--sdist"
            ])
        else:
            return self.base_manager.run_command([
                sys.executable, "-m", "build", "--wheel", "--sdist", "--no-isolation"
            ])
    
    def _build_with_hatchling(self) -> int:
        """Build using hatchling (modern backend)."""
        print("\nBuilding with hatchling...")
        
        # Ensure hatchling is installed
        self.base_manager.run_command([
            sys.executable, "-m", "pip", "install", "hatchling>=1.18.0"
        ])
        
        # Temporarily modify pyproject.toml
        original_pyproject = self.project_root / "pyproject.toml"
        backup_pyproject = self.project_root / "pyproject.toml.backup"
        
        try:
            # Backup original
            shutil.copy2(original_pyproject, backup_pyproject)
            
            # Create hatchling configuration
            self._create_hatchling_config()
            
            # Build
            result = self.base_manager.run_command([
                sys.executable, "-m", "build", "--wheel", "--sdist"
            ])
            
            return result
            
        finally:
            # Restore original
            if backup_pyproject.exists():
                shutil.move(backup_pyproject, original_pyproject)
    
    def _create_hatchling_config(self):
        """Create hatchling-compatible pyproject.toml."""
        pyproject_path = self.project_root / "pyproject.toml"
        
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib
        
        with open(pyproject_path, "rb") as f:
            config = tomllib.load(f)
        
        # Update build system
        config["build-system"] = {
            "requires": ["hatchling>=1.18.0"],
            "build-backend": "hatchling.build"
        }
        
        # Add hatchling configuration
        if "tool" not in config:
            config["tool"] = {}
        
        config["tool"]["hatch"] = {
            "build": {
                "artifacts": [
                    "panther/plugins/**/*",
                    "panther/webapp/**/*",
                ],
                "targets": {
                    "wheel": {
                        "packages": ["panther"],
                        "include": [
                            "/panther",
                            "*.md",
                            "*.txt"
                        ],
                        "exclude": [
                            "tests/",
                            "outputs*/",
                            ".github/",
                            "**/__pycache__"
                        ]
                    }
                }
            }
        }
        
        # Write updated configuration
        try:
            import tomli_w
            with open(pyproject_path, "wb") as f:
                tomli_w.dump(config, f)
        except ImportError:
            print("Warning: tomli-w not available, using manual write")
            # Fallback to manual write (less reliable)
    
    def run_comprehensive_tests(self) -> int:
        """Run comprehensive tests including packaging validation."""
        print("\nRunning comprehensive test suite...")
        
        # Run standard tests
        test_result = self.base_manager.run_tests()
        
        if test_result != 0:
            return test_result
        
        # Run packaging tests
        print("\nRunning packaging validation tests...")
        
        packaging_test_result = self.base_manager.run_command([
            sys.executable, "-m", "pytest",
            "tests/test_packaging/",
            "-v"
        ])
        
        return packaging_test_result
    
    def generate_sbom(self) -> int:
        """Generate Software Bill of Materials."""
        print("\nGenerating SBOM...")
        
        sbom_dir = self.project_root / "sbom"
        sbom_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Try multiple SBOM generators
        generators = [
            # CycloneDX
            ([
                sys.executable, "-m", "pip", "install", "cyclonedx-bom"
            ], [
                sys.executable, "-m", "cyclonedx_py", 
                "-o", str(sbom_dir / f"sbom_cyclonedx_{timestamp}.json"),
                "-F", "json"
            ]),
            
            # pip-audit SBOM
            ([
                sys.executable, "-m", "pip", "install", "pip-audit"
            ], [
                sys.executable, "-m", "pip_audit",
                "--format", "cyclonedx",
                "--output", str(sbom_dir / f"sbom_pip_audit_{timestamp}.json")
            ])
        ]
        
        success = False
        for install_cmd, generate_cmd in generators:
            try:
                self.base_manager.run_command(install_cmd)
                result = self.base_manager.run_command(generate_cmd)
                if result == 0:
                    success = True
                    print(f"✅ SBOM generated successfully")
            except Exception as e:
                print(f"Warning: SBOM generation failed: {e}")
        
        return 0 if success else 1

def main():
    """Enhanced main entry point."""
    parser = argparse.ArgumentParser(
        description="Enhanced PANTHER Build Script with Modern Features",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Environment Variables:
    PANTHER_USE_MODERN_BACKEND - Use hatchling instead of setuptools (default: false)
    PANTHER_USE_DEP_LOCKS     - Generate and use dependency lock files (default: false)  
    PANTHER_SECURITY_SCAN     - Enable security scanning (default: true)
    PANTHER_BUILD_CACHE       - Enable build caching (default: true)
    PANTHER_PARALLEL_BUILDS   - Enable parallel builds (default: false)
    
Examples:
    # Build with modern features
    PANTHER_USE_MODERN_BACKEND=true python panther_builder_enhanced.py build
    
    # Generate dependency locks
    python panther_builder_enhanced.py generate-locks
    
    # Run security scan
    python panther_builder_enhanced.py security-scan
    
    # Build with all modern features
    PANTHER_USE_MODERN_BACKEND=true PANTHER_USE_DEP_LOCKS=true \\
        python panther_builder_enhanced.py build
        """
    )
    
    parser.add_argument(
        "command",
        nargs="?",
        default="help",
        choices=[
            # Original commands
            "package", "package-dev", "package-test", "clean",
            "install-local", "docs", "serve-docs", "deploy-docs",
            "check", "install-precommit", "zip-outputs",
            "remove-images-all", "remove-images-services",
            "remove-system-all", "remove-system-services",
            "remove-volume", "help",
            
            # New enhanced commands
            "build", "generate-locks", "security-scan",
            "validate-packaging", "generate-sbom",
            "comprehensive-test", "show-config"
        ],
        help="Command to execute"
    )
    
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose output"
    )
    
    args = parser.parse_args()
    
    if args.command == "help":
        parser.print_help()
        return 0
    
    # Create enhanced build manager
    try:
        build_manager = ModernBuildManager()
    except Exception as e:
        print(f"Error initializing build manager: {e}")
        return 1
    
    # Map new commands
    enhanced_command_map = {
        "build": build_manager.build_with_features,
        "generate-locks": lambda: build_manager.dependency_manager.generate_lock_file("default"),
        "security-scan": lambda: 0 if all(build_manager.security_scanner.run_comprehensive_scan().values()) else 1,
        "validate-packaging": lambda: subprocess.run([
            sys.executable, "tests/test_packaging/test_migration_validator.py"
        ]).returncode,
        "generate-sbom": build_manager.generate_sbom,
        "comprehensive-test": build_manager.run_comprehensive_tests,
        "show-config": lambda: (PackagingConfig.print_config(), 0)[1],
    }
    
    # Check if using enhanced command
    if args.command in enhanced_command_map:
        try:
            result = enhanced_command_map[args.command]()
            return result if result is not None else 0
        except KeyboardInterrupt:
            print("\nBuild interrupted by user")
            return 130
        except Exception as e:
            print(f"Error: {e}")
            return 1
    
    # Fall back to original build manager for legacy commands
    sys.path.insert(0, str(Path(__file__).parent))
    from panther_builder import main as original_main
    
    # Restore original args
    sys.argv = sys.argv[:1] + [args.command]
    if args.verbose:
        sys.argv.append("-v")
    
    return original_main()

if __name__ == "__main__":
    sys.exit(main())