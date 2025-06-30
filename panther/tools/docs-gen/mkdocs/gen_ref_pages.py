# https://mkdocstrings.github.io/recipes/#automatic-code-reference-pages

"""Generate the code reference pages and navigation."""

from pathlib import Path

import mkdocs_gen_files

nav = mkdocs_gen_files.Nav()

# Adjust root to be the top-level directory of the project
root = Path(__file__).resolve().parent.parent.parent.parent
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
            # Only include these specific files from panther_ivy
            if not (
                "/panther_ivy/panther_ivy.py" in path.as_posix()
                or "/panther_ivy/config_schema.py" in path.as_posix()
            ):
                continue  # Skip this file

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

# # Now process Markdown files in source directories
# print("Generating reference pages for Markdown files in source directories")
# for src in srcs:
#     for path in sorted(src.rglob("**/*.md")):
#         # Create appropriate path for documentation
#         relative_path = path.relative_to(root)
#         parent_dir = relative_path.parent
#         doc_path = parent_dir / path.name
#         full_doc_path = Path("panther", doc_path)

#         # Create navigation entry
#         module_parts = tuple(parent_dir.as_posix().split("/"))
#         if module_parts[-1] == "__init__":
#             module_parts = module_parts[:-1]
#             doc_path = doc_path.with_name("index.md")
#             full_doc_path = full_doc_path.with_name("index.md")
#         elif module_parts[-1] == "__main__":
#             continue

#         print(f"  Markdown: {parent_dir.as_posix()} -> {doc_path}")

#         # Add to navigation
#         nav[module_parts] = doc_path.as_posix()

#         # Read Markdown content
#         with open(path) as md_file:
#             md_content = md_file.read()

#         with mkdocs_gen_files.open(full_doc_path, "w") as fd:
#             ident = ".".join(parts)
#             fd.write(f"::: {ident}")

#         # Set edit path
#         mkdocs_gen_files.set_edit_path(full_doc_path, Path("../../") / path)
#         print(f"  Edit path set to: {Path('../../') / path}")

# # Process Markdown files at the root of the project
# print("Generating reference pages for Markdown files at project root")
# for path in sorted(root.glob("*.md")):
#     # Create appropriate path for documentation
#     relative_path = path.relative_to(root)
#     parent_dir = relative_path.parent
#     doc_path = parent_dir / path.name
#     full_doc_path = Path("panther", doc_path)

#     print(f"  Root Markdown: {path.name} -> {doc_path}")

#     # Add to navigation with a "Project" prefix to distinguish from package docs
#     nav[("Project", path.stem)] = doc_path.as_posix()

#     # Read Markdown content
#     with open(path) as md_file:
#         md_content = md_file.read()

#     # Write Markdown content to the documentation
#     with mkdocs_gen_files.open(full_doc_path, "w") as fd:
#         ident = ".".join(parts)
#         fd.write(f"::: {ident}")

#     # Set edit path
#     mkdocs_gen_files.set_edit_path(full_doc_path, Path("../../") / path)
#     print(f"  Edit path set to: {Path('../../') / path}")

with mkdocs_gen_files.open("panther/SUMMARY.md", "w") as nav_file:
    nav_lit = nav.build_literate_nav()
    print(nav_lit)
    nav_file.writelines(nav_lit)
    print("Navigation file written to panther/SUMMARY.md")
