"""The reset step of the documentation pipeline, and where it writes.

``docs/`` is a tracked corpus of plan and spec files; the pipeline's generated
output belongs somewhere else entirely. The pipeline used to delete ``docs/``
on every build, so the reset step is asserted from both directions: the corpus
survives, and the generated directory comes back removed *and* recreated,
because the copy loops downstream write straight into it.
"""

import inspect
from pathlib import Path

import pytest

from panther.cli.commands import docs
from panther.tools import build_paths

pytestmark = pytest.mark.unit


def _seed_corpus_and_generated_output(root: Path) -> None:
    """Write one tracked-corpus file and one file in each generated directory.

    Args:
        root: Directory to treat as the project root for a reset.
    """
    (root / "docs").mkdir()
    (root / "docs" / "keep.md").write_text("tracked corpus\n")
    (root / build_paths.GENERATED_DOCS_DIR).mkdir()
    (root / build_paths.GENERATED_DOCS_DIR / "old.html").write_text("stale\n")
    (root / build_paths.SITE_DIR).mkdir()
    (root / build_paths.SITE_DIR / "index.html").write_text("stale render\n")


def test_reset_generated_output_preserves_docs(tmp_path):
    """The reset must clear generated output and leave the corpus alone.

    The third assertion is not decoration, and it is not a claim that some
    copy step downstream would crash without it — every one of them passes
    ``parents=True`` and would recreate the directory incidentally. It pins
    the postcondition to the reset itself rather than to five call sites, and
    it makes this test say what the release gate's
    ``find docs_build -type f | wc -l`` check says.
    """
    _seed_corpus_and_generated_output(tmp_path)

    docs._reset_generated_output(tmp_path)

    generated = tmp_path / build_paths.GENERATED_DOCS_DIR
    assert (tmp_path / "docs" / "keep.md").exists()
    assert not (generated / "old.html").exists()
    assert generated.is_dir() and not any(generated.iterdir())


def test_reset_generated_output_clears_the_rendered_site(tmp_path):
    """The rendered site is generated output too, and mkdocs recreates it.

    Its deletion shares a loop with the generated docs directory, so folding
    that loop into one step is exactly where it could be dropped. Asserted
    separately from the docs directory because the two are not symmetric: this
    one is removed and *not* recreated.
    """
    _seed_corpus_and_generated_output(tmp_path)

    docs._reset_generated_output(tmp_path)

    assert not (tmp_path / build_paths.SITE_DIR).exists()


def test_pipeline_reads_the_shared_directory_name():
    """One definition, reached at the point of use rather than re-spelled.

    A source scan and not an identity check: CPython interns
    identifier-shaped string constants, so ``docs.GENERATED_DOCS_DIR is
    build_paths.GENERATED_DOCS_DIR`` holds even for a module that writes the
    literal. Only the source discriminates. Scoped to the two function bodies
    so that prose elsewhere in the file cannot trip either negative needle.

    **What is pinned.** That the generated directory is reached through the
    shared name, that the pipeline does not re-spell that name as a literal,
    and that it does not name the tracked corpus instead. The last of those is
    the load-bearing one and it is not implied by the other two: restoring
    ``docs_dir = project_root / "docs"`` leaves ``GENERATED_DOCS_DIR`` present
    elsewhere in the body and introduces no ``docs_build`` literal, so a test
    carrying only the first two needles stays green while the ``docs_src``
    copy, the ``panther/**/*.md`` hierarchy and the ivy conversion all write
    into the corpus. That is an overwrite rather than a deletion, which is why
    the reset assertions above keep passing through it.

    **What is not pinned.** That the destination is *right* — only that it is
    spelled neither as a bare ``docs_build`` nor as a bare ``"docs"``. A
    corpus path reached through some third name, or assembled a character at a
    time, would pass all three needles.
    """
    bodies = inspect.getsource(docs._build_documentation) + inspect.getsource(
        docs._reset_generated_output
    )

    assert "GENERATED_DOCS_DIR" in bodies
    assert build_paths.GENERATED_DOCS_DIR not in bodies
    assert '"docs"' not in bodies, (
        "the pipeline names the tracked corpus as a directory to write into; "
        "the generated tree is what it may write to, reached through "
        "GENERATED_DOCS_DIR"
    )
