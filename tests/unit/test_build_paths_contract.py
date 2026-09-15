"""Where mkdocs reads from and writes to, and what may not put it back.

The documentation pipeline writes its generated tree to ``docs_build/`` and
``docs/`` is a tracked corpus, so ``mkdocs.yml`` has to say so: mkdocs' own
default for ``docs_dir`` is ``docs``, which is precisely the corpus. Nothing
downstream catches a mistake here either — the ``same-dir`` plugin replaces
``mkdocs.config.config_options.Dir.post_validation`` in its ``__init__``, which
removes mkdocs' guard against ``docs_dir``/``site_dir`` overlap — so these
assertions are the only thing standing between a wrong value and a build that
renders, or deletes, the wrong tree.

The build used to copy a tracked ``mkdocs.yml.bak`` over ``mkdocs.yml`` on
every run. That backup was stale, so the copy silently reverted whatever the
live config said; a single build dropped a nav entry. Two tests below pin
that the mechanism is gone, because with it in place the first test's subject
is rewritten from disk before mkdocs ever reads it.

The remaining tests pin the same split across the tooling that surrounds the
build: which of the two directories the ignore rules cover, which one the sdist
recipe names, which one pytest walks, and which one ``panther build clean``
tells a user it is about to delete.
"""

import configparser
import inspect
import subprocess
from pathlib import Path

import pytest
import yaml

import panther_builder
from panther.cli.commands import docs
from panther.cli.commands.build import clean
from panther.tools import build_paths

pytestmark = pytest.mark.unit

REPO_ROOT = Path(panther_builder.__file__).resolve().parent

# The corpus directory gets a literal rather than a constant, deliberately.
# ``build_paths`` names the directories the build *writes*, and this is the one
# directory in the contract it must never write to; giving it an entry there
# would invite a cleaner to iterate over it. It is the subject of these
# assertions, not a second spelling of a shared value.
CORPUS_DIR = "docs"


class _TagTolerantLoader(yaml.SafeLoader):
    """A ``SafeLoader`` that resolves every unknown tag to ``None``.

    ``mkdocs.yml`` carries four ``!!python/...`` tags and one ``!relative``,
    which ``yaml.safe_load`` refuses with ``ConstructorError``. Constructing
    them is out of the question here — that is arbitrary import and call — and
    mkdocs' own ``load_config`` is worse for a test, because instantiating the
    plugins patches ``Dir.post_validation`` process-wide and leaks into
    whatever runs next. Resolving unknown tags to ``None`` reads the plain
    keys this module asserts on and touches nothing else.
    """


_TagTolerantLoader.add_multi_constructor("", lambda loader, suffix, node: None)


def _load_mkdocs_config() -> dict:
    """Parse the shipped ``mkdocs.yml`` without constructing its Python tags.

    Returns:
        The top-level mapping of the configuration file.
    """
    text = (REPO_ROOT / "mkdocs.yml").read_text(encoding="utf-8")
    return yaml.load(text, Loader=_TagTolerantLoader)


def test_mkdocs_declares_generated_docs_dir():
    """The generated tree is mkdocs' input, and the tracked corpus is not.

    Both values are compared against the shared constants rather than against
    string literals: a test that spelled ``"docs_build"`` itself would keep
    passing after the constant moved and the pipeline started writing
    somewhere mkdocs no longer reads.
    """
    config = _load_mkdocs_config()

    assert config["docs_dir"] == build_paths.GENERATED_DOCS_DIR
    assert config["site_dir"] == build_paths.SITE_DIR


def test_no_tracked_mkdocs_backup():
    """The stale backup must not exist, because the build copied it over."""
    backup = REPO_ROOT / "panther" / "tools" / "docs_gen" / "mkdocs.yml.bak"

    assert not backup.exists()


def test_docs_module_does_not_restore_mkdocs_config():
    """No code path may put a backup copy back over the live config.

    Structural rather than behavioural, deliberately: the restore lived in the
    middle of ``_build_documentation``, which shells out to pip, pytest and
    mkdocs, and is not callable in a unit test. Deleting the backup file is
    not enough on its own — the block also *wrote* one on every run, so it
    would recreate its own input from the first build onwards. Scanning source
    for the name is an established convention here
    (``tests/test_documented_tool_params.py``).
    """
    assert "mkdocs.yml.bak" not in inspect.getsource(docs)


def _check_ignore(*paths: str) -> subprocess.CompletedProcess:
    """Ask git which of ``paths`` the repository's ignore rules match.

    Two flags carry the whole meaning of these assertions and neither is
    optional. ``--no-index`` is the load-bearing one: ``check-ignore``
    consults the index by default and reports a *tracked* path as not
    ignored however ``.gitignore`` reads, so the index-aware form silently
    answers "is this file tracked?" — always yes, for a corpus file — rather
    than "would a rule match it?", and passes just as happily with the
    corpus ignored as without. ``core.excludesFile=/dev/null`` drops the
    developer's personal ignore file, so a machine-local rule cannot decide
    the verdict on someone's laptop and not in CI.

    Args:
        paths: Repository-relative pathnames to test. They need not exist on
            disk; ``check-ignore`` matches rules against names.

    Returns:
        The completed process. Exit status 0 means at least one path matched
        a rule and 1 means none did, while ``stdout`` names each path that
        matched together with the rule that matched it.

    Raises:
        RuntimeError: If git itself failed, which it reports as status 128
            and which neither verdict should be read from.
    """
    result = subprocess.run(
        [
            "git",
            "-C",
            str(REPO_ROOT),
            "-c",
            "core.excludesFile=/dev/null",
            "check-ignore",
            "--no-index",
            "--verbose",
            "--stdin",
        ],
        input="\n".join(paths),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode not in (0, 1):
        raise RuntimeError(f"git check-ignore failed: {result.stderr.strip()}")
    return result


def _tracked_corpus_paths() -> list[str]:
    """List the corpus files git currently tracks.

    Returns:
        Repository-relative pathnames under the corpus directory. The list is
        empty on a checkout that has committed no plan yet, which is why the
        caller also tests a synthetic path.
    """
    result = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "ls-files", CORPUS_DIR],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.splitlines()


def _manifest_directives() -> list[list[str]]:
    """Split ``MANIFEST.in`` into whitespace-separated directives.

    Returns:
        One token list per line that carries a directive, with blank lines
        and comments dropped.
    """
    text = (REPO_ROOT / "MANIFEST.in").read_text(encoding="utf-8")
    return [
        line.split()
        for line in text.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def test_corpus_is_not_gitignored():
    """No ignore rule may cover the tracked corpus.

    A single ``docs/`` rule used to, and it cost on both sides of the line:
    every plan and spec needed ``git add -f`` to commit, and any corpus file
    not yet committed was invisible to ``git status`` and destroyed outright
    by ``git clean -fdx``.
    """
    # A synthetic path stands alongside the real ones so this can never pass
    # vacuously: on a checkout whose corpus is still empty — production
    # tracks nothing under it — the measured list alone would test nothing.
    representative = f"{CORPUS_DIR}/superpowers/plans/2026-01-01-example.md"
    result = _check_ignore(representative, *_tracked_corpus_paths())

    assert result.returncode == 1, (
        "ignore rules match corpus files, which therefore need 'git add -f' "
        f"to commit and are deleted by 'git clean -fdx':\n{result.stdout}"
    )


def test_generated_docs_is_gitignored():
    """Generated documentation must stay out of the index.

    The other half of the move, asserted separately because relocating a
    rule has to land somewhere and not merely leave: without this, a docs
    build offers its whole regenerated tree to the next commit.
    """
    result = _check_ignore(f"{build_paths.GENERATED_DOCS_DIR}/index.md")

    assert result.returncode == 0, (
        f"{build_paths.GENERATED_DOCS_DIR}/ is not ignored, so a docs build "
        "leaves its generated tree staged for the next commit"
    )


def test_manifest_ships_generated_docs_not_corpus():
    """The sdist recipe must name the generated tree, not the corpus.

    This is parity, not a feature. ``docs_build/`` is gitignored and absent
    from a fresh checkout, so an sdist built from a clean tree carries no
    documentation either before or after — exactly as true today, where
    ``docs/`` is likewise gitignored and ``production`` tracks nothing under
    it. What the repoint buys is that the recipe stops naming a corpus of
    plan and spec files it was never meant to publish.
    """
    directives = _manifest_directives()
    included = [d[1] for d in directives if d[0] == "recursive-include" and d[1:]]
    pruned = [d[1] for d in directives if d[0] == "prune" and d[1:]]

    assert build_paths.GENERATED_DOCS_DIR in included
    assert CORPUS_DIR not in included, "the sdist recipe still ships the corpus"
    # ``prune docs/site`` named a directory the pipeline no longer writes; the
    # rendered site now sits at the project root, outside every include above.
    assert not [p for p in pruned if p.split("/")[0] == CORPUS_DIR]


def test_pytest_does_not_recurse_into_generated_docs():
    """Collection must skip the generated tree.

    A docs build leaves behind a copy of every Markdown file the project can
    produce, and collection walks whatever it finds on every run afterwards.
    """
    # interpolation=None: the log_*_format values carry %(asctime)s, which the
    # default parser reads as interpolation syntax and refuses.
    parser = configparser.ConfigParser(interpolation=None)
    parser.read(REPO_ROOT / "tests" / "pytest.ini", encoding="utf-8")

    norecursedirs = parser["pytest"]["norecursedirs"].split()

    assert build_paths.GENERATED_DOCS_DIR in norecursedirs


def test_clean_help_enumerates_only_what_clean_removes():
    """``panther build clean`` must not offer to delete the corpus.

    Its docstring named ``docs/`` for as long as the cleaner removed it, and
    that sentence is the only warning a user gets before a command that
    calls ``shutil.rmtree``. The enumeration is checked against
    ``CLEAN_DIRS`` rather than against the one stale name, so the prose has
    to keep up the next time the tuple changes.
    """
    # click wraps the function, so the prose lives on the callback.
    help_text = clean.callback.__doc__

    for dir_name in build_paths.CLEAN_DIRS:
        assert f"{dir_name}/" in help_text, f"clean removes {dir_name}/ unannounced"
    assert f"{CORPUS_DIR}/" not in help_text, "clean still claims to remove the corpus"
