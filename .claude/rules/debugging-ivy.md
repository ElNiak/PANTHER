## Debugging Ivy/BGP — pointer

Detailed Ivy debugging methodology lives in the panther-ivy-plugin skill `ivy-debugging-methodology` (invoke via the Skill tool). Use that for: MCP sidecar health checks, staging path resolution, include path investigation, stale-process detection, and the structured triage order.

Worktree-specific notes only:

- Confirm `IVY_LSP_DEV_ROOT` and `PANTHER_IVY_PLUGIN_DEV_ROOT` env vars resolve to the lsp-to-claude submodule paths before running any Ivy tool. The worktree's `.claude/settings.local.json` defines them.
- When an MCP server drops or returns errors, treat it as an infrastructure issue until proven otherwise. Investigate every WARN — past WARNs in this worktree have revealed real bugs (sidecar early-capture, stale PIDs, missing resolvers).
