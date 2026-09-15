"""The clean step of both build entry points, and the directory list they share.

``docs/`` is a tracked corpus of plan and spec files; only ``docs_build/`` holds
generated output. Both cleaners must agree on that distinction, and they must
agree because they read one definition rather than two copies of a literal.
"""

import inspect
from pathlib import Path

import pytest

import panther_builder
from panther.cli.commands import build
from panther.tools import build_paths

pytestmark = pytest.mark.unit


def _seed_corpus_and_generated_output(root: Path) -> None:
    """Write one tracked-corpus file and one generated file under ``root``.

    Args:
        root: Directory to treat as the project root for a clean.
    """
    (root / "docs").mkdir()
    (root / "docs" / "keep.md").write_text("tracked corpus\n")
    (root / "docs_build").mkdir()
    (root / "docs_build" / "generated.md").write_text("generated output\n")


def test_clean_preserves_docs_directory(tmp_path):
    """``panther build clean`` must not delete the tracked corpus."""
    _seed_corpus_and_generated_output(tmp_path)

    build._clean_build_artifacts(tmp_path)

    assert (tmp_path / "docs" / "keep.md").exists()
    assert not (tmp_path / "docs_build" / "generated.md").exists()


def test_builder_clean_preserves_docs_directory(tmp_path):
    """The bootstrap script cleans before the CLI exists, so it must agree."""
    _seed_corpus_and_generated_output(tmp_path)

    panther_builder._clean(tmp_path)

    assert (tmp_path / "docs" / "keep.md").exists()
    assert not (tmp_path / "docs_build" / "generated.md").exists()


def test_clean_dirs_exclude_docs():
    """One definition, reached by both consumers: no literal list survives.

    The identity check is the load-bearing half. A tuple literal rebuilt in a
    consumer would compare equal but would not be the same object, so ``is``
    catches a copy that ``==`` would wave through.
    """
    assert "docs" not in build_paths.CLEAN_DIRS
    assert build_paths.GENERATED_DOCS_DIR in build_paths.CLEAN_DIRS

    assert build.CLEAN_DIRS is build_paths.CLEAN_DIRS
    assert panther_builder.CLEAN_DIRS is build_paths.CLEAN_DIRS

    assert '"docs"' not in inspect.getsource(build._clean_build_artifacts)
    assert '"docs"' not in inspect.getsource(panther_builder._clean)


def test_builder_resolves_build_paths_from_repo_root():
    """The bootstrap import must reach this checkout, never an installed copy."""
    repo_root = Path(panther_builder.__file__).resolve().parent

    assert Path(build_paths.__file__).resolve().is_relative_to(repo_root)
