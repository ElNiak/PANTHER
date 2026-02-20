#!/usr/bin/env python3
"""
Interactive Protocol Plugin Tutorial for PANTHER

This tutorial guides you through creating protocol plugins for PANTHER,
covering protocol specification, test case generation, and validation rules.

Status: Under active development. Currently provides an overview and
references to existing protocol plugin examples.
"""

import sys
from pathlib import Path


class ProtocolPluginTutorial:
    """Interactive tutorial for creating PANTHER protocol plugins."""

    def __init__(self):
        self.tutorial_dir = Path(__file__).parent
        self.plugins_dir = self.tutorial_dir.parent.parent

    def run(self):
        """Run the protocol plugin tutorial."""
        self.display_header()
        self.display_overview()
        self.display_existing_examples()
        self.display_next_steps()
        return 0

    def display_header(self):
        """Display tutorial header."""
        print("=" * 70)
        print("  PANTHER Protocol Plugin Development Tutorial")
        print("=" * 70)

    def display_overview(self):
        """Display protocol plugin overview."""
        print()
        print("Protocol plugins define how PANTHER understands and tests")
        print("network protocols. They provide:")
        print()
        print("  - Protocol specification and version definitions")
        print("  - Test case generation rules")
        print("  - Validation and coverage analysis")
        print("  - Protocol-specific configuration schemas")
        print()
        print("Note: This tutorial is under active development.")
        print("      The interactive walkthrough will be added in a future release.")

    def display_existing_examples(self):
        """Show existing protocol plugin examples for reference."""
        print()
        print("-" * 50)
        print("  Existing Protocol Plugins (for reference)")
        print("-" * 50)
        print()

        protocols_dir = self.plugins_dir / "protocols"
        if protocols_dir.exists():
            found = False
            for item in sorted(protocols_dir.iterdir()):
                if item.is_dir() and not item.name.startswith(("_", ".", "tutorials")):
                    print(f"  - {item.name}/")
                    found = True
            if not found:
                print("  (no protocol plugins found in the plugins directory)")
        else:
            print(f"  Protocols directory: panther/plugins/protocols/")
            print("  (directory not found - check your installation)")

        print()
        print("  To examine a protocol plugin's structure:")
        print("    ls panther/plugins/protocols/<protocol_name>/")
        print()
        print("  Key files in each protocol plugin:")
        print("    - __init__.py        : Plugin registration")
        print("    - config_schema.py   : Configuration schema definition")
        print("    - <name>.py          : Core protocol implementation")

    def display_next_steps(self):
        """Display next steps for the user."""
        print()
        print("-" * 50)
        print("  Next Steps")
        print("-" * 50)
        print()
        print("  1. Browse existing protocol plugins for reference")
        print("  2. Read the plugin development guide:")
        print("     panther/plugins/development.md")
        print("  3. Try creating a service plugin first (more mature tutorial):")
        print("     panther tutorial run service")
        print("  4. Check back for updates to this tutorial")
        print()
        print("=" * 70)


if __name__ == "__main__":
    tutorial = ProtocolPluginTutorial()
    sys.exit(tutorial.run())
