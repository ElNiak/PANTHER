"""Link-rewriting helpers for documentation copies.

Provides functions to rewrite markdown links during documentation builds,
handling flat copies, hierarchy copies, non-doc link stripping, and
Ivy-to-Markdown conversion.
"""

import re
from pathlib import Path

_MD_LINK_RE = re.compile(r"(!?\[([^\]]*)\])\(([^)]+)\)")
_MD_REF_LINK_RE = re.compile(r"^(\s*\[([^\]]+)\]:\s+)(\S+)", re.MULTILINE)
_NON_DOC_EXTS = frozenset(
    {
        ".html",
        ".py",
        ".sh",
        ".txt",
        ".pdf",
        ".yml",
        ".yaml",
        ".json",
        ".toml",
        ".cfg",
        ".ini",
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".svg",
        ".ico",
        ".c",
        ".h",
        ".cpp",
        ".rs",
        ".go",
        ".java",
    }
)
_URL_PREFIXES = ("http://", "https://", "mailto:", "ftp://", "#")

# Regex to match single-backtick inline code (not inside code fences).
_INLINE_CODE_RE = re.compile(r"(?<!`)(`[^`\n]+?`)(?!`)")

# Regex to match [word] patterns that are NOT part of markdown links.
_MD_LINK_BRACKET_RE = re.compile(r"!?\[([^\]]*)\]\([^)]+\)")
_ALL_BRACKET_RE = re.compile(r"\[([^\]]+)\]")


def read_md_as_utf8(src):
    """Read a markdown file, decoding to UTF-8."""
    raw = src.read_bytes()
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("latin-1")  # Fallback: latin-1 accepts all byte values


def strip_non_doc_links(text):
    """Strip links to non-markdown/non-doc targets, keeping display text."""

    def _replace(m):
        display = m.group(2)
        target = m.group(3)
        if any(target.startswith(p) for p in _URL_PREFIXES):
            return m.group(0)
        path_part = target.split("#")[0]
        if not path_part:
            return m.group(0)
        suffix = Path(path_part).suffix.lower()
        # Rewrite .ivy links to .md
        if suffix == ".ivy":
            new_target = str(Path(path_part).with_suffix(".md"))
            if "#" in target:
                new_target += "#" + target.split("#", 1)[1]
            return f"{m.group(1)}({new_target})"
        if suffix in _NON_DOC_EXTS:
            return display
        return m.group(0)

    text = _MD_LINK_RE.sub(_replace, text)

    def _replace_ref(m):
        target = m.group(3)
        if any(target.startswith(p) for p in _URL_PREFIXES):
            return m.group(0)
        suffix = Path(target.split("#")[0]).suffix.lower()
        if suffix in _NON_DOC_EXTS:
            return ""
        return m.group(0)

    text = _MD_REF_LINK_RE.sub(_replace_ref, text)
    return text


def _inline_to_html(m):
    """Convert a backtick inline code span to an HTML <code> tag."""
    content = m.group(1)[1:-1]
    return f"<code>{content}</code>"


def _escape_bare_brackets(line):
    """Escape square brackets that aren't part of markdown links."""
    placeholders = []

    def _protect(m):
        placeholders.append(m.group(0))
        return f"\x00LINK{len(placeholders) - 1}\x00"

    protected = _MD_LINK_BRACKET_RE.sub(_protect, line)
    escaped = _ALL_BRACKET_RE.sub(lambda m: f"\\[{m.group(1)}\\]", protected)
    for i, original in enumerate(placeholders):
        escaped = escaped.replace(f"\x00LINK{i}\x00", original)
    return escaped


def escape_autorefs(text):
    r"""Escape patterns that mkdocs_autorefs misinterprets in Ivy docs.

    Handles two cases:
    1. Backtick inline code (e.g. ``range``) -> ``<code>range</code>``
    2. Bare square brackets (e.g. ``[packet_number]``) -> ``\\[packet_number\\]``

    Both are only applied outside of fenced code blocks.
    """
    in_fence = False
    lines = text.split("\n")
    result = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            result.append(line)
        elif in_fence:
            result.append(line)
        else:
            line = _INLINE_CODE_RE.sub(_inline_to_html, line)
            line = _escape_bare_brackets(line)
            result.append(line)
    return "\n".join(result)


def rewrite_links_flat(text, source_rel_path, build_dict, project_root):
    """Rewrite links for a flat-copied doc file.

    Resolves each relative link against the source file's directory, looks it
    up in *build_dict* to find the flat target name, falls back to hierarchy
    path, or strips the link entirely when the target cannot be resolved.
    """
    source_dir = (project_root / source_rel_path).parent
    flat_lookup = {src: Path(dst).name for src, dst in build_dict.items()}

    def _replace(m):
        prefix = m.group(1)
        display = m.group(2)
        target = m.group(3)
        if any(target.startswith(p) for p in _URL_PREFIXES):
            return m.group(0)
        if "#" in target:
            path_part, fragment = target.split("#", 1)
            fragment = "#" + fragment
        else:
            path_part = target
            fragment = ""
        if not path_part:
            return m.group(0)
        suffix = Path(path_part).suffix.lower()
        if suffix == ".ivy":
            path_part = str(Path(path_part).with_suffix(".md"))
            suffix = ".md"
        if suffix in _NON_DOC_EXTS:
            return display
        try:
            resolved = (source_dir / path_part).resolve()
            repo_rel = str(resolved.relative_to(project_root))
        except (ValueError, OSError):
            return display  # Fallback: return display text when path cannot be resolved
        if repo_rel in flat_lookup:
            return f"{prefix}({flat_lookup[repo_rel]}{fragment})"
        if repo_rel.startswith("panther/") and (project_root / repo_rel).exists():
            return f"{prefix}({repo_rel}{fragment})"
        return display

    text = _MD_LINK_RE.sub(_replace, text)

    def _replace_ref(m):
        target = m.group(3)
        if any(target.startswith(p) for p in _URL_PREFIXES):
            return m.group(0)
        suffix = Path(target.split("#")[0]).suffix.lower()
        if suffix in _NON_DOC_EXTS:
            return ""
        return m.group(0)

    text = _MD_REF_LINK_RE.sub(_replace_ref, text)
    return text


def copy_md_rewriting_links(
    src, dst, *, source_rel=None, build_dict=None, project_root=None
):
    """Copy markdown file with link rewriting.

    For *flat* copies: provide ``source_rel``, ``build_dict``, ``project_root``
    to resolve links against the build dictionary.
    For *hierarchy* copies: omit those params -- only non-doc links are stripped.

    GitHub-style callouts (``> [!NOTE]``) are converted to MkDocs
    admonitions (``!!! note``) automatically.
    """
    text = read_md_as_utf8(src)
    if source_rel is not None and build_dict is not None and project_root is not None:
        text = rewrite_links_flat(text, source_rel, build_dict, project_root)
    else:
        text = strip_non_doc_links(text)
    from panther.tools.docs_gen.convert_admonitions import github_to_mkdocs

    text = github_to_mkdocs(text)
    dst.write_text(text, encoding="utf-8")
