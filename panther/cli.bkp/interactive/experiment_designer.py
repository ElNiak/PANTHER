"""
Interactive experiment designer for PANTHER.

Provides a guided interface for creating experiment configurations.
"""

import logging
from pathlib import Path
from typing import Optional

import yaml

from panther.cli.interactive.builders import GlobalConfigBuilder, TestConfigBuilder
from panther.cli.interactive.validation_helper import ValidationHelper


class ExperimentDesigner:
    """Main orchestrator for interactive experiment configuration design."""

    def __init__(
        self,
        output_path: str,
        from_file: Optional[str] = None,
        quick_mode: bool = False,
    ):
        """Initialize the experiment designer.

        Args:
            output_path: Path where the configuration will be saved
            from_file: Optional existing configuration to start from
            quick_mode: If True, use more defaults and skip optional configs
        """
        self.output_path = Path(output_path)
        self.from_file = Path(from_file) if from_file else None
        self.quick_mode = quick_mode
        self.config = {}
        self.validation_helper = ValidationHelper()

    def run(self) -> bool:
        """Run the interactive designer.

        Returns:
            True if configuration was successfully created, False otherwise
        """
        try:
            # Welcome and mode selection
            self._show_welcome()

            # Load existing config if provided
            if self.from_file:
                if not self._load_existing_config():
                    return False

            # Build configuration
            if not self.config:
                # Starting fresh
                self._build_from_scratch()
            else:
                # Modifying existing
                self._modify_existing()

            # Review and validate
            if not self._review_and_validate():
                return False

            # Save configuration
            return self._save_configuration()

        except KeyboardInterrupt:
            logging.info("\n\n⚠️  Design session cancelled by user")
            return False
        except Exception as e:
            logging.info(f"\n❌ Error during design: {e}")
            import traceback

            traceback.print_exc()
            return False

    def _show_welcome(self):
        """Show welcome message and design tips."""
        if self.quick_mode:
            logging.info("\n🚀 Quick Mode: Using sensible defaults where possible")
        else:
            logging.info(
                "\n📋 Full Mode: Complete control over all configuration options"
            )

        logging.info("\n💡 Design Tips:")
        logging.info("  • Start simple - you can always add complexity later")
        logging.info("  • Use Ctrl+C to cancel at any time")
        logging.info("  • Default values are shown in parentheses")
        logging.info("  • Leave optional fields empty to skip them")

    def _load_existing_config(self) -> bool:
        """Load and validate existing configuration."""
        logging.info(f"\n📂 Loading existing configuration: {self.from_file}")

        try:
            with open(self.from_file, "r") as f:
                self.config = yaml.safe_load(f) or {}

            logging.info("✅ Configuration loaded successfully")

            # Show summary
            test_count = len(self.config.get("tests", []))
            logging.info(f"\n📊 Summary:")
            logging.info(f"  • Tests: {test_count}")

            if test_count > 0:
                for i, test in enumerate(self.config["tests"], 1):
                    service_count = len(test.get("services", {}))
                    logging.info(
                        f"  • Test {i} '{test.get('name', 'Unnamed')}': {service_count} services"
                    )

            return True

        except yaml.YAMLError as e:
            logging.info(f"❌ YAML error in existing file: {e}")
            return False
        except FileNotFoundError:
            logging.info(f"❌ File not found: {self.from_file}")
            return False
        except Exception as e:
            logging.info(f"❌ Error loading file: {e}")
            return False

    def _build_from_scratch(self):
        """Build a new configuration from scratch."""
        logging.info("\n🏗️  Building new configuration from scratch")

        # Global configuration
        global_builder = GlobalConfigBuilder(self.quick_mode)
        self.config.update(global_builder.build())

        # Tests
        self.config["tests"] = []
        self._add_tests()

    def _modify_existing(self):
        """Modify an existing configuration."""
        logging.info("\n✏️  Modifying existing configuration")

        while True:
            logging.info("\n🔧 What would you like to do?")
            logging.info("  1. Add a new test")
            logging.info("  2. Modify global configuration")
            logging.info("  3. Modify an existing test")
            logging.info("  4. Remove a test")
            logging.info("  5. Review current configuration")
            logging.info("  6. Done with modifications")

            choice = input("\nEnter choice [1-6]: ").strip()

            if choice == "1":
                self._add_single_test()
            elif choice == "2":
                self._modify_global_config()
            elif choice == "3":
                self._modify_test()
            elif choice == "4":
                self._remove_test()
            elif choice == "5":
                self._show_config_summary()
            elif choice == "6":
                break
            else:
                logging.info("❌ Invalid choice. Please enter 1-6.")

    def _add_tests(self):
        """Add tests to the configuration."""
        test_count = 0

        while True:
            test_count += 1
            logging.info(f"\n📝 Configuring Test {test_count}")

            test_builder = TestConfigBuilder(test_count, self.quick_mode)
            test_config = test_builder.build()
            self.config["tests"].append(test_config)

            if test_count == 1:
                # Always ask for at least one test
                if not self._prompt_bool("\nAdd another test?", False):
                    break
            else:
                if not self._prompt_bool("\nAdd another test?", False):
                    break

    def _add_single_test(self):
        """Add a single test to existing configuration."""
        test_count = len(self.config.get("tests", [])) + 1
        test_builder = TestConfigBuilder(test_count, self.quick_mode)
        test_config = test_builder.build()

        if "tests" not in self.config:
            self.config["tests"] = []

        self.config["tests"].append(test_config)
        logging.info(f"✅ Test '{test_config['name']}' added successfully")

    def _modify_global_config(self):
        """Modify global configuration settings."""
        logging.info("\n🌐 Modifying global configuration")
        logging.info("(Note: This will overwrite existing global settings)")

        if self._prompt_bool("Continue?", True):
            global_builder = GlobalConfigBuilder(self.quick_mode)
            new_global = global_builder.build()

            # Merge with existing, preserving tests
            tests = self.config.get("tests", [])
            self.config.update(new_global)
            self.config["tests"] = tests

            logging.info("✅ Global configuration updated")

    def _modify_test(self):
        """Modify an existing test."""
        if not self.config.get("tests"):
            logging.info("❌ No tests to modify")
            return

        # List tests
        logging.info("\n📋 Available tests:")
        for i, test in enumerate(self.config["tests"], 1):
            logging.info(f"  {i}. {test.get('name', 'Unnamed test')}")

        choice = input(
            f"\nSelect test to modify [1-{len(self.config['tests'])}]: "
        ).strip()

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(self.config["tests"]):
                logging.info(
                    f"\n✏️  Modifying test: {self.config['tests'][idx].get('name')}"
                )
                logging.info("(Note: This will replace the entire test configuration)")

                if self._prompt_bool("Continue?", True):
                    test_builder = TestConfigBuilder(idx + 1, self.quick_mode)
                    self.config["tests"][idx] = test_builder.build()
                    logging.info("✅ Test modified successfully")
            else:
                logging.info("❌ Invalid test number")
        except ValueError:
            logging.info("❌ Please enter a valid number")

    def _remove_test(self):
        """Remove a test from the configuration."""
        if not self.config.get("tests"):
            logging.info("❌ No tests to remove")
            return

        # List tests
        logging.info("\n📋 Available tests:")
        for i, test in enumerate(self.config["tests"], 1):
            logging.info(f"  {i}. {test.get('name', 'Unnamed test')}")

        choice = input(
            f"\nSelect test to remove [1-{len(self.config['tests'])}]: "
        ).strip()

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(self.config["tests"]):
                test_name = self.config["tests"][idx].get("name", "Unnamed test")
                if self._prompt_bool(f"Remove test '{test_name}'?", True):
                    self.config["tests"].pop(idx)
                    logging.info(f"✅ Test '{test_name}' removed")
            else:
                logging.info("❌ Invalid test number")
        except ValueError:
            logging.info("❌ Please enter a valid number")

    def _show_config_summary(self):
        """Show current configuration summary."""
        logging.info("\n📊 Current Configuration Summary")
        logging.info("=" * 50)

        # Global settings
        if "logging" in self.config:
            logging.info(f"Logging: {self.config['logging'].get('level', 'INFO')}")

        if "docker" in self.config:
            build_images = self.config["docker"].get("force_build_docker_image", False)
            logging.info(f"Docker: Build images = {build_images}")

        # Tests
        test_count = len(self.config.get("tests", []))
        logging.info(f"\nTests: {test_count}")

        for i, test in enumerate(self.config.get("tests", []), 1):
            logging.info(f"\n  Test {i}: {test.get('name', 'Unnamed')}")
            logging.info(
                f"    Network: {test.get('network_environment', {}).get('type', 'unknown')}"
            )

            services = test.get("services", {})
            logging.info(f"    Services: {len(services)}")
            for svc_name, svc_config in services.items():
                impl = svc_config.get("implementation", {}).get("name", "unknown")
                role = svc_config.get("protocol", {}).get("role", "unknown")
                logging.info(f"      • {svc_name}: {impl} ({role})")

    def _review_and_validate(self) -> bool:
        """Review and validate the configuration."""
        logging.info("\n🔍 Configuration Review")
        logging.info("=" * 50)

        # Show final configuration
        self._show_config_summary()

        # Validate
        logging.info("\n🔎 Validating configuration...")

        # Basic validation
        errors = []

        if not self.config.get("tests"):
            errors.append("No tests defined")

        for i, test in enumerate(self.config.get("tests", []), 1):
            if not test.get("services"):
                errors.append(f"Test {i} has no services")
            else:
                # Validate service relationships
                service_errors = self.validation_helper.validate_service_relationships(
                    test["services"]
                )
                errors.extend(service_errors)

        if errors:
            logging.info("\n❌ Validation errors found:")
            for error in errors:
                logging.info(f"  • {error}")

            if not self._prompt_bool("\nProceed anyway?", False):
                return False
        else:
            logging.info("✅ Configuration validation passed")

        return True

    def _save_configuration(self) -> bool:
        """Save the configuration to file."""
        logging.info(f"\n💾 Saving configuration to: {self.output_path}")

        try:
            # Create directory if needed
            self.output_path.parent.mkdir(parents=True, exist_ok=True)

            # Check if file exists
            if self.output_path.exists():
                if not self._prompt_bool(
                    f"File {self.output_path} exists. Overwrite?", True
                ):
                    # Suggest alternative name
                    base = self.output_path.stem
                    ext = self.output_path.suffix
                    counter = 1
                    while True:
                        new_path = self.output_path.parent / f"{base}_{counter}{ext}"
                        if not new_path.exists():
                            self.output_path = new_path
                            logging.info(
                                f"📝 Using alternative name: {self.output_path}"
                            )
                            break
                        counter += 1

            # Save configuration
            with open(self.output_path, "w") as f:
                yaml.dump(self.config, f, default_flow_style=False, sort_keys=False)

            logging.info(f"✅ Configuration saved successfully!")

            # Show next steps
            logging.info("\n🎯 Next Steps:")
            logging.info(
                f"  1. Validate: panther config validate --config {self.output_path} --explain"
            )
            logging.info(f"  2. Run: panther run --config {self.output_path}")

            return True

        except Exception as e:
            logging.info(f"❌ Error saving configuration: {e}")
            return False

    def _prompt_bool(self, message: str, default: bool = True) -> bool:
        """Prompt for yes/no question."""
        default_str = "Y/n" if default else "y/N"
        response = input(f"{message} [{default_str}]: ").strip().lower()

        if not response:
            return default

        return response in ["y", "yes", "true", "1"]
