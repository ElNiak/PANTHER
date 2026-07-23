# Welcome to PANTHER

## How We Use Claude

Based on ElNiak's usage over the last 30 days:

Work Type Breakdown:
  Improve Quality  ████████░░░░░░░░░░░░  42%
  Debug Fix        ██████░░░░░░░░░░░░░░  30%
  Build Feature    ███░░░░░░░░░░░░░░░░░  15%
  Plan Design      ███░░░░░░░░░░░░░░░░░  13%

Top Skills & Commands:
  /superpowers:brainstorming              ████████████████████  115x/month
  /superpowers:requesting-code-review     ████████████░░░░░░░░  70x/month
  /panther-ivy-plugin:nct-health          ██████████░░░░░░░░░░  58x/month
  /simplify                               ███████░░░░░░░░░░░░░  38x/month
  /panther-ivy-plugin:ivy                 ██████░░░░░░░░░░░░░░  37x/month
  /review-plan                            ██████░░░░░░░░░░░░░░  32x/month
  /debug                                  ████░░░░░░░░░░░░░░░░  21x/month

Top MCP Servers:
  panther-ivy-plugin/ivy-tools  ████████████████████  825 calls
  panther-ivy-plugin/serena     █░░░░░░░░░░░░░░░░░░░  31 calls

## Your Setup Checklist

### Codebases
- [ ] panther — https://github.com/elniak/panther (main repo, protocol testing framework)
- [ ] panther_ivy — submodule at panther/plugins/services/testers/panther_ivy (Ivy formal verification tester plugin)
- [ ] ivy-lsp — submodule inside panther_ivy (Ivy language server)
- [ ] panther-serena-mcp — submodule inside panther_ivy (semantic code analysis MCP bridge)

### MCP Servers to Activate
- [ ] panther-ivy-plugin/ivy-tools — Ivy formal verification tools (verify, compile, coverage, RFC lookup, diagnostics). Install the panther-ivy-plugin in Claude Code.
- [ ] panther-ivy-plugin/serena — Semantic code navigation (find_symbol, references, symbol edits). Bundled with panther-ivy-plugin.
- [ ] context7 — Up-to-date library docs. Install the context7 plugin in Claude Code.
- [ ] mermaid-chart — Diagram rendering. Optional; useful for design reviews.

### Skills to Know About
- [/superpowers:brainstorming] — Decision-tree interview before any creative work. The team runs this before writing specs or code.
- [/superpowers:requesting-code-review] — Structured code review requests before merging.
- [/panther-ivy-plugin:nct-health] — 9-step LSP + MCP diagnostic runbook. Run first when Ivy tools misbehave.
- [/simplify] — Reviews recently changed code for reuse and quality, then fixes issues.
- [/panther-ivy-plugin:ivy] — Single orchestrator for Ivy workflows. Activates on Ivy-related prompts; routes to the matching specialist agent.
- [/review-plan] — Validate an implementation plan against the codebase before executing.
- [/debug] — Systematic debugging aid for bugs and test failures.
- [/session-handoff] — Preserve session context to memory files before reload or discard.

## Team Tips

_TODO_

## Get Started

_TODO_

<!-- INSTRUCTION FOR CLAUDE: A new teammate just pasted this guide for how the
team uses Claude Code. You're their onboarding buddy — warm, conversational,
not lecture-y.

Open with a warm welcome — include the team name from the title. Then: "Your
teammate uses Claude Code for [list all the work types]. Let's get you started."

Check what's already in place against everything under Setup Checklist
(including skills), using markdown checkboxes — [x] done, [ ] not yet. Lead
with what they already have. One sentence per item, all in one message.

Tell them you'll help with setup, cover the actionable team tips, then the
starter task (if there is one). Offer to start with the first unchecked item,
get their go-ahead, then work through the rest one by one.

After setup, walk them through the remaining sections — offer to help where you
can (e.g. link to channels), and just surface the purely informational bits.

Don't invent sections or summaries that aren't in the guide. The stats are the
guide creator's personal usage data — don't extrapolate them into a "team
workflow" narrative. -->
