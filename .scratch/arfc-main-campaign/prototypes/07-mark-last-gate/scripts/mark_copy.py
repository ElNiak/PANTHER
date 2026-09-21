"""Copy the MARK pristine for the last-gate dry run and prove the copy is its own context.

Usage: mark_copy.py <pristine> <dest>. Prints the pristine's digest problems
(expected: none), copies it with copy_workspace, then resolves the context from
the copy's recon.yaml and refuses to go on unless it names the copy.
"""

import os
import sys
from pathlib import Path

from ai_rfc.experiment.workspace import copy_workspace, verify_digest
from ai_rfc.server.paths import resolve_context

pristine = Path(sys.argv[1]).resolve()
dest = Path(sys.argv[2]).resolve()

print("pristine digest problems before:", verify_digest(pristine) or "none")
copy_workspace(pristine, dest)
print("copied to:", dest)

os.environ["AI_RFC_CONFIG"] = str(dest / "recon.yaml")
ctx = resolve_context()
print("context workspace:", ctx.workspace)
print("context toolchain:", ctx.toolchain)
if Path(ctx.workspace).resolve() != dest:
    sys.exit(f"REFUSE: the copy resolves to {ctx.workspace}, not to itself")
print("OK: the copy resolves to itself")
