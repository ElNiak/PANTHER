# https://mkdocstrings.github.io/recipes/#automatic-code-reference-pages

"""Generate the code reference pages and navigation."""

from pathlib import Path

import mkdocs_gen_files

nav = mkdocs_gen_files.Nav()

# Use cwd (mkdocs always runs from the project root where mkdocs.yml lives).
# Do NOT use Path(__file__).resolve() — that follows symlinks into
# site-packages when the package is installed non-editable.
root = Path.cwd()
srcs = [root / "panther"]

print(f"Generating reference pages in {root}")
print(f"Source directories: {srcs}")

# First process Python files
for src in srcs:
    print(f"Generating reference pages for Python files in {src}")
    for path in sorted(src.rglob("*.py")):
        # Include all files except those in panther_ivy directory (with specific exceptions)
        # This is more readable with explicit exclude/include logic
        if "/panther_ivy/" in path.as_posix():
            continue  # Skip entire submodule - has own docs

        module_path = (
            path.relative_to(root).with_suffix("").as_posix().replace("/", ".")
        )
        doc_path = path.relative_to(root).with_suffix(".md")
        full_doc_path = Path("panther", doc_path)
        print(f"  {module_path} -> {doc_path}")

        parts = tuple(module_path.split("."))

        if parts[-1] == "__init__":
            parts = parts[:-1]
            doc_path = doc_path.with_name("index.md")
            full_doc_path = full_doc_path.with_name("index.md")
        elif parts[-1] == "__main__":
            continue

        print(f"  Module: {parts} -> {doc_path}")
        nav[parts] = doc_path.as_posix()

        with mkdocs_gen_files.open(full_doc_path, "w") as fd:
            ident = ".".join(parts)
            fd.write(f"::: {ident}")

        # Use the original file path for edit links
        mkdocs_gen_files.set_edit_path(full_doc_path, Path("../../") / path)
        print(f"  Edit path set to: {Path('../../') / path}")

with mkdocs_gen_files.open("panther/SUMMARY.md", "w") as nav_file:
    nav_lit = nav.build_literate_nav()
    print(nav_lit)
    nav_file.writelines(nav_lit)
    print("Navigation file written to panther/SUMMARY.md")
