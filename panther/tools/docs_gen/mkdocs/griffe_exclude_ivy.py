"""Griffe extension to exclude panther_ivy submodule from API docs."""

import griffe


class ExcludeIvyExtension(griffe.Extension):
    """Remove panther_ivy from the module tree before alias resolution.

    The panther_ivy submodule contains ``z3_shim.py`` with an unresolvable
    wildcard import (``from ...z3 import *``) that causes griffe to crash
    with an ``AliasResolutionError``.  This extension intercepts the loaded
    package and prunes the subtree so griffe never attempts to resolve it.
    """

    def on_package_loaded(self, *, pkg: griffe.Module, **kwargs):
        self._remove_panther_ivy(pkg)

    def _remove_panther_ivy(self, mod: griffe.Module):
        if "panther_ivy" in mod.members:
            mod.del_member("panther_ivy")
        for member in list(mod.members.values()):
            if isinstance(member, griffe.Module):
                self._remove_panther_ivy(member)
