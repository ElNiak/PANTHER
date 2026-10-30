"""Where mkdocs reads from and writes to, and what may not put it back.

The documentation pipeline writes its generated tree to ``docs_build/`` and
``docs/`` is a tracked corpus, so ``mkdocs.yml`` has to say so: mkdocs' own
default for ``docs_dir`` is ``docs``, which is precisely the corpus.

Nothing downstream catches a mistake here. mkdocs' guard
(``SiteDir.post_validation``, ``mkdocs/config/config_options.py:781``) rejects
only *containment* — one of the two directories lying inside the other — and
the wrong values that matter here are siblings: ``docs_dir: docs`` beside a
separate ``site_dir``, and ``site_dir: docs`` beside ``docs_dir: docs_build``,
are both accepted in silence, plugin or no plugin. The ``same-dir`` plugin
then narrows the guard further, though not by removing it: it patches ``Dir``
and ``DocsDir`` (``mkdocs_same_dir/plugin.py:22,24``) and leaves ``SiteDir``'s
own body running, but ``_replace_validation`` (``:46-49``) first rewrites
``docs_dir`` to ``…/docs/.``, and the unnormalised ``startswith`` test for a
``site_dir`` *inside* ``docs_dir`` no longer matches. Measured on the
installed versions: ``docs_dir: docs`` with ``site_dir: docs/site`` is
rejected without the plugin and accepted with it, while the other direction
(``site_dir`` containing ``docs_dir``) still fires either way. So these
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
from distutils.filelist import FileList
from pathlib import Path

try:  # Python 3.11 and later
    import tomllib
except ModuleNotFoundError:  # Python 3.10, where pytest itself pins tomli
    import tomli as tomllib

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

# Names a plan or spec could plausibly carry. They are asserted on instead of
# only the files that happen to exist today, because "no tracked name collides
# with an ignore rule" is a property of the names people have reached for so
# far and not of the rules.
#
# The tuple carries one entry per rule that had to be anchored to the
# repository root, and the entry has to be a name the *unanchored* form would
# match, or the rule is pinned by nothing. Two ways to get that wrong, both of
# which this tuple made and both of which are fixed below: a dated
# ``2026-09-15-REVIEW.md`` does not match the exact-basename rule ``REVIEW.md``,
# so the plain name is listed too; and ``coordination`` matches a *directory*,
# which ``coordination.md`` cannot exercise, so a file beneath one is listed as
# well. Anything removed from here silently un-pins a rule.
PLAUSIBLE_CORPUS_PATHS = (
    f"{CORPUS_DIR}/superpowers/plans/2026-09-15-REVIEW.md",
    f"{CORPUS_DIR}/research/2026-09-15-Threat_Report.md",
    f"{CORPUS_DIR}/superpowers/plans/AUDIT-sp6.md",
    f"{CORPUS_DIR}/coordination.md",
    f"{CORPUS_DIR}/superpowers/memory/notes.md",
    f"{CORPUS_DIR}/build/notes.md",
    f"{CORPUS_DIR}/research/2026-09-15-notes.txt",
    f"{CORPUS_DIR}/superpowers/plans/REVIEW.md",
    f"{CORPUS_DIR}/CROSS_REVIEW.md",
    f"{CORPUS_DIR}/ONBOARDING.md",
    f"{CORPUS_DIR}/coordination/notes.md",
)

# The tree the sdist recipe is executed against. Fixed names rather than the
# files on disk, so the assertions describe the recipe and not the checkout.
#
# The last entry sits directly under the corpus directory and the others are
# nested, because ``include`` anchors on the pattern exactly as written: with
# only nested paths here, an ``include docs/*.md`` appended below the prune
# matches nothing and re-ships the corpus with every assertion still green. No
# tracked file sits at the top level of the corpus today, so that entry exists
# for the recipe's sake rather than the checkout's -- and the sibling ignore
# test above already treats ``docs/coordination.md`` as a name the corpus can
# take.
SYNTHETIC_CORPUS = (
    f"{CORPUS_DIR}/superpowers/plans/2026-01-01-example.md",
    f"{CORPUS_DIR}/research/2026-01-01-example.md",
    f"{CORPUS_DIR}/coordination.md",
)
SYNTHETIC_GENERATED = (
    f"{build_paths.GENERATED_DOCS_DIR}/index.md",
    f"{build_paths.GENERATED_DOCS_DIR}/api/panther.md",
)
# One ordinary packaged module, asserted to survive so that a recipe which
# pruned everything could not pass the corpus assertion vacuously.
SYNTHETIC_SOURCE = "panther/cli/commands/docs.py"

# pytest's own lookup, keyed by file name: which section a file's settings live
# in is decided by the file it is in, and reading the wrong one makes a setting
# that is plainly declared invisible to a test. These are the ini-style entries
# of the list pytest searches (``_pytest/config/findpaths.py:103-107``), paired
# with the section ``load_config_dict_from_file`` reads from each.
# ``pyproject.toml`` is the remaining entry and is handled separately below,
# being TOML rather than ini.
PYTEST_INI_SECTIONS = {
    "pytest.ini": "pytest",
    ".pytest.ini": "pytest",
    "tox.ini": "pytest",
    "setup.cfg": "tool:pytest",
}


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


def _ignored_paths(*paths: str) -> dict[str, str]:
    """Map each of ``paths`` the ignore rules genuinely exclude to its rule.

    The process exit status cannot answer this. ``--verbose`` reports the last
    pattern that matched a path, and a *negated* pattern matches exactly as a
    positive one does: with a re-include covering the corpus, ``check-ignore``
    prints ``!/docs/**/build/*`` for a file that is emphatically not ignored
    and exits 0 for it. ``returncode`` therefore answers "did any rule match?"
    rather than "is anything ignored?", and the two part company the moment a
    negation governs the directory under test — which one now does. Only the
    pattern text discriminates, so it is read here rather than the status.

    Args:
        paths: Repository-relative pathnames to test. They need not exist on
            disk.

    Returns:
        One entry per genuinely-ignored path, mapping it to the rule that
        excluded it as ``.gitignore:<line>:<pattern>``. A path that matched no
        rule, and a path whose last match was a negation, are both absent.
    """
    ignored: dict[str, str] = {}
    for line in _check_ignore(*paths).stdout.splitlines():
        rule, tab, pathname = line.partition("\t")
        if not tab:
            continue
        pattern = rule.split(":", 2)[2]
        if not pattern.startswith("!"):
            ignored[pathname] = rule
    return ignored


def _format_ignored(ignored: dict[str, str]) -> str:
    """Render ``_ignored_paths`` output one path per line for a failure.

    Args:
        ignored: The mapping returned by ``_ignored_paths``.

    Returns:
        A newline-joined block naming each path and the rule that hid it.
    """
    return "\n".join(f"  {path}  <- {rule}" for path, rule in ignored.items())


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


def _sdist_filelist(manifest_text: str) -> list[str]:
    """Report which files a ``MANIFEST.in`` template would ship in an sdist.

    Behavioural rather than a scan for directive tokens, because the
    directives apply *in order* and a token scan cannot see order: a ``graft
    docs`` appended below the ``prune`` puts the whole corpus back, and a scan
    that merely finds a ``prune docs`` somewhere in the file reports the
    recipe safe. The template is therefore executed, through the same
    ``FileList`` that setuptools' own ``manifest_maker`` drives.

    Seeding ``files`` before the first directive runs is what makes the result
    mean anything. ``setuptools-scm`` registers a ``setuptools.file_finders``
    entry point, so ``add_defaults`` calls ``walk_revctrl()`` and every
    git-tracked file is already in the list by the time the template is read.
    Starting from an empty list would make ``prune docs`` inert, and deleting
    it outright would then go unnoticed here.

    Args:
        manifest_text: Contents of a ``MANIFEST.in``. Blank lines and comments
            are dropped, as ``read_template`` drops them.

    Returns:
        The surviving paths, sorted and de-duplicated the way
        ``manifest_maker`` leaves them.
    """
    file_list = FileList()
    # Assigned before the first include-type directive: when allfiles is None,
    # include_pattern falls back to findall(), which walks the process's
    # current working directory.
    file_list.allfiles = [*SYNTHETIC_CORPUS, *SYNTHETIC_GENERATED, SYNTHETIC_SOURCE]
    # The generated tree is gitignored, so walk_revctrl never sees it: it is
    # absent from the seed and can only arrive by way of an include, which is
    # what lets the assertion on it discriminate.
    file_list.files = [*SYNTHETIC_CORPUS, SYNTHETIC_SOURCE]

    for line in manifest_text.splitlines():
        directive = line.strip()
        if directive and not directive.startswith("#"):
            file_list.process_template_line(directive)

    file_list.sort()
    file_list.remove_duplicates()
    return list(file_list.files)


def _shipped_corpus(survivors: list[str]) -> list[str]:
    """Pick the corpus paths out of an sdist filelist.

    Args:
        survivors: The return value of ``_sdist_filelist``.

    Returns:
        Every path under the corpus directory, in the order given.
    """
    return [path for path in survivors if path.startswith(f"{CORPUS_DIR}/")]


def _tracked_pytest_config_paths() -> list[Path]:
    """List every tracked file pytest would read its settings from.

    Returns:
        Absolute paths in ``git ls-files`` order. Submodule configurations are
        absent, because ``git ls-files`` does not descend into a submodule,
        and that is the right answer here: a submodule's configuration governs
        its own rootdir and never this repository's collection walk.
    """
    names = set(PYTEST_INI_SECTIONS) | {"pyproject.toml"}
    result = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "ls-files"],
        capture_output=True,
        text=True,
        check=True,
    )
    return [
        REPO_ROOT / line
        for line in result.stdout.splitlines()
        if Path(line).name in names
    ]


def _declared_norecursedirs(path: Path) -> list[str] | None:
    """Read ``norecursedirs`` out of one pytest configuration file.

    Args:
        path: A configuration file as named by
            ``_tracked_pytest_config_paths``.

    Returns:
        The declared patterns, or ``None`` when the file declares none. A
        ``pyproject.toml`` may spell the value either as a list or as a single
        whitespace-separated string, and both are normalised to a token list.
    """
    if path.name == "pyproject.toml":
        with path.open("rb") as handle:
            table = tomllib.load(handle)
        options = table.get("tool", {}).get("pytest", {}).get("ini_options", {})
        value = options.get("norecursedirs")
        if value is None:
            return None
        return list(value) if isinstance(value, list) else value.split()

    # interpolation=None: the log_*_format values carry %(asctime)s, which the
    # default parser reads as interpolation syntax and refuses.
    parser = configparser.ConfigParser(interpolation=None)
    parser.read(path, encoding="utf-8")
    section = PYTEST_INI_SECTIONS[path.name]
    if not parser.has_option(section, "norecursedirs"):
        return None
    return parser.get(section, "norecursedirs").split()


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
    ignored = _ignored_paths(representative, *_tracked_corpus_paths())

    assert not ignored, (
        "ignore rules match corpus files, which therefore need 'git add -f' "
        f"to commit and are deleted by 'git clean -fdx':\n{_format_ignored(ignored)}"
    )


def test_plausible_corpus_filenames_are_not_gitignored():
    """No ignore rule may hide a corpus file that has not been written yet.

    The test above asks only about the files committed today plus one
    synthetic name, and all of them happen to miss the unanchored rules this
    repository's ``.gitignore`` carries for root-level scaffolding. Those
    rules match on a basename at any depth, so a plan called ``AUDIT-sp6.md``
    or a note filed under ``docs/build/`` was invisible to ``git status`` and
    destroyed outright by ``git clean -fdx`` — the exact loss this contract
    exists to prevent — while every test here stayed green.

    The names are fixed rather than generated so that a failure names the rule
    that hides one, and none of them is the name of a file in this suite.
    """
    ignored = _ignored_paths(*PLAUSIBLE_CORPUS_PATHS)

    assert not ignored, (
        "ignore rules hide plausible corpus filenames, which would therefore "
        "need 'git add -f' to commit and be deleted by 'git clean -fdx':\n"
        f"{_format_ignored(ignored)}"
    )


def test_generated_docs_is_gitignored():
    """Generated documentation must stay out of the index.

    The other half of the move, asserted separately because relocating a
    rule has to land somewhere and not merely leave: without this, a docs
    build offers its whole regenerated tree to the next commit.
    """
    target = f"{build_paths.GENERATED_DOCS_DIR}/index.md"

    # Read through _ignored_paths rather than off the exit status: a negation
    # matching this path would set the status to 0 while leaving the file
    # committable, so the status alone would report the generated tree safely
    # ignored at exactly the moment it stopped being.
    assert target in _ignored_paths(target), (
        f"{build_paths.GENERATED_DOCS_DIR}/ is not ignored, so a docs build "
        "leaves its generated tree staged for the next commit"
    )


def test_manifest_ships_generated_docs_not_corpus():
    """The sdist must name the generated tree and prune the corpus.

    Dropping an include does not keep anything out of an sdist here, because
    ``MANIFEST.in`` is only half of what decides the filelist.
    ``setuptools-scm`` sits in ``[build-system].requires`` and registers a
    ``setuptools.file_finders`` entry point, so ``manifest_maker.run`` calls
    ``add_defaults``, and that calls ``walk_revctrl()`` and adds *every
    git-tracked file* — the whole corpus of plans and specs — before the
    template is read at all. Only a ``prune`` takes those back out, which is
    why one is asserted here alongside the include. ``prune docs`` compiles to
    a pattern anchored on ``docs/`` and so leaves ``docs_build/`` untouched.
    """
    survivors = _sdist_filelist((REPO_ROOT / "MANIFEST.in").read_text(encoding="utf-8"))

    assert SYNTHETIC_SOURCE in survivors, (
        "the recipe ships no packaged module at all, so the assertions below "
        "would hold for an sdist that is simply empty"
    )
    assert not _shipped_corpus(survivors), (
        "an sdist built from this recipe ships tracked plans and specs: "
        f"{_shipped_corpus(survivors)}. walk_revctrl adds them whatever the "
        "includes say, so only a prune takes them back out -- and a later "
        "graft or recursive-include naming the corpus puts them back again"
    )
    assert set(SYNTHETIC_GENERATED) <= set(survivors), (
        f"the sdist does not ship {build_paths.GENERATED_DOCS_DIR}/, which no "
        "walk_revctrl can supply because it is gitignored: only an include in "
        "this recipe can put it there"
    )


def test_manifest_check_is_sensitive_to_directive_order(tmp_path):
    """A directive appended below the prune must not slip past the check above.

    The assertion this replaced scanned for directive tokens, and so reported
    a recipe safe as long as a ``prune docs`` appeared somewhere in it.
    ``MANIFEST.in`` directives apply in order, so a ``graft docs`` written
    below that prune re-adds every plan and spec while the scan still finds
    its token and passes.

    This runs the check against exactly that input and requires it to notice,
    which keeps the guarantee a property of what the recipe *does* rather than
    of which words it contains. The real file is copied rather than edited.
    """
    grafted = tmp_path / "MANIFEST.in"
    grafted.write_text(
        (REPO_ROOT / "MANIFEST.in").read_text(encoding="utf-8")
        + f"\ngraft {CORPUS_DIR}\n",
        encoding="utf-8",
    )

    survivors = _sdist_filelist(grafted.read_text(encoding="utf-8"))

    assert _shipped_corpus(survivors) == sorted(SYNTHETIC_CORPUS), (
        "a graft appended below the prune did not put the corpus back, so "
        "this check cannot see directive order and the assertion above it "
        "would pass on a recipe that re-ships every plan and spec"
    )


def test_pytest_does_not_recurse_into_generated_docs():
    """Collection must skip the generated tree.

    A docs build leaves behind a copy of every Markdown file the project can
    produce, and collection walks whatever it finds on every run afterwards.

    The root ``pytest.ini`` is asserted on by name because it is the only
    configuration that can govern this at all: a root-level ``docs_build/`` is
    reachable only from a run whose rootdir is the repository root, and such a
    run reads that file. The same entry in ``tests/pytest.ini`` is inert —
    its rootdir is ``tests/``, so collection never walks up to a sibling of
    it — exactly as that file's long-standing ``docs`` entry is inert. The
    loop then covers every other configuration that limits the walk, so a
    file added later cannot quietly reintroduce one that descends into the
    generated tree.
    """
    declaring = {
        path: patterns
        for path in _tracked_pytest_config_paths()
        if (patterns := _declared_norecursedirs(path)) is not None
    }

    assert REPO_ROOT / "pytest.ini" in declaring, (
        "the root pytest.ini declares no norecursedirs, so pytest's built-in "
        "default applies to a run rooted at the repository root, and that "
        f"default contains neither {CORPUS_DIR} nor "
        f"{build_paths.GENERATED_DOCS_DIR}"
    )
    for path, patterns in declaring.items():
        assert build_paths.GENERATED_DOCS_DIR in patterns, (
            f"{path.relative_to(REPO_ROOT)} limits collection but does not "
            f"exclude {build_paths.GENERATED_DOCS_DIR}/: {patterns}"
        )


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
