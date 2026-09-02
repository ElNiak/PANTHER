# `ai_rfc` Code Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement
> this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Do **not** use
> subagent-driven-development here — Task 3 already dispatches five subagents of its own,
> and nesting a per-task subagent around it would spawn readers that spawn readers.

**Goal:** Produce one committed, evidence-bound review of all 18,443 lines of `ai_rfc`
across both repositories, answering whether the code is sound, whether debt is hiding in
it, and whether every command and feature is finished.

**Architecture:** Six sequential tasks. The controller establishes a measured baseline and
re-derives every unverified claim *before* any reader runs, because handing subagents
unverified "facts" is the defect that revision 1 of this plan carried. Five read-only
readers then cover disjoint slices in parallel, returning findings whose severity is bound
to a settling check rather than to a confidence score. The controller settles those checks,
audits the debt register, and writes one report.

**Tech Stack:** Python 3.10+, pytest 8 with `pytest-xdist`, mypy, black, flake8, git,
and the `Agent` tool (`general-purpose`, model `inherit`) for the five readers.

**Spec:** This document. There is no separate design doc — the deliverable is a report,
not a system, so the *Context*, *Scope* and *Seed findings* sections below are the spec
and travel with the plan.

## Global Constraints

- **No source file is edited by this plan.** The deliverable is a report. A fix phase, if
  wanted, is a separate plan built from it.
- **Nothing under `harness/` is modified.** It is a git submodule pinned at `0b62bf3`, and
  its strings are the completed pilot's instrument.
- **Never run `panther docs build` or `panther_builder.py clean|package-dev`.**
  `panther/cli/commands/docs.py:84` is an unconditional `shutil.rmtree(docs_dir)`, and
  `docs/` holds 12 tracked files including all nine plan documents and this one.
- **`ruff` is not installed in `.venv`.** It exists only as a `.pre-commit-config.yaml:32-35`
  hook that fetches its own environment. Any `.venv/bin/ruff` invocation fails.
- **`flake8` must be given `--max-line-length=88`.** It defaults to 79 and is
  `stages: [manual]`, so it never fires at commit time and its bare output is false E501s.
- **`mypy` must be given `--follow-imports=silent`.** Without it: ~1,100 pre-existing
  errors across 108 files, burying everything.
- **Disable the sandbox for `pytest` runs.** The sandbox blocks an SSL-keylog write during
  collection.
- **Readers never spawn subagents, and never mutate the working tree, index, HEAD or
  branch state.** Five run concurrently in one worktree.
- **Severity follows the one-line contract** in Task 3, never a separate `confidence:` field.
- Commit format: `type(scope): lowercase summary`, no trailing period. Line length 88.

---

## Context

The `ai_rfc` substrate reconstructs an RFC-style specification from a project's own commit
history. This branch sits **162 commits** ahead of `production` with no PR. Before the
pending main experiment run spends real money against it, three questions need answering:
is the code any good, is there technical debt hiding in it, and are the commands and
features actually finished.

A review ran on 2026-08-31 and found 22 tiered defects. **Its durable artifact no longer
exists** — it lived in `~/.claude/plans/what-is-next-on-crystalline-sun.md`, which a later
session overwrote. Only a summary survived, in the memory note
`handoff-2026-08-31-arfc-review-backlog.md`. That loss is why this report is committed to
the repository.

Three decisions taken by the user: review both repositories but land fixes only on the
PANTHER side; stop at a written report and decide about fixes afterwards; and **count
registered gaps as debt**, not as accepted design.

The tree is free — no campaign has touched `~/arfc-experiments/campaigns/` today, the
harness submodule is clean at its pinned pointer, and the working tree has no uncommitted
changes.

## Scope

| In | Out |
|---|---|
| `panther/plugins/services/testers/ai_rfc/` (55 files, 6,933 LOC) | Any source edit — report only |
| `panther/cli/commands/ai_rfc.py` (the click front door) | Fixes inside `harness/` |
| `harness/` submodule (59 files, 11,510 LOC) — **read-only** | The BGP, Veil and Ivy tracks |
| Both test trees (52 files / 5,881 LOC, plus 4,506 LOC under `harness/`) | `.mypy_cache`, `__pycache__`, egg-info |

## Seed findings — verified by hand in this session

| # | Location | What is wrong |
|---|---|---|
| S-1 | `harness/…/core/queries.py:22,33,58` | `_ROW_CAP = 200` with `fetchmany`; docstring says "truncated without notice". MARK's `commits` table holds 969 rows. |
| S-2 | `harness/…/core/questions.py:157` | `ctx.workspace / "interviews" / transcript` unsanitized; `../` escapes the workspace and becomes a recorded evidence locator. |
| S-3 | `forge/fetch.py:97` | `urlopen(request)` has no timeout. |
| S-4 | `forge/fetch.py:112` | 403 and 429 raise one `ForgeThrottled`; a caller cannot tell transient from permanent by type. |
| S-5 | `draft/gate.py:274-283` | The "no normative change" gate compares cited claim **id sets**, never content. |
| S-6 | `views/emit.py:5` vs `:301,367-375` | Docstring claims "byte-for-byte"; `_patches_drifted` compares only `patches`. |
| S-7 | `harness/experiment/runner.py:34,238` | Tamper check digests `guard.json`, never the `guard.py` it points at. |

Also verified: seven unregistered `# noqa` suppressions (`experiment/guard.py:15,59`,
`experiment/workspace.py:126`, `server/tests/conftest.py:13`, `server/cli.py:303`,
`core/claims.py:41`, `core/questions.py:13`); the duplication register at
`README.md:475-482` has six rows while `TRACKED_HELPERS` (`test_cli_conventions.py:67`)
covers four; `README.md:490-492` names a seventh helper deliberately excluded; twelve
unchecked boxes in `harness/docs/experiment-protocol.md`; and `history/index.py:111-112`
documents that `open_index` does not close its connection.

**Refuted on inspection, recorded so no reader re-files it:** there is no contradiction
between `README.md:247-249` and `:320-326`. Both say the report pairs each claim's `stored`
status with the `supported` one its evidence earns. The phrase previously attributed to
line 247 does not appear in the file.

Closed since 2026-08-31, not to be re-reported: `views --only` reaches `verify_views`;
`TARGETS` gained `mark`; the console script is `ai_rfc` and `ai_rfc_server` imports;
strict findings exit 3; the rename is complete PANTHER-side; `pipeline/run.py`'s
`type: ignore` is retired.

## File Structure

| File | Responsibility |
|---|---|
| `docs/superpowers/plans/2026-09-02-ai-rfc-code-review.md` *(new)* | This plan, in the repo. |
| `docs/research/2026-09-02-ai-rfc-code-review.md` *(new)* | The report. Lives beside `docs/research/2026-08-25-progressive-rfc-related-work.md`, the repo's existing findings document — `plans/` and `specs/` stay semantically clean. |

The report is built section by section across Tasks 1–6, each committed. It is never
written in one pass at the end, so an interrupted run leaves a partial but honest
artifact rather than nothing.

---

## Task 0: Land the plan

**Files:**
- Create: `docs/superpowers/plans/2026-09-02-ai-rfc-code-review.md`

**Interfaces:**
- Consumes: nothing.
- Produces: the plan at its repo path, which every later task's commits reference.

- [ ] **Step 1: Copy this document into the repository**

Write the full contents of this plan to
`docs/superpowers/plans/2026-09-02-ai-rfc-code-review.md`, dropping only the two
plan-mode blockquotes at the top.

- [ ] **Step 2: Confirm it landed inside the tracked tree**

Run: `git status --short docs/superpowers/plans/`
Expected: exactly one `??` line for the new file. Any other path means it went to the
wrong place.

- [ ] **Step 3: Commit**

```bash
git add docs/superpowers/plans/2026-09-02-ai-rfc-code-review.md
git commit -m "docs(ai_rfc): plan the whole-codebase review"
```

---

## Task 1: Baseline, and the report skeleton

**Files:**
- Create: `docs/research/2026-09-02-ai-rfc-code-review.md`

**Interfaces:**
- Consumes: nothing.
- Produces: the report file with a `## Baseline` section holding three suite counts and
  the type/format/lint results. Task 6 reads these numbers for its Assessment.

A review that cannot say what "green" meant on the day it ran cannot tell a defect it
found from a defect it caused.

- [ ] **Step 1: Run the PANTHER-side suite**

Run, with the sandbox disabled:

```bash
.venv/bin/pytest tests/unit/plugins/services/testers/ai_rfc/ tests/unit/test_cli/test_ai_rfc_commands.py -n auto -q
```

Expected from memory: **587 passed**. Record the real number verbatim, pass *and* fail.
A different count is itself a finding and goes in the report — it is not to be
reconciled away.

- [ ] **Step 2: Run the two harness suites**

```bash
.venv/bin/pytest panther/plugins/services/testers/ai_rfc/harness/experiment/tests/ -q
.venv/bin/pytest panther/plugins/services/testers/ai_rfc/harness/plugins/ai-rfc/server/tests/ -q
```

Expected from memory: **263** and **38**. Both conftests derive their roots from
`Path(__file__)` (`experiment/tests/conftest.py:14,16`;
`server/tests/conftest.py:6,7`), so the worktree's depth does not affect them. If either
errors on collection with a path assertion, stop and report it — that is a finding about
the suites, not a step to work around.

- [ ] **Step 3: Run the type, format and lint checks**

```bash
.venv/bin/mypy --follow-imports=silent panther/plugins/services/testers/ai_rfc/
.venv/bin/black --check panther/plugins/services/testers/ai_rfc/
.venv/bin/flake8 --max-line-length=88 panther/plugins/services/testers/ai_rfc/
```

Do **not** substitute `.venv/bin/ruff` — it does not exist. Record each result.

- [ ] **Step 4: Write the skeleton with the baseline in it**

Create `docs/research/2026-09-02-ai-rfc-code-review.md` with a title, a one-paragraph
statement of what was reviewed and under which three decisions, and:

```markdown
## Baseline, 2026-09-02

| Check | Command | Result |
|---|---|---|
| PANTHER suite | `pytest tests/unit/…/ai_rfc/ tests/unit/test_cli/test_ai_rfc_commands.py -n auto` | <verbatim> |
| harness experiment suite | `pytest harness/experiment/tests/` | <verbatim> |
| harness server suite | `pytest harness/plugins/ai-rfc/server/tests/` | <verbatim> |
| mypy | `mypy --follow-imports=silent …/ai_rfc/` | <verbatim> |
| black | `black --check …/ai_rfc/` | <verbatim> |
| flake8 | `flake8 --max-line-length=88 …/ai_rfc/` | <verbatim> |

Scope: 18,443 LOC across two repositories; 55 files in the PANTHER package, 59 under the
`harness/` submodule at pinned pointer `0b62bf3`.
```

Replace every `<verbatim>` with the actual output. Leaving one is a plan failure.

- [ ] **Step 5: Commit**

```bash
git add docs/research/2026-09-02-ai-rfc-code-review.md
git commit -m "docs(ai_rfc): record the review baseline"
```

---

## Task 2: Re-derive what orientation did not verify

**Files:**
- Modify: `docs/research/2026-09-02-ai-rfc-code-review.md` (append `## Established facts`)

**Interfaces:**
- Consumes: the report file from Task 1.
- Produces: an `## Established facts` section. Task 3 pastes it into every reader prompt
  as *already known*; Task 5 uses the command inventory as the register's spine.

Exploration produced six claims that were never checked, from the same agent pair that
also produced one fabricated quotation and one wrong marker count. Checking them costs
minutes; shipping them to five readers as facts costs the report's credibility.

- [ ] **Step 1: Count the debt markers directly**

```bash
grep -rnE "TODO|FIXME|HACK|XXX|NotImplementedError|pytest\.mark\.(skip|xfail)|# ?type: ?ignore|# ?noqa" --include="*.py" panther/plugins/services/testers/ai_rfc/ tests/unit/plugins/services/testers/ai_rfc/
```

Expected: **7 hits, all `# noqa`, all under `harness/`**. Any `TODO`, `FIXME`, `HACK`,
`XXX`, `NotImplementedError`, skip, xfail or `type: ignore` is a new finding.

- [ ] **Step 2: Inventory every command and its test**

For each of the eight entries in
`panther/plugins/services/testers/ai_rfc/entrypoints.py:71-131`, open its `cli.py` and
list every verb. Then do the same for `harness/experiment/cli.py` and for
`harness/…/ai_rfc_server/cli.py`, and list every tool in `ai_rfc_server/tools.py`'s
`ALL_TOOLS`. For each verb and tool, find its test:

```bash
grep -rn "<verb-or-tool-name>" tests/unit/plugins/services/testers/ai_rfc/ panther/plugins/services/testers/ai_rfc/harness/experiment/tests/ panther/plugins/services/testers/ai_rfc/harness/plugins/ai-rfc/server/tests/
```

Record `verb → test file:line`, or `NO TEST`. The claims to confirm or refute: 13 PANTHER
verbs all tested; 8 of 16 MCP tools untested at the tool boundary; `cluster-get`,
`question-draft`, `question-export`, `answer-record` untested at either layer; and
`preflight`, `render`, `workspace reseal` never reached through `cli.main`.

- [ ] **Step 3: Check for flags defined but never read**

For each `cli.py` in the package, list every `add_argument` destination and grep the
module for its use:

```bash
grep -n "add_argument" panther/plugins/services/testers/ai_rfc/*/cli.py panther/plugins/services/testers/ai_rfc/cli.py
```

Then confirm each corresponding `args.<name>` is consumed. `views --only` was silently
ignored under `--verify` once already, so this is a repeat defect class, not a
hypothetical.

- [ ] **Step 4: Append the section**

Append to the report:

```markdown
## Established facts

Every row here was verified by running the command shown, not inherited from exploration.

| Claim | Command | Verdict |
|---|---|---|
| … | … | confirmed / refuted / corrected to … |
```

Include the marker count, the full verb-and-tool table with test status, and the
flag-consumption result. Mark any refuted claim **refuted**, with what is true instead.

- [ ] **Step 5: Commit**

```bash
git add docs/research/2026-09-02-ai-rfc-code-review.md
git commit -m "docs(ai_rfc): verify the command inventory before dispatching readers"
```

---

## Task 3: Five parallel readers

**Files:**
- Modify: `docs/research/2026-09-02-ai-rfc-code-review.md` (append `## Raw findings`)

**Interfaces:**
- Consumes: `## Established facts` from Task 2; the seed findings from this document.
- Produces: `## Raw findings` — every finding from all five readers, unfiltered, each
  with an id `<slice>-NN` and a severity line. Task 4 settles them.

- [ ] **Step 1: Dispatch all five readers in one message**

Five `Agent` calls in a single response so they run concurrently.
`subagent_type: "general-purpose"`, `model: "inherit"`. Per-slice substitutions:

| `{SLICE}` | `{PATHS}` | LOC | `{SEEDS}` |
|---|---|---|---|
| `core` | package root `*.py`, `draft/`, `pipeline/`, and `panther/cli/commands/ai_rfc.py` | 3,444 | S-5 |
| `evidence` | `forge/` `history/` `timeline/` `views/` `coverage/` | 3,532 | S-3, S-4, S-6 |
| `runner` | `harness/experiment/`, excluding its `tests/` | 5,345 | S-7 |
| `server` | `harness/plugins/ai-rfc/server/src/` | 1,659 | S-1, S-2 |
| `tests` | `tests/unit/…/ai_rfc/`, `tests/unit/test_cli/test_ai_rfc_commands.py`, `harness/**/tests/` | 10,387 | none |

The prompt, verbatim, with the four braces substituted:

```
You are a Senior Code Reviewer with expertise in software architecture, design
patterns, and best practices. Review one slice of a Python codebase and report
what is wrong with it.

Repo root: /Users/elniak/Documents/Documents/Work/Project/Protocol-Testing-Security/PANTHER/master/.claude/worktrees/iut-ai-rfc

## Your slice — read only these, and all of these
{PATHS}
That is {LOC} lines. Files outside this list belong to another reviewer; do not
report on them.

## What this code is
`ai_rfc` reconstructs an RFC-style requirement specification from a project's own
commit history. Claims are mined from commits, bound to code by anchors, promoted
by evidence, and gated before they reach a draft. It is a research instrument: a
wrong number that looks right is worse than a crash.

## Read-Only Review
Your review is read-only on this checkout. Do not mutate the working tree, the
index, HEAD, or branch state in any way. Use `git show`, `git diff`, `git log` to
inspect history. Never check out a revision here.

## You Do Not Dispatch Subagents
Do all of this review yourself. Never spawn a subagent to review part of the
slice, and never spawn another reviewer for a second opinion. If the slice feels
too large for one pass, review it in passes yourself and say so.

## Already known — confirm or refute, do not re-file
{SEEDS}, quoted in full, plus the whole `## Established facts` section from
docs/research/2026-09-02-ai-rfc-code-review.md, plus: there is NO contradiction
between README.md:247-249 and :320-326 (an earlier reviewer fabricated one);
`views --only`, the `TARGETS` registry, the `ai_rfc` console script, exit-3 for
strict findings, the a_rfc→ai_rfc rename and `pipeline/run.py`'s type-ignore are
all already fixed.

## What to check
Plan alignment: does each module do what its own docstring and README say?
Code quality: separation of concerns, error handling, type safety, DRY without
premature abstraction, edge cases.
Architecture: sound decisions, security, clean integration with neighbours.
Testing: do the tests verify real behaviour, or do they assert what a fixture
just supplied?
Production readiness: backward compatibility, documentation that matches code.

## How to state severity — this is the part that matters
A finding's existence is a claim about code. Its severity is a claim about
consequence, and consequence usually depends on runtime state you did not
observe. You can establish "this loop has no bound" by reading; you cannot
establish "this hangs" that way.

So every finding ends with ONE severity line, in one of two forms:

  SEVERITY: <Critical|Important|Minor> if <condition>; <other level> otherwise
            — settled by <exact check>

  SEVERITY: <Critical|Important|Minor> — confirmed against <artifact>,
            which shows <value>

The condition travels INSIDE the severity line. Never emit a separate
"confidence:" field — certainty about the mechanism reads as certainty about the
impact, which is the failure this format exists to prevent.

Prefer settling to hedging: you have Bash. If the check is one command, run it
and report the confirmed form. If a check narrows without settling, name what it
could not reach inside the severity line rather than rounding up to confirmed.

## Output — at most 2000 tokens
### Strengths
Two to four specific things done well, with file:line. Be accurate, not kind.

### Findings
For each:
  id        {SLICE}-NN
  file:line
  category  correctness | security | resource | api-contract | test-gap |
            duplication | doc-drift | dead-code | naming
  claim     one sentence: what the code does
  SEVERITY: <the one line above>

Report everything you find, including Minor. The filter runs downstream of you.

### Assessment
One or two sentences: is this slice sound, and what is the single thing you would
fix first?

## Escalation
If a path in your slice does not exist, say so and continue. Do not guess at
replacements, and do not widen your slice to compensate.
```

- [ ] **Step 2: Check every returned finding carries a legal severity line**

A finding with a bare `severity:` and a separate `confidence:` violates the contract.
Send it back to its reader once via `SendMessage`, asking for the one-line form. Do not
repair it yourself — a severity the reader did not choose is not the reader's finding.

- [ ] **Step 3: Deduplicate and append**

Merge the five sets. Where two readers report the same code (`pipeline/run.py` dispatches
into CLIs the `evidence` reader owns), keep the one whose slice contains the defect and
note the other id beside it. Append as `## Raw findings`, grouped by reader, each with
its `Strengths` and `Assessment` preserved.

- [ ] **Step 4: Commit**

```bash
git add docs/research/2026-09-02-ai-rfc-code-review.md
git commit -m "docs(ai_rfc): collect findings from five slice reviews"
```

---

## Task 4: Settle every residual condition

**Files:**
- Modify: `docs/research/2026-09-02-ai-rfc-code-review.md` (append `## Confirmed defects`)

**Interfaces:**
- Consumes: `## Raw findings` from Task 3.
- Produces: `## Confirmed defects`, tiered Critical / Important / Minor, each with the
  evidence that fixed its level. Task 6 counts these for the Assessment.

Both headline findings of the 2026-08-31 review were reported as corrupting live pilot
data. Both were latent. The check that would have shown it was one command in each case.

- [ ] **Step 1: Run every `settled by` check that a reader left unresolved**

Work through `## Raw findings` in order. For each severity line still in the
`if <condition>` form, run the check it names. Most will be a `grep`, a file read, or a
single `pytest -k`.

- [ ] **Step 2: Record the outcome on the finding, not beside it**

Rewrite each severity line into the confirmed form with the artifact and the value that
settled it. Where a check narrowed without settling — it could not reach a remote host, a
runtime state, or a paid run's output — keep the residue in the line. Never promote an
unsettled condition to confirmed.

- [ ] **Step 3: Verify the seven seeds explicitly**

```bash
grep -nE "S-[1-7]" docs/research/2026-09-02-ai-rfc-code-review.md
```

Expected: all seven present. Each must be either confirmed still-open with its
`file:line`, or shown fixed with the evidence. A seed that no reader mentioned is not
thereby resolved — settle it yourself.

- [ ] **Step 4: Append the tiered section**

```markdown
## Confirmed defects

### Critical
### Important
### Minor
### Latent — real mechanism, severity did not survive its check
```

The fourth heading is not optional. A defect proved latent is worth writing down, and
recording it is what stops the next review re-raising it at full severity.

- [ ] **Step 5: Commit**

```bash
git add docs/research/2026-09-02-ai-rfc-code-review.md
git commit -m "docs(ai_rfc): settle each finding against its own evidence"
```

---

## Task 5: Audit the debt register

**Files:**
- Modify: `docs/research/2026-09-02-ai-rfc-code-review.md` (append `## Debt backlog`)

**Interfaces:**
- Consumes: the command inventory from Task 2.
- Produces: `## Debt backlog`, every registered gap ranked with a cost and a blocker.

The user's decision is that registered gaps count as debt. So the register is not a
defence; it is the backlog, and its own accuracy is under review.

- [ ] **Step 1: Collect every registered gap**

Read, and extract each stated gap, deferral, cap, truncation or accepted cost:

```bash
grep -rn "deferred\|not yet\|known gap\|hand-maintained\|accepted\|only covers\|left alone\|cannot" panther/plugins/services/testers/ai_rfc/README.md panther/plugins/services/testers/ai_rfc/*/README.md docs_src/reference/ai_rfc.md docs_src/reference/cli.md
```

Then the four named sections of the two most recent plan files —
`docs/superpowers/plans/2026-09-02-arfc-panther-subcommand.md` and
`2026-09-02-arfc-cli-legibility.md`: *Known and accepted*, *Known cosmetic gaps*,
*Corrections found during execution*, *Deferred, and why*.

- [ ] **Step 2: Check each against the code**

For each gap: is it still true, silently fixed, or silently worse? A register entry that
no longer matches the code is a defect in its own right — the failure mode recorded as
`feedback_two_readers_of_one_command_drift`. Two known cases to get right: the duplication
table's six rows against `TRACKED_HELPERS`' four, and the seventh helper at
`README.md:490-492` that is excluded *deliberately* and must not be counted as an omission.

- [ ] **Step 3: Add the unregistered debt**

The seven `# noqa` suppressions from Task 2 Step 1 appear in no register. Add them, with
the rule each suppresses and whether the stated reason still holds.

- [ ] **Step 4: Append the ranked backlog**

```markdown
## Debt backlog

| # | Item | Registered where | Still true? | Cost | Blocker | Recommendation |
|---|---|---|---|---|---|---|
```

Rank by cost-to-close against risk-of-leaving. The four structural deferrals — module root
as dispatcher, re-rendering the agent skills, extracting `ai_rfc` as its own project,
renaming `adjudicate` inside the harness — are ranked and costed like everything else,
with **"blocked on the main experiment run"** in the Blocker column. Blocked is not
dropped.

- [ ] **Step 5: Commit**

```bash
git add docs/research/2026-09-02-ai-rfc-code-review.md
git commit -m "docs(ai_rfc): rank the debt register as a backlog"
```

---

## Task 6: Strengths, assessment, and the honest limits

**Files:**
- Modify: `docs/research/2026-09-02-ai-rfc-code-review.md`

**Interfaces:**
- Consumes: every section from Tasks 1–5.
- Produces: the finished report.

- [ ] **Step 1: Write the Strengths section**

Merge the five readers' `Strengths`, deduplicated, with `file:line`. This section is not
decoration — the template's reasoning is that accurate praise is what makes the rest of
the feedback trustworthy, and this codebase has real strengths to name: zero debt markers
outside seven explained suppressions, a register that admits its own gaps in prose, and
tests that mirror the package structure.

- [ ] **Step 2: Write the Assessment**

Answer the user's three questions directly, in order, each in a short paragraph: is the
code good; is debt hiding in it; are the commands and features finished. Give counts from
Tasks 4 and 5. Do not hedge a confirmed result and do not upgrade a latent one.

- [ ] **Step 3: Write the Limits section**

State plainly what this review did not establish: that the `harness/` findings are
reported but unfixable this cycle by decision, so S-1, S-2 and S-7 — a path traversal, a
silent truncation and an ineffective tamper check — remain open; and any residual
condition Task 4 could not settle, listed individually.

- [ ] **Step 4: Check every severity line is legal**

```bash
grep -n "SEVERITY:" docs/research/2026-09-02-ai-rfc-code-review.md | grep -v "settled by\|confirmed against"
```

Expected: **no output**. Any line printed is a severity with neither a settling check nor
a confirming artifact, which the contract forbids.

- [ ] **Step 5: Check no placeholder survived**

```bash
grep -n "<verbatim>\|TBD\|TODO\|FIXME\|XXX" docs/research/2026-09-02-ai-rfc-code-review.md
```

Expected: no output, except where a literal `TODO` is being *quoted* as a finding about
the source. Any `<verbatim>` left from Task 1 is a plan failure.

- [ ] **Step 6: Commit**

```bash
git add docs/research/2026-09-02-ai-rfc-code-review.md
git commit -m "docs(ai_rfc): finish the whole-codebase review"
```

- [ ] **Step 7: Offer the report as an Artifact**

Ask whether to publish the same report as an Artifact for reading and sharing. Do not
publish without an answer.

---

## Final verification

```bash
git log --oneline -7
grep -c "SEVERITY:" docs/research/2026-09-02-ai-rfc-code-review.md
grep -nE "S-[1-7]" docs/research/2026-09-02-ai-rfc-code-review.md | wc -l
git status --short
```

Seven commits, one per task. Every `SEVERITY:` line carries a settling check or a
confirming artifact. All seven seeds accounted for. A clean tree: this plan edits no
source file, so anything else modified is a mistake to investigate before finishing.

## Self-review of this plan

**Spec coverage.** The three asks map to tasks: *is the code good* → Tasks 3 and 4; *is
there hidden debt* → Tasks 2 and 5; *are commands and features finished* → Task 2's
inventory, carried into Task 5's backlog. The user's three decisions map to constraints:
review-both-fix-PANTHER-only → Global Constraints and Task 6 Step 3; report-then-decide →
"No source file is edited"; registered-gaps-are-debt → Task 5 entire.

**Placeholders.** One deliberate template remains — `<verbatim>` in Task 1 Step 4 — and
Task 6 Step 5 greps for it as a gate. The reader prompt's four braces are substituted from
the table directly above it.

**Type consistency.** The report path is
`docs/research/2026-09-02-ai-rfc-code-review.md` in every task; the plan path is under
`docs/superpowers/plans/` and differs only by directory, which is why the seed ids are
`S-n` and the finding ids are `<slice>-NN` — no collision. `## Established facts`,
`## Raw findings`, `## Confirmed defects` and `## Debt backlog` are each produced once and
consumed by name.

**Known weakness, stated rather than hidden.** Task 3's readers are the same class of
agent that has already produced one fabricated quotation and one wrong marker count on
this codebase. Task 4 exists because of that, and the report separates what was confirmed
against an artifact from what was only read. This does not eliminate the risk; it bounds it.

## Execution

Task 3 dispatches five subagents itself, so `subagent-driven-development` is the wrong
outer harness here — it would wrap each task in a subagent that then spawns five more.
Use `superpowers:executing-plans`: inline, in this session, with a checkpoint at each
task's commit. Estimated spend ≈ 250k tokens, dominated by Task 3.
