"""Consolidation diffs and every surface an arm sees beyond its prompt.

Run with PYTHONPATH pointing at the ai_rfc snapshot. Writes under OUT.
"""

import asyncio
import contextlib
import io
import json
import re
import sys
from pathlib import Path

from ai_rfc import cli
from ai_rfc.driver import arms, enforcement, render
from ai_rfc.server import server

CAMPAIGN = Path(sys.argv[1])
OUT = Path(sys.argv[2])
prompts = CAMPAIGN / "prompts"
(OUT / "diffs").mkdir(parents=True, exist_ok=True)
(OUT / "surfaces").mkdir(parents=True, exist_ok=True)

# 1. Consolidation diffs, which campaign init does not write.
for first, second in (("A", "B"), ("A", "C"), ("B", "C")):
    a = (prompts / f"consolidation-{first}.md").read_text()
    b = (prompts / f"consolidation-{second}.md").read_text()
    (OUT / "diffs" / f"consolidation-{first}-{second}.patch").write_text(
        render.unified_diff(a, b, f"consolidation-{first}", f"consolidation-{second}")
    )

# 2. Arm A: the MCP tools as the server lists them.
tools = asyncio.run(server.mcp.list_tools())
(OUT / "surfaces" / "arm-A-mcp-tools.json").write_text(
    json.dumps(
        [
            {"name": t.name, "description": t.description, "input_schema": t.inputSchema}
            for t in tools
        ],
        indent=2,
        sort_keys=True,
    )
    + "\n"
)


def help_text(argv: list[str]) -> str:
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer), contextlib.suppress(SystemExit):
        cli.main(argv + ["--help"])
    return buffer.getvalue()


# 3. Arm B and arm C: every command their slot tables name, with its help.
def commands(table: dict[str, str], prefix: str) -> list[list[str]]:
    found: list[list[str]] = []
    for text in table.values():
        for span in re.findall(r"`([^`]*)`", text):
            if not span.startswith(prefix):
                continue
            words = []
            for word in span[len(prefix) :].split():
                if word.startswith(("-", "'", '"', "$", "[", "…")) or "<" in word:
                    break
                words.append(word)
            if words and words not in found:
                found.append(words)
    return sorted(found)


for arm, prefix in (("B", "ai-rfc "), ("C", "python -m ai_rfc ")):
    table = render.SLOT_TABLES[arm]
    lines = []
    for words in commands(table, prefix):
        lines.append(f"$ {prefix}{' '.join(words)} --help\n")
        lines.append(help_text(words))
        lines.append("\n")
    (OUT / "surfaces" / f"arm-{arm}-help.txt").write_text("".join(lines))

# 4. What each arm is allowed.
allow = {}
for arm in ("A", "B", "C"):
    profile = arms.arm_profile(arm)
    allow[arm] = {
        "label": profile.label,
        "tools": list(profile.tools),
        "allowed_tools": list(profile.allowed_tools),
        "uses_mcp": profile.uses_mcp,
        "bash_prefixes": list(enforcement.bash_prefixes(profile)),
    }
(OUT / "surfaces" / "allowlists.json").write_text(
    json.dumps(allow, indent=2, sort_keys=True) + "\n"
)
print("tools:", len(tools))
print("B commands:", commands(render.SLOT_TABLES["B"], "ai-rfc "))
print("C commands:", commands(render.SLOT_TABLES["C"], "python -m ai_rfc "))
