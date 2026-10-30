"""Which directories ``cleanup_build_artifacts`` measures, and which it skips.

The function reports a size for every directory the build writes, and the
tracked ``docs/`` corpus of plan and spec files is not one of them: it is
authored, not generated, and a measurement keyed on it invites a future reader
to treat it as disposable alongside ``build/`` and ``dist/``.

The report's values are floats, so "the corpus does not appear" cannot be
checked by looking for a path inside them. It is checked behaviourally
instead: the two directories are seeded with different amounts of data and the
totals have to account for the generated tree alone.
"""

from pathlib import Path

import pytest

from panther.builder_metrics.utils import cleanup_build_artifacts
from panther.tools.build_paths import CLEAN_DIRS, GENERATED_DOCS_DIR

pytestmark = pytest.mark.unit

# A literal, deliberately, and not a value read back from ``build_paths``.
# This is the one directory the shared constant must never name, so an
# assertion sourced from that constant would go green the moment somebody put
# the corpus back into it.
CORPUS_DIR = "docs"

# Different sizes, so the assertions can tell the two trees apart: were they
# equal, a report that measured the corpus instead of the generated tree would
# still add up.
CORPUS_MB = 3.0
GENERATED_MB = 1.0


def _fill(directory: Path, size_mb: float) -> None:
    """Create a directory holding exactly ``size_mb`` megabytes of data.

    Args:
        directory: Directory to create; missing parents are created too.
        size_mb: Size of the single file written into it, in megabytes.
    """
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "payload.bin").write_bytes(b"\0" * int(size_mb * 1024 * 1024))


def _measured_names(sizes: dict) -> set:
    """Recover the directory names a report is keyed on.

    Substring matching is wrong here: ``"docs" in "docs_build_size_mb"`` is
    true, so the corpus check has to compare whole names rather than look for
    the word inside a key.

    Args:
        sizes: A report as returned by ``cleanup_build_artifacts``.

    Returns:
        The directory name behind each ``"<name>_size_mb"`` key.
    """
    return {key.removesuffix("_size_mb") for key in sizes}


def test_measures_the_generated_docs_tree_and_not_the_tracked_corpus(tmp_path):
    """A seeded corpus is reported nowhere; the generated tree is reported."""
    _fill(tmp_path / CORPUS_DIR, CORPUS_MB)
    _fill(tmp_path / GENERATED_DOCS_DIR, GENERATED_MB)

    sizes = cleanup_build_artifacts(tmp_path)

    measured = _measured_names(sizes)
    assert CORPUS_DIR not in measured
    assert measured == set(CLEAN_DIRS)
    assert sizes[f"{GENERATED_DOCS_DIR}_size_mb"] == pytest.approx(GENERATED_MB)
    # Every other directory is absent from the root, so the generated tree is
    # the whole of the reported total and the corpus's megabytes went nowhere.
    assert sum(sizes.values()) == pytest.approx(GENERATED_MB)


def test_reports_a_zero_float_for_every_directory_a_bare_root_lacks(tmp_path):
    """The report's shape does not depend on what is on disk."""
    sizes = cleanup_build_artifacts(tmp_path)

    assert set(sizes) == {f"{name}_size_mb" for name in CLEAN_DIRS}
    assert all(isinstance(value, float) for value in sizes.values())
    assert set(sizes.values()) == {0.0}
