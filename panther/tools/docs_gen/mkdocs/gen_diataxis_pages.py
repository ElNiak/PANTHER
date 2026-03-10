"""Generate Diataxis explanation pages from module docstrings.

Registered as a gen-files hook in mkdocs.yml alongside gen_ref_pages.py.
Each explanation page extracts the module docstring at build time and writes
it as plain markdown — no mkdocstrings directive — so that autorefs only
registers identifiers from the Code Reference pages (gen_ref_pages.py).
"""

import ast
from pathlib import Path

import mkdocs_gen_files

EXPLANATION_PAGES = {
    "explanation/plugin_system.md": "panther/plugins/__init__.py",
    "explanation/config_system.md": "panther/config/__init__.py",
    "explanation/events.md": "panther/core/__init__.py",
}

root = Path.cwd()

for doc_path, source_file in EXPLANATION_PAGES.items():
    src = root / source_file
    if not src.exists():
        continue
    tree = ast.parse(src.read_text(encoding="utf-8"))
    docstring = ast.get_docstring(tree) or ""
    module_name = source_file.replace("/__init__.py", "").replace("/", ".")
    ref_path = source_file.replace("/__init__.py", "/index.md")
    with mkdocs_gen_files.open(doc_path, "w") as f:
        f.write(docstring + "\n")
        f.write(f"\n---\n\n")
        f.write(f"*Full API reference: [{module_name}](../panther/{ref_path})*\n")
