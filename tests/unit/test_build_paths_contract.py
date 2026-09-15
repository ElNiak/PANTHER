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
live config said; a single build dropped a nav entry. The last two tests pin
that the mechanism is gone, because with it in place the first test's subject
is rewritten from disk before mkdocs ever reads it.
"""

import inspect
from pathlib import Path

import pytest
import yaml

import panther_builder
from panther.cli.commands import docs
from panther.tools import build_paths

pytestmark = pytest.mark.unit

REPO_ROOT = Path(panther_builder.__file__).resolve().parent


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
