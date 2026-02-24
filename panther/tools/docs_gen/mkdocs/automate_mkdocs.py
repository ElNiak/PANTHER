"""Automates Python scripts formatting, linting and Mkdocs documentation."""

import ast
import importlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Union

import yaml


def add_val(indices, value, data):
    if not len(indices):
        return
    element = data
    for index in indices[:-1]:
        element = element[index]
    element[indices[-1]] = value


def automate_mkdocs_from_docstring(
    mkdocs_dir: str | Path, mkgendocs_f: str, repo_dir: Path, match_string: str
) -> dict:
    """Automates the -pages for mkgendocs package by adding all Python functions in a directory to the mkgendocs config.
    Args:
        mkdocs_dir (typing.Union[str, pathlib.Path]): textual directory for the hierarchical directory & navigation in Mkdocs
        mkgendocs_f (str): The configurations file for the mkgendocs package
        repo_dir (pathlib.Path): textual directory to search for Python functions in
        match_string (str): the text to be matches, after which the functions will be added in mkgendocs format
    Example:
        >>>
        >>> automate_mkdocs_from_docstring('scripts', repo_dir=Path.cwd(), match_string='pages:')
    Returns:
        list: list of created markdown files and their relative paths

    """
    p = repo_dir.glob("panther/**/*.py")
    scripts = [x for x in p if x.is_file()]

    if (
        Path.cwd() != repo_dir
    ):  # look for mkgendocs.yml in the parent file if a subdirectory is used
        repo_dir = repo_dir.parent

    functions = defaultdict(dict)
    structure = fix(defaultdict)()
    full_repo_dir = str(repo_dir) + "/"
    for script in scripts:
        print("Current script: ", script)
        if "/panther_ivy/" in str(script):
            continue
        with open(script) as source:
            tree = ast.parse(source.read())
        funcs = {"classes": [], "functions": []}
        for child in ast.iter_child_nodes(tree):
            print("Current child: ", child)
            try:
                if isinstance(
                    child, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)
                ):
                    if child.name not in ["main"]:
                        # script = script.replace("/panther/", "/")
                        relative_path = (
                            str(script)
                            .replace(full_repo_dir, "")
                            .replace("/", ".")
                            .replace(".py", "")
                        )
                        print("Relative path: ", relative_path)
                        module = importlib.import_module(relative_path)
                        print("Module: ", module)
                        f_ = getattr(module, child.name)
                        function = f_.__name__
                        # TODO dataclass
                        if isinstance(child, (ast.ClassDef)):
                            funcs["classes"].append(function)
                        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            funcs["functions"].append(function)

            except Exception as e:
                print("trouble on importing " + script.stem)
                print("did not document " + child.name)
                print(str(e))
                # exit()
        if not funcs["classes"]:
            funcs.pop("classes")
        if not funcs["functions"]:
            funcs.pop("functions")
        if funcs:
            functions[script] = funcs

    with open(f"{repo_dir}/{mkgendocs_f}", "r+") as mkgen_config:
        insert_string = ""
        for path, function_names in functions.items():
            relative_path = str(path).replace(full_repo_dir, "").replace(".py", "")
            insert_string += (
                f'  - page: "{relative_path}.md"\n    '
                f'source: "{relative_path}.py"\n'  # functions:\n'
            )
            page = f"{relative_path}"
            split_page = page.split("/")
            split_page = ["  - " + s for s in split_page]
            page += ".md"

            add_val(split_page, page, structure)
            for class_name, class_list in function_names.items():
                insert_string += f"    {class_name}:\n"
                f_string = ""
                for f in class_list:
                    insert_f_string = f"      - {f}\n"
                    f_string += insert_f_string

                insert_string += f_string
            insert_string += "\n"

        contents = mkgen_config.readlines()
        if match_string in contents[-1]:
            contents.append(insert_string)
        else:
            for index, line in enumerate(contents):
                if match_string in line and insert_string not in contents[index + 1]:
                    contents = contents[: index + 1]
                    contents.append(insert_string)
                    break

    with open(f"{repo_dir}/{mkgendocs_f}", "w") as mkgen_config:
        mkgen_config.writelines(contents)

    return structure


def include_markdown_files(
    mkdocs_dir: str | Path, mkgendocs_f: str, repo_dir: Path, match_string: str
) -> dict:
    """Include existing markdown files in the mkgendocs.yml configuration.

    Args:
        mkdocs_dir (typing.Union[str, pathlib.Path]): textual directory for the hierarchical directory & navigation in Mkdocs
        mkgendocs_f (str): The configurations file for the mkgendocs package
        repo_dir (pathlib.Path): textual directory to search for markdown files in
        match_string (str): the text to be matches, after which the markdown files will be added in mkgendocs format

    Returns:
        dict: Structure representing the added markdown files
    """

    # Get specific markdown files from targeted directories
    p = []

    # Root markdown files
    root_md_files = [
        "README.md",
        "CHANGELOG.md",
        "CONTRIBUTING.md",
        "PACKAGING.md",
        "QUICK_START.md",
        "WORKFLOW.md",
    ]

    # Add root markdown files
    for md_file in root_md_files:
        file_path = repo_dir / md_file
        if file_path.exists():
            p.append(file_path)

    # Add markdown files from panther/tools/docs_gen directory
    docs_gen_files = list(repo_dir.glob("panther/tools/docs_gen/**/*.md"))
    p.extend([x for x in docs_gen_files if x.is_file()])

    # Add markdown files from panther directory
    panther_files = list(repo_dir.glob("panther/**/*.md"))
    p.extend([x for x in panther_files if x.is_file()])

    # Create the target directory if it doesn't exist
    target_dir = repo_dir / "docs" / "panther"
    target_dir.mkdir(parents=True, exist_ok=True)

    # # Copy markdown files from panther/ to docs/panther/
    # for md_file in panther_files:
    #     if md_file.is_file():
    #         # Determine relative path from panther/ directory
    #         rel_path = md_file.relative_to(repo_dir / "panther")
    #         # Create the target path
    #         dest_path = target_dir / rel_path
    #         # Create parent directories if they don't exist
    #         dest_path.parent.mkdir(parents=True, exist_ok=True)
    #         # Copy the file
    #         shutil.copy2(md_file, dest_path)
    #         print(f"Copied: {md_file} -> {dest_path}")

    if Path.cwd() != repo_dir:
        repo_dir = repo_dir.parent

    structure = fix(defaultdict)()
    full_repo_dir = str(repo_dir) + "/"

    # First, read the existing configuration to avoid duplicates
    existing_entries = set()
    try:
        with open(f"{repo_dir}/{mkgendocs_f}") as f:
            content = f.read()
            # Extract source paths from existing entries using a simple pattern match
            import re

            sources = re.findall(r'source:\s*"([^"]+)"', content)
            for source in sources:
                existing_entries.add(source)
        print(f"Found {len(existing_entries)} existing entries in {mkgendocs_f}")
    except Exception as e:
        print(f"Error reading existing configuration: {e}")
        existing_entries = set()

    # Prepare new entries
    new_entries = []
    for md_file in p:
        relative_path = str(md_file).replace(full_repo_dir, "")

        # Skip if this file is already in the configuration
        if relative_path in existing_entries:
            print(f"Skipping already included file: {relative_path}")
            continue

        dest_path = f"{relative_path.replace('.md', '')}"

        # Add to new entries
        new_entries.append({"source": relative_path, "page": f"{dest_path}.md"})

        # Create structure for nav
        split_page = dest_path.split("/")
        split_page = ["  - " + s for s in split_page]
        dest_path += ".md"
        add_val(split_page, dest_path, structure)

    # If there's nothing to add, just return
    if not new_entries:
        print("No new markdown files to add.")
        return structure

    # Format entries for insertion
    insert_string = ""
    for entry in new_entries:
        insert_string += (
            f'  - page: "{entry["page"]}"\n    source: "{entry["source"]}"\n\n'
        )

    # Update the configuration file
    try:
        print(f"Updating {mkgendocs_f} with new entries...")
        with open(f"{repo_dir}/{mkgendocs_f}") as f:
            contents = f.readlines()

        # Find the right position to insert new entries
        insertion_point = None
        for index, line in enumerate(contents):
            if match_string.strip() in line.strip():
                insertion_point = index + 1
                # Find the end of existing entries
                while (
                    insertion_point < len(contents)
                    and contents[insertion_point].strip()
                    and contents[insertion_point].strip().startswith("  -")
                ):
                    insertion_point += 1
                break

        if insertion_point:
            contents.insert(insertion_point, insert_string)
            with open(f"{repo_dir}/{mkgendocs_f}", "w") as f:
                f.writelines(contents)
            print(f"Added {len(new_entries)} new markdown files to {mkgendocs_f}")
        else:
            print(f"Could not find insertion point in {mkgendocs_f}")
    except Exception as e:
        print(f"Error updating configuration: {e}")

    return structure


def automate_nav_structure(
    mkdocs_dir: str | Path,
    mkdocs_f: str,
    repo_dir: Path,
    match_string: str,
    structure: dict,
) -> None:
    """Automates the navigation structure in the mkdocs.yml configuration file.
    Args:
        mkdocs_dir (typing.Union[str, pathlib.Path]): textual directory for the hierarchical directory & navigation in Mkdocs
        mkdocs_f (str): The configurations file for the mkdocs
        repo_dir (pathlib.Path): textual directory to search for Python functions in
        match_string (str): the text to be matched, after which the navigation structure will be added
        structure (dict): The navigation structure to insert
    Returns:
        None
    """
    insert_string = yaml.safe_dump(json.loads(json.dumps(structure, indent=4))).replace(
        "'", ""
    )

    with open(f"{repo_dir}/{mkdocs_f}") as mkgen_config:
        print("Insert string: ", insert_string)
        contents = mkgen_config.readlines()

        # Find the current nav section
        nav_start = None
        nav_end = None

        for index, line in enumerate(contents):
            if match_string.strip() in line.strip():
                nav_start = index
                # Find where the nav section ends (either next top-level YAML key or EOF)
                for i in range(index + 1, len(contents)):
                    if contents[i].strip() and not contents[i].startswith("  "):
                        nav_end = i
                        break
                break

        if nav_start is not None:
            # If we didn't find an end, it means nav extends to EOF
            if nav_end is None:
                nav_end = len(contents)

            # Build new contents with updated nav
            print(f"Nav section found from {nav_start} to {nav_end}")
            # Create new contents with the insert_string
            print("Current contents: ", contents)
            new_contents = contents[: nav_start + 1]  # Include the "nav:" line
            new_contents.append(insert_string)
            new_contents.extend(contents[nav_end:])  # Add everything after nav section
            contents = new_contents

    with open(f"{repo_dir}/{mkdocs_f}", "w") as mkgen_config:
        mkgen_config.writelines(contents)


def fix(f):
    """Allows creation of arbitrary length dict item

    Args:
        f (type): Description of parameter `f`.

    Returns:
        type: Description of returned object.

    """
    return lambda *args, **kwargs: f(fix(f), *args, **kwargs)


def indent(string: str) -> int:
    """Count the indentation in whitespace characters.
    Args:
        string (str): text with indents
    Returns:
        int: Number of whitespace indentations

    """
    return sum(4 if char == "\t" else 1 for char in string[: -len(string.lstrip())])


def merge_structures(structure1: dict, structure2: dict) -> dict:
    """Merge two navigation structures.

    Args:
        structure1 (dict): First structure to merge
        structure2 (dict): Second structure to merge

    Returns:
        dict: Merged navigation structure
    """
    result = fix(defaultdict)()

    # Helper function to deeply merge dictionaries
    def _merge(s1, s2):
        for k, v in s2.items():
            if k in s1:
                if isinstance(v, dict) and isinstance(s1[k], dict):
                    _merge(s1[k], v)
                else:
                    s1[k] = v
            else:
                s1[k] = v

    # Create a copy of structure1
    for k, v in structure1.items():
        if isinstance(v, dict):
            result[k] = defaultdict()
            _merge(result[k], v)
        else:
            result[k] = v

    # Merge with structure2
    for k, v in structure2.items():
        if isinstance(v, dict):
            if k not in result:
                result[k] = defaultdict()
            _merge(result[k], v)
        else:
            result[k] = v

    return result


def main():
    """Execute when running this script."""
    python_tips_dir = Path.cwd().joinpath(".")
    print("Python Tips Directory: ", python_tips_dir)

    # Process Python files
    structure_py = automate_mkdocs_from_docstring(
        mkdocs_dir="panther",
        mkgendocs_f="mkgendocs.yml",
        repo_dir=python_tips_dir,
        match_string="pages:\n",
    )

    print("Structure from Python files: ", structure_py)

    # structure_md = include_markdown_files(
    #     mkdocs_dir="panther",
    #     mkgendocs_f="mkgendocs.yml",
    #     repo_dir=python_tips_dir,
    #     match_string="pages:\n",
    # )
    # print("Structure from Markdown files: ", structure_md)

    # # Update navigation
    # automate_nav_structure(
    #     mkdocs_dir=".",
    #     mkdocs_f="mkdocs.yml",
    #     repo_dir=python_tips_dir,
    #     match_string="- Code Reference: panther/\n",
    #     structure=structure_md,
    # )


if __name__ == "__main__":
    main()
