"""
Admin Command - Administrative and system management
"""

from argparse import ArgumentParser, _SubParsersAction
import logging
from typing import Any

from ..base import BaseCommand


class AdminCommand(BaseCommand):
    """Handle administrative and system management commands."""

    @classmethod
    def register_parser(cls, subparsers: _SubParsersAction) -> ArgumentParser:
        """Register the admin subcommand parser."""
        parser = subparsers.add_parser(
            "admin",
            help="Administrative and system management",
            description="Administrative commands for system management and maintenance",
        )

        subcommands = parser.add_subparsers(
            dest="admin_action", help="Administrative actions", metavar="ACTION"
        )

        # Teardown subcommand
        teardown_parser = subcommands.add_parser(
            "teardown",
            help="Clean up system resources",
            description="Clean up Docker containers, networks, and other system resources",
        )
        teardown_parser.add_argument(
            "--force", action="store_true", help="Force cleanup without confirmation"
        )

        # Webapp subcommand
        webapp_parser = subcommands.add_parser(
            "webapp",
            help="Start web application",
            description="Start the PANTHER web interface (if available)",
        )
        webapp_parser.add_argument(
            "--port",
            type=int,
            default=8080,
            help="Port to run web application (default: 8080)",
        )
        webapp_parser.add_argument(
            "--host",
            type=str,
            default="localhost",
            help="Host to bind web application (default: localhost)",
        )

        # Status subcommand
        status_parser = subcommands.add_parser(
            "status",
            help="Show system status",
            description="Display PANTHER system status and health information",
        )

        # Clean subcommand
        clean_parser = subcommands.add_parser(
            "clean",
            help="Clean up temporary files",
            description="Clean up temporary files, logs, and cache",
        )
        clean_parser.add_argument("--logs", action="store_true", help="Clean log files")
        clean_parser.add_argument(
            "--cache", action="store_true", help="Clean cache files"
        )
        clean_parser.add_argument(
            "--all", action="store_true", help="Clean all temporary files"
        )

        # Docker management subcommands
        docker_parser = subcommands.add_parser(
            "docker",
            help="Manage Docker resources",
            description="Manage Docker images, containers, and volumes",
        )
        docker_parser.add_argument(
            "--images-all",
            action="store_true",
            help="Remove all Docker images with 'panther' in the name",
        )
        docker_parser.add_argument(
            "--images-services",
            action="store_true",
            help="Remove Docker images with '_panther' in the name",
        )
        docker_parser.add_argument(
            "--system-all",
            action="store_true",
            help="Remove images and prune system data with 'panther' label",
        )
        docker_parser.add_argument(
            "--system-services",
            action="store_true",
            help="Remove images and prune system data with '_panther' label",
        )
        docker_parser.add_argument(
            "--volumes",
            action="store_true",
            help="Remove Docker volumes with 'panther' in the name",
        )
        docker_parser.add_argument(
            "--containers",
            action="store_true",
            help="Remove stopped containers with 'panther' label",
        )
        docker_parser.add_argument(
            "--show-registry",
            action="store_true",
            help="Show Docker registry statistics",
        )
        docker_parser.add_argument(
            "--prune-cache",
            action="store_true",
            help="Prune old Docker build cache entries",
        )
        docker_parser.add_argument(
            "--export-registry",
            type=str,
            metavar="PATH",
            help="Export Docker registry to file",
        )
        docker_parser.add_argument(
            "--import-registry",
            type=str,
            metavar="PATH",
            help="Import Docker registry from file",
        )
        docker_parser.add_argument(
            "--cache-max-age",
            type=int,
            default=7,
            help="Maximum age in days for cache entries (default: 7)",
        )

        return parser

    @classmethod
    def handle(cls, args: Any) -> int:
        """Handle the admin command execution."""
        if not hasattr(args, "admin_action") or args.admin_action is None:
            logging.info(
                "❌ No admin action specified. Use 'panther admin --help' for options."
            )
            return 1

        if args.admin_action == "teardown":
            return cls._handle_teardown(args)
        elif args.admin_action == "webapp":
            return cls._handle_webapp(args)
        elif args.admin_action == "status":
            return cls._handle_status(args)
        elif args.admin_action == "clean":
            return cls._handle_clean(args)
        elif args.admin_action == "docker":
            return cls._handle_docker(args)
        else:
            logging.info(f"❌ Unknown admin action: {args.admin_action}")
            return 1

    @classmethod
    def _handle_teardown(cls, args: Any) -> int:
        """Handle system teardown and cleanup."""
        try:
            import subprocess
            from pathlib import Path

            logging.info("🧹 Starting system teardown and cleanup...")

            if not args.force:
                response = input(
                    "This will clean up Docker containers and networks. Continue? (y/N): "
                )
                if response.lower() not in ["y", "yes"]:
                    logging.info("❌ Teardown cancelled")
                    return 0

            # Clean up Docker containers
            try:
                logging.info("🐳 Cleaning up Docker containers...")
                subprocess.run(
                    ["docker", "container", "prune", "-f"],
                    check=False,
                    capture_output=True,
                )

                # Clean up PANTHER-specific containers
                result = subprocess.run(
                    [
                        "docker",
                        "ps",
                        "-a",
                        "--filter",
                        "label=panther",
                        "--format",
                        "{{.ID}}",
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                )

                if result.returncode == 0 and result.stdout.strip():
                    container_ids = result.stdout.strip().split("\n")
                    subprocess.run(
                        ["docker", "rm", "-f"] + container_ids,
                        check=False,
                        capture_output=True,
                    )
                    logging.info(f"🗑️  Removed {len(container_ids)} PANTHER container(s)")

            except Exception as e:
                logging.info(f"⚠️  Warning: Docker cleanup failed: {e}")

            # Clean up Docker networks
            try:
                logging.info("🌐 Cleaning up Docker networks...")
                subprocess.run(
                    ["docker", "network", "prune", "-f"],
                    check=False,
                    capture_output=True,
                )
            except Exception as e:
                logging.info(f"⚠️  Warning: Network cleanup failed: {e}")

            # Clean up temporary files
            try:
                logging.info("📁 Cleaning up temporary files...")
                temp_dirs = ["outputs", "logs", "tmp"]

                for temp_dir in temp_dirs:
                    temp_path = Path(temp_dir)
                    if temp_path.exists() and temp_path.is_dir():
                        import shutil

                        shutil.rmtree(temp_path, ignore_errors=True)
                        logging.info(f"🗑️  Removed directory: {temp_path}")

            except Exception as e:
                logging.info(f"⚠️  Warning: File cleanup failed: {e}")

            logging.info("✅ System teardown completed")
            return 0

        except Exception as e:
            logging.info(f"❌ Error during teardown: {e}")
            return 1

    @classmethod
    def _handle_webapp(cls, args: Any) -> int:
        """Handle web application startup."""
        try:
            host = args.host
            port = args.port

            logging.info(f"🌐 Starting PANTHER web application...")
            logging.info(f"   Host: {host}")
            logging.info(f"   Port: {port}")
            logging.info(f"   URL: http://{host}:{port}")

            # TODO: Implement actual web application startup
            logging.info("❌ Web application not yet implemented")
            logging.info("   This feature will be available in a future release")

            return 1

        except Exception as e:
            logging.info(f"❌ Error starting web application: {e}")
            return 1

    @classmethod
    def _handle_status(cls, args: Any) -> int:
        """Handle system status display."""
        try:
            import subprocess
            import sys
            from pathlib import Path

            logging.info("🔍 PANTHER System Status")
            logging.info("=" * 40)

            # Python version
            logging.info(f"🐍 Python: {sys.version.split()[0]}")

            # Docker status
            try:
                result = subprocess.run(
                    ["docker", "--version"], capture_output=True, text=True, check=True
                )
                docker_version = result.stdout.strip()
                logging.info(f"🐳 Docker: {docker_version}")

                # Docker daemon status
                try:
                    subprocess.run(["docker", "info"], capture_output=True, check=True)
                    logging.info("✅ Docker daemon: Running")
                except subprocess.CalledProcessError:
                    logging.info("❌ Docker daemon: Not running")

            except (subprocess.CalledProcessError, FileNotFoundError):
                logging.info("❌ Docker: Not installed or not accessible")

            # PANTHER installation
            try:
                import panther

                logging.info(f"🐾 PANTHER: Installed")

                # Check for main directories
                panther_dir = Path(__file__).parent.parent.parent
                plugin_dir = panther_dir / "plugins"

                if plugin_dir.exists():
                    logging.info(f"📦 Plugin directory: {plugin_dir}")
                else:
                    logging.info(f"⚠️  Plugin directory not found: {plugin_dir}")

            except ImportError:
                logging.info("❌ PANTHER: Not properly installed")

            # Running containers
            try:
                result = subprocess.run(
                    [
                        "docker",
                        "ps",
                        "--filter",
                        "label=panther",
                        "--format",
                        "table {{.Names}}\t{{.Status}}",
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                )

                if result.returncode == 0 and result.stdout.strip():
                    lines = result.stdout.strip().split("\n")
                    if len(lines) > 1:  # More than just header
                        logging.info(f"\n🏃 Running PANTHER containers:")
                        for line in lines[1:]:  # Skip header
                            logging.info(f"   {line}")
                    else:
                        logging.info("\n💤 No PANTHER containers currently running")
                else:
                    logging.info("\n💤 No PANTHER containers currently running")

            except Exception as e:
                logging.info(f"\n⚠️  Could not check container status: {e}")

            return 0

        except Exception as e:
            logging.info(f"❌ Error checking system status: {e}")
            return 1

    @classmethod
    def _handle_clean(cls, args: Any) -> int:
        """Handle cleanup operations."""
        try:
            import shutil
            from pathlib import Path

            logging.info("🧹 Starting cleanup operations...")

            cleaned_items = []

            if args.all or args.logs:
                # Clean log files
                log_dirs = ["logs", "outputs/logs"]
                for log_dir in log_dirs:
                    log_path = Path(log_dir)
                    if log_path.exists():
                        shutil.rmtree(log_path, ignore_errors=True)
                        cleaned_items.append(f"Log directory: {log_path}")

            if args.all or args.cache:
                # Clean cache files
                cache_dirs = ["__pycache__", ".pytest_cache", ".coverage"]
                for cache_dir in cache_dirs:
                    cache_path = Path(cache_dir)
                    if cache_path.exists():
                        if cache_path.is_dir():
                            shutil.rmtree(cache_path, ignore_errors=True)
                        else:
                            cache_path.unlink(missing_ok=True)
                        cleaned_items.append(f"Cache: {cache_path}")

                # Find and clean __pycache__ directories recursively
                for pycache_dir in Path(".").rglob("__pycache__"):
                    shutil.rmtree(pycache_dir, ignore_errors=True)
                    cleaned_items.append(f"Cache directory: {pycache_dir}")

            if args.all:
                # Clean temporary files
                temp_files = ["*.tmp", "*.temp", ".DS_Store"]
                for pattern in temp_files:
                    for temp_file in Path(".").rglob(pattern):
                        temp_file.unlink(missing_ok=True)
                        cleaned_items.append(f"Temporary file: {temp_file}")

            if cleaned_items:
                logging.info("🗑️  Cleaned items:")
                for item in cleaned_items:
                    logging.info(f"   - {item}")
                logging.info(f"✅ Cleanup completed ({len(cleaned_items)} items)")
            else:
                logging.info("ℹ️  No items to clean")

            return 0

        except Exception as e:
            logging.info(f"❌ Error during cleanup: {e}")
            return 1

    @classmethod
    def _handle_docker(cls, args: Any) -> int:
        """Handle Docker resource management."""
        try:
            import subprocess

            # Check if Docker is available
            try:
                subprocess.run(["docker", "--version"], capture_output=True, check=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                logging.info("❌ Docker is not available or not installed")
                return 1

            # Check what operations to perform
            operations = []
            if args.images_all:
                operations.append("images_all")
            if args.images_services:
                operations.append("images_services")
            if args.system_all:
                operations.append("system_all")
            if args.system_services:
                operations.append("system_services")
            if args.volumes:
                operations.append("volumes")
            if args.containers:
                operations.append("containers")

            # Registry operations
            if args.show_registry:
                return cls._show_docker_registry(args)
            elif args.export_registry:
                return cls._export_docker_registry(args)
            elif args.import_registry:
                return cls._import_docker_registry(args)
            elif args.prune_cache:
                return cls._prune_docker_cache(args)

            if not operations:
                logging.info(
                    "❌ No Docker operations specified. Use 'panther admin docker --help' for options."
                )
                return 1

            logging.info("🐳 Docker Resource Management")
            logging.info("=" * 40)

            total_errors = 0

            # Remove all PANTHER images
            if "images_all" in operations:
                logging.info("\n🗑️  Removing Docker images with 'panther' in the name...")
                result = subprocess.run(
                    [
                        "bash",
                        "-c",
                        "docker images --format '{{.Repository}}:{{.Tag}}' | grep panther | xargs -r docker rmi",
                    ],
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0:
                    logging.info("   ✅ Images removed successfully")
                else:
                    logging.info("   ⚠️  Some images could not be removed (may be in use)")
                    total_errors += 1

            # Remove service images
            if "images_services" in operations:
                logging.info("\n🗑️  Removing Docker images with '_panther' in the name...")
                result = subprocess.run(
                    [
                        "bash",
                        "-c",
                        "docker images --format '{{.Repository}}:{{.Tag}}' | grep _panther | xargs -r docker rmi",
                    ],
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0:
                    logging.info("   ✅ Service images removed successfully")
                else:
                    logging.info("   ⚠️  Some images could not be removed (may be in use)")
                    total_errors += 1

            # System prune with panther label
            if "system_all" in operations:
                logging.info("\n🧹 Pruning Docker system data with 'panther' label...")
                # First remove images
                subprocess.run(
                    [
                        "bash",
                        "-c",
                        "docker images --format '{{.Repository}}:{{.Tag}}' | grep panther | xargs -r docker rmi",
                    ],
                    capture_output=True,
                )
                # Then prune system
                result = subprocess.run(
                    ["docker", "system", "prune", "--filter", "label=panther", "-f"],
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0:
                    logging.info("   ✅ System pruned successfully")
                else:
                    logging.info("   ❌ System prune failed")
                    total_errors += 1

            # System prune with _panther label
            if "system_services" in operations:
                logging.info("\n🧹 Pruning Docker system data with '_panther' label...")
                # First remove images
                subprocess.run(
                    [
                        "bash",
                        "-c",
                        "docker images --format '{{.Repository}}:{{.Tag}}' | grep _panther | xargs -r docker rmi",
                    ],
                    capture_output=True,
                )
                # Then prune system
                result = subprocess.run(
                    ["docker", "system", "prune", "--filter", "label=_panther", "-f"],
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0:
                    logging.info("   ✅ System pruned successfully")
                else:
                    logging.info("   ❌ System prune failed")
                    total_errors += 1

            # Remove volumes
            if "volumes" in operations:
                logging.info("\n🗑️  Removing Docker volumes with 'panther' in the name...")
                result = subprocess.run(
                    [
                        "bash",
                        "-c",
                        "docker volume ls --format '{{.Name}}' | grep panther | xargs -r docker volume rm",
                    ],
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0:
                    logging.info("   ✅ Volumes removed successfully")
                else:
                    logging.info("   ⚠️  Some volumes could not be removed (may be in use)")
                    total_errors += 1

            # Remove containers
            if "containers" in operations:
                logging.info("\n🗑️  Removing stopped containers with 'panther' label...")
                # First stop running containers
                subprocess.run(
                    [
                        "bash",
                        "-c",
                        "docker ps -q --filter label=panther | xargs -r docker stop",
                    ],
                    capture_output=True,
                )
                # Then remove them
                result = subprocess.run(
                    [
                        "bash",
                        "-c",
                        "docker ps -aq --filter label=panther | xargs -r docker rm",
                    ],
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0:
                    logging.info("   ✅ Containers removed successfully")
                else:
                    logging.info("   ⚠️  Some containers could not be removed")
                    total_errors += 1

            # Remove dangling images
            logging.info("\n🗑️  Removing dangling Docker images...")
            result = subprocess.run(
                ["docker", "images", "--filter", "dangling=true", "-q"],
                capture_output=True,
                text=True,
            )
            if result.stdout.strip():
                remove_result = subprocess.run(
                    [
                        "bash",
                        "-c",
                        "docker images --filter dangling=true -q | xargs -r docker rmi",
                    ],
                    capture_output=True,
                )
                if remove_result.returncode == 0:
                    logging.info("   ✅ Dangling images removed")
                else:
                    logging.info("   ⚠️  Some dangling images could not be removed")
            else:
                logging.info("   ℹ️  No dangling images found")

            if total_errors == 0:
                logging.info("\n✅ Docker cleanup completed successfully")
                return 0
            else:
                logging.info(f"\n⚠️  Docker cleanup completed with {total_errors} warning(s)")
                return 0  # Don't fail on warnings

        except Exception as e:
            logging.info(f"❌ Error during Docker management: {e}")
            return 1

    @classmethod
    def _show_docker_registry(cls, args: Any) -> int:
        """Show Docker registry statistics."""
        try:
            from panther.core.docker_registry import DockerRegistry

            logging.info("📁 Docker Registry Statistics")
            logging.info("=" * 40)

            registry = DockerRegistry()
            stats = registry.get_registry_stats()

            logging.info(f"Total resources: {stats['total_resources']}")
            logging.info(f"Cache entries: {stats['cache_entries']}")
            logging.info(f"Registry size: {stats['registry_size_kb']:.1f} KB")

            if stats["by_type"]:
                logging.info("\nResources by type:")
                for resource_type, count in stats["by_type"].items():
                    logging.info(f"  {resource_type}: {count}")

            # Show recent builds
            logging.info("\n📦 Recent cached builds:")
            recent_builds = []
            for key, entry in registry.build_cache.items():
                recent_builds.append(
                    (entry.build_time, entry.image_tag, entry.size_bytes)
                )

            recent_builds.sort(reverse=True)
            for build_time, tag, size in recent_builds[:5]:
                size_mb = size / (1024 * 1024)
                logging.info(f"  {tag}: {size_mb:.1f} MB (built: {build_time[:10]})")

            return 0

        except Exception as e:
            logging.info(f"❌ Error showing registry: {e}")
            return 1

    @classmethod
    def _prune_docker_cache(cls, args: Any) -> int:
        """Prune Docker build cache."""
        try:
            from panther.core.docker_registry import DockerRegistry

            logging.info("🧹 Pruning Docker cache...")
            logging.info(f"Max age: {args.cache_max_age} days")

            registry = DockerRegistry()

            # Show current stats
            stats_before = registry.get_registry_stats()
            logging.info(f"\nBefore pruning:")
            logging.info(f"  Cache entries: {stats_before['cache_entries']}")
            logging.info(f"  Total resources: {stats_before['total_resources']}")

            # Prune cache
            from panther.core.docker_builder.docker_cache_mixin import DockerCacheMixin

            cache_mixin = DockerCacheMixin()
            cache_mixin._docker_registry = registry

            pruned = cache_mixin.prune_cache(max_age_days=args.cache_max_age)

            logging.info(f"\nPruned:")
            logging.info(f"  Cache entries removed: {pruned['cache_entries']}")
            logging.info(f"  Images removed: {pruned['images']}")
            logging.info(f"  Space freed: {pruned['size_freed_mb']:.1f} MB")

            # Show after stats
            stats_after = registry.get_registry_stats()
            logging.info(f"\nAfter pruning:")
            logging.info(f"  Cache entries: {stats_after['cache_entries']}")
            logging.info(f"  Total resources: {stats_after['total_resources']}")

            logging.info("\n✅ Cache pruning completed")
            return 0

        except Exception as e:
            logging.info(f"❌ Error pruning cache: {e}")
            return 1

    @classmethod
    def _export_docker_registry(cls, args: Any) -> int:
        """Export Docker registry to file."""
        try:
            from pathlib import Path

            from panther.core.docker_registry import DockerRegistry

            export_path = Path(args.export_registry)

            logging.info(f"📤 Exporting Docker registry to: {export_path}")

            registry = DockerRegistry()
            registry.export_registry(export_path)

            # Show file size
            size_kb = export_path.stat().st_size / 1024
            logging.info(f"✅ Registry exported successfully ({size_kb:.1f} KB)")

            return 0

        except Exception as e:
            logging.info(f"❌ Error exporting registry: {e}")
            return 1

    @classmethod
    def _import_docker_registry(cls, args: Any) -> int:
        """Import Docker registry from file."""
        try:
            from pathlib import Path

            from panther.core.docker_registry import DockerRegistry

            import_path = Path(args.import_registry)

            if not import_path.exists():
                logging.info(f"❌ Import file not found: {import_path}")
                return 1

            logging.info(f"📥 Importing Docker registry from: {import_path}")

            # Ask for merge strategy
            response = input("Merge with existing registry? (Y/n): ")
            merge = response.lower() != "n"

            registry = DockerRegistry()
            registry.import_registry(import_path, merge=merge)

            # Show new stats
            stats = registry.get_registry_stats()
            logging.info(f"\n✅ Registry imported successfully")
            logging.info(f"Total resources: {stats['total_resources']}")
            logging.info(f"Cache entries: {stats['cache_entries']}")

            return 0

        except Exception as e:
            logging.info(f"❌ Error importing registry: {e}")
            return 1
