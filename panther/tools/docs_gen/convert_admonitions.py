#!/usr/bin/env python3
"""Convert between MkDocs admonitions and GitHub markdown callouts.

MkDocs format:
    !!! note "Title"
        Body line 1
        Body line 2

    ??? warning "Collapsible Title"
        Body line

GitHub format:
    > [!NOTE]
    > "Title"
    > Body line 1
    > Body line 2

Usage:
    python scripts/convert_admonitions.py --to-github FILE [FILE ...]
    python scripts/convert_admonitions.py --to-mkdocs FILE [FILE ...]
    python scripts/convert_admonitions.py --to-github --in-place FILE [FILE ...]

    # Pipe / stdin
    cat README.md | python scripts/convert_admonitions.py --to-github -
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Mapping between MkDocs type keywords and GitHub callout types.
# GitHub supports: NOTE, TIP, IMPORTANT, WARNING, CAUTION
_MKDOCS_TO_GITHUB = {
    "note": "NOTE",
    "tip": "TIP",
    "hint": "TIP",
    "important": "IMPORTANT",
    "warning": "WARNING",
    "caution": "CAUTION",
    "danger": "CAUTION",
    "attention": "WARNING",
    "admonition": "NOTE",
    "info": "NOTE",
    "question": "NOTE",
    "example": "TIP",
    "quote": "NOTE",
    "abstract": "NOTE",
    "summary": "NOTE",
    "success": "TIP",
    "check": "TIP",
    "failure": "CAUTION",
    "bug": "CAUTION",
}

_GITHUB_TO_MKDOCS = {
    "NOTE": "note",
    "TIP": "tip",
    "IMPORTANT": "important",
    "WARNING": "warning",
    "CAUTION": "danger",
}

# ---------------------------------------------------------------------------
# MkDocs → GitHub
# ---------------------------------------------------------------------------

# Matches  !!! type "title"  or  ??? type "title"  or  ???+ type "title"
_MKDOCS_OPEN = re.compile(
    r"^(?P<indent> *)(?:!!!|\?\?\?)\+?\s+"
    r"(?P<type>\w+)"
    r'(?:\s+"(?P<title>[^"]*)")?'
    r"\s*$"
)


def _mkdocs_to_github(text: str) -> str:
    lines = text.split("\n")
    result: list[str] = []
    i = 0

    while i < len(lines):
        m = _MKDOCS_OPEN.match(lines[i])
        if not m:
            result.append(lines[i])
            i += 1
            continue

        admon_type = m.group("type").lower()
        title = m.group("title") or ""
        gh_type = _MKDOCS_TO_GITHUB.get(admon_type, "NOTE")

        result.append(f"> [!{gh_type}]")
        if title:
            result.append(f'> "{title}"')

        # Consume indented body (4-space or 1-tab indent relative to the marker)
        i += 1
        body_indent = m.group("indent") + "    "
        while i < len(lines):
            line = lines[i]
            # Blank line inside admonition → keep as empty quote line
            if line.strip() == "":
                # Peek ahead: if next non-blank line is still indented, it's
                # part of the admonition body; otherwise we're done.
                j = i + 1
                while j < len(lines) and lines[j].strip() == "":
                    j += 1
                if j < len(lines) and (
                    lines[j].startswith(body_indent)
                    or lines[j].startswith(m.group("indent") + "\t")
                ):
                    result.append(">")
                    i += 1
                    continue
                else:
                    break
            elif line.startswith(body_indent) or line.startswith(
                m.group("indent") + "\t"
            ):
                content = (
                    line[len(body_indent) :]
                    if line.startswith(body_indent)
                    else line.lstrip("\t")
                )
                result.append(f"> {content}" if content else ">")
                i += 1
            else:
                break

    return "\n".join(result)


# ---------------------------------------------------------------------------
# GitHub → MkDocs
# ---------------------------------------------------------------------------

_GITHUB_OPEN = re.compile(
    r"^>\s*\[!(?P<type>NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]\s*$",
    re.IGNORECASE,
)
_GITHUB_TITLE = re.compile(r'^>\s*"(?P<title>[^"]*)"\s*$')
_GITHUB_BODY = re.compile(r"^>(?P<content>.*)$")


def _github_to_mkdocs(text: str) -> str:
    lines = text.split("\n")
    result: list[str] = []
    i = 0

    while i < len(lines):
        m = _GITHUB_OPEN.match(lines[i])
        if not m:
            result.append(lines[i])
            i += 1
            continue

        gh_type = m.group("type").upper()
        mkdocs_type = _GITHUB_TO_MKDOCS.get(gh_type, "note")

        title = ""
        i += 1
        # Check for optional title line
        if i < len(lines):
            tm = _GITHUB_TITLE.match(lines[i])
            if tm:
                title = tm.group("title")
                i += 1

        if title:
            result.append(f'!!! {mkdocs_type} "{title}"')
        else:
            result.append(f"!!! {mkdocs_type}")

        # Consume  > body  lines
        while i < len(lines):
            bm = _GITHUB_BODY.match(lines[i])
            if not bm:
                break
            content = bm.group("content")
            # Strip the leading space after >
            if content.startswith(" "):
                content = content[1:]
            result.append(f"    {content}" if content else "")
            i += 1

    return "\n".join(result)


# ---------------------------------------------------------------------------
# Public API (used by panther_builder.py)
# ---------------------------------------------------------------------------

mkdocs_to_github = _mkdocs_to_github
github_to_mkdocs = _github_to_mkdocs


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    """CLI entry point for converting between MkDocs admonitions and GitHub callouts."""
    parser = argparse.ArgumentParser(
        description="Convert between MkDocs admonitions and GitHub callouts.",
    )
    direction = parser.add_mutually_exclusive_group(required=True)
    direction.add_argument(
        "--to-github", action="store_true", help="MkDocs → GitHub callouts"
    )
    direction.add_argument(
        "--to-mkdocs", action="store_true", help="GitHub callouts → MkDocs"
    )
    parser.add_argument(
        "--in-place",
        "-i",
        action="store_true",
        help="Modify files in place (ignored for stdin)",
    )
    parser.add_argument(
        "files",
        nargs="+",
        help="Markdown files to convert (use '-' for stdin)",
    )
    args = parser.parse_args()

    convert = _mkdocs_to_github if args.to_github else _github_to_mkdocs

    for filepath in args.files:
        if filepath == "-":
            sys.stdout.write(convert(sys.stdin.read()))
            continue

        path = Path(filepath)
        text = path.read_text(encoding="utf-8")
        converted = convert(text)

        if args.in_place:
            path.write_text(converted, encoding="utf-8")
            print(f"Converted: {path}", file=sys.stderr)
        else:
            sys.stdout.write(converted)


if __name__ == "__main__":
    main()
