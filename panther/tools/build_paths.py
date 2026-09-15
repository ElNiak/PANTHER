"""Directory names the build and documentation pipelines write to.

One definition, imported by every consumer, so the two build entry points
cannot drift apart. ``docs/`` is deliberately absent from ``CLEAN_DIRS``: it is
a tracked corpus of plan and spec files, not generated output, and a cleaner
that removes it destroys work no build can reproduce.

Attributes:
    GENERATED_DOCS_DIR: Directory the documentation build writes into.
    SITE_DIR: Directory the rendered documentation site is written to.
    CLEAN_DIRS: Directory names a clean removes from the project root.
"""

GENERATED_DOCS_DIR = "docs_build"
SITE_DIR = "site"
CLEAN_DIRS = ("build", "dist", GENERATED_DOCS_DIR, SITE_DIR, "htmlcov")
