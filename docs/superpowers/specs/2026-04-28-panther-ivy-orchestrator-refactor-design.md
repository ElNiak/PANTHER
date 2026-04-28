# Refactor panther-ivy-plugin toward a bio-research–style design

> Status: **brainstorming / Phase 1 (Initial Understanding)**. This file is being built incrementally as the grilling interview proceeds. Sections marked `[OPEN]` are pending user input. Final plan section is at the bottom.

---

## Context

The `panther-ivy-plugin` (currently at `panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin/`) has accumulated significant structural surface area: 19 skills (workflow / knowledge / cross-cutting / meta prefix groups), 4 agents, 7 slash commands, 13 auto-loaded rules, 4 output styles, ~30 hook scripts wired across 9 hook events, a `routing-rules.json` programmatic dispatcher, and 2 MCP servers backed by an LSP with workspace/indexing/PID lifecycle. Recent commits show a sustained simplification arc (Phase 1–5 flat-with-prefix migration, T1+T2+T4 surgical simplification, hook footprint cleanup, knowledge-skill lazy-loading).

The user wants to push that arc further by aiming the plugin at the structural shape of `anthropics/knowledge-work-plugins/main/bio-research`. Bio-research is radically minimal: 6 skills, **zero** agents/hooks/commands/rules/output-styles, just `plugin.json` + `.mcp.json` + `README.md` + `CONNECTORS.md` + `skills/`. Each skill is `SKILL.md` + `references/*.md` + (optionally) `scripts/*.py`. Cross-skill dispatch is conversational via a single `start` skill — no programmatic routing. MCP servers are HTTP-only and tool-agnostic via `~~category` placeholders.

The intended outcome is a leaner, easier-to-maintain plugin that someone unfamiliar with the codebase can understand by reading the README and 6–8 skill files in sequence. The trade-off the refactor must resolve honestly is that bio-research is a *knowledge plugin* and panther-ivy is a *workflow-enforcement plugin* — they belong to different categories, and copying structure does not automatically transfer behavior.

---

## Orientation findings

### Bio-research target structure (target template)

```
bio-research/
├── .claude-plugin/plugin.json    # name, version, description, author — that's it
├── .mcp.json                     # 10 HTTP MCP servers, no LSP backing
├── README.md                     # ~4 KB, lists MCP servers + skills + workflows
├── CONNECTORS.md                 # ~~category placeholder mapping
├── LICENSE
└── skills/                       # 6 skills, kebab-case, no prefix taxonomy
    ├── start/SKILL.md            # conversational dispatcher (~1 file)
    ├── single-cell-rna-qc/       # SKILL.md + scripts/ (3 .py) + references/ (1 .md)
    ├── scvi-tools/               # SKILL.md + scripts/ (8 .py) + references/ (11 .md)
    ├── nextflow-development/     # SKILL.md + scripts/ + scripts/config/ + references/
    ├── instrument-data-to-allotrope/  # SKILL.md + scripts/ + references/ + requirements.txt
    └── scientific-problem-selection/  # SKILL.md + references/01-…-09-meta-framework.md
```

Notable design choices observed:

- **No agents, no hooks, no commands, no rules.** Cross-skill dispatch is conversational from the `start` skill.
- **Tool-agnostic placeholders.** Skills reference `~~literature`, `~~drug targets`; `.mcp.json` decides which servers fulfill each category.
- **Index + references pattern.** `SKILL.md` is the entry / model-selection guide; deep content lives in `references/*.md` (numbered when sequential, e.g. `01-…-09-meta-framework.md`).
- **Convenience scripts + modular building blocks.** `qc_analysis.py` (CLI wrapper) plus `qc_core.py` and `qc_plotting.py` (utilities).
- **Stateless lifecycle.** No session state, no orchestration, no observability beyond default Claude Code logging.

### Current panther-ivy-plugin structure

```
panther-ivy-plugin/plugins/panther-ivy-plugin/
├── .claude-plugin/plugin.json    # 7 userConfig fields (LSP log level, serena toggle, observability, statusline modes, etc.)
├── .mcp.json                     # 2 servers: ivy-tools (LSP-backed) + serena
├── .claude/rules/                # 13 auto-loaded rules incl. iron-laws.md, ivy-formatting.md, plan-mode.md, …
├── README.md (14.5 KB), CHANGELOG.md
├── settings.json                 # env-var pass-through for userConfig
├── routing-rules.json            # 6 workflow keyword/intent/file rules + learning_injection
├── agents/                       # 4 agents: model-reviewer, plugin-conventions-reviewer, spec-analyst, traceability-agent
├── commands/                     # 7 slash commands (nct-check, nct-compile, nct-health, nct-iut-test, nct-learn, nct-model-info, nct-observability)
├── docs/, evals/, tests/, styles/
├── hooks/hooks.json + hooks/scripts/   # ~30 hook scripts across PreToolUse / PostToolUse / PostToolUseFailure / SessionStart / SessionEnd / Stop / SubagentStart / SubagentStop / PreCompact / UserPromptSubmit / Notification / PermissionRequest
├── output-styles/                # 4 styles: ivy-default, ivy-guided, ivy-audit + README
├── scripts/                      # start-ivy-server.sh, start-serena.sh, statusline, workspace-common.sh
└── skills/                       # 19 skills, flat-with-prefix (4 prefix groups)
    ├── workflow-build, workflow-verify, workflow-review, workflow-triage, workflow-navigate
    ├── knowledge-apt-attack-patterns, knowledge-ivy-toolkit, knowledge-ivy-writing-guide,
    │   knowledge-methodology-reference, knowledge-propagation-patterns, knowledge-specification-patterns,
    │   knowledge-verification-failures
    ├── cross-cutting-completion-gate, cross-cutting-knowledge-capture, cross-cutting-parallel-dispatch,
    │   cross-cutting-reflection-patterns
    └── meta-using-panther-ivy-plugin, meta-plugin-self-mod
```

### The load-bearing asymmetry

| Dimension                     | Bio-research                                 | panther-ivy                                                                       |
|------------------------------|----------------------------------------------|------------------------------------------------------------------------------------|
| Plugin category              | **Knowledge plugin** (passive Q&A + tooling) | **Workflow-enforcement plugin** (active gating, iron laws, adversarial review)     |
| MCP backing                  | 10 HTTP servers (stateless)                  | 2 stdio servers backed by LSP with workspace, indexing, PID lifecycle              |
| Cross-skill dispatch         | Conversational via `start` skill             | UserPromptSubmit hook + routing-rules.json + in-skill `Skill()` + journal events  |
| Enforcement                  | None                                          | `NO_FIX_WITHOUT_VERIFY`, `NO_LAYER_WITHOUT_SCAFFOLD`, `NO_QUALITY_WITHOUT_COVERAGE`, `STALENESS_RULE` (auto-loaded rule) |
| Adversarial review           | None                                          | 4 agents (model-reviewer, plugin-conventions-reviewer, spec-analyst, traceability-agent) dispatched at gate phases |
| Methodology routing          | None                                          | NCT / NACT / NSCT classification drives workflow selection                         |
| State                        | Stateless                                     | Workspace state (`/set-workspace`, `IVY_WORKSPACE_ROOT`), workflow journal, observability JSONL |
| Output styles                | Default                                       | ivy-default / ivy-guided / ivy-audit                                              |

These differences are not stylistic. They map to specific failure modes already documented in user memory:

- `NO_FIX_WITHOUT_VERIFY` exists because of the documented "claim resolved without re-running ivy_verify" anti-pattern.
- The verifier-pattern catalog (#NN) and claim-resolution gate exist because counterexample interpretation is bug-prone without structured guidance.
- `route-user-prompt.py` and `inject-using-plugin.sh` exist because LLMs forget the methodology framing without SessionStart re-injection.
- Workspace detection hooks exist because `IVY_LSP_DEV_ROOT` and `PANTHER_IVY_PLUGIN_DEV_ROOT` env vars must resolve correctly for the LSP-backed MCP to function.

A pure structural copy of bio-research deletes that enforcement layer and risks regression to the failure modes the layer was built to prevent.

### Dependency map (external references that would silently break)

External references (non-plugin tree):

- `ONBOARDING.md` at worktree root references `/panther-ivy-plugin:nct-health` and `/panther-ivy-plugin:navigate`. The latter is **already rotted**: current canonical name is `workflow-navigate`, not `navigate`. Current command name is `nct-health` so that one still resolves.
- `.claude/settings.local.json`:
  - `env.IVY_LSP_DEV_ROOT = …/submodules/ivy-lsp` (LSP backend path).
  - `env.PANTHER_IVY_PLUGIN_DEV_ROOT = …/submodules/panther-ivy-plugin` (plugin root). Hooks rely on this for dev-mode resolution.
  - `outputStyle = "panther-ivy-plugin:Ivy Guided"` — names a specific output style asset.
  - `permissions.allow` has shell-command entries referencing already-deleted agent files (`nct-guide.md`, `nact-guide.md`, …); these are stale allowlist lines, not active breakage.
- 4 memory files name specific plugin skills/agents: `feedback_reuse_existing_xml_tags.md`, `feedback_agent_orchestrator_three_layer_split.md`, `handoff-2026-04-27.md`, `handoff-2026-04-27-simplification.md`. These are user-side and would go stale on rename.
- Parent-repo rule `.claude/rules/debugging-ivy.md` points users to the plugin's `ivy-debugging-methodology` skill — a name that exists in the duplicate `panther-ivy-plugin 2/` tree (bare-name layout) and would need to be re-mapped to `workflow-triage` or wherever debugging methodology lives in the canonical tree.

**Stale duplicate tree:** A second tree at `submodules/panther-ivy-plugin 2/plugins/panther-ivy-plugin/` carries the *previous* skill-name convention (`navigate`, `verify`, `build`, `review`, `triage`, `knowledge-capture`, `completion-gate`, `reflection-patterns`, `parallel-dispatch`, `ivy-toolkit`, `ivy-writing-guide`, `ivy-debugging-methodology`, `propagation-patterns`, `ivy-error-patterns`). It is not used at runtime (the canonical tree without `" 2"` is the registered submodule) but it carries cross-skill references that look authoritative on grep. Per memory rule "no relocate or remove backup files without per-file approval", it cannot be deleted as part of this refactor without explicit per-file user approval.

Internal self-references (must stay consistent under any rename):

- 30+ `Skill(skill="panther-ivy-plugin:<name>")` invocations across SKILL.md and `references/*.md` files.
- `routing-rules.json` keys are workflow names (`workflow-verify`, `workflow-build`, …); `route-user-prompt.py` consumes them.
- Hook scripts hard-code `_PLUGIN_PREFIX = "panther-ivy-plugin:"` plus skill names for `track-workflow-skill.py` and `auto-load-skill-references.py`.
- Plugin README and CHANGELOG name skills/agents/hooks; both go stale on rename.

---

## Open decisions to grill

1. **Plugin category target.** Pure knowledge-plugin clone (drop enforcement), enforcement-preserved but visually reorganised, or knowledge-plugin core with enforcement opt-in via a separate companion plugin?
2. **Iron laws & gate disposition.** Auto-loaded `.claude/rules/`, inline into skill bodies, push to per-skill `references/`, drop entirely?
3. **Hook scope.** All 30 hooks (current), critical-only (workspace detection + MCP health + observability), conversational only (no hooks)?
4. **Agent disposition.** Keep all 4, consolidate to 1–2, push critique into skill bodies and drop, or push to a separate review plugin?
5. **Slash command disposition.** Keep all 7 `/nct-*`, reduce to `/start` + `/set-workspace`, drop entirely (rely on natural language)?
6. **Routing-rules.json.** Keep programmatic, replace with conversational `start`-skill dispatch, hybrid?
7. **Output styles.** Keep 3 + default, reduce to default + guided, drop?
8. **Skill taxonomy.** Keep flat-with-prefix (`workflow-*`, `knowledge-*`, …), flatten to bio-research style (descriptive names only), reorganise by Ivy lifecycle stage?
9. **Tool-agnostic placeholders.** Adopt `~~category` pattern for Ivy stages (e.g. `~~ivy-build`, `~~ivy-verify`)? Probably low value since we have one LSP, not many alternatives.
10. **MCP integration depth.** Keep ivy-tools + serena as-is, restructure server boundaries, move LSP-backed tools to a separate plugin?
11. **Migration phasing.** Big-bang refactor branch, incremental phases (continuing the Phase-1–5 arc), or prototype-first in a sibling directory?
12. **Backward-compat / external references.** Memory entries reference specific skill names (`workflow-verify`, `cross-cutting-completion-gate`, etc.). Parent repo `.claude/rules/debugging-ivy.md` references plugin skills by name. Iron law of no-compat-shims means we update callers cleanly — but how aggressive on the rename pass?

---

## Research-grounded findings (2026-04-28)

Three parallel research streams: (1) every plugin in `anthropics/knowledge-work-plugins` (16+), (2) Anthropic's official docs on skills / sub-agents / plugins / hooks / output styles, (3) local plugin-dev SKILLS plus the current `workflow-navigate` and `meta-using-panther-ivy-plugin` SKILL.md bodies plus `agent-dispatch.md` and `skill-conventions.md` rules.

Load-bearing observations:

- **Bio-research is an outlier.** Of 16 surveyed knowledge-work plugins, 11 use flat skill lists with conversational dispatch and no orchestrator; 1 uses command-mapping (product-management); 2 use entry-point orchestrators (bio-research, productivity); 1 is command-only (pdf-viewer). None ship agents, hooks, or routing-rules.json. The bio-research orchestrator pattern is the exception, not the canonical pattern in that repo.
- **Skill-for-agent loading is canonical in Anthropic's docs but undocumented in our local guidance.** `agents/<name>.md` frontmatter supports a `skills: [...]` array that preloads full skill bodies into the spawned agent's system prompt. Our existing agents (`spec-analyst`, `model-reviewer`) already use this field; the loading semantics just are not formally documented in `skill-conventions.md` or `agent-dispatch.md`.
- **Skills can fork their own context** via `context: fork` + `agent: Explore` (or `Plan`) frontmatter — a third lever on top of "main-thread skill", "agent dispatched via subagent_type", and "skill preloaded into agent". This is the canonical mechanism behind the user's "efficiency agents to manage long-context workflows" framing.
- **No programmatic-routing config is canonical.** Anthropic's docs explicitly say "write clear descriptions, let Claude decide". Our `routing-rules.json` is a workaround. It can stay if it earns its keep, but the canonical default is conversational dispatch via descriptions.
- **Workflow-navigate is already a 7-phase orchestrator** (Phase 0 plan-detection → Phase 1 silent scan → Phase 1.5 plan-gate → Phase 2 branch-by-context → Reflection Gate → Dispatch → pending-dispatch consumption with G0/G0b gates). It is structurally close to a bio-research-style entry skill; the refactor should promote it, not replace it.
- **Meta-using-panther-ivy-plugin is the iron-law primer**, currently injected at SessionStart by `inject-using-plugin.sh`. It is small (~80 LOC). It belongs inside the orchestrator's preamble or as numbered reference 01.
- **Knowledge skills are well-segregated by domain** (methodology, toolkit, ivy-writing, verification-failures, specification-patterns, propagation-patterns, apt-attack-patterns). Consolidating them into orchestrator references collapses 7 skills into 7 numbered files; alternatively, they can stay as separate skills the orchestrator dispatches into agents via `skills: [...]`.

## Five candidate approaches

Each approach is a distinct architectural commitment. They differ on (a) where the orchestrator lives, (b) how sub-workflows are loaded, (c) where knowledge is anchored, (d) how agents fit, (e) how much enforcement scaffolding (hooks, rules, output-styles, commands, routing-rules.json) survives.

### A. Bio-research clone — one orchestrator, everything inline

```
panther-ivy-plugin/
├── .claude-plugin/plugin.json
├── .mcp.json
├── README.md  (~5 KB)
├── CONNECTORS.md  (Ivy stage placeholders)
└── skills/
    ├── start/SKILL.md                # ~150 LOC: 3 entry questions + dispatch
    └── ivy/                          # the orchestrator
        ├── SKILL.md                  # ~250 LOC entry router; iron-laws preamble
        └── references/
            ├── 01-iron-laws.md
            ├── 02-methodology-NCT-NACT-NSCT.md
            ├── 03-ivy-toolkit-catalog.md
            ├── 04-ivy-syntax.md
            ├── 05-completion-gate.md
            ├── 06-parallel-dispatch.md
            ├── 07-knowledge-capture.md
            ├── 10-triage.md          # ~300 LOC each; full sub-workflow inline
            ├── 11-build.md
            ├── 12-verify.md
            ├── 13-review.md
            ├── 14-meta-self-mod.md
            ├── 20-verification-failures.md
            ├── 21-specification-patterns.md
            └── 22-apt-attack-patterns.md

# DELETED: agents/, hooks/, commands/, .claude/rules/, routing-rules.json,
#          output-styles/, settings.json
```

- Pure structural mimicry of bio-research. No agents, no hooks, no commands, no auto-loaded rules, no output-styles.
- Claude reads orchestrator SKILL.md → branches into a numbered reference based on user intent → executes inline.
- **Cost:** loses agent dispatch (no model-reviewer / spec-analyst / traceability-agent for adversarial review), loses workspace detection hook (LSP env vars never set), loses observability JSONL stream (breaks ICSE 2027 research telemetry), loses `/nct-iut-test` and `/nct-health` commands, loses iron-law auto-load.
- **Win:** smallest visible surface; entire plugin readable in one orchestrator + 14 references.

### B. Productivity-style — paired entry skills + persistent state files

```
panther-ivy-plugin/
├── .claude-plugin/plugin.json
├── .mcp.json
├── README.md
├── skills/
│   ├── start/SKILL.md                # Initialise workspace, env, MCP health
│   ├── update/SKILL.md               # Routine triage / status / next-step
│   ├── triage/                       (multi-phase skill)
│   ├── build/                        (multi-phase skill)
│   ├── verify/                       (multi-phase skill)
│   ├── review/                       (multi-phase skill)
│   └── ivy-knowledge/                # consolidated knowledge skill
│       ├── SKILL.md
│       └── references/01-…-07-….md
├── WORKFLOW-STATE.md                 # bidirectional sync target (replaces .panther-ivy/session-logs JSONL)
├── hooks/                            # SessionStart only: workspace detect, MCP health
└── settings.json
```

- Modeled on `productivity` plugin (the only other entry-point-orchestrator in the repo). `/start` and `/update` are the user-facing slash commands; everything else is conversational.
- Persistent state in `WORKFLOW-STATE.md` (bidirectional, like productivity's TASKS.md) instead of opaque JSONL event log.
- Keeps a slim `hooks/` directory for SessionStart workspace detection (genuinely needed; LSP/MCP can't operate without env vars).
- **Cost:** loses adversarial gate dispatch (no agents); two entry points (`/start`, `/update`) violate the user's "single official skills orchestrator" preference unless we treat `/start` as the orchestrator and `/update` as a subordinate workflow.
- **Win:** plain-text persistent state is readable, diffable, version-controllable; smaller hook surface than current.

### C. Hub-and-spokes with skill-for-agent pairs — recommended baseline

```
panther-ivy-plugin/
├── .claude-plugin/plugin.json
├── .mcp.json
├── README.md  (~5 KB; points at the orchestrator)
├── CONNECTORS.md
├── skills/
│   ├── ivy/                          # ⭐ ORCHESTRATOR (replaces workflow-navigate + meta-using-panther-ivy-plugin)
│   │   ├── SKILL.md                  # ~250 LOC; routes to sub-skills + dispatches agents
│   │   └── references/
│   │       ├── 01-iron-laws.md
│   │       ├── 02-methodology.md
│   │       ├── 03-toolkit.md         (was knowledge-ivy-toolkit)
│   │       ├── 04-ivy-syntax.md      (was knowledge-ivy-writing-guide)
│   │       ├── 05-completion-gate.md (was cross-cutting-completion-gate)
│   │       ├── 06-parallel-dispatch.md
│   │       └── 07-knowledge-capture.md
│   ├── triage/SKILL.md + references/
│   ├── build/SKILL.md + references/  # specification-patterns + propagation-patterns inlined
│   ├── verify/SKILL.md + references/ # verification-failures inlined
│   ├── review/SKILL.md + references/ # apt-attack-patterns + traceability inlined
│   └── meta-self-mod/SKILL.md
├── agents/                           # 4 agents, each preloads a skill via `skills:` frontmatter
│   ├── spec-analyst.md               (skills: [verify])
│   ├── model-reviewer.md             (skills: [build])
│   ├── traceability-agent.md         (skills: [review])
│   └── plugin-conventions-reviewer.md (skills: [meta-self-mod])
├── hooks/                            # SLIMMED to ~10 critical
│   └── scripts/
│       ├── detect-ivy-workspace.sh   (SessionStart — env vars)
│       ├── cleanup-stale-pids.sh     (SessionStart — MCP/LSP lifecycle)
│       ├── cleanup-ivy-lsp.sh        (SessionEnd — process teardown)
│       ├── wait-for-indexing.sh      (SessionStart — LSP readiness)
│       ├── inject-using-plugin.sh    (SessionStart — orchestrator priming)
│       ├── route-user-prompt.py      (UserPromptSubmit — keyword routing TO orchestrator)
│       ├── observability/observe.py  (all events — JSONL telemetry; ICSE 2027 research)
│       ├── render-summary.py         (Stop — workflow journal recap)
│       ├── retry-ivy-mcp.py          (PostToolUseFailure — transient retry)
│       └── notify-mcp-disconnect.py  (Notification)
├── commands/                         # 2: /nct-health, /nct-iut-test
├── output-styles/ivy-guided.md       # 1
├── routing-rules.json                # All keywords route to orchestrator; orchestrator sub-routes
├── settings.json
└── scripts/                          # start-ivy-server.sh, start-serena.sh, statusline
```

- Single orchestrator skill `ivy/` (replaces both `workflow-navigate` and `meta-using-panther-ivy-plugin`).
- Sub-workflows stay separate skills because each is multi-phase with its own gates and Step Tracking sections (skill-conventions §6 mandates this for rigid skills).
- 7 knowledge skills collapse into 7 numbered orchestrator references.
- **Skill-for-agent pairs:** each major agent preloads the matching workflow skill into its system prompt via `skills: [...]` frontmatter — the agent has the full operating procedure when it's spawned for long-context work. Documents the previously undocumented `skills:` field.
- Slim hooks (10 from 30) keep workspace detection, MCP lifecycle, observability (research telemetry), and routing.
- `routing-rules.json` survives but only to route ALL keywords to the orchestrator; orchestrator owns sub-routing.
- **Cost:** still 5 separate workflow skills; orchestrator + 5 sub-skills + 4 agents = 10 components, vs bio-research's 6.
- **Win:** preserves enforcement (iron laws, gates, observability), preserves agent dispatch, mimics bio-research surface, documents the skill-for-agent pattern. Closest match to user's stated direction.

### D. Split orchestrator — knowledge index + workflow dispatcher

```
panther-ivy-plugin/
├── .claude-plugin/plugin.json
├── .mcp.json
├── skills/
│   ├── ivy-knowledge/                # ⭐ Knowledge-only entry; pure Q&A
│   │   ├── SKILL.md                  # methodology, toolkit, ivy-syntax, verifier-patterns
│   │   └── references/01-…-07-….md
│   ├── ivy-workflow/                 # ⭐ Workflow-only entry; routes to sub-skills
│   │   └── SKILL.md
│   ├── triage/, build/, verify/, review/, meta-self-mod/
├── agents/  hooks/  commands/  routing-rules.json  (as in C)
```

- Two entry skills, mirroring bio-research's split between `scientific-problem-selection` (workflow orchestrator) and the other domain skills (knowledge).
- User asks "how does NCT methodology work?" → `ivy-knowledge`. User asks "verify this spec" → `ivy-workflow` → `verify`.
- **Cost:** violates user's "single official orchestrator" preference. Two entry points are conceptually clean but one more thing to remember.
- **Win:** clean separation between learning and doing; knowledge skill becomes a self-contained reference document.

### E. Agent-first — orchestrator as thin dispatcher; logic in agents

```
panther-ivy-plugin/
├── .claude-plugin/plugin.json
├── .mcp.json
├── skills/
│   └── ivy/SKILL.md                  # ~80 LOC; only role is to dispatch the right agent
├── agents/                           # 5 agents own the workflow logic
│   ├── ivy-triage-agent.md           (skills: [triage-ops])
│   ├── ivy-builder-agent.md          (skills: [build-ops])
│   ├── ivy-verifier-agent.md         (skills: [verify-ops, verification-failures])
│   ├── ivy-reviewer-agent.md         (skills: [review-ops, traceability])
│   └── ivy-meta-agent.md             (skills: [meta-self-mod])
├── skills/                           # second-level: ops-only skills loaded into agents
│   ├── triage-ops/, build-ops/, verify-ops/, review-ops/
│   ├── verification-failures/, traceability/, meta-self-mod/
│   └── ivy-knowledge/                # for direct Q&A
├── hooks/                            (slim as in C)
```

- The orchestrator skill is a thin (~80 LOC) router. All workflow logic lives in agents that preload "ops" skills via `skills: [...]` frontmatter and run in `context: fork` for context isolation.
- Maximum use of context isolation; main thread stays clean while agents handle multi-turn work in their own context.
- **Cost:** workflow logic inside agent definitions is harder for users to read than skill bodies; counterexample interpretation, gate dispatching, and step tracking all happen inside spawned agents. Makes the plugin opaque to anyone who didn't write it.
- **Win:** main-context token budget is minimal regardless of workflow length; 5 named agent specialists each with their own preloaded skill; cleanest implementation of the "efficiency agents for long-context workflows" framing.

### F. Minimal-change — rename only, keep current architecture

- Drop `workflow-` / `knowledge-` / `cross-cutting-` / `meta-` prefixes (`workflow-verify` → `verify`).
- Rename `workflow-navigate` → `ivy` (or `start`); fold `meta-using-panther-ivy-plugin` into it.
- Keep all 4 agents, 30 hooks, 13 rules, 7 commands, 4 output-styles, routing-rules.json.
- Update README to point at the new orchestrator and use bio-research-style skill descriptions.
- **Cost:** doesn't really achieve the bio-research aesthetic; the visible plugin is still heavy.
- **Win:** lowest blast radius; keeps everything that currently works; ~30 file renames + 30+ Skill() invocation rewrites.

## Comparison matrix

| Dimension                    | A: Clone | B: Productivity | C: Hub-and-spokes | D: Split | E: Agent-first | F: Minimal |
|------------------------------|----------|-----------------|-------------------|----------|----------------|------------|
| Single entry skill           | ✓        | ~ (`/start`+`/update`) | ✓             | ✗ (2)    | ✓              | ✓ (renamed) |
| Skill-for-agent pairs        | ✗        | ✗               | ✓ (4 pairs)       | ✓ (4)    | ✓ (5)          | partial    |
| Iron laws preserved          | inlined  | inlined         | preamble + ref    | preamble | inlined in agents | rule-file |
| Adversarial agent dispatch   | ✗        | ✗               | ✓                 | ✓        | ✓              | ✓          |
| Workspace + LSP env vars     | ✗        | ✓ (slim hook)   | ✓ (slim hook)     | ✓        | ✓              | ✓          |
| Observability JSONL          | ✗        | ✗               | ✓                 | ✓        | ✓              | ✓          |
| Routing-rules.json           | ✗        | ✗               | ✓ (slim, single target) | ✓ | ✓              | ✓          |
| Number of top-level skills   | 1–2      | 6               | 6                 | 7        | 8              | 19         |
| Number of agents             | 0        | 0               | 4                 | 4        | 5              | 4          |
| Number of hooks              | 0        | 2               | 10                | 10       | 10             | 30         |
| Files touched in refactor    | ~60      | ~50             | ~70               | ~80      | ~90            | ~30        |
| External-reference rot       | total    | high            | medium            | medium   | high           | low        |
| Match to user direction      | weak     | weak            | strong            | medium   | strong         | weak       |

## Selected approach: E — Agent-first (2026-04-28)

User selected approach **E** in the comparison matrix above. Architectural commitment:

- **Thin orchestrator skill** (`skills/ivy/SKILL.md`, ~80 LOC) handles silent context scan, methodology routing, and dispatch. Reads as the bio-research-style entry point.
- **Workflow logic lives in agents.** Each specialist agent preloads its operating procedure via the `skills: [...]` frontmatter (canonical Anthropic pattern; runs at agent spawn). Agents run with `context: fork` so multi-turn long-context work stays out of the main thread.
- **Ops-skills** are agent-loaded operating procedures, not user-invocable workflows. They bundle phases, Step Tracking, Red Flags, Process Flow digraphs — everything a rigid workflow currently has — but get injected into the agent that needs them rather than the main thread.
- **Knowledge** that needs main-thread visibility (iron laws, methodology routing, completion-gate, parallel-dispatch) lives as numbered references on the orchestrator. Knowledge that an agent needs (verifier-pattern catalog, specification-patterns, RFC text) is preloaded into the agent.

### Concrete sketch — agent-first roster

```
panther-ivy-plugin/
├── .claude-plugin/plugin.json
├── .mcp.json                         # ivy-tools + serena (kept)
├── README.md  (~5 KB)
├── CONNECTORS.md
├── skills/
│   ├── ivy/                          # ⭐ ORCHESTRATOR (thin dispatcher, ~80 LOC)
│   │   ├── SKILL.md
│   │   └── references/
│   │       ├── 01-iron-laws.md             # main-thread visible
│   │       ├── 02-methodology.md           # NCT / NACT / NSCT routing
│   │       ├── 03-completion-gate.md       # 5-step gate (used by orchestrator + agents)
│   │       └── 04-parallel-dispatch.md     # used when dispatching multiple agents
│   │
│   ├── triage-ops/                   # ops-skill, preloaded into ivy-triage-agent
│   ├── build-ops/                    # → ivy-builder-agent
│   ├── verify-ops/                   # → ivy-verifier-agent
│   ├── review-ops/                   # → ivy-reviewer-agent
│   ├── meta-self-mod-ops/            # → ivy-meta-agent
│   │
│   ├── verification-failures/        # cross-cutting; preloaded into verifier + reviewer
│   ├── specification-patterns/       # → builder + reviewer
│   ├── propagation-patterns/         # → builder
│   ├── apt-attack-patterns/          # → builder + reviewer (NACT scope)
│   ├── ivy-toolkit/                  # → all agents (tool catalog)
│   ├── ivy-syntax/                   # → builder + verifier (ivy-writing-guide content)
│   └── ivy-knowledge/                # standalone Q&A skill (no agent; main-thread reference)
│
├── agents/
│   ├── ivy-triage-agent.md           skills: [triage-ops, ivy-toolkit]
│   ├── ivy-builder-agent.md          skills: [build-ops, specification-patterns, propagation-patterns, ivy-syntax, ivy-toolkit]
│   ├── ivy-verifier-agent.md         skills: [verify-ops, verification-failures, ivy-syntax, ivy-toolkit]
│   ├── ivy-reviewer-agent.md         skills: [review-ops, verification-failures, apt-attack-patterns, ivy-toolkit]
│   └── ivy-meta-agent.md             skills: [meta-self-mod-ops]
│
├── hooks/                            # SLIMMED: workspace detection + observability + lifecycle
│   ├── hooks.json
│   └── scripts/
│       ├── detect-ivy-workspace.sh   (SessionStart — env vars; LSP/MCP cannot start without)
│       ├── cleanup-stale-pids.sh     (SessionStart)
│       ├── cleanup-ivy-lsp.sh        (SessionEnd)
│       ├── wait-for-indexing.sh      (SessionStart)
│       ├── inject-using-plugin.sh    (SessionStart — orchestrator priming)
│       ├── observability/observe.py  (all events — JSONL telemetry; ICSE 2027 research)
│       ├── retry-ivy-mcp.py          (PostToolUseFailure — transient retry)
│       └── notify-mcp-disconnect.py  (Notification)
│
├── commands/
│   ├── nct-health.md                 (standalone diagnostic; dispatches ivy-triage-agent)
│   └── nct-iut-test.md               (direct IUT test; bypasses orchestrator)
│
├── output-styles/
│   └── ivy-guided.md                 # the only style; default for plugin sessions
│
├── routing-rules.json                # OPEN — keep / drop (see grill question Q4 below)
├── settings.json                     # env-var passthrough
└── scripts/                          # start-ivy-server.sh, start-serena.sh, statusline
```

### Persistence model under agent-first

Agents run in forked contexts. They cannot share live state with each other or with the main thread. Two persistence layers needed:

1. **Session journal** — `.panther-ivy/session-logs/<timestamp>.jsonl` (kept; current observability stream feeds ICSE 2027 research). Orchestrator and `record-session-end.py` hook write to it; agents append journal entries via the `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_workflow_state` tool. This is the durable cross-agent state.
2. **Agent return values** — each agent returns a structured verdict (JSON-shaped) that the orchestrator reads on the main thread and appends to the journal. Verdicts include `claim`, `evidence_paths`, `gate_status`, `next_dispatch_hint`. The orchestrator decides whether to dispatch another agent, hand control to the user, or finalise.

### Iron-law and gate dispatch under agent-first

- **Main-thread iron laws** (visible to orchestrator): `STALENESS_RULE`, `NO_FIX_WITHOUT_VERIFY` (the orchestrator refuses to claim "verified" without a fresh agent verdict). Live in `skills/ivy/references/01-iron-laws.md`.
- **Agent-internal iron laws** (visible inside the agent's preloaded ops-skill): `NO_LAYER_WITHOUT_SCAFFOLD` (build-ops), `NO_QUALITY_WITHOUT_COVERAGE` (review-ops). Live in the ops-skill SKILL.md preamble.
- **Adversarial gates** (G0/G0b/G1-G6) — currently fire from skill bodies. Under E, gates that need 3-critic asymmetric votes (G0 plan-gate, G6 knowledge-gate) get dispatched as their own short-lived agents from the orchestrator. Gates internal to a workflow (G2/G3 build, G4 verify) fire inside the dispatched workflow agent.

### What's no longer needed under E

- `meta-using-panther-ivy-plugin/` — folds into `skills/ivy/SKILL.md` preamble.
- `workflow-navigate/` — replaced by `skills/ivy/SKILL.md`.
- `cross-cutting-completion-gate/` — collapses to `skills/ivy/references/03-completion-gate.md`.
- `cross-cutting-parallel-dispatch/` — collapses to `skills/ivy/references/04-parallel-dispatch.md`.
- `cross-cutting-reflection-patterns/` — split: gate critic prompts move to a per-gate agent; the rest folds into ops-skills.
- `cross-cutting-knowledge-capture/` — fires as its own short-lived agent at session-end and at gate breakpoints.
- 7 of 13 `.claude/rules/` (iron-laws, ivy-formatting, ivy-patterns, nct-methodology, mcp-tool-reliability, propagation-authority, agent-dispatch) — collapse into orchestrator references or ops-skill preambles.
- 5 of 7 commands (`/nct-check`, `/nct-compile`, `/nct-learn`, `/nct-model-info`, `/nct-observability`) — orchestrator handles dispatch.
- 3 of 4 output-styles (`ivy-default`, `ivy-audit`, README in `output-styles/`) — keep `ivy-guided` only.
- ~20 of 30 hook scripts — keep workspace detection (5), observability (1), MCP retry (1), notification (1), routing-via-orchestrator (optional), summary-render (optional).
- `routing-rules.json` — keep or drop is open (Q4).

### Decision Q1 (2026-04-28): Agent roster — 8 agents

Selected: **Adversarial-gate agents alongside workflow agents.** Roster:

```
agents/                         # 5 workflow specialists + 3 gate critics
├── ivy-triage-agent.md         skills:[triage-ops, ivy-toolkit]
├── ivy-builder-agent.md        skills:[build-ops, specification-patterns,
│                                       propagation-patterns, ivy-syntax,
│                                       ivy-toolkit]
├── ivy-verifier-agent.md       skills:[verify-ops, verification-failures,
│                                       ivy-syntax, ivy-toolkit]
├── ivy-reviewer-agent.md       skills:[review-ops, verification-failures,
│                                       apt-attack-patterns, ivy-toolkit]
├── ivy-meta-agent.md           skills:[meta-self-mod-ops]
│
├── g-plan-critic.md            # G0 / G0b adversarial gate; dispatched ×3 in parallel
├── g-fidelity-critic.md        # plan-fidelity gate (post-ExitPlanMode)
└── g-knowledge-critic.md       # G6 knowledge-capture gate (session-end)
```

Knowledge access stays on the main thread: orchestrator owns `references/01-iron-laws.md` … `04-parallel-dispatch.md`, plus a non-agent `skills/ivy-knowledge/SKILL.md` for direct Q&A on methodology / toolkit / ivy-syntax / verifier-patterns. The orchestrator dispatches a workflow agent only when the user wants to *do* something; for "explain X" it reads its own references inline.

Gate critics fire from the orchestrator, not from inside workflow agents. Orchestrator dispatches the same critic agent three times in parallel (3-critic asymmetric vote, 2-of-3 SOUND ⇒ proceed) when a gate is owed; otherwise the orchestrator skips the dispatch.

### Open dimensions to grill (post-Q1)

- **Q1 — Agent roster size and shape.** ✓ Decided: 8 agents (5 workflow + 3 gate critics).
- **Q2 — Ops-skill granularity.** ✓ Decided (2026-04-28): **Option B+ (Composed + on-demand reference loading)**. Each cross-cutting skill keeps content in `references/` rather than SKILL.md body. SKILL.md is a thin index; references load on-demand even within the agent's preloaded context. Per Anthropic canon, agent's `references/` stay on-demand even when its SKILL.md is preloaded. Most progressive-disclosure-aligned; smallest preloaded context per agent; agent reads reference when its SKILL.md body explicitly points at it.

  Skill files (11 total):
  - 5 workflow ops-skills: `triage-ops/`, `build-ops/`, `verify-ops/`, `review-ops/`, `meta-self-mod-ops/`
  - 6 cross-cutting catalog skills: `verification-failures/`, `specification-patterns/`, `propagation-patterns/`, `apt-attack-patterns/`, `ivy-toolkit/`, `ivy-syntax/`

  Each cross-cutting skill: `SKILL.md` (thin index, ~50–80 LOC, lists references with one-line summaries) + `references/*.md` (the actual catalog content, on-demand).

- **Q3 — Knowledge access on the main thread.** ✓ Decided (2026-04-28): **Option B (Orchestrator references minimal; cross-cutting skills are canonical home)**.

  Orchestrator SKILL.md body inlines load-bearing-every-turn content: iron-law primer + methodology routing (NCT/NACT/NSCT decision logic).

  Orchestrator's references hold only main-thread-on-demand content: `completion-gate.md` (5-step gate; loaded at claim time) and `parallel-dispatch.md` (loaded when dispatching multiple critics in parallel).

  For direct Q&A on the main thread (e.g. "explain NCT methodology", "what does ivy_diagnostics return"): orchestrator invokes the relevant cross-cutting skill via `Skill(skill="panther-ivy-plugin:<skill-name>")`, then reads the matching on-demand reference inside that skill's `references/`.

  One canonical home per topic (the cross-cutting skill); two access paths to that single home (main-thread `Skill()` for Q&A; agent preload via `skills:[...]` frontmatter for ops use). Aligns with Q2 B+ decision; aligns with bio-research's "skills are independent and standalone" pattern.
- **Q2 — Ops-skill granularity.** One ops-skill per agent (5 ops-skills total) or finer-grained shared ops-skills the agents compose (e.g. verify-ops + verification-failures + ivy-syntax preloaded together)?
- **Q3 — Knowledge access.** Knowledge-only Q&A (e.g. "explain NCT methodology") — handled by orchestrator reading its references inline, by a dispatched ivy-knowledge-agent, or by a non-agent `ivy-knowledge` skill the orchestrator points at?
- **Q4 — `routing-rules.json` disposition.** ✓ Decided: Option 3 hybrid. Drop `routing-rules.json`, drop `route-user-prompt.py`, drop `compose-style.py`. Keep all SessionStart, SessionEnd, PostToolUseFailure, Notification hooks because they solve concrete operational problems (env vars, LSP/MCP lifecycle, telemetry, retry, disconnect alerts). UserPromptSubmit chain shrinks to `observe.py` only. The orchestrator's description owns invocation; Anthropic canon ("write clear descriptions, let Claude decide") applies.

### Concrete hook inventory under Option 3

Group A — **KEEP** (33 → 21 hook entries; many of these are the same `observe.py` script wired to different events for telemetry):

```
SessionStart:
  ├── cleanup-stale-pids.sh         # MCP/LSP PID hygiene; required before liveness checks
  ├── cleanup-stale-workflow.py     # Clears orphaned active-workflow flags
  ├── detect-ivy-workspace.sh       # Writes IVY_WORKSPACE_ROOT, IVY_*_LOG_PATH env vars
  ├── inject-using-plugin.sh        # Injects orchestrator preamble (1% rule, iron laws)
  ├── wait-for-indexing.sh          # Blocks until LSP indexing ready
  └── observability/observe.py      # Telemetry

SessionEnd:
  ├── cleanup-ivy-lsp.sh            # Process teardown (LSP/MCP)
  └── observability/observe.py

PreToolUse:
  ├── block-direct-ivy.sh           # Bash matcher; blocks direct ivyc CLI invocation (memory rule: never run ivyc directly)
  ├── check-mcp-health.py           # mcp__.*ivy matcher; surfaces server-down before tool dispatch
  └── observability/observe.py

PostToolUse:
  ├── post-write-ivy-lint.sh        # Write|Edit matcher; runs ivy_diagnostics after .ivy edits
  ├── render-tool-result.py         # ivy_verify/coverage/diagnostics formatters; UI quality
  └── observability/observe.py

PostToolUseFailure:
  ├── retry-ivy-mcp.py              # Idempotent ivy_* tool retry on transient failure
  └── observability/observe.py

Stop:
  ├── render-summary.py             # End-of-turn workflow recap from journal
  └── observability/observe.py

Notification:
  ├── notify-mcp-disconnect.py      # Surfaces MCP-disconnect to user promptly
  └── observability/observe.py

SubagentStart, SubagentStop, PreCompact, PermissionRequest:
  └── observability/observe.py      # Telemetry only
```

Group B — **DROP** (12 hook entries removed):

```
UserPromptSubmit:
  ├── compose-style.py              # Output-style overlay (drop with output-styles slim)
  └── route-user-prompt.py          # routing-rules.json consumer (Q4 decision)

PreToolUse:
  ├── check-workspace-scope.py      # Orchestrator owns workspace via ivy_workspace tool
  ├── tip-shown.py                  # Orchestrator teaches usage; not hook responsibility
  ├── check-indexing-ready.sh       # wait-for-indexing.sh covers this at SessionStart
  └── observability/check_lsp_log.py # Roll into single observe.py call

PostToolUse:
  ├── track-workflow-skill.py       # Orchestrator + agents own workflow journal directly
  ├── auto-load-skill-references.py # Orchestrator owns reference loading
  ├── post-write-workflow-aware.py  # Orchestrator owns workflow state
  ├── assess-modeling.py            # Orchestrator decides when to dispatch builder agent
  ├── assess-testspec.py            # Orchestrator decides when to dispatch verifier agent
  ├── assess-trace.py               # Orchestrator decides when to dispatch reviewer agent
  ├── interaction-checkpoint.py     # Folds into render-summary.py end-of-turn
  └── record-workflow-error.py      # Orchestrator + agents append journal entries directly

Stop:
  └── record-session-end.py         # render-summary.py and observe.py cover end-of-session
```

The slim eliminates 12 hook entries (and their ~9 distinct script files) — the entire "workflow-aware decision" layer that today guesses when to fire gates and dispatch agents from PostToolUse. Under E that responsibility moves to the orchestrator, which sees the user's intent and the agent verdicts directly. Hooks survive only for things hooks uniquely solve: env injection at SessionStart, process lifecycle, transient retry, telemetry, output formatting.

### Per-script hook decisions log

Each dropped script gets explored individually with its concrete content; per-script decisions are recorded here.

| # | Script | Decision | Date | Notes |
|---|--------|----------|------|-------|
| 1 | `compose-style.py` (UserPromptSubmit; 40 LOC) | DROP | 2026-04-28 | Per-workflow output-style overlays move into each agent's preloaded ops-skill; single `ivy-guided.md` style + auto-loaded `ivy-formatting.md` rule cover main thread |
| 2 | `route-user-prompt.py` (UserPromptSubmit; 303 LOC) + `routing-rules.json` (4 KB) | DROP | 2026-04-28 | Eliminates misfire class. All 7 behaviors migrate into orchestrator: pending-dispatch consumption, active-workflow continuation, context-switch logging, activation, knowledge dispatch, [ROUTING:AVAILABLE] reminder, G1 gate trigger |
| 3 | `track-workflow-skill.py` (PostToolUse on Skill; 177 LOC) | DROP | 2026-04-28 | Trigger goes inert under E (orchestrator dispatches agents via Agent tool, not workflow sub-skills via Skill). Active-workflow YAML written by orchestrator via `ivy_workflow_state(action="set",...)` MCP tool at dispatch time; statusline reads YAML directly; phase_transition journal entries appended by orchestrator |
| 4 | `auto-load-skill-references.py` (PostToolUse on Skill; 80 LOC) | DROP | 2026-04-28 | Workaround for incomplete progressive disclosure. Inline iron laws + methodology routing into orchestrator SKILL.md body; keep completion-gate.md and parallel-dispatch.md as on-demand references body explicitly points at; ivy-knowledge references stay on-demand body-pointed by topic |
| 5 | `post-write-workflow-aware.py` (PostToolUse on Write\|Edit; 54 LOC) | KEEP + EXTEND | 2026-04-28 | Extend matcher to `Write\|Edit\|Agent`. On Write\|Edit of .ivy: existing statusline+suggestion behavior. On Agent dispatch with `subagent_type` starting `panther-ivy-plugin:`: update statusline with active agent + target file (extracted from prompt), emit "agent dispatched outside workflow" if no active workflow. Single script handles both code edits and agent dispatches |
| 6 | `assess-modeling.py` (PostToolUse on Write\|Edit\|NotebookEdit, build-only; 167 LOC) | KEEP + REWRITE | 2026-04-28 | Deterministic G2 modeling-gate trigger; fires inside builder agent forked context. Rewrite directive: drop `reflection-patterns` ref (preloaded into builder agent), rename `ivy-error-patterns` → `verification-failures`, update workflow filter `workflow-build` → `build` post-prefix-drop. Keep filter (layer files only, build-only), keep journal `gate_dispatched` append, keep build-state layer-name detection |
| 7 | `assess-testspec.py` (PostToolUse on Write\|Edit\|NotebookEdit, build-only, `*_test_*.ivy`; 133 LOC) | KEEP + REWRITE | 2026-04-28 | Mirror of #6 for G3 test-spec gate. Same rewrites: drop `reflection-patterns`, rename `ivy-error-patterns` → `verification-failures`, update workflow filter `workflow-build` → `build`. Catalog ID ranges (#200-208, #256-259, #300-399) and required inputs (test file + requirements manifest + ivy_coverage matrix) preserved |
| 8 | `assess-trace.py` (PostToolUse on `ivy_iut_test`; 143 LOC) | KEEP + REWRITE | 2026-04-28 | Mirror of #6/#7 for G5 trace-analysis gate. Tool match `ivy_iut_test` (not Write\|Edit). Not workflow-filtered (fires on all IUT runs incl `/nct-iut-test`). Same rewrites: drop `reflection-patterns`, rename `ivy-error-patterns` → `verification-failures`. Critical constraint preserved: critics MUST NOT invoke `ivy_iut_test` themselves; mandatory artifact-read order |
| 9 | `interaction-checkpoint.py` (PostToolUse on `ivy_verify\|ivy_coverage\|ivy_extract_requirements\|ivy_quality`; 133 LOC) | DROP | 2026-04-28 | References stale `claim-discussion` skill (no longer exists). Active-workflow filter brittle. Under E orchestrator-first model, "no workflow active during heavy MCP tool" rare. Orchestrator reads journal on next invocation for FAIL events; turn-level latency replaces same-turn nudge |
| 10 | `record-workflow-error.py` (PostToolUse on `ivy_verify\|ivy_compile\|ivy_diagnostics\|ivy_coverage\|ivy_iut_test\|ivy_quality`; 133 LOC) | KEEP + REWRITE | 2026-04-28 | Two responsibilities preserved: structured error-event journaling (regex-classified) + G4 verification-gate trigger (false-SOUND catcher with #401-406 calibrated-skepticism checklist). Same rewrites as #6/#7/#8: drop `reflection-patterns`, rename `ivy-error-patterns` → `verification-failures`, update workflow filter post-prefix-drop. Completes the deterministic gate-firing quartet G2/G3/G4/G5. Verifier-agent must avoid double-dispatching G4 in diagnose-and-retry loops |
| 11 | `record-session-end.py` (Stop hook, active-workflow-filtered; 48 LOC) | KEEP AS-IS | 2026-04-28 | Reversed earlier DROP recommendation. Two load-bearing responsibilities not covered elsewhere: structured `session_end{clean: True, phase_at_exit}` entry for warm-resume + journal rotation (essential for long-running ICSE 2027 telemetry). Filter retained; knowledge-only turns ending cleanly skip the marker (acceptable trade-off) |
| 12 | `check-workspace-scope.py` (PreToolUse on Write\|Edit for .ivy files; 177 LOC) | KEEP + REWRITE DENY MSG | 2026-04-28 | Reversed earlier DROP recommendation. Real harness-level enforcement (blocks out-of-workspace edits via `deny_reason`). Stronger than orchestrator prompt guidance; prevents cross-protocol contamination from confused agents. Rewrite deny message: replace `/set-workspace` / `/clear-workspace` command refs with `ivy_workspace(action="set"\|"clear", target="...")` MCP tool dispatch (kwarg is `target=`, not `protocol=`). Confirm whether `/set-workspace` is a slash command and reconcile with kept-commands list |
| 13 | `tip-shown.py` (PreToolUse on `ivy_verify`, `ivy_coverage`; 91 LOC) | DROP | 2026-04-28 | Once-per-session usage tips redundant under E. ivy_verify procedure (`ivy_diagnostics` first → `ivy_verify`) lives in verifier-agent's verify-ops preloaded SKILL.md. ivy_coverage procedure (`mode=stats` before `mode=matrix`) lives in reviewer-agent's review-ops preloaded SKILL.md. Orchestrator preamble covers main-thread invocations. Per-session state file `.observability/sessions/<id>/tips-shown.json` goes away |
| 14 | `check-indexing-ready.sh` (PreToolUse on `mcp__.*ivy`; 114 LOC) | KEEP AS-IS | 2026-04-28 | Reversed earlier DROP recommendation. Complements wait-for-indexing.sh: SessionStart hook blocks cold-start, this PreToolUse hook blocks mid-session not-ready windows (workspace switches, manual restarts). Real harness-level enforcement under E with agents driving heavy ivy_* tool cadence. Circuit breaker (6 denials ≈ 60s → fail-open with warning) prevents infinite blocking |
| 15 | `observability/check_lsp_log.py` (PreToolUse on `mcp__.*ivy`; 95 LOC) | FOLD INTO `check-mcp-health.py` | 2026-04-28 | Surfaces 60s recent-MCP-error categorisation. Catches server-internal errors (Tracebacks, ConnectionReset) that observe.py PostToolUseFailure misses (different log stream). Consolidate with check-mcp-health.py into one PreToolUse hook on `mcp__.*ivy` doing both 'is server alive?' and 'any recent server-side errors?'. Two scripts → one |

### Hook decisions summary

**Dropped (6 scripts + 1 config):** `compose-style.py`, `route-user-prompt.py` + `routing-rules.json`, `track-workflow-skill.py`, `auto-load-skill-references.py`, `interaction-checkpoint.py`, `tip-shown.py`.

**Folded:** `observability/check_lsp_log.py` → into `check-mcp-health.py`.

**Kept + extended (1 script):** `post-write-workflow-aware.py` (matcher widens to `Write|Edit|Agent`).

**Kept + rewritten directives (4 scripts):** `assess-modeling.py`, `assess-testspec.py`, `assess-trace.py`, `record-workflow-error.py`. Common rewrites: drop `reflection-patterns` ref (preloaded into agents), rename `ivy-error-patterns` → `verification-failures`, update workflow filter post-prefix-drop, update styles refs if styles tree changes. The G2/G3/G4/G5 deterministic gate-firing quartet is preserved.

**Kept + rewrote deny message (1 script):** `check-workspace-scope.py` (deny references `/set-workspace` / `/clear-workspace` → reconcile with kept-commands list and/or use `ivy_workspace` MCP tool).

**Kept as-is (2 scripts):** `record-session-end.py`, `check-indexing-ready.sh` (both reversed earlier DROP recommendations after reading actual code).

**Final hook footprint:** roughly 21 scripts kept (down from ~30 today). Of the kept, 9 are observability/lifecycle (cleanup-stale-pids, cleanup-stale-workflow, detect-ivy-workspace, wait-for-indexing, inject-using-plugin, observability/observe wired to several events, cleanup-ivy-lsp, retry-ivy-mcp, notify-mcp-disconnect), and the rest are gate-firing + enforcement + UI scripts revisited above.

### Open dimensions to grill (post-Q4)

- **Q7 — Slash command roster.** ✓ Decided (2026-04-28): **Option B (2 commands)**. Keep `/nct-health` and `/nct-iut-test` only. Drop `/nct-check`, `/nct-compile`, `/nct-learn`, `/nct-model-info`, `/nct-observability`. Do NOT add `/set-workspace` or `/clear-workspace` — workspace control happens via the `ivy_workspace(action="set"|"clear", target="...")` MCP tool dispatch (kwarg is `target=`, not `protocol=`). Workflow tracking (active-workflow YAML) happens via the separate `ivy_workflow_state(action="set", workflow=…, phase=…, protocol=…)` MCP tool.

  **Cascading rewrites required by this decision:**
  - **Decision #12 deny-message rewrite is now mandatory.** `check-workspace-scope.py`'s deny `permissionDecisionReason` must reference the MCP tool, not slash commands: e.g. `"To allow: invoke ivy_workspace(action='set', target='<group>') or ivy_workspace(action='clear')"`. The kwarg is `target=`, not `protocol=`.
  - **`inject-using-plugin.sh` SessionStart hook rewrite.** Today injects the meta-using primer that documents `/set-workspace <protocol>`. Rewrite the primer to point at the MCP tool: `Use ivy_workspace(action='set', target='<name>') to scope edits.`
  - **No mid-session manual knowledge-capture trigger.** `g-knowledge-critic` agent dispatches automatically at session-end via the orchestrator's session-end gate. Users wanting mid-session capture ask the orchestrator conversationally; the orchestrator dispatches the gate critic on demand.

- **Q5 — Migration phasing.** ✓ Decided (2026-04-28): **Option A (Phased on the existing arc)**. Six commits A–F plus Phase G after Q6 decides.

  **Phase 0 — Capability check (pre-Phase-A; no commit).** Verify the `ivy_workspace` AND `ivy_workflow_state` MCP tools' action surfaces BEFORE starting any phase. Confirm `ivy_workspace(action="set", target="bgp")` (kwarg is `target=`, not `protocol=`) updates workspace state and `ivy_workspace(action="clear")` clears state. Confirm `ivy_workflow_state(action="set", workflow="verify", phase="init", protocol="bgp")` round-trips via a paired `ivy_workflow_state(action="get")`. If either tool's expected action surface is unavailable, the refactor cannot land as planned: decision #12's deny-message rewrite, Q7's drop of `/set-workspace` / `/clear-workspace`, and the orchestrator's per-dispatch journal write all rely on these tools. Two outcomes:
  - **Actions exist** → proceed to Phase A.
  - **Actions don't exist** → escalate scope: either add the actions to the MCP server first (extends Phase A scope by ~50–200 LOC of MCP-server work and a coordinated submodule pointer bump), or revert Q7 to keep `/set-workspace` and `/clear-workspace` slash commands. The decision returns to the user before continuing.

  **Phase A — Scaffold orchestrator and disable old entry points.** Create `skills/ivy/SKILL.md` (thin orchestrator) + `agents/g-plan-critic.md` + `agents/g-fidelity-critic.md` + `agents/g-knowledge-critic.md`. The orchestrator SKILL.md body **must include an explicit dispatch-time step that updates `.panther-ivy/active-workflow` via the `ivy_workflow_state(action="set", workflow="<target>", phase="init", protocol="<protocol>")` MCP tool call before dispatching any agent** (the `ivy_workflow_state` tool is separate from `ivy_workspace`; the latter manages verification scope, the former manages the workflow journal). This is the replacement for the dropped `track-workflow-skill.py` PostToolUse hook (decision #3). Without this step in Phase A, the YAML goes unmaintained after Phase D drops the hook. **The 3 gate-critic agents in Phase A are self-contained — no `skills:[...]` preload chain.** Their critic-prompt content (the verbatim adversarial-vote template, the calibrated abstention rubric, the SOUND/UNSOUND/ABSTAIN aggregation rules) is fully inline in each agent's `.md` body. This avoids a Phase-A-on-Phase-B dependency for cross-cutting skill names that don't yet exist under their post-E names. (Trade-off: gate critics don't reuse the canonical numbered pattern catalog from `verification-failures` skill; they enumerate the relevant patterns inline. Acceptable because gate critics are short-lived and the patterns they cite are gate-specific, not the full #100-#599 catalog.) **Crucially, Phase A also rewrites `inject-using-plugin.sh` and `meta-using-panther-ivy-plugin/SKILL.md` content** so the SessionStart primer points at the new `ivy` orchestrator instead of `workflow-navigate`. To prevent activation competition, set `user-invocable: false` and strip the trigger phrases from `workflow-navigate/SKILL.md` and `meta-using-panther-ivy-plugin/SKILL.md` descriptions in the same commit. Both skills remain on disk (deleted in Phase F per backup-before-delete) but no longer compete with the orchestrator for Claude's intent matcher. **Note: `user-invocable: false` only blocks description-driven activation by Claude's intent matcher. Explicit `Skill(skill="panther-ivy-plugin:workflow-navigate")` invocations from other skills' bodies continue to resolve until those calling skills are themselves rewritten in Phases B/C/E.** **Verify** with the following concrete test prompts in a fresh session:
  1. `"help me navigate to bgp"` → expected: orchestrator (`skills/ivy`) activates; `workflow-navigate` does NOT.
  2. `"use using-panther-ivy-plugin to set up"` → expected: orchestrator activates; `meta-using-panther-ivy-plugin` does NOT.
  3. `"start a verification gate dispatch"` → expected: orchestrator dispatches `g-plan-critic` (or `g-fidelity-critic` depending on which gate is wired in this phase) end-to-end with 3-critic asymmetric vote; result returned.
  4. Note: `workflow-build`, `workflow-verify`, `workflow-review`, `workflow-triage` are still triggering at Phase A — their disablement comes in Phase C. So a prompt like `"verify the spec"` may still activate `workflow-verify` at Phase A; this is expected and not a regression.

  **Commit**: `feat(plugin): scaffold ivy orchestrator + 3 gate-critic agents + disable workflow-navigate/meta-using triggering (Phase A)`.

  **Phase B — Cross-cutting skills (Q2 B+ structure) + global rename pass.** Rename `knowledge-ivy-toolkit` → `ivy-toolkit`; `knowledge-ivy-writing-guide` → `ivy-syntax`; `knowledge-methodology-reference` → `methodology`; `knowledge-verification-failures` → `verification-failures`; `knowledge-specification-patterns` → `specification-patterns`; `knowledge-propagation-patterns` → `propagation-patterns`; `knowledge-apt-attack-patterns` → `apt-attack-patterns`. Restructure each into thin SKILL.md (~50–80 LOC index) + `references/*.md` (catalog content moves out of SKILL.md body if not already there).

  **Crucially, Phase B's commit also includes a global rename pass across the entire plugin tree** so no file references the old `knowledge-*` names after the commit. Targets:
  - Other skills' `SKILL.md` bodies and `references/*.md` files (notably `cross-cutting-*` skills and `workflow-*` skills that invoke knowledge-* via `Skill()`).
  - Hook directive text in `assess-modeling.py`, `assess-testspec.py`, `assess-trace.py`, `record-workflow-error.py` (the skill-name-string portion of the rewrites; the structural removal of `reflection-patterns` ref stays in Phase D).
  - Rule bodies in `ivy-patterns.md` and `nct-methodology.md` (the `Skill(...)` target in the body; the structural rule rewrite stays in Phase E).

  This atomicity prevents the intermediate-state failure where Phase B's commit ships hook directives and rules pointing at defunct skill names. Phase D and Phase E retain their STRUCTURAL changes (removing `reflection-patterns` references, restructuring rule bodies); they no longer carry the rename burden.

  **Verify**:
  1. Each cross-cutting skill loads independently via `Skill(skill="panther-ivy-plugin:<new-name>")`; the index SKILL.md returns; references load on-demand from inside it.
  2. **Body length check**: each renamed skill's SKILL.md is ≤ 80 LOC after restructuring. Run `wc -l skills/{ivy-toolkit,ivy-syntax,methodology,verification-failures,specification-patterns,propagation-patterns,apt-attack-patterns}/SKILL.md`; report body line counts in the commit message body.
  3. **Zero defunct references**: after the global rename pass, `git grep -l 'knowledge-ivy-toolkit\|knowledge-ivy-writing-guide\|knowledge-methodology-reference\|knowledge-verification-failures\|knowledge-specification-patterns\|knowledge-propagation-patterns\|knowledge-apt-attack-patterns' panther-ivy-plugin/plugins/panther-ivy-plugin/` returns zero matches.

  **Commit**: `refactor(plugin): cross-cutting skills to thin-index + on-demand references + global rename (Phase B, Q2 B+)`.

  **Phase C — Ops-skills + workflow agents + disable remaining old triggers + handle old agent files.** Create `skills/{triage-ops,build-ops,verify-ops,review-ops,meta-self-mod-ops}/SKILL.md`. Move phase content from existing `workflow-*` skills. Create `agents/{ivy-triage,ivy-builder,ivy-verifier,ivy-reviewer,ivy-meta}-agent.md` with `skills:[...]` preload chains per Q1.

  **Per-agent capability migration table** (C-W1 fix). Each new agent's capabilities trace explicitly to source agents and workflow phases:

  | New agent | Capabilities absorbed from | Source workflow phase | Required `<dispatch-context>` fields beyond the canonical 3 |
  |---|---|---|---|
  | `ivy-triage-agent` | (net new content from `workflow-triage` skill body) | triage Phases 1–3 | none beyond canonical (`target_files`, `workspace`, `phase_context`) |
  | `ivy-builder-agent` | `model-reviewer.md` (build-time portion) | build Phases 1–6 | `review_scope` (when dispatched for build-time gate dispatch) |
  | `ivy-verifier-agent` | `spec-analyst.md` (full); `model-reviewer.md` (verify Phase 6 diagnosis portion) | verify Phases 1–7 | `verification_target`, `failure_context` (when dispatched for diagnosis) |
  | `ivy-reviewer-agent` | `model-reviewer.md` (review-time portion); `traceability-agent.md` (full) | review Phases 1–4 | `review_scope`, `rfc_source`, `existing_manifest` (per agent-dispatch.md schema) |
  | `ivy-meta-agent` | `plugin-conventions-reviewer.md` (full) | (plugin self-mod, no current workflow phase) | none beyond canonical |

  **Old specialist agent files (`spec-analyst.md`, `model-reviewer.md`, `traceability-agent.md`, `plugin-conventions-reviewer.md`) stay on disk through Phase C** (option b for C-C1). They become inert after Phase C because nothing in the new orchestrator + new workflow agents dispatches them; only the deprecated `workflow-*` skills' bodies still reference them, and those skills have `user-invocable: false` set in this same Phase C commit. Phase F deletes these 4 old agent files (with `.backup/2026-04-28/` per memory rule) along with the deprecated skills.

  **After moving content, disable activation on every remaining deprecated skill so they don't compete with the new orchestrator after Phase D drops the routing hook**: set `user-invocable: false` and strip trigger phrases from `workflow-build`, `workflow-verify`, `workflow-review`, `workflow-triage`, `cross-cutting-completion-gate`, `cross-cutting-knowledge-capture`, `cross-cutting-parallel-dispatch`, `cross-cutting-reflection-patterns`, `meta-plugin-self-mod` SKILL.md frontmatter. (Phase A already disabled `workflow-navigate` and `meta-using-panther-ivy-plugin`.) The deprecated skills remain on disk for Phase F deletion, but their descriptions no longer match user prompts.

  **Active-workflow YAML schema migration** (C-W3 fix). User sessions in progress write `.panther-ivy/active-workflow` with `workflow: workflow-verify` (old name). After Phase C commits, warm-resume from a pre-Phase-C session reads an old workflow name. Phase C ships a one-shot migration step:
  - Add a `scripts/migrate-active-workflow.sh` that walks `protocol-testing/*/.panther-ivy/active-workflow` and rewrites old workflow names (`workflow-{navigate,build,verify,review,triage}` → `{ivy-orchestrator,build,verify,review,triage}` or `ivy-{builder,verifier,reviewer,triage}-agent` per the plan's mapping). The script should run idempotently and skip files already on the new schema.
  - Run this script as part of Phase C's smoke test before declaring the phase verified.
  - Orchestrator code on warm-resume gracefully handles either schema (accepts old `workflow-*` names by mapping internally) for one minor version, then drops the compat path in a future cleanup.
  - The append-only `.panther-ivy/workflow-journal.jsonl` retains old `workflow: workflow-verify` entries permanently; orchestrator's journal-replay code accepts either name.

  **Verify**:
  1. Orchestrator dispatches each of the 5 workflow agents on a stub task; agent preloads its skill chain (test by inspecting agent context after spawn); agent runs Phase 1 of its workflow successfully on a known-clean fixture.
  2. Prompts containing old workflow trigger phrases ("verify the spec", "build a layer", "review coverage") activate the new orchestrator, NOT the old `workflow-*` skills.
  3. **No deprecated `cross-cutting-*` or `workflow-*` skill invocations from new files**: `git grep -E 'panther-ivy-plugin:(cross-cutting-|workflow-)' panther-ivy-plugin/plugins/panther-ivy-plugin/skills/{ivy,triage-ops,build-ops,verify-ops,review-ops,meta-self-mod-ops}/ panther-ivy-plugin/plugins/panther-ivy-plugin/agents/{ivy-triage,ivy-builder,ivy-verifier,ivy-reviewer,ivy-meta}-agent.md` returns zero matches.
  4. Each new agent's body includes a `<dispatch-context>` block conforming to `agent-dispatch.md` schema (canonical 3 required fields plus the agent-specific optional fields enumerated above).
  5. `migrate-active-workflow.sh` runs successfully on a fixture pre-Phase-C session; warm-resume from the migrated state lands the orchestrator at the right resumption point.

  **Commit**: `feat(plugin): 5 workflow ops-skills + 5 specialist agents + disable deprecated skill triggers + active-workflow migration (Phase C)`.

  **Phase D — Hook slim (15-script decisions) + workflow-name string renames in kept hooks.** Drop 6 scripts (`compose-style`, `route-user-prompt`, `track-workflow-skill`, `auto-load-skill-references`, `interaction-checkpoint`, `tip-shown`). Drop `routing-rules.json`. Fold `check_lsp_log` into `check-mcp-health`. Extend `post-write-workflow-aware` matcher to `Write|Edit|Agent`. Rewrite 4 gate-firing scripts (Phase B's global rename pass already updated the skill-name strings to `verification-failures`; Phase D removes the structural `reflection-patterns` reference and any other content updates not handled by the rename). Rewrite `check-workspace-scope` deny message (use `ivy_workspace` MCP tool, not `/set-workspace`). Update `hooks.json` to the target structure below.

  **Workflow-name rename pass in kept hooks** (D-C1 fix). Phase C's `migrate-active-workflow.sh` rewrites `.panther-ivy/active-workflow` from `workflow: workflow-build` to `workflow: build` (or to `ivy-builder-agent` per the new schema). Several kept hook scripts filter or display workflow names by string literal:
  - `hooks/scripts/assess-modeling.py` line 132: `if ctx.workflow != "workflow-build"` → `if ctx.workflow != "build"`.
  - `hooks/scripts/assess-testspec.py` line 101: same rename.
  - `hooks/scripts/record-workflow-error.py`: any workflow-name literal reference.
  - `hooks/scripts/detect-ivy-workspace.sh`: rewrite the `[ROUTING:AVAILABLE]` message. Two options: (a) drop the workflow-skill list entirely (orchestrator description handles activation; the routing-available hint is no longer load-bearing under Q4 hybrid), or (b) update to the new orchestrator name ("Active workspace: \<protocol\>. Invoke /panther-ivy-plugin:ivy or describe your task in plain text"). Option (a) is recommended.
  - Any other kept hook script with `workflow-*` string literals — `git grep -E 'workflow-(navigate|build|verify|review|triage)' hooks/scripts/` enumerates them.

  Without this rename pass, gate-firing hooks silently no-op after Phase C's active-workflow YAML migration runs.

  **Standardise hook output keys** (user feedback, 2026-04-28). Every kept hook that emits non-trivial output sets BOTH `systemMessage` (user-visible summary) AND `additionalContext` (Claude-actionable directive) where both make sense. Today most hooks emit only `additionalContext`, so the user has no visibility into what fired or what was injected. Per-hook target shape:

  | Hook | `systemMessage` (user-visible) | `additionalContext` (Claude-actionable) |
  |---|---|---|
  | `inject-using-plugin.sh` | `"[panther-ivy] orchestrator preamble injected"` (brief) | full primer body (load-bearing for Claude) |
  | `detect-ivy-workspace.sh` | `"[ivy-workspace] detected: bgp"` (active workspace + MCP status) | (none — no Claude directive needed) |
  | `wait-for-indexing.sh` | `"[ivy-indexing] ready"` or `"[ivy-indexing] still indexing (Ns)"` | (none) |
  | `cleanup-stale-pids.sh` / `cleanup-stale-workflow.py` | (silent unless something cleaned up: `"[ivy-cleanup] cleared N stale PIDs"`) | (none) |
  | `cleanup-ivy-lsp.sh` | `"[ivy-lifecycle] LSP/MCP terminated cleanly"` | (none) |
  | `block-direct-ivy.sh` | `"[ivy-block] direct ivyc invocation refused (use ivy_compile MCP tool)"` | brief Claude hint to use the MCP tool |
  | `check-mcp-health.py` (folded with `check_lsp_log.py`) | `"[ivy-health] OK"` or `"[ivy-health] N recent errors (crashes/timeouts/connection/other)"` | (none on OK; brief retry advisory on errors) |
  | `check-indexing-ready.sh` | `"[ivy-indexing] not ready (attempt N/6)"` (on deny) | (deny path uses `permissionDecisionReason`, not additionalContext) |
  | `check-workspace-scope.py` | `"[ivy-workspace-scope] BLOCKED: <file>"` (on deny) | (deny path uses `permissionDecisionReason`) |
  | `post-write-ivy-lint.sh` | `"[ivy-lint] PASS"` or `"[ivy-lint] N structural findings"` | full diagnostics on findings (Claude reads to decide next step) |
  | `post-write-workflow-aware.py` (extended to Agent matcher) | `"[ivy-state] active-workflow=<...>, test_file=<...>"` | (suggestion text only when no active workflow) |
  | `assess-modeling.py` (G2) | `"[G2 modeling gate] dispatched on <file>"` | full G2 directive (8-step) |
  | `assess-testspec.py` (G3) | `"[G3 test-spec gate] dispatched on <file>"` | full G3 directive |
  | `assess-trace.py` (G5) | `"[G5 trace-analysis gate] dispatched on <run_id>"` | full G5 directive |
  | `record-workflow-error.py` (G4) | `"[G4 verification gate] dispatched on <verify-result>"` or `"[ivy-error] <classification>"` (on error path) | full G4 directive |
  | `retry-ivy-mcp.py` | `"[ivy-retry] retried <tool> on transient failure"` | retry advisory text |
  | `render-tool-result.py` | (already produces user-visible output as `tool_response` modifier; no systemMessage needed) | (none) |
  | `render-summary.py` | `"[ivy-recap] session recap below"` plus full recap text | (none) |
  | `notify-mcp-disconnect.py` | `"[ivy-health] MCP disconnected — run /mcp to reconnect"` | (none) |
  | `record-session-end.py` | (silent — observability stream captures the event) | (none) |
  | `observability/observe.py` | (silent — telemetry writes to JSONL only) | (none) |

  This gives the user a continuous log of what hooks fired and what they did, while preserving Claude's full directive context for action. The implementation pattern: each hook calls `emit_hook_output(event, system_message=..., additional_context=...)` from `hook_utils.py` (the helper kept in Phase D); update `hook_utils.emit_hook_output` to accept both kwargs and produce `hookSpecificOutput.{systemMessage, additionalContext}` correctly.

  **Target post-D `hooks.json` structure** (referenceable diff target):
  ```
  SessionStart      : 6 entries
    cleanup-stale-pids.sh ; cleanup-stale-workflow.py ; detect-ivy-workspace.sh ;
    inject-using-plugin.sh ; wait-for-indexing.sh ; observability/observe.py
  SessionEnd        : 2 entries (cleanup-ivy-lsp.sh ; observability/observe.py)
  PreToolUse        : Bash matcher (block-direct-ivy.sh) ;
                      mcp__.*ivy matcher (check-mcp-health.py incl. folded check_lsp_log,
                                           check-indexing-ready.sh) ;
                      Write|Edit matcher (check-workspace-scope.py) ;
                      catch-all matcher (observability/observe.py)
  PostToolUse       : Write|Edit|Agent matcher (post-write-workflow-aware.py) ;
                      Write|Edit matcher (post-write-ivy-lint.sh) ;
                      Write|Edit|NotebookEdit matcher filtered (assess-modeling.py) ;
                      Write|Edit|NotebookEdit matcher filtered (assess-testspec.py) ;
                      ivy_iut_test matcher (assess-trace.py) ;
                      ivy_verify|ivy_compile|ivy_diagnostics|ivy_coverage|ivy_iut_test|ivy_quality matcher
                                                          (record-workflow-error.py , render-tool-result.py) ;
                      catch-all (observability/observe.py)
  PostToolUseFailure: 2 (retry-ivy-mcp.py ; observability/observe.py)
  Stop              : 3 (record-session-end.py ; render-summary.py ; observability/observe.py)
  Notification      : 2 (notify-mcp-disconnect.py ; observability/observe.py)
  SubagentStart, SubagentStop, PreCompact, PermissionRequest : observability/observe.py only
  UserPromptSubmit  : observability/observe.py only       <-- compose-style.py and route-user-prompt.py DROPPED
  ```

  **Verify**:
  1. **SessionStart hook chain runs cleanly with the post-Phase-D `hooks.json`**; observability JSONL captured for all events; G2/G3/G4/G5 gates fire correctly on their respective triggers.
  2. **No UserPromptSubmit misfires**: `observability/observe.py` is the only hook firing on UserPromptSubmit; no `[ROUTING]` / `[ROUTING:AVAILABLE]` / `[ROUTING:CONTINUE]` / `(style overlay)` additionalContext markers appear in any user prompt's hook output (test with 5 representative prompts: knowledge Q&A, verify request, build request, plain-text question, refactor planning).
  3. **`ivy_workspace` AND `ivy_workflow_state` MCP tool actions confirmed**: `ivy_workspace(action="set", target="bgp")` and `ivy_workspace(action="clear")` execute successfully; `ivy_workflow_state(action="set", workflow="verify", phase="init", protocol="bgp")` plus a paired `ivy_workflow_state(action="get")` round-trip cleanly (re-confirms Phase 0).
  4. **`check-workspace-scope.py` deny message correctness**: trigger an out-of-scope `.ivy` edit and confirm the deny message quotes `ivy_workspace(action='set', target='<group>')` and `ivy_workspace(action='clear')` exactly (kwarg `target=`, not `protocol=`), not `/set-workspace` / `/clear-workspace`.
  5. **Orchestrator activation without routing hook**: 5 representative user prompts (mixed Ivy and non-Ivy) exercise the orchestrator's description-driven activation. The orchestrator activates on Ivy-relevant prompts; does not activate on non-Ivy prompts (refactor planning, plain conversation). No deprecated skill activates instead.
  6. **`ivy-guided.md` style sufficiency**: orchestrator main-thread output (knowledge Q&A, agent-verdict synthesis, end-of-turn recap) renders acceptably under the single style. If a workflow-specific format expectation is missed (e.g., verdict block format for verify-result synthesis), document the gap and either rewrite `ivy-guided.md` body or accept the gap and note for a future cleanup.
  7. **Active-workflow YAML still maintained**: after a turn that dispatches an agent, `.panther-ivy/active-workflow` reflects the latest dispatch. The orchestrator's body (Phase A scaffolded) writes via `ivy_workspace(action="set", ...)` at dispatch time; confirm by reading the YAML mid-session.

  **Commit**: `refactor(plugin/hooks): slim hook footprint per 15-script per-script decisions (Phase D)`.

  **Phase E — Commands / output-styles / rules slim.** Drop 5 commands (`nct-check`, `nct-compile`, `nct-learn`, `nct-model-info`, `nct-observability`). Drop 3 styles + README (`ivy-default`, `ivy-audit`, `output-styles/README.md`).

  **Rule rewrites (substantive after Phase B's global rename pass):**
  - `iron-laws.md`: add a note at the top of `<context>` block — "The orchestrator's `skills/ivy/SKILL.md` body inlines a short iron-law primer for main-thread visibility on every dispatch decision; this rule auto-loads the full `<iron-law>` block detail on `.ivy`/`.spec` edits via the `paths:` glob. Both surfaces stay in sync via this rule being the canonical source — primer is a summary derived from the rule body."
  - `gap-markers.md`: drop the entire "Relationship to claim-discussion prefixes" section (claim-discussion skill subsumed). Keep the rest as-is. Confirm `ivy-error-patterns` references already renamed to `verification-failures` by Phase B.
  - `output-style.md`: drop these 5 marker rows from the table — `[ROUTING]`, `[ROUTING:AVAILABLE]`, `[ROUTING:CONTINUE]`, `(style overlay)`, `[INTERACTION CHECKPOINT]`. Add the `[G4 verification gate]` row pointing at `record-workflow-error.py`. Add notes about the post-Phase-D systemMessage convention so users know the new dual-key output shape.
  - `postuse-hook-ordering.md`: rewrite the ordering table to reflect the post-D PostToolUse list (per the target hooks.json shape in Phase D). Drop the `interaction-checkpoint.py` row; add the `record-workflow-error.py` row; reflect the Agent-matcher extension on `post-write-workflow-aware.py` and the new gate-trigger ordering. Update §"State read by each script" table.
  - `skill-conventions.md` §2 roster rewrite — full new shape:
    - Rigid (6): `ivy` (orchestrator), `triage-ops`, `build-ops`, `verify-ops`, `review-ops`, `meta-self-mod-ops`.
    - Flexible (6): `verification-failures`, `specification-patterns`, `propagation-patterns`, `apt-attack-patterns`, `ivy-toolkit`, `ivy-syntax`.
    - Add a new section §"Agent conventions" specifying the gate-critic agent type (self-contained, no preload, inline critic-prompt template) and the workflow-agent type (preload skill chain via `skills:[...]` frontmatter, `<dispatch-context>` block per agent-dispatch.md schema).
    - Update §"Common violations" §8 to add the post-E patterns.
  - `ivy-patterns.md`, `nct-methodology.md`, `plan-mode.md`: skill-name renames already handled by Phase B's global pass. **No Phase E rewrite needed for these 3 unless additional structural changes surface during the per-rule walkthrough**.

  (Note: `inject-using-plugin.sh` primer text was already rewritten in Phase A.)

  **Verify**:
  1. Kept commands resolve: invoke `/nct-health` and `/nct-iut-test`; both return their command file content. Invoke each dropped command (`/nct-check`, `/nct-compile`, `/nct-learn`, `/nct-model-info`, `/nct-observability`); each returns "command not found" cleanly.
  2. `outputStyle = "panther-ivy-plugin:Ivy Guided"` resolves; the dropped styles (`Ivy Default`, `Ivy Audit`) return "style not found".
  3. Path-glob auto-load fires for kept rules on matching file edits: edit a `.ivy` file → confirm `iron-laws.md` + `gap-markers.md` + `ivy-patterns.md` + `nct-methodology.md` + `propagation-authority.md` + `plan-mode.md` content appears in the next system-reminder.
  4. `skill-conventions.md` §2 roster lists exactly the 12 skills (6 rigid + 6 flexible) above.
  5. `output-style.md` table no longer references dropped hook markers; the `[G4 verification gate]` row is present.

  **Commit**: `refactor(plugin): slim commands / output-styles / rules (Phase E)`.

  **Phase F — Cleanup + parent repo + memory.** Split into two sub-commits for safe rollback (F-W2 fix).

  **Phase F.1 — Reversible cleanup commit.** All file moves and metadata updates; reversible via `git revert` if Phase F.2 smoke test fails.
  - **Skill backup-and-remove**: move deprecated skills to `.backup/2026-04-28/skills/` per memory rule. Targets: `workflow-navigate`, `workflow-build`, `workflow-verify`, `workflow-review`, `workflow-triage`, `cross-cutting-completion-gate`, `cross-cutting-knowledge-capture`, `cross-cutting-parallel-dispatch`, `cross-cutting-reflection-patterns`, `meta-using-panther-ivy-plugin`, `meta-plugin-self-mod`. (11 deprecated skill directories.)
  - **Agent backup-and-remove**: move 4 deprecated specialist agent files to `.backup/2026-04-28/agents/`. Targets: `agents/spec-analyst.md`, `agents/model-reviewer.md`, `agents/traceability-agent.md`, `agents/plugin-conventions-reviewer.md`.
  - **Plugin metadata**: update `README.md` and `CHANGELOG.md` to reflect the new layout (orchestrator + 8 agents + 11 skills + 2 commands + 1 style + 13 rules).
  - **Parent-repo fix**: replace defunct `/panther-ivy-plugin:navigate` reference in `/Users/elniak/Documents/.../lsp-to-claude/ONBOARDING.md` with `/panther-ivy-plugin:ivy` or remove the line.
  - **Memory file updates** (F-W1 fix). Concrete steps:
    1. Run `git grep -lE 'workflow-(navigate|build|verify|review|triage)|cross-cutting-|meta-using-panther|knowledge-(ivy|methodology|specification|propagation|apt|verification)|spec-analyst|model-reviewer|traceability-agent|plugin-conventions-reviewer' /Users/elniak/.claude/projects/-Users-elniak-Documents-Documents-Work-Project-Protocol-Testing-Security-PANTHER-master/memory/` to enumerate the actual rename surface across the user's memory directory (likely 8–15 files based on prior dependency grep + likely additional historical references).
    2. For each match, classify and act:
       - **Active feedback / handoff still relevant under new layout**: update skill-name references inline (e.g., `workflow-verify` → `verify`).
       - **Active work entry that this refactor supersedes**: move to `memory/historical/` with a date-stamped filename (e.g., `historical/2026-04-28-pre-orchestrator-refactor-active-work.md`); remove the pointer from `MEMORY.md` index.
    3. Add a new entry `memory/handoff-2026-04-28-orchestrator-refactor.md` summarising Phases A–F outcomes, current architecture (orchestrator + 8 agents + 11 skills + 2 commands + 1 style + 13 rules), the 21-script kept hook footprint, and any open follow-up (notably the stale `panther-ivy-plugin 2/` tree per Q6 leave-alone).
    4. Update `MEMORY.md` index: add the new handoff pointer, remove pointers at moved/historical entries.
  - **Commit**: `chore(plugin): backup-and-remove deprecated skills + agents + parent-repo fix + memory graduation (Phase F.1)`.

  **Phase F.2 — Smoke test verification.** No new file edits unless smoke test surfaces issues; verifies the refactor works end-to-end on real workspaces.
  - Run the end-to-end smoke test on **at least 2 workspaces** (F-I1 fix). Recommended pair: BGP (largest test surface, ICSE 2027 telemetry priority) + QUIC (oldest workspace, most complex `.panther-ivy/` state).
  - For each workspace: orchestrator activates on a verify request → dispatches `ivy-verifier-agent` → agent runs verify-compile-IUT cycle → G4 critic fires → orchestrator returns verdict → Stop hook fires → `record-session-end` writes `session_end{clean: True}` → `render-summary` produces recap → confirm `systemMessage` keys are populated on hooks per the Phase D table.
  - **Verify** (zero-match grep): `git grep -lE 'workflow-(navigate|build|verify|review|triage)|cross-cutting-|meta-using-panther|knowledge-(ivy|methodology|specification|propagation|apt|verification)|spec-analyst|model-reviewer|traceability-agent|plugin-conventions-reviewer' panther-ivy-plugin/plugins/panther-ivy-plugin/` returns zero matches across canonical paths (skills/, agents/, hooks/, .claude/rules/, commands/, output-styles/, README.md, CHANGELOG.md). The `.backup/` tree is excluded.
  - If smoke test passes on both workspaces and grep is zero: **no commit** (F.1's commit is the cleanup; F.2 is the verification gate, not a new file change). Phase F is complete.
  - If smoke test fails: `git revert` Phase F.1 to restore the deprecated tree, diagnose, fix forward, retry. (Optional: tag the failing state before revert for forensic analysis.)

  Phase F is then complete; deprecated artefacts live in `.backup/2026-04-28/` per the standing memory rule on backup retention.

  **Phase G — Stale `panther-ivy-plugin 2/` tree disposition.** Per Q6 outcome (still open).

  **Rationale for phased**: continues the Phase-1–5 / T1+T2+T4 cadence the project already runs; bounded reviewer load per PR; per-phase verification gates surface regressions early; bisection on regression is easy; natural backup-before-delete adherence (Phase F deletes deprecated skills only after Phases A–E succeed); each phase commits a complete working state of the plugin.
- **Q6 — Stale duplicate `panther-ivy-plugin 2/` tree.** ✓ Decided (2026-04-28): **Leave alone**. Preserves the standing memory rule (`feedback_no_relocate_backup_files`). The duplicate tree stays on disk under `submodules/panther-ivy-plugin 2/` but is not used at runtime (only the canonical `submodules/panther-ivy-plugin/` is registered as the active submodule). No risk of accidental data loss; the cost is roughly 50 MB of disk and occasional grep confusion when both trees report skill references. Phase G of Q5 phasing is therefore a **no-op** — the tree stays exactly as it is.
- **Q8 — Output-styles slim depth.** ✓ Decided (2026-04-28): **Keep `ivy-guided.md` only**. Drop `ivy-default.md`, `ivy-audit.md`, and `output-styles/README.md`.

  Single style. Matches the active selection in `.claude/settings.local.json` (`"outputStyle": "panther-ivy-plugin:Ivy Guided"`). Bio-research and most knowledge-work plugins ship 0 output styles; one is the bare minimum to set the verbose-mentor posture. Citation / severity / Considerations conventions live in auto-loaded `ivy-formatting.md` rule (kept Q9), independent of the style.

  Audit-style output (numbered findings, RFC traceability tables, structured compliance artifacts) can be requested ad-hoc verbally when needed. Compliance sessions are rare enough not to warrant a one-flag posture switch.

  Per Anthropic docs: output styles affect the main agent loop only, NOT subagents. Under approach E with 8 agents handling heavy work, main-thread output is mostly orchestrator routing + Q&A + render-summary recaps. The verbose-mentor / trade-off-discussion / confirmation-prompt posture of `ivy-guided` fits this main-thread surface well.
- **Q9 — `.claude/rules/` slim depth.** ✓ Decided (2026-04-28): **Keep all 13 rules (5 as-is + 8 rewrites)**.

  **Keep as-is (5 rules):** `agent-dispatch.md` (8-agent dispatch contract), `ivy-formatting.md` (citation + severity + Considerations), `mcp-tool-reliability.md` (MCP retry pattern), `propagation-authority.md` (ivy_propagation impact authority), `insights.md` (per memory rule placeholder).

  **Keep + rewrite (8 rules):**
  - `iron-laws.md` — keep auto-load with full 216-line detail; orchestrator SKILL.md body inlines a SHORT primer per Q3, the rule auto-loads on `.ivy`/`.spec` edits with full `<iron-law>` blocks.
  - `gap-markers.md` — rename `ivy-error-patterns` ref → `verification-failures`; remove `claim-discussion` ref.
  - `ivy-patterns.md` — rename `Skill(panther-ivy-plugin:knowledge-ivy-writing-guide)` → `Skill(panther-ivy-plugin:ivy-syntax)`.
  - `nct-methodology.md` — rename `Skill(panther-ivy-plugin:knowledge-methodology-reference)` → `Skill(panther-ivy-plugin:methodology)`.
  - `output-style.md` — drop entries for dropped hooks (`[ROUTING]`, `[ROUTING:AVAILABLE]`, `[ROUTING:CONTINUE]`, `(style overlay)`, `[INTERACTION CHECKPOINT]`); add `[G4 verification gate]` marker (from rewritten `record-workflow-error.py`).
  - `plan-mode.md` — rename `skills/workflow-navigate/references/plan-mode-lifecycle.md` → `skills/ivy/references/plan-mode-lifecycle.md`.
  - `postuse-hook-ordering.md` — drop `interaction-checkpoint.py` row; add `record-workflow-error.py` row (G4 trigger); reflect Agent-matcher extension on `post-write-workflow-aware.py` per decision #5.
  - `skill-conventions.md` — major §2 roster rewrite: rigid skills (5 ops-skills + orchestrator = 6: `triage-ops`, `build-ops`, `verify-ops`, `review-ops`, `meta-self-mod-ops`, `ivy`); flexible skills (6 cross-cutting: `verification-failures`, `specification-patterns`, `propagation-patterns`, `apt-attack-patterns`, `ivy-toolkit`, `ivy-syntax`). Add gate-critic agent conventions for `g-plan-critic`, `g-fidelity-critic`, `g-knowledge-critic`.

  **Rationale for keeping all 13**: each rule has a concrete role under approach E. The 5 description-loaded rules (3 named above plus `agent-dispatch` and `ivy-formatting`) are dispatch contracts and formatting canon. The 8 path-glob auto-loaded rules cover the file-edit auto-injection layer that surfaces conventions at the right moment without depending on Claude's memory. The slim is in rewrites, not drops.

### Sketch — orchestrator-centric layout

```
panther-ivy-plugin/
├── .claude-plugin/plugin.json
├── .mcp.json                       # ivy-tools + serena (kept)
├── README.md                       # ~5 KB, points at the orchestrator skill
├── CONNECTORS.md                   # optional Ivy-stage placeholders (~ivy-build, ~ivy-verify)
├── skills/
│   ├── ivy/                        # ⭐ ORCHESTRATOR (replaces workflow-navigate + meta-using-panther-ivy-plugin)
│   │   ├── SKILL.md                # Entry router; lists workflows, owns iron-law preamble
│   │   └── references/
│   │       ├── 01-iron-laws.md            # NO_FIX_WITHOUT_VERIFY, etc.
│   │       ├── 02-methodology.md          # NCT / NACT / NSCT selection
│   │       ├── 03-toolkit.md              # ivy-tools catalog + parameter matrix
│   │       ├── 04-ivy-syntax.md           # Ivy 1.7 patterns
│   │       ├── 05-completion-gate.md      # 5-step IDENTIFY→RUN→READ→VERIFY→THEN-claim
│   │       ├── 06-parallel-dispatch.md    # Single-message multi-Agent composition
│   │       └── 07-knowledge-capture.md    # Session-end learnings persistence
│   ├── triage/      SKILL.md + references/   # MCP/LSP/Serena health
│   ├── build/       SKILL.md + references/   # Spec authoring + scaffolding
│   ├── verify/      SKILL.md + references/   # Verify-compile-IUT cycle
│   ├── review/      SKILL.md + references/   # Coverage + traceability + quality
│   └── meta-self-mod/  SKILL.md              # Plugin-source-edit guard (only fires on plugin paths)
├── agents/                         # Efficiency agents — long-context-isolated work
│   ├── model-reviewer.md           # Adversarial spec review (reads many .ivy)
│   ├── spec-analyst.md             # Counterexample interpretation
│   ├── traceability-agent.md       # RFC ↔ assertion mapping
│   └── plugin-conventions-reviewer.md  # Self-mod review loop
├── hooks/                          # Slimmed (currently ~30 → target ~10)
├── commands/                       # Slimmed (currently 7 → target 2: /nct-health, /nct-iut-test)
├── output-styles/                  # Slimmed (currently 4 → target 1: ivy-guided)
├── .claude/rules/                  # Slimmed (currently 13 → target 0–3 auto-load-only rules)
├── routing-rules.json              # Routes ALL keywords to the orchestrator; orchestrator sub-routes internally
├── settings.json                   # env-var passthrough (kept)
└── scripts/                        # start-ivy-server.sh, start-serena.sh, statusline (kept)
```

The shape mirrors bio-research's hub-and-spokes (one entry skill + numbered references) but keeps each workflow as a separate skill because each is multi-phase with its own gates — too large to inline as a `references/01-….md` block. Iron laws live in the orchestrator's preamble (auto-injected on session start) and as a numbered reference; agents handle long-context work for context isolation, matching the user's "efficiency agents to manage long-context workflows" framing.

### Open dimensions to grill

A. Workflow disposition — sub-skills (callable `Skill()`), orchestrator references (read inline), or hybrid?
B. Knowledge disposition — orchestrator references (consolidate 7 knowledge skills into 7 references) or stay as separate skills?
C. Iron-laws disposition — orchestrator preamble + numbered reference, `.claude/rules/iron-laws.md` auto-load, or both?
D. Hook scope — slim to ~10 critical hooks, keep all ~30, or drop entirely (orchestrator handles state)?
E. Command scope — keep `/nct-health` + `/nct-iut-test` only, keep all 7, or drop?
F. routing-rules.json — keep with all keywords routing to orchestrator, drop in favour of conversational orchestrator dispatch, or hybrid?
G. Migration approach — phased (continue Phase-1–5 arc), big-bang refactor branch, or prototype-first?
H. Cleanup of stale `panther-ivy-plugin 2/` duplicate tree — leave alone (per memory rule), per-file approval to delete, or move to `refactor-archive/` branch?


---

## Final consolidated plan

All 9 grilled dimensions are decided. The detailed deliberation lives above in this file; this section is the executable summary the implementer reads.

### Architecture summary (approach E, agent-first)

- **Orchestrator skill** at `skills/ivy/SKILL.md` (~250 LOC) replaces `workflow-navigate` and `meta-using-panther-ivy-plugin`. Body inlines iron-law primer + methodology routing (Q3). References folder holds only `completion-gate.md` and `parallel-dispatch.md` (Q3 on-demand at claim time / multi-critic dispatch).
- **8 agents** (Q1): 5 workflow specialists (`ivy-triage-agent`, `ivy-builder-agent`, `ivy-verifier-agent`, `ivy-reviewer-agent`, `ivy-meta-agent`) + 3 gate critics (`g-plan-critic`, `g-fidelity-critic`, `g-knowledge-critic`). Each workflow agent preloads its operating procedure via `skills:[...]` frontmatter.
- **11 skills** (Q2 B+ on-demand structure): 5 ops-skills (`triage-ops`, `build-ops`, `verify-ops`, `review-ops`, `meta-self-mod-ops`) + 6 cross-cutting catalogs (`verification-failures`, `specification-patterns`, `propagation-patterns`, `apt-attack-patterns`, `ivy-toolkit`, `ivy-syntax`). Each cross-cutting skill is a thin SKILL.md index (~50–80 LOC) plus on-demand `references/*.md` (catalog content). One canonical home per knowledge domain.
- **Hooks**: ~21 scripts kept (down from ~30). 6 dropped, 1 folded, 1 extended, 4 directive rewrites, 1 deny-message rewrite, 2 kept as-is. Q4 hybrid disposition: SessionStart/lifecycle hooks kept; UserPromptSubmit routing chain dropped.
- **Commands**: 2 kept (`/nct-health`, `/nct-iut-test`). 5 dropped. Workspace control via `ivy_workspace` MCP tool, not slash commands.
- **Output styles**: 1 kept (`ivy-guided`). 3 dropped.
- **Rules**: 13 kept (5 as-is, 8 rewrites). The path-glob auto-load layer survives because it earns its keep at file-edit time.

### Critical paths the refactor touches

Plugin canonical tree at `panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin/`:

**New files (Phase A–C):**
- `skills/ivy/SKILL.md` (orchestrator)
- `skills/ivy/references/{completion-gate,parallel-dispatch}.md`
- `agents/{ivy-triage,ivy-builder,ivy-verifier,ivy-reviewer,ivy-meta}-agent.md` (rewriting / renaming the existing 4 specialist agents and adding `ivy-meta-agent.md`)
- `agents/{g-plan-critic,g-fidelity-critic,g-knowledge-critic}.md`
- `skills/{triage-ops,build-ops,verify-ops,review-ops,meta-self-mod-ops}/SKILL.md` plus per-skill `references/`

**Renames + restructures (Phase B):**
- `skills/knowledge-ivy-toolkit/` → `skills/ivy-toolkit/` (thin SKILL.md index + references)
- `skills/knowledge-ivy-writing-guide/` → `skills/ivy-syntax/`
- `skills/knowledge-methodology-reference/` → `skills/methodology/`
- `skills/knowledge-verification-failures/` → `skills/verification-failures/`
- `skills/knowledge-specification-patterns/` → `skills/specification-patterns/`
- `skills/knowledge-propagation-patterns/` → `skills/propagation-patterns/`
- `skills/knowledge-apt-attack-patterns/` → `skills/apt-attack-patterns/`

**Hook scripts (Phase D)** under `hooks/scripts/`:
- DELETE: `compose-style.py`, `route-user-prompt.py`, `track-workflow-skill.py`, `auto-load-skill-references.py`, `interaction-checkpoint.py`, `tip-shown.py`, `observability/check_lsp_log.py`
- DELETE: `routing-rules.json` at plugin root
- FOLD: `observability/check_lsp_log.py` content into `check-mcp-health.py`
- EXTEND: `post-write-workflow-aware.py` matcher to `Write|Edit|Agent`
- REWRITE: `assess-modeling.py`, `assess-testspec.py`, `assess-trace.py`, `record-workflow-error.py` (drop `reflection-patterns` ref, rename `ivy-error-patterns` → `verification-failures`, update workflow filter post-prefix-drop)
- REWRITE: `check-workspace-scope.py` deny message (use `ivy_workspace` MCP tool, not `/set-workspace` slash command)
- KEEP AS-IS: `check-indexing-ready.sh`, `record-session-end.py`, plus all SessionStart hooks (`cleanup-stale-pids.sh`, `cleanup-stale-workflow.py`, `detect-ivy-workspace.sh`, `inject-using-plugin.sh` (Phase E primer rewrite), `wait-for-indexing.sh`), `cleanup-ivy-lsp.sh`, `block-direct-ivy.sh`, `post-write-ivy-lint.sh`, `render-tool-result.py`, `retry-ivy-mcp.py`, `render-summary.py`, `notify-mcp-disconnect.py`, `observability/observe.py`
- UPDATE: `hooks/hooks.json` (drop 6 entries, fold 1, extend 1 matcher)

**Commands (Phase E)** under `commands/`:
- DELETE: `nct-check.md`, `nct-compile.md`, `nct-learn.md`, `nct-model-info.md`, `nct-observability.md`
- KEEP: `nct-health.md`, `nct-iut-test.md`

**Output styles (Phase E)** under `output-styles/`:
- DELETE: `ivy-default.md`, `ivy-audit.md`, `README.md`
- KEEP: `ivy-guided.md`

**Rules (Phase E)** under `.claude/rules/`:
- KEEP AS-IS: `agent-dispatch.md`, `ivy-formatting.md`, `mcp-tool-reliability.md`, `propagation-authority.md`, `insights.md`
- REWRITE: `iron-laws.md` (interact with orchestrator primer in `skills/ivy/SKILL.md`); `gap-markers.md` (rename refs); `ivy-patterns.md` (rename to `ivy-syntax`); `nct-methodology.md` (rename to `methodology`); `output-style.md` (drop dropped-hook markers, add G4 marker); `plan-mode.md` (rename `workflow-navigate` references to `ivy`); `postuse-hook-ordering.md` (drop `interaction-checkpoint`, add `record-workflow-error` row, reflect Agent-matcher extension); `skill-conventions.md` (major §2 roster rewrite)

**Plugin metadata (Phase E–F):**
- UPDATE: `README.md`, `CHANGELOG.md`, `.claude-plugin/plugin.json`
- UPDATE: `inject-using-plugin.sh` primer text (workspace control via `ivy_workspace` MCP, not `/set-workspace`)

**Cleanup (Phase F):**
- DELETE (after backup): `skills/workflow-navigate/`, `skills/workflow-build/`, `skills/workflow-verify/`, `skills/workflow-review/`, `skills/workflow-triage/`
- DELETE (after backup): `skills/cross-cutting-completion-gate/`, `skills/cross-cutting-knowledge-capture/`, `skills/cross-cutting-parallel-dispatch/`, `skills/cross-cutting-reflection-patterns/`
- DELETE (after backup): `skills/meta-using-panther-ivy-plugin/`
- DELETE: agents that get renamed: `agents/spec-analyst.md`, `agents/model-reviewer.md`, `agents/traceability-agent.md`, `agents/plugin-conventions-reviewer.md` (renamed to `ivy-*-agent.md` files in Phase C)
- BACKUP DESTINATION: `.backup/2026-04-28/<original-name>/` per memory rule

**Parent-repo fixes (Phase F)** at `/Users/elniak/Documents/Documents/Work/Project/Protocol-Testing-Security/PANTHER/master/.claude/worktrees/lsp-to-claude/`:
- UPDATE: `ONBOARDING.md` line 18 (`/panther-ivy-plugin:navigate` → `/panther-ivy-plugin:ivy` or remove)
- VERIFY: `.claude/settings.local.json` env vars `IVY_LSP_DEV_ROOT` and `PANTHER_IVY_PLUGIN_DEV_ROOT` (no path changes; both still resolve)
- VERIFY: `.claude/settings.local.json` `outputStyle` (`"panther-ivy-plugin:Ivy Guided"` still resolves)

**Memory file updates (Phase F)** at `/Users/elniak/.claude/projects/-Users-elniak-Documents-Documents-Work-Project-Protocol-Testing-Security-PANTHER-master/memory/`:
- UPDATE: `feedback_reuse_existing_xml_tags.md`, `feedback_agent_orchestrator_three_layer_split.md`, `handoff-2026-04-27.md`, `handoff-2026-04-27-simplification.md` — replace skill-name references (`workflow-verify` → `verify` etc.) with the post-E names; add a graduation entry pointing at this plan file as the next-phase handoff.
- ADD: a new `handoff-2026-04-28-orchestrator-refactor.md` summarising the refactor's status when sessions hand off mid-execution.

### Existing functions / utilities to reuse

The refactor avoids inventing new infrastructure where existing pieces work. Specifically:

- `hooks/scripts/hook_utils.py` (kept) — provides `read_stdin`, `emit_hook_output`, `resolve_session_id`, `get_workspace_root`. Reused by every kept hook and by the rewritten gate-firing scripts.
- `hooks/scripts/workflow_state.py` (kept) — provides `WorkflowContext.current()`, `find_protocol_dir`, `append_journal_event`, `get_active_workflow`, `rotate_journal`, `get_build_state_safe`. Reused by `assess-*.py`, `record-workflow-error.py`, `record-session-end.py`. The orchestrator writes through the `ivy_workspace` MCP tool.
- `hooks/scripts/statusline_cache.py` (kept) — provides `update_from_hook`, `update_sections_from_hook`. Reused by extended `post-write-workflow-aware.py` and merged `check-mcp-health.py`.
- `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_workspace` MCP tool — replaces the dropped `/set-workspace` slash command. Reused in the rewritten `check-workspace-scope.py` deny message.
- `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_workflow_state` MCP tool — used by orchestrator for active-workflow YAML writes (replacing dropped `track-workflow-skill.py`).
- `superpowers:writing-plans` skill — invoked from `plan-mode.md` for non-trivial implementation plans (already wired).

### Verification — end-to-end test plan

After each phase commits, run the matching verification gate before proceeding to the next phase. After Phase F completes, run the full end-to-end smoke test on a real workspace.

**Per-phase verification gates:**

| Phase | Verification |
|---|---|
| A | New orchestrator skill loads (`Skill(skill="panther-ivy-plugin:ivy")`); orchestrator dispatches `g-plan-critic` 3× in parallel and aggregates SOUND/UNSOUND/ABSTAIN verdict; existing `workflow-navigate` still loads. |
| B | Each renamed cross-cutting skill loads independently. Orchestrator invokes `Skill(skill="panther-ivy-plugin:methodology")` and reads a reference on-demand. Agent preload via `skills:[methodology]` injects SKILL.md body at spawn (test on a stub agent). |
| C | Orchestrator dispatches each of the 5 workflow agents on a stub task. Each agent preloads its skill chain (verify with `Read /tmp/agent-context-dump.txt` after spawn — agent should have ops-skill SKILL.md plus cross-cutting skills' SKILL.md bodies in its system prompt). Agent runs Phase 1 of its workflow successfully on a known-clean fixture. |
| D | SessionStart hook chain runs cleanly (env vars exported, MCP/LSP up, indexing ready). UserPromptSubmit chain emits only telemetry (no `[ROUTING]` / `[ROUTING:AVAILABLE]` / `[ROUTING:CONTINUE]` lines). G2/G3 fire on `.ivy` Write|Edit; G4 fires on `ivy_verify` return; G5 fires on `ivy_iut_test` return. PreToolUse `check-mcp-health` (now folded with `check_lsp_log`) reports both liveness and recent-error categorisation. |
| E | `/nct-health` and `/nct-iut-test` resolve; the 5 dropped commands return "command not found" cleanly. `outputStyle = "panther-ivy-plugin:Ivy Guided"` still resolves; the 3 dropped styles return "not found" if selected. Path-glob auto-load fires for kept rules on matching file edits (test by editing a `.ivy` file and confirming `iron-laws.md` + `gap-markers.md` + `ivy-patterns.md` + `nct-methodology.md` + `propagation-authority.md` + `plan-mode.md` content appears in the next system-reminder). |
| F | Full session start-to-end on a BGP workspace: `/nct-health` passes; orchestrator dispatched on a verify request via `ivy_verify`; verifier-agent runs verify-compile-IUT cycle; G4 critic fires; orchestrator returns verdict; `render-summary` produces session recap on Stop. No references to deprecated skill names in any orchestrator / agent / hook output. Memory files reflect the new layout; parent-repo `ONBOARDING.md` no longer references `/panther-ivy-plugin:navigate`. |

**End-to-end smoke test (post-Phase F):**

```bash
# 1. Restart Claude Code session in this worktree
# 2. Confirm SessionStart chain produces no [ROUTING] / [ROUTING:AVAILABLE] / [ROUTING:CONTINUE] lines
# 3. Set workspace via the MCP tool, not slash command:
#    Use ivy_workspace(action="set", target="bgp")
# 4. Ask the orchestrator: "verify protocol-testing/bgp/bgp_stack/bgp_connection.ivy"
# 5. Expect: orchestrator activates, dispatches ivy-verifier-agent
# 6. Agent runs ivy_verify -> ivy_compile -> ivy_iut_test in sequence
# 7. assess-trace.py fires on ivy_iut_test return; verifier-agent dispatches G5 critics
# 8. record-workflow-error.py fires on ivy_verify return; verifier-agent dispatches G4 critics
# 9. Orchestrator aggregates verdicts, returns to user
# 10. Stop hook fires; record-session-end writes session_end{clean: True}; render-summary produces recap
# 11. Confirm no references to "workflow-verify", "knowledge-*", "cross-cutting-*", "meta-using-panther-ivy-plugin" in any output
# 12. Confirm /panther-ivy-plugin:ivy resolves; /panther-ivy-plugin:navigate does NOT (returns "not found")
```

If any verification gate fails, halt the phase, diagnose, and either revert or fix forward before proceeding. The plan is bisectable per-phase: a regression after Phase D points squarely at the hook slim, etc.

### Out of scope for this refactor

- The stale `panther-ivy-plugin 2/` duplicate tree stays untouched (Q6 decision).
- The `submodules/ivy-lsp` LSP-backed MCP server's internal implementation is not refactored — only the plugin's interface to it (workspace control via `ivy_workspace`).
- The 14-layer protocol-modeling template content (specifications themselves under `protocol-testing/`) is not modified — only the plugin's reference to it via `specification-patterns/references/`.
- Telemetry schema in `.panther-ivy/session-logs/*.jsonl` is not changed; the ICSE 2027 research stream remains compatible.
