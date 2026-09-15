"""The clean step of both build entry points, and the directory list they share.

``docs/`` is a tracked corpus of plan and spec files; only ``docs_build/`` holds
generated output. Both cleaners must agree on that distinction, and they must
agree because they read one definition rather than two copies of a literal.
"""

import inspect
import subprocess
import sys
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
    """One definition, and both cleaners reach it at the point of use.

    Two independent claims, because neither alone is enough. The identity
    check catches a tuple rebuilt at module level: it would compare equal but
    would not be the same object. The source check catches a literal written
    inside the function body, which identity cannot see at all, because it
    reads the module-level binding and never looks at the loop.

    The needle is positive on purpose. A negative needle for ``"docs"`` misses
    a *correct* duplicate — ``["build", "dist", "docs_build", "site",
    "htmlcov"]`` inlined in the body — because ``"docs"`` is not a substring of
    ``"docs_build"``, and every other assertion here still passes on it.
    """
    assert "docs" not in build_paths.CLEAN_DIRS
    assert build_paths.GENERATED_DOCS_DIR in build_paths.CLEAN_DIRS

    assert build.CLEAN_DIRS is build_paths.CLEAN_DIRS
    assert panther_builder.CLEAN_DIRS is build_paths.CLEAN_DIRS

    assert "CLEAN_DIRS" in inspect.getsource(build._clean_build_artifacts)
    assert "CLEAN_DIRS" in inspect.getsource(panther_builder._clean)


def test_builder_resolves_build_paths_from_repo_root():
    """The bootstrap import must reach this checkout, never an installed copy."""
    repo_root = Path(panther_builder.__file__).resolve().parent

    assert Path(build_paths.__file__).resolve().is_relative_to(repo_root)


@pytest.mark.parametrize("unsafe", ["/etc", "/", "..", "../..", ".", "", "a/b"])
def test_clean_dirs_rejects_entries_that_are_not_one_relative_segment(unsafe):
    """Every entry is fed to ``shutil.rmtree(project_root / entry)`` unchecked.

    ``pathlib`` makes that dangerous in two distinct ways: an absolute right
    operand discards the left entirely, so ``Path('/repo') / '/etc'`` is
    ``/etc``; and ``''`` or ``'.'`` resolve back to the root itself, so the
    clean would delete the project. Both must be refused, loudly.
    """
    with pytest.raises(ValueError):
        build_paths._reject_unsafe_segments((unsafe,))


def test_shipped_clean_dirs_pass_the_guard():
    """The guard must accept what the module actually ships."""
    build_paths._reject_unsafe_segments(build_paths.CLEAN_DIRS)


_CLEAN_DIRS_LINE = (
    'CLEAN_DIRS = ("build", "dist", GENERATED_DOCS_DIR, SITE_DIR, "htmlcov")'
)
_CLEAN_DIRS_WITHOUT_SITE_DIR = (
    'CLEAN_DIRS = ("build", "dist", GENERATED_DOCS_DIR, "htmlcov")'
)


def _import_mutated_build_paths(tmp_path, mutations):
    """Import a copy of ``build_paths`` whose source has been rewritten.

    The guard is only worth anything if it *runs*, and nothing that calls
    ``_reject_unsafe_segments`` directly can tell whether the module invokes
    it at import. Importing a deliberately unsafe copy in a subprocess can:
    the import either raises or it does not, and a copy is used because the
    real module has already been imported into this interpreter.

    Each ``before`` must occur exactly once in the real source. That is what
    keeps the anchors honest — reformat the module and this helper fails
    loudly, rather than writing an unmutated copy that imports cleanly and
    hands every caller a pass for the wrong reason.

    Args:
        tmp_path: Directory the copy is written to and imported from.
        mutations: ``(before, after)`` pairs applied to the module source.

    Returns:
        The completed subprocess that attempted the import.
    """
    source = Path(build_paths.__file__).read_text(encoding="utf-8")
    for before, after in mutations:
        assert source.count(before) == 1, f"anchor no longer unique: {before!r}"
        source = source.replace(before, after)

    module_path = tmp_path / "build_paths_under_test.py"
    module_path.write_text(source, encoding="utf-8")

    return subprocess.run(
        [sys.executable, "-c", "import build_paths_under_test"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )


def test_unmutated_build_paths_copy_imports_cleanly(tmp_path):
    """Control for the two mutation tests below.

    Without it, a copy that fails to import for some unrelated reason — a bad
    path, a stray syntax error — would satisfy every "the import must fail"
    assertion and report a guard that is not there.
    """
    result = _import_mutated_build_paths(tmp_path, ())

    assert result.returncode == 0, result.stderr


def test_import_rejects_an_unsafe_docs_build_target(tmp_path):
    """The rmtree targets must be validated in their own right.

    ``GENERATED_DOCS_DIR`` and ``SITE_DIR`` are handed to ``shutil.rmtree``
    by the documentation pipeline, which never consults ``CLEAN_DIRS``. They
    pass the guard today only because ``CLEAN_DIRS`` happens to contain them,
    and "what a clean removes" and "where the docs build writes" are two
    concepts that merely coincide. The mutation separates them — an unsafe
    ``SITE_DIR`` that ``CLEAN_DIRS`` no longer mentions — so only a guard
    call that names the rmtree targets can refuse it.
    """
    result = _import_mutated_build_paths(
        tmp_path,
        (
            ('SITE_DIR = "site"', 'SITE_DIR = ".."'),
            (_CLEAN_DIRS_LINE, _CLEAN_DIRS_WITHOUT_SITE_DIR),
        ),
    )

    assert result.returncode != 0, result.stdout
    assert "ValueError" in result.stderr


def test_import_rejects_an_unsafe_clean_dirs_entry(tmp_path):
    """The other half of the wiring, pinned the same way.

    ``"htmlcov"`` is a clean target and nothing else, so only the guard call
    over ``CLEAN_DIRS`` can refuse it. Delete that call and this goes red.
    """
    result = _import_mutated_build_paths(tmp_path, (('"htmlcov"', '".."'),))

    assert result.returncode != 0, result.stdout
    assert "ValueError" in result.stderr


def test_build_paths_imports_without_site_packages():
    """The bootstrap imports this before any dependency is installed.

    ``-S`` drops ``site`` entirely, so no ``site-packages`` and no ``.pth``
    files are on the path. A third-party import anywhere in the chain fails
    here, rather than at somebody's first ``package-dev`` on a bare checkout.
    """
    repo_root = Path(panther_builder.__file__).resolve().parent

    result = subprocess.run(
        [
            sys.executable,
            "-S",
            "-c",
            "from panther.tools.build_paths import CLEAN_DIRS",
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
