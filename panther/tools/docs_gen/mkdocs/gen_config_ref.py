"""Generate Config Schema reference page from Pydantic models.

Discovers all config_schema.py files under panther/plugins/ and generates
mkdocstrings directives for each. griffe-pydantic renders Field descriptions
as schema tables automatically.
"""

from pathlib import Path

import mkdocs_gen_files

root = Path.cwd()
plugins_dir = root / "panther" / "plugins"
config_files = sorted(plugins_dir.rglob("config_schema.py"))

lines = [
    "# Configuration Schema Reference\n\n",
    (
        "This page is auto-generated from Pydantic models in each plugin's "
        "`config_schema.py`.\n\n"
    ),
]

for config_file in config_files:
    # Skip __pycache__, panther_ivy submodule, venvs, build dirs
    if "__pycache__" in config_file.parts:
        continue
    if ".venv" in config_file.parts or "build" in config_file.parts:
        continue
    if "panther_ivy" in config_file.parts:
        continue

    # Convert file path to module path
    rel = config_file.relative_to(root)
    module = rel.with_suffix("").as_posix().replace("/", ".")

    # Derive a readable section title from the path
    parts = list(rel.parts)
    # e.g. panther/plugins/environments/network_environment/docker_compose/config_schema.py
    # -> "Docker Compose (Network Environment)"
    if len(parts) >= 4:
        plugin_name = parts[-2].replace("_", " ").title()
        category = parts[-3].replace("_", " ").title() if len(parts) >= 5 else ""
        title = f"{plugin_name}" + (f" ({category})" if category else "")
    else:
        title = module

    lines.append(f"## {title}\n\n")
    lines.append(f"::: {module}\n")
    lines.append("    options:\n")
    lines.append("      show_source: false\n")
    lines.append("      members: true\n")
    lines.append("      show_root_heading: false\n\n")

with mkdocs_gen_files.open("reference/config_schema.md", "w") as f:
    f.writelines(lines)
