# ai_rfc Draft Quality v2 — SP7b "structures" Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make a draft's wire formats, messages, records, enums and state machines *generated output* rather than prose an agent invents — declared once in the manifest, bound field-by-field to claims the adjudicator already decides, rendered deterministically, frozen into the checkpoint, and compared byte-for-byte at every revision tag.

**Architecture:** The manifest gains a top-level `structures:` registry and a closed `level` enum. A pure renderer turns one structure into one delimited kramdown block. The checkpoint writer freezes the rendered blocks as `structures.md` beside `manifest.yaml` and records their digest; a sibling writer produces consolidation checkpoints under their own `consolidations/<NN>/` root. The gate gains revision `kind`/`checkpoint` fields and four checks that tie every delimited block in a tagged draft back to the frozen bytes. Each new capability lands as one core function with an `ai-rfc` verb, an MCP tool, a `parity.md` row and a `test_parity.py` twin.

**Tech Stack:** Python 3.10 (stdlib + PyYAML), pytest 8 + pytest-xdist, git.

**Spec:** `docs/superpowers/specs/2026-09-02-arfc-draft-quality-design.md` — decisions **D40** (registry + byte-for-byte gate), **D42** (one core, two frontends; arm C frozen), **D48** (consolidation checkpoints under their own root), **D52** (closed `Level`, two-digit `REVISION_TAG`, unbound data-model claim is a *lint* finding). Roadmap position: SP7b in the same spec's "Roadmap placement" table. Predecessor: `docs/superpowers/plans/2026-09-03-arfc-draft-quality-sp7a.md`. Successor: SP7c (consolidation rounds), which consumes every surface this plan produces.

## Global Constraints

- **Layout.** Executes AFTER SP1 (extraction) and AFTER SP7a, on the ai_rfc repository layout. `AIRFC` = the single submodule at `$PANTHER/panther/plugins/services/testers/ai_rfc` (its own git repository). Packages: `ai_rfc/` (substrate), `ai_rfc/server/`, `ai_rfc/experiment/`, `plugins/ai-rfc/`, `docs/`. Tests: `tests/substrate/`, `tests/server/`, `tests/experiment/`. `PY` = `$PANTHER/.venv/bin/python`. **Task 0 is the precondition gate; do not skip it.**
- **Every interface this plan assumes about SP7a is in the `Interface contract` section below**, pinned to SP7a plan commit `34e4bdd45`. Tasks reference the contract by item number and never restate it. If Task 0 finds a contract item false, repair the contract *there* and let the tasks inherit the repair — do not patch individual tasks.
- **Anchors are by symbol, never by line number.** Every `file:line` in this document was verified on the **pre-move, pre-SP7a** tree (PANTHER `21aa06fdc`, harness `26e522a`) and is a *pointer to a symbol*, not a coordinate. Re-anchor with `grep -n "def <name>"` before every edit.
- **Two sessions, one branch.** Run `git log -1 --format='%h %ad %s' --date=format:'%H:%M:%S'` and `git status --short` in BOTH `$PANTHER` and `$AIRFC` before every task. **If `git status --short` lists files you did not touch, do not commit** — pre-commit stashes and restores a peer session's unstaged work around your commit; wait or coordinate. Never `git stash` on this worktree.
- **Stage by explicit path**: never `git add -A` or `git add .`. Commit format in `$AIRFC`: `type: lowercase summary` (no scope). No `--no-verify`; a pre-commit failure is fixed and re-staged.
- **Tests**: `cd $AIRFC && SSLKEYLOGFILE= $PY -m pytest tests -n auto`. Baseline is whatever SP7a's Task 10 recorded (SP1's 769 plus roughly 40); read it from `docs/experiments/2026-09-03-sp7a-mark-baseline.md` at Task 0 and use that number, not a remembered one. Sandbox off for `pytest` and nested-git writes. `mypy --follow-imports=silent`; `flake8 --max-line-length=88`; `black --check`.
- **Never run** `panther docs build`, `panther_builder.py clean|package-dev`, or `ai_rfc.experiment audit|analyze` against `~/ai-rfc-experiments/campaigns/mark-full-1` or the aioquic pilot — they rewrite evidence. A read-only snapshot of the MARK A1 run is sealed at `~/ai-rfc-experiments/baselines/mark-a1-2026-09-03`; copy from it, never into it.
- **The substrate stays model-free and network-free.** Nothing in this plan runs a model or opens a socket.
- Line length 88, Google-style docstrings on public functions, `from __future__ import annotations`, comments only for a non-obvious *why*. No backward-compatibility shims. Fixed dates in every fixture (`2026-01-01T00:00:09+00:00` style, as the existing fixtures do). **A test needle must never match a fixture's own name** — grep the fixture ids before asserting a substring. A RED test must fail at the path the change addresses, not somewhere incidental.

## Interface contract (pinned to SP7a plan `34e4bdd45`)

Everything SP7b assumes about code SP7a lands. Task 0 verifies each item with one `grep`; every later task cites items by number instead of re-deriving them.

| # | Item | Assumed shape | Verify with |
|---|---|---|---|
| C1 | `ai_rfc/draft/gate.py` | `draft_text(draft_repo: Path, ref: str) -> tuple[str, str]` returning `(name, text)`, extracted from `cited_ids` and shared by `cited_ids`, `build` and `lint` | `grep -n "def draft_text" ai_rfc/draft/gate.py` |
| C2 | `ai_rfc/draft/lint.py` | module exists; `lint(text, *, manifest=None, manifest_error=None, source=None) -> LintReport`; `LintReport` is a frozen dataclass with a `findings: tuple[str, ...]` and a `to_json()`; constant `REPORT_FILE = "lint-report.json"` | `grep -n "^def lint\|^class LintReport\|^REPORT_FILE" ai_rfc/draft/lint.py` |
| C3 | `ai_rfc/draft/lint.py` | `LintReport.extra` exists as the documented SP7b hook but is **never populated** and the dataclass is **frozen** — SP7b must add a `lint()` keyword to fill it (SP7a's own review recorded this gap) | `grep -n "extra" ai_rfc/draft/lint.py` |
| C4 | `ai_rfc/server/tools.py` | `draft_lint`'s core filters its report through a closed `_METRIC_KEYS` tuple with no `extra` member — SP7b must extend it or structure metrics never reach the tool and CLI output | `grep -n "_METRIC_KEYS" ai_rfc/server/*.py ai_rfc/server/core/*.py` |
| C5 | `ai_rfc/draft/cli.py` | verbs `build` and `lint` registered as argparse subparsers, each with its own `if args.verb == …` branch. **`gate` is the unguarded bottom fallthrough**: a verb registered without its own branch runs gate's code and raises `AttributeError` | `grep -n "add_parser\|args.verb ==" ai_rfc/draft/cli.py` |
| C6 | `ai_rfc/server/tools.py` | `ALL_TOOLS` has **18** members (SP1's 16 plus `ai_rfc_draft_build`, `ai_rfc_draft_lint`), ordered as in `docs/parity.md` | `grep -n "ALL_TOOLS" -A 22 ai_rfc/server/tools.py` |
| C7 | `ai_rfc/server/core/draft.py` | `tag_revision(ctx, tag, message)` runs a `draft_build` stage before `git tag` | `grep -n "def tag_revision" -A 60 ai_rfc/server/core/draft.py` |
| C8 | `ai_rfc/experiment/` | `toolchain.py` with `provision`/`verify`; `workspace.scaffold_draft` produces the adopter layout | `grep -rn "def provision\|def verify" ai_rfc/experiment/toolchain.py` |
| C9 | `plugins/ai-rfc/skills/` | `ai-rfc-rfc-style` rewritten and `ai-rfc-figures` added; **no** `ai-rfc-structures` (this plan adds it) and **no** `ai-rfc-editorial` (SP7c adds it) | `ls plugins/ai-rfc/skills/` |
| C10 | `ai_rfc/entrypoints.py` | **untouched by SP7a** (it appears zero times in that plan) — SP7b owns any change here and must read its landed SP1 shape rather than assume one | `grep -n "draft" ai_rfc/entrypoints.py` |

Facts about code SP7a does **not** touch, verified directly on the current tree and therefore only invalidated by SP1's move (which is verbatim):

| # | Item | Verified shape |
|---|---|---|
| C11 | `schema.load` | requires exactly `("rfc", "title", "requirements")` at top level and **silently drops every unknown top-level key**; failures raise `SchemaError(ValueError)` with message `f"{claim_id_or_path}: {problem}"`. **SP0 is complete as of `2e5354b6c` (2026-09-03), so its strict duplicate-key loader has landed** — Task 1 extends that loader rather than adding a second one, and a duplicated `structures:` id is already refused before this plan's validation runs |
| C12 | `schema.dump` | `yaml.safe_dump({"rfc", "title", "requirements"}, sort_keys=True, default_flow_style=False, allow_unicode=True, width=88)`. `sort_keys=True` sorts **every** mapping level. Adding `structures` yields top-level order `requirements, rfc, structures, title` |
| C13 | optional-key precedent | `dump` gates an optional key exactly as `if claim.testable is not None: body["testable"] = …`. `structures` must be gated the same way or `test_dump_is_byte_stable` / `test_load_of_dump_is_a_fixed_point` break |
| C14 | `models.py` | every dataclass is `@dataclass(frozen=True)` and performs **zero** validation — all validation lives in `schema.py`. `RequirementClaim.level` and `.layer` are plain `str` |
| C15 | `schema._enum` | `_enum(enum_cls, raw, field, claim_id)` is the existing coercion helper; message `f"{claim_id}: {field} is {raw!r}; permitted values are {permitted}"` |
| C16 | `promotion` | `adjudicate(claim) -> Status`; `STATUS_RANK: dict[Status, int]` = `{GAP: 0, INFERRED: 1, CONFIRMED: 2}`. **No "minimum over a set" helper exists** — write `min(…, key=lambda s: STATUS_RANK[s])` |
| C17 | `report.to_markdown` | one monolithic function appending to a `lines: list[str]`, sections in order `Status counts, Externally checked fraction, Promotable, Normative, Descriptive, Promotion violations, Unverified anchors`; `_payload()` is the shared JSON/YAML dict builder |
| C18 | `draft/gate.py` | `RevisionEntry` is frozen with six **required** fields `tag, number, cluster_id, checkpoint_manifest_sha256, normative_change, note`. `load_revisions` reads only `cluster_id`, `checkpoint_manifest_sha256`, `normative_change`, `note` — unknown keys are silently ignored in both directions |
| C19 | `draft/gate.py` | `run_gate(draft_repo, timeline_dir, checkpoints_dir, questions_path, revisions_path) -> tuple[str, ...]` — five positional params, **no defaults**. Checkpoint resolution is one line: `checkpoint_dir = checkpoints_dir / entry.cluster_id`. Findings are plain strings `f"{tag}: {reason}"`; the gate carries **no in-code check numbers** (the 8–11 numbering is the spec's) |
| C20 | `draft/checkpoint.py` | `write_checkpoint(manifest_path, timeline_dir, cluster_id, out) -> Path`; `verify_checkpoint(checkpoint_dir) -> str | None`. A checkpoint dir holds exactly `manifest.yaml` + `checkpoint.json`; the record keys are `adjudication, cluster_id, manifest_sha256, ordinal, prev_cluster_id, timeline_sha256`. `verify_checkpoint` re-digests only `manifest.yaml` |
| C21 | `draft/checkpoint.py` | `checkpoint_dir = out / cluster_id` is hard-coded and `_cluster_row` raises `CheckpointError` for any id absent from `clusters.jsonl`. **A consolidation checkpoint therefore cannot reuse `write_checkpoint`** — it needs a sibling writer. Post-`21aa06fdc`, every input is read before `mkdir` |
| C22 | `server/core/claims.py` | `upsert_claim(ctx, claim_id, fields)` persists through `_normalize_and_write`, which **round-trips the document through `schema.load`/`schema.dump`**. Any top-level key the schema does not know is therefore **destroyed on the next write** — the schema (Task 1) must land before any tool that writes structures (Task 7) |
| C23 | `server/core/revisions.py` | `record_revision(ctx, tag, cluster_id, normative_change, note) -> dict`. A `kind` added only here is silently dropped by the substrate (C18) — `RevisionEntry` must gain the field too |
| C24 | `server/core/gates.py` | the server's checkpoint core **shells out** to the substrate CLI (`python -m …ai_rfc.draft checkpoint …`), so a `--consolidation` mode must exist in the **substrate** CLI before the server can offer one |
| C25 | `server/cli.py` | `_emit(payload) -> None` prints JSON and returns nothing; a verb returning a **string** (e.g. `question-export`) uses `print(...)` instead. New core modules must be added to **two** import sites: the module-level import in `tools.py` and the deferred import inside `cli.py`'s dispatch |
| C26 | `tests/server/test_parity.py` | `_twins(make_workspace)` returns `(tool_arm, cli_arm, use)`; each operation has a **hand-written** `test_*_parity`. `test_every_tool_is_in_the_parity_table` only asserts the backticked tool name appears in the table. `question_export` has **no** twin — a precedent gap; do not copy it |
| C27 | `docs/parity.md` | header `\| MCP tool \| \`ai_rfc\` verb \| Raw substrate command (when one exists) \|` then `\|---\|---\|---\|`. An unavailable raw command is a bare em dash `—`, optionally with a parenthetical reason |
| C28 | `tests/substrate/draft/conftest.py` | fixtures `timeline_dir`, `draft_workspace` (keys `repo, timeline, checkpoints, questions, revisions`), `manifest_path`, `sparse_workspace`; module helpers `git`, `_record`, `_manifest_text`, `_checkpoint_sha`. **No golden-file comparison exists anywhere in this tree**; the closest precedent is `test_two_checkpoints_of_same_manifest_are_byte_identical` (write twice, compare bytes) |
| C29 | `draft/gate.py` | `CITATION = re.compile(r"`ai_rfc:([^`\s]+)`")` and `REVISION_TAG = re.compile(r"^draft-.+-(?P<nn>\d\d)$")` |

## File Structure

| File (under `$AIRFC`) | Task | Responsibility after the change |
|---|---|---|
| `ai_rfc/models.py` | 1 | `Level` enum; `StructureKind`; frozen `Field`, `Value`, `State`, `Transition`, `Structure`; `Manifest.structures` |
| `ai_rfc/schema.py` | 1 | Load and dump `structures:`, gated so a structure-free manifest stays byte-identical; every `claim:` must exist in `requirements:` |
| `ai_rfc/draft/structures.py` (new) | 2 | Pure renderer: one `Structure` → one delimited kramdown block, per kind. No I/O |
| `ai_rfc/promotion.py` | 3 | `structure_statuses(manifest)` — a structure's status is the minimum over its bound claims |
| `ai_rfc/report.py` | 3 | A `## Structures` section in `report.md` and a `structures` key in the JSON/YAML payload |
| `ai_rfc/draft/checkpoint.py` | 4 | Freeze `structures.md` and record `structures_sha256`; `write_consolidation_checkpoint`; `verify_checkpoint` covers both |
| `ai_rfc/draft/gate.py` | 5 | `RevisionEntry.kind`/`.checkpoint`; `run_gate(consolidations_dir=…)`; one `_checkpoint_dir` resolver; spec checks 8–11 |
| `ai_rfc/draft/cli.py` | 6 | `render` verb; `--consolidation` on `checkpoint`; `--consolidations` on `gate` |
| `ai_rfc/server/core/structures.py` (new) | 7 | `upsert_structure`, `render_structures` cores |
| `ai_rfc/server/{tools,cli}.py`, `core/{revisions,gates}.py` | 7 | Four surfaces, their parity rows and their twins |
| `ai_rfc/draft/lint.py` | 8 | The `structures` block of `lint-report.json`; unrendered/stale/unknown/malformed findings; data-model claims bound to no structure |
| `plugins/ai-rfc/skills/ai-rfc-structures/SKILL.md` (new) | 9 | What to declare as a structure, and what not to |
| `docs/parity.md`, `docs/experiment-protocol.md`, `README.md` | 7, 10 | The recorded surface change |

Tasks 1–4 touch only files SP7a leaves alone, so they can proceed even if a contract item about SP7a's own files turns out wrong. Tasks 5–8 are the shared-file registrations and are deliberately last.

---

### Task 0: Verify the contract before writing a line

**Files:** none — this task only reads and, if needed, edits the `Interface contract` table of this document.

**Interfaces:**
- Consumes: the landed SP1 and SP7a trees.
- Produces: a contract table every later task can trust, or a STOP.

- [ ] **Step 1: Confirm the layout and the suite**

```bash
cd $AIRFC && ls ai_rfc/draft ai_rfc/server ai_rfc/experiment tests/substrate tests/server tests/experiment
cd $AIRFC && $PY -c "import ai_rfc, ai_rfc.draft, ai_rfc.server, ai_rfc.experiment"
cd $AIRFC && git status --short
cd $PANTHER && git status --short
```

Expected: every directory lists; the import is silent; **both** trees clean. A modified file you did not touch means a peer session is mid-task — wait, do not proceed. If `ai_rfc/draft/build.py` and `ai_rfc/draft/lint.py` are absent, SP7a has not landed: **STOP**, this plan has no foundation.

- [ ] **Step 2: Record the real baseline**

Run: `cd $AIRFC && SSLKEYLOGFILE= $PY -m pytest tests -n auto 2>&1 | tail -3`

Read the pass count from `docs/experiments/2026-09-03-sp7a-mark-baseline.md` and confirm the suite matches it. Write the number here, in this document, replacing this sentence — every later task's "Expected" compares against it. A mismatch means something landed between SP7a and now: find out what before continuing.

- [ ] **Step 3: Run one grep per contract item**

```bash
cd $AIRFC
grep -n "def draft_text" ai_rfc/draft/gate.py                                  # C1
grep -n "^def lint\|^class LintReport\|^REPORT_FILE" ai_rfc/draft/lint.py      # C2
grep -n "extra" ai_rfc/draft/lint.py                                           # C3
grep -rn "_METRIC_KEYS" ai_rfc/server/                                         # C4
grep -n "add_parser\|args.verb ==" ai_rfc/draft/cli.py                         # C5
grep -n "ALL_TOOLS" -A 22 ai_rfc/server/tools.py                               # C6
grep -n "def tag_revision" -A 60 ai_rfc/server/core/draft.py                   # C7
grep -rn "def provision\|def verify" ai_rfc/experiment/toolchain.py            # C8
ls plugins/ai-rfc/skills/                                                      # C9
grep -n "draft" ai_rfc/entrypoints.py                                          # C10
grep -n "def load\|def dump\|sort_keys" ai_rfc/schema.py                       # C11, C12, C13
grep -n "def _enum\|frozen=True" ai_rfc/models.py ai_rfc/schema.py             # C14, C15
grep -n "STATUS_RANK\|def adjudicate" ai_rfc/promotion.py                      # C16
grep -n "def to_markdown\|def _payload" ai_rfc/report.py                       # C17
grep -n "class RevisionEntry" -A 12 ai_rfc/draft/gate.py                       # C18
grep -n "def run_gate" -A 10 ai_rfc/draft/gate.py                              # C19
grep -n "def write_checkpoint\|def verify_checkpoint" -A 8 ai_rfc/draft/checkpoint.py  # C20, C21
grep -n "def upsert_claim\|_normalize_and_write" ai_rfc/server/core/claims.py  # C22
grep -n "def record_revision" -A 8 ai_rfc/server/core/revisions.py             # C23
grep -n "checkpoint" ai_rfc/server/core/gates.py                               # C24
grep -n "def _emit" -A 3 ai_rfc/server/cli.py                                  # C25
grep -n "def _twins" -A 4 tests/server/test_parity.py                          # C26
sed -n '1,12p' docs/parity.md                                                  # C27
grep -n "^def \|^@pytest.fixture" -A 1 tests/substrate/draft/conftest.py       # C28
grep -n "^CITATION\|^REVISION_TAG" ai_rfc/draft/gate.py                        # C29
```

For each item: matches the contract, or does not. **A mismatch is repaired in the contract table above, once**, with a one-line note saying what the landed shape actually is. Tasks read the table, so a repair there propagates. Two mismatches deserve special care because a later task's design depends on them:

- **C22 false** (the server no longer round-trips writes through `schema.load`/`schema.dump`): Task 7's ordering rationale weakens but the ordering still holds; note it and continue.
- **C21 false** (`write_checkpoint` grew a way to write outside `out / cluster_id`): Task 4 shrinks to reusing it. Read the landed signature before writing Task 4's code.

- [ ] **Step 4: Commit the repaired contract, if anything changed**

Only if Step 3 changed the table:

```bash
cd $PANTHER && git status --short
git add -f docs/superpowers/plans/2026-09-03-arfc-draft-quality-sp7b.md
git commit -m "docs(ai_rfc): repair the SP7b contract against the landed tree"
```

---

### Task 1: A closed `level`, and `structures:` in the manifest schema

The schema lands first because the server persists every manifest write by round-tripping it through `schema.load` and `schema.dump` (**C22**). Until the schema knows the key, anything written under `structures:` is destroyed on the next write — so no tool may touch structures before this task is green.

**Files:**
- Modify: `ai_rfc/models.py`, `ai_rfc/schema.py`
- Test: `tests/substrate/test_models.py`, `tests/substrate/test_schema.py`

**Interfaces:**
- Consumes: **C11**–**C15** (load/dump shape, `sort_keys=True`, the `testable` gating precedent, frozen models, `_enum`).
- Produces: `models.Level`, `models.StructureKind`, `models.VARIABLE_WIDTH`, frozen `models.{Field,Value,Transition,Structure}`, `Structure.claims -> tuple[str, ...]`, `Manifest.structures: tuple[Structure, ...] = ()`; `schema.load` and `schema.dump` handle `structures:`; `schema.SchemaError` still signals every failure.

**Why this shape.** `models.py` performs zero validation by construction (**C14**), so the dataclasses stay dumb and every rule lives in `schema.py` beside the existing `_enum`/`_anchor`/`_claim` helpers. YAML says `from:`/`to:` (both Python keywords), so `Transition` names them `source`/`target` and the schema maps them — the only place the two vocabularies differ. `dump` gates `structures` exactly as it gates `testable` (**C13**), which is what keeps a structure-free manifest byte-identical and the three existing stability tests green.

- [ ] **Step 1: Write the failing model tests**

Append to `tests/substrate/test_models.py`:

```python
def test_a_structure_lists_the_claims_it_binds_in_declaration_order():
    from ai_rfc.models import Field, Structure, StructureKind, Transition, Value

    wire = Structure(
        id="hdr",
        kind=StructureKind.WIRE_FORMAT,
        title="Header",
        section="4.1",
        fields=(
            Field(name="version", claim="spec:4.1", width=8),
            Field(name="length", claim="spec:4.2", width="variable"),
        ),
    )
    assert wire.claims == ("spec:4.1", "spec:4.2")

    machine = Structure(
        id="conn",
        kind=StructureKind.STATE_MACHINE,
        title="Connection",
        section="5",
        states=("idle", "open"),
        transitions=(Transition(source="idle", event="connect", target="open", claim="spec:5.1"),),
    )
    assert machine.claims == ("spec:5.1",)

    codes = Structure(
        id="codes",
        kind=StructureKind.ENUM,
        title="Error codes",
        section="6",
        values=(Value(name="NO_ERROR", value="0", claim="spec:6.1"),),
    )
    assert codes.claims == ("spec:6.1",)
```

- [ ] **Step 2: Run them to verify they fail**

Run: `cd $AIRFC && SSLKEYLOGFILE= $PY -m pytest tests/substrate/test_models.py -k structure -v`
Expected: FAIL — `ImportError: cannot import name 'Field' from 'ai_rfc.models'`.

- [ ] **Step 3: Add the types**

In `ai_rfc/models.py`, after the existing enums (re-anchor with `grep -n "^class Intent"`):

```python
class Level(Enum):
    """The BCP 14 keyword a requirement is stated with."""

    MUST = "MUST"
    MUST_NOT = "MUST NOT"
    SHOULD = "SHOULD"
    SHOULD_NOT = "SHOULD NOT"
    MAY = "MAY"


class StructureKind(Enum):
    """What a structure describes."""

    WIRE_FORMAT = "wire-format"
    MESSAGE = "message"
    RECORD = "record"
    ENUM = "enum"
    STATE_MACHINE = "state-machine"


#: A last field may be declared ``variable`` instead of a bit count.
VARIABLE_WIDTH = "variable"

#: Kinds whose members are ``fields``; the remaining two use ``values``/``states``.
FIELD_KINDS = frozenset(
    {StructureKind.WIRE_FORMAT, StructureKind.MESSAGE, StructureKind.RECORD}
)
```

and after `RequirementClaim` (re-anchor with `grep -n "^class Manifest"`):

```python
@dataclass(frozen=True)
class Field:
    """One field of a wire format, message or record."""

    name: str
    claim: str
    width: int | str | None = None
    type: str | None = None
    description: str = ""


@dataclass(frozen=True)
class Value:
    """One member of an enumeration."""

    name: str
    value: str
    claim: str
    description: str = ""


@dataclass(frozen=True)
class Transition:
    """One edge of a state machine.

    ``source`` and ``target`` are the manifest's ``from`` and ``to``, renamed
    because both are Python keywords.
    """

    source: str
    event: str
    target: str
    claim: str
    guard: str = ""


@dataclass(frozen=True)
class Structure:
    """A format, record, enumeration or state machine, bound to claims."""

    id: str
    kind: StructureKind
    title: str
    section: str
    fields: tuple[Field, ...] = ()
    values: tuple[Value, ...] = ()
    states: tuple[str, ...] = ()
    transitions: tuple[Transition, ...] = ()

    @property
    def claims(self) -> tuple[str, ...]:
        """Every claim id this structure binds, in declaration order."""
        members: tuple[Field | Value | Transition, ...] = (
            self.fields + self.values + self.transitions
        )
        return tuple(member.claim for member in members)
```

Then add `structures: tuple[Structure, ...] = ()` as the **last** field of `Manifest` (its three existing fields have no defaults, so a defaulted field must come last).

- [ ] **Step 4: Run the model tests to verify they pass**

Run: `cd $AIRFC && SSLKEYLOGFILE= $PY -m pytest tests/substrate/test_models.py -k structure -v`
Expected: PASS.

- [ ] **Step 5: Write the failing schema tests**

Append to `tests/substrate/test_schema.py`. `_manifest_text` comes from the suite's `conftest` (**C28**); this helper appends a structures block to it:

```python
STRUCTURES = """\
structures:
  header:
    kind: wire-format
    title: Message header
    section: "4.1"
    fields:
      - name: version
        width: 8
        claim: spec:1.1
        description: Protocol version.
      - name: payload
        width: variable
        claim: spec:1.2
"""


def _with_structures(tmp_path, block=STRUCTURES, **kwargs):
    path = tmp_path / "m.yaml"
    path.write_text(_manifest_text(with_second_claim=True, **kwargs) + block)
    return path


def test_every_bcp14_level_loads_and_anything_else_is_refused(tmp_path):
    from ai_rfc.models import Level

    for keyword in ("MUST", "MUST NOT", "SHOULD", "SHOULD NOT", "MAY"):
        path = tmp_path / "level.yaml"
        path.write_text(_manifest_text().replace("level: MUST", f"level: {keyword}"))
        assert load(path).claims[0].level is Level(keyword)

    path = tmp_path / "bad.yaml"
    path.write_text(_manifest_text().replace("level: MUST", "level: descriptive"))
    with pytest.raises(SchemaError) as error:
        load(path)
    assert "permitted values are" in str(error.value)
    assert "descriptive" in str(error.value)


def test_structures_load_with_their_members(tmp_path):
    from ai_rfc.models import StructureKind

    manifest = load(_with_structures(tmp_path))
    assert len(manifest.structures) == 1
    header = manifest.structures[0]
    assert header.id == "header"
    assert header.kind is StructureKind.WIRE_FORMAT
    assert header.claims == ("spec:1.1", "spec:1.2")
    assert header.fields[0].width == 8
    assert header.fields[1].width == "variable"


def test_a_bound_claim_must_exist_in_requirements(tmp_path):
    block = STRUCTURES.replace("claim: spec:1.2", "claim: spec:9.9")
    with pytest.raises(SchemaError) as error:
        load(_with_structures(tmp_path, block=block))
    assert "spec:9.9" in str(error.value)
    assert "not a requirement" in str(error.value)


def test_variable_width_is_refused_anywhere_but_the_last_field(tmp_path):
    block = STRUCTURES.replace("width: 8", "width: variable")
    with pytest.raises(SchemaError) as error:
        load(_with_structures(tmp_path, block=block))
    assert "only the last field" in str(error.value)


def test_a_transition_must_name_declared_states(tmp_path):
    block = """\
structures:
  conn:
    kind: state-machine
    title: Connection
    section: "5"
    states: [idle, open]
    transitions:
      - from: idle
        event: connect
        to: half-open
        claim: spec:1.1
"""
    with pytest.raises(SchemaError) as error:
        load(_with_structures(tmp_path, block=block))
    assert "half-open" in str(error.value)
    assert "not a declared state" in str(error.value)


def test_structure_ids_are_constrained(tmp_path):
    for bad in ("-header", "hea--der", "head er"):
        block = STRUCTURES.replace("  header:", f"  {bad}:")
        with pytest.raises(SchemaError) as error:
            load(_with_structures(tmp_path, block=block))
        assert bad in str(error.value)


def test_a_structure_free_manifest_dumps_exactly_as_before(tmp_path):
    path = tmp_path / "plain.yaml"
    path.write_text(_manifest_text())
    text = dump(load(path))
    assert "structures" not in text
    assert text == dump(load(path))


def test_structures_serialise_between_requirements_and_title(tmp_path):
    text = dump(load(_with_structures(tmp_path)))
    assert text.index("requirements:") < text.index("structures:") < text.index("title:")
    assert load(_with_structures(tmp_path)) == load_text(text, tmp_path / "round.yaml")
```

Add this one helper beside the others in the same test module (the suite has no `load_text`; a round-trip needs a file because `load` takes a path):

```python
def load_text(text, path):
    path.write_text(text)
    return load(path)
```

- [ ] **Step 6: Run them to verify they fail**

Run: `cd $AIRFC && SSLKEYLOGFILE= $PY -m pytest tests/substrate/test_schema.py -k "level or structure" -v`
Expected: FAIL — the level test fails because `level` is still a plain `str` (**C14**) so `descriptive` loads happily; the structure tests fail because `load` drops unknown top-level keys silently (**C11**), leaving `manifest.structures` empty.

- [ ] **Step 7: Coerce `level` through the existing enum helper**

In `ai_rfc/schema.py`, import `Level` and change `_claim`'s `level` handling from a plain string read to the same `_enum` call the other enums use (**C15**); re-anchor with `grep -n "def _claim"`:

```python
        level=_enum(Level, raw["level"], "level", claim_id),
```

and in `dump`'s claim body, emit `claim.level.value` where it emitted `claim.level`.

- [ ] **Step 8: Load and validate structures**

In `ai_rfc/schema.py`, beside the other helpers:

```python
_STRUCTURE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
_MEMBER_KEYS = {
    StructureKind.WIRE_FORMAT: "fields",
    StructureKind.MESSAGE: "fields",
    StructureKind.RECORD: "fields",
    StructureKind.ENUM: "values",
    StructureKind.STATE_MACHINE: "transitions",
}


def _width(raw: Any, where: str) -> int | str | None:
    if raw is None:
        return None
    if raw == VARIABLE_WIDTH:
        return VARIABLE_WIDTH
    if isinstance(raw, bool) or not isinstance(raw, int) or raw < 1:
        raise SchemaError(
            f"{where}: width is {raw!r}; permitted values are a positive "
            f"integer or {VARIABLE_WIDTH!r}"
        )
    return raw


def _fields(structure_id: str, raw: Any) -> tuple[Field, ...]:
    entries = _sequence(structure_id, raw, "fields")
    fields = []
    for index, entry in enumerate(entries):
        where = f"{structure_id}.fields[{index}]"
        name = _required(where, entry, "name")
        fields.append(
            Field(
                name=name,
                claim=_required(where, entry, "claim"),
                width=_width(entry.get("width"), f"{where} ({name})"),
                type=entry.get("type"),
                description=entry.get("description", ""),
            )
        )
    for field in fields[:-1]:
        if field.width == VARIABLE_WIDTH:
            raise SchemaError(
                f"{structure_id}: {field.name} is {VARIABLE_WIDTH}, but only "
                f"the last field of a structure may be"
            )
    return tuple(fields)


def _values(structure_id: str, raw: Any) -> tuple[Value, ...]:
    entries = _sequence(structure_id, raw, "values")
    return tuple(
        Value(
            name=_required(f"{structure_id}.values[{index}]", entry, "name"),
            value=str(_required(f"{structure_id}.values[{index}]", entry, "value")),
            claim=_required(f"{structure_id}.values[{index}]", entry, "claim"),
            description=entry.get("description", ""),
        )
        for index, entry in enumerate(entries)
    )


def _transitions(structure_id: str, raw: Any, states: tuple[str, ...]) -> tuple[Transition, ...]:
    entries = _sequence(structure_id, raw, "transitions")
    transitions = []
    for index, entry in enumerate(entries):
        where = f"{structure_id}.transitions[{index}]"
        source = _required(where, entry, "from")
        target = _required(where, entry, "to")
        for endpoint in (source, target):
            if endpoint not in states:
                raise SchemaError(
                    f"{structure_id}: {endpoint!r} is not a declared state; "
                    f"declared states are {sorted(states)}"
                )
        transitions.append(
            Transition(
                source=source,
                event=_required(where, entry, "event"),
                target=target,
                claim=_required(where, entry, "claim"),
                guard=entry.get("guard", ""),
            )
        )
    return tuple(transitions)


def _structure(structure_id: str, raw: Any) -> Structure:
    if not _STRUCTURE_ID.match(structure_id) or "--" in structure_id:
        raise SchemaError(
            f"{structure_id}: a structure id must match "
            f"{_STRUCTURE_ID.pattern} and must not contain '--'"
        )
    if not isinstance(raw, dict):
        raise SchemaError(f"{structure_id}: a structure must be a mapping")
    kind = _enum(StructureKind, _required(structure_id, raw, "kind"), "kind", structure_id)
    states = tuple(raw.get("states") or ())
    structure = Structure(
        id=structure_id,
        kind=kind,
        title=_required(structure_id, raw, "title"),
        section=str(_required(structure_id, raw, "section")),
        fields=_fields(structure_id, raw.get("fields")) if kind in FIELD_KINDS else (),
        values=_values(structure_id, raw.get("values")) if kind is StructureKind.ENUM else (),
        states=states,
        transitions=(
            _transitions(structure_id, raw.get("transitions"), states)
            if kind is StructureKind.STATE_MACHINE
            else ()
        ),
    )
    if not structure.claims:
        raise SchemaError(
            f"{structure_id}: a {kind.value} structure needs at least one "
            f"{_MEMBER_KEYS[kind]} entry"
        )
    return structure
```

with two small shared helpers beside them:

```python
def _sequence(structure_id: str, raw: Any, field: str) -> list[dict[str, Any]]:
    if raw is None:
        return []
    if not isinstance(raw, list) or any(not isinstance(item, dict) for item in raw):
        raise SchemaError(f"{structure_id}: {field} must be a list of mappings")
    return raw


def _required(where: str, entry: dict[str, Any], key: str) -> Any:
    if key not in entry or entry[key] in (None, ""):
        raise SchemaError(f"{where}: missing required field {key}")
    return entry[key]
```

- [ ] **Step 9: Wire structures into `load` and `dump`**

In `load`, after the claims are built and before the `Manifest` is constructed (re-anchor with `grep -n "def load"`):

```python
    structures = tuple(
        _structure(structure_id, raw)
        for structure_id, raw in (document.get("structures") or {}).items()
    )
    known = {claim.id for claim in claims}
    for structure in structures:
        for claim_id in structure.claims:
            if claim_id not in known:
                raise SchemaError(
                    f"{structure.id}: binds {claim_id}, which is not a "
                    f"requirement in this manifest"
                )
```

and pass `structures=structures` to `Manifest(...)`.

In `dump`, build the payload and gate the key exactly as `testable` is gated (**C13**) — re-anchor with `grep -n "def dump"`:

```python
    document = {"rfc": manifest.rfc, "title": manifest.title, "requirements": requirements}
    if manifest.structures:
        document["structures"] = {
            structure.id: _structure_to_dict(structure) for structure in manifest.structures
        }
```

with the serialiser beside `_anchor_to_dict`:

```python
def _structure_to_dict(structure: Structure) -> dict[str, Any]:
    """Serialise one structure, omitting every empty optional member."""
    body: dict[str, Any] = {
        "kind": structure.kind.value,
        "title": structure.title,
        "section": structure.section,
    }
    if structure.fields:
        body["fields"] = [
            {
                key: value
                for key, value in (
                    ("name", field.name),
                    ("width", field.width),
                    ("type", field.type),
                    ("description", field.description),
                    ("claim", field.claim),
                )
                if value not in (None, "")
            }
            for field in structure.fields
        ]
    if structure.values:
        body["values"] = [
            {
                key: value
                for key, value in (
                    ("name", value_.name),
                    ("value", value_.value),
                    ("description", value_.description),
                    ("claim", value_.claim),
                )
                if value not in (None, "")
            }
            for value_ in structure.values
        ]
    if structure.states:
        body["states"] = list(structure.states)
    if structure.transitions:
        body["transitions"] = [
            {
                key: value
                for key, value in (
                    ("from", transition.source),
                    ("event", transition.event),
                    ("guard", transition.guard),
                    ("to", transition.target),
                    ("claim", transition.claim),
                )
                if value not in (None, "")
            }
            for transition in structure.transitions
        ]
    return body
```

- [ ] **Step 10: Run the whole substrate manifest suite**

Run: `cd $AIRFC && SSLKEYLOGFILE= $PY -m pytest tests/substrate/test_schema.py tests/substrate/test_models.py -v`
Expected: all PASS, **including** the three pre-existing stability tests `test_dump_is_byte_stable`, `test_load_of_dump_is_a_fixed_point` and `test_json_is_byte_stable`. If any of those three fails, `structures` is being emitted unconditionally — fix the gate, not the test.

- [ ] **Step 11: Find every reader of `claim.level`**

`level` was a `str` and is now a `Level` (**C14**). Grep the whole repository and fix each site to use `.value` where a string is wanted:

```bash
cd $AIRFC && grep -rn "\.level" ai_rfc/ tests/ plugins/ | grep -v "logging"
```

Expected sites: `report.py`'s normative/descriptive grouping, `draft/lint.py`'s keyword accounting if it reads the manifest, `server/core/claims.py`'s `_WRITABLE_FIELDS` round-trip (which passes strings *into* the schema and is unaffected), and the fixtures. Run the full suite afterwards.

- [ ] **Step 12: Lint, type-check and commit**

```bash
cd $AIRFC && $PY -m black ai_rfc/models.py ai_rfc/schema.py tests/substrate/test_models.py tests/substrate/test_schema.py
cd $AIRFC && $PY -m flake8 --max-line-length=88 ai_rfc/models.py ai_rfc/schema.py
cd $AIRFC && $PY -m mypy --follow-imports=silent ai_rfc/models.py ai_rfc/schema.py
cd $AIRFC && SSLKEYLOGFILE= $PY -m pytest tests -n auto 2>&1 | tail -3
```

Expected: clean, and the suite at the Task 0 baseline plus the new tests.

```bash
cd $AIRFC && git status --short
git add ai_rfc/models.py ai_rfc/schema.py tests/substrate/test_models.py tests/substrate/test_schema.py
git commit -m "feat: close the level vocabulary and give the manifest a structures registry"
```

---

### Task 2: The renderer, and the one reader of a delimited block

**Files:**
- Create: `ai_rfc/draft/structures.py`
- Test: `tests/substrate/draft/test_structures.py`

**Interfaces:**
- Consumes: `models.{Structure, StructureKind, Field, Value, Transition, VARIABLE_WIDTH, FIELD_KINDS}` (Task 1).
- Produces: `render(structure) -> str` (one delimited block), `render_all(manifest) -> str` (the whole `structures.md`), `parse_blocks(text) -> tuple[dict[str, str], tuple[str, ...]]` (bodies by id, plus malformed-delimiter findings), constants `STRUCTURES_FILE = "structures.md"`, `BITS_PER_ROW = 32`.

**Why this shape.** The module is pure: `Structure` in, `str` out, no filesystem and no git. That is what lets the checkpoint freeze it, the gate re-derive it, and the lint count it without three different notions of "the block". **`parse_blocks` is deliberately the single reader** — the gate (Task 5) and the lint (Task 8) both call it rather than each writing a regex, because two readers of one input drift apart and produce a *false* finding rather than a missing one.

Three properties the tests pin, because they are the ones that silently break a build:

1. **No trailing whitespace on any line.** The template's `lint-whitespace` target refuses it, so a structure block would fail the build gate that SP7a made hard. The bit ruler generates trailing spaces naturally — every emitted line is `rstrip`ed.
2. **Citation tokens never sit inside artwork.** The token belongs in the legend table so the existing `CITATION` regex (**C29**) counts it, while the `~~~` artwork stays a picture.
3. **`|` is escaped in every table cell**, or a field named `a|b` silently adds a column.

- [ ] **Step 1: Write the failing tests**

Create `tests/substrate/draft/test_structures.py`:

```python
"""The structure renderer and the delimited-block reader."""

from __future__ import annotations

import pytest

from ai_rfc.draft.structures import parse_blocks, render, render_all
from ai_rfc.models import (
    Field,
    Manifest,
    Structure,
    StructureKind,
    Transition,
    Value,
)

pytestmark = pytest.mark.unit


def _wire():
    return Structure(
        id="header",
        kind=StructureKind.WIRE_FORMAT,
        title="Message header",
        section="4.1",
        fields=(
            Field(name="Version", claim="spec:1.1", width=4, description="Protocol version."),
            Field(name="Type", claim="spec:1.2", width=4),
            Field(name="Length", claim="spec:1.3", width=24),
            Field(name="Payload", claim="spec:1.4", width="variable"),
        ),
    )


def _enum():
    return Structure(
        id="codes",
        kind=StructureKind.ENUM,
        title="Error codes",
        section="6",
        values=(
            Value(name="NO_ERROR", value="0x00", claim="spec:6.1", description="Normal close."),
            Value(name="PROTO", value="0x01", claim="spec:6.2"),
        ),
    )


def _machine():
    return Structure(
        id="conn",
        kind=StructureKind.STATE_MACHINE,
        title="Connection lifecycle",
        section="5",
        states=("idle", "open", "closed"),
        transitions=(
            Transition(source="idle", event="connect", target="open", claim="spec:5.1"),
            Transition(
                source="open", event="timeout", target="closed", claim="spec:5.2", guard="no traffic"
            ),
        ),
    )


def test_a_block_is_delimited_by_its_own_id():
    text = render(_enum())
    assert "{::comment}\nai_rfc:struct:codes begin\n{:/comment}" in text
    assert "{::comment}\nai_rfc:struct:codes end\n{:/comment}" in text


def test_no_line_carries_trailing_whitespace():
    # The template's lint-whitespace target refuses it, and the bit ruler
    # produces it naturally, so this is the property most likely to regress.
    for structure in (_wire(), _enum(), _machine()):
        for line in render(structure).splitlines():
            assert line == line.rstrip(), repr(line)


def test_every_bound_claim_appears_as_a_citation_token_outside_the_artwork():
    text = render(_wire())
    artwork = text.split("~~~")[1]
    for claim in ("spec:1.1", "spec:1.2", "spec:1.3", "spec:1.4"):
        assert f"`ai_rfc:{claim}`" in text
        assert claim not in artwork


def test_the_bit_diagram_wraps_at_thirty_two_bits_and_fits_seventy_two_columns():
    text = render(_wire())
    artwork = text.split("~~~")[1]
    lines = [line for line in artwork.splitlines() if line]
    assert all(len(line) <= 72 for line in lines)
    # 4 + 4 + 24 bits exactly fill one row; the variable field takes its own.
    assert artwork.count("+-+") >= 2
    assert "Payload (variable)" in artwork


def test_a_field_wider_than_a_row_is_split_and_marked_continued():
    wide = Structure(
        id="big",
        kind=StructureKind.WIRE_FORMAT,
        title="Wide",
        section="4.2",
        fields=(Field(name="Nonce", claim="spec:1.1", width=48),),
    )
    artwork = render(wide).split("~~~")[1]
    assert "Nonce" in artwork
    assert "(cont.)" in artwork


def test_a_pipe_in_a_cell_is_escaped():
    odd = Structure(
        id="odd",
        kind=StructureKind.RECORD,
        title="Odd",
        section="7",
        fields=(Field(name="a|b", claim="spec:1.1", type="uint8", description="x|y"),),
    )
    body = render(odd)
    assert r"a\|b" in body and r"x\|y" in body


def test_each_kind_renders_its_own_legend():
    assert "| Field | Bits | Description | Claim |" in render(_wire())
    assert "| Value | Name | Description | Claim |" in render(_enum())
    assert "| From | Event | Guard | To | Claim |" in render(_machine())
    record = Structure(
        id="rec",
        kind=StructureKind.RECORD,
        title="A record",
        section="7",
        fields=(Field(name="n", claim="spec:1.1", type="uint8", description="d"),),
    )
    assert "| Field | Type | Size | Description | Claim |" in render(record)


def test_a_state_machine_draws_its_states_before_the_table():
    text = render(_machine())
    artwork = text.split("~~~")[1]
    for state in ("idle", "open", "closed"):
        assert state in artwork


def test_rendering_is_deterministic_and_ordered_by_id():
    manifest = Manifest(rfc="spec", title="T", claims=(), structures=(_machine(), _enum()))
    first = render_all(manifest)
    assert first == render_all(manifest)
    assert first.index("ai_rfc:struct:codes") < first.index("ai_rfc:struct:conn")


def test_parse_blocks_round_trips_what_render_produced():
    manifest = Manifest(rfc="spec", title="T", claims=(), structures=(_wire(), _enum()))
    bodies, findings = parse_blocks(render_all(manifest))
    assert findings == ()
    assert set(bodies) == {"header", "codes"}
    assert bodies["codes"] == render(_enum()).split("{:/comment}\n", 1)[1].rsplit("{::comment}", 1)[0]


@pytest.mark.parametrize(
    "text, needle",
    [
        ("{::comment}\nai_rfc:struct:a begin\n{:/comment}\nbody\n", "never closed"),
        ("{::comment}\nai_rfc:struct:a end\n{:/comment}\n", "closed but never opened"),
        (
            "{::comment}\nai_rfc:struct:a begin\n{:/comment}\n"
            "{::comment}\nai_rfc:struct:b end\n{:/comment}\n",
            "closed by b",
        ),
    ],
)
def test_malformed_delimiters_are_findings_not_exceptions(text, needle):
    bodies, findings = parse_blocks(text)
    assert bodies == {}
    assert any(needle in finding for finding in findings), findings
```

- [ ] **Step 2: Run them to verify they fail**

Run: `cd $AIRFC && SSLKEYLOGFILE= $PY -m pytest tests/substrate/draft/test_structures.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'ai_rfc.draft.structures'`.

- [ ] **Step 3: Write the layout engine**

Create `ai_rfc/draft/structures.py`:

```python
"""Render a manifest structure as one delimited kramdown block.

Pure: a :class:`~ai_rfc.models.Structure` in, text out. The checkpoint freezes
what this produces, the gate re-derives it, and the lint counts it, so every
caller sees the same bytes.
"""

from __future__ import annotations

import re

from ai_rfc.models import (
    FIELD_KINDS,
    VARIABLE_WIDTH,
    Manifest,
    Structure,
    StructureKind,
)

#: The frozen rendering beside a checkpoint's ``manifest.yaml``.
STRUCTURES_FILE = "structures.md"

#: Bits per row of a wire-format diagram; 32 keeps a row inside 72 columns.
BITS_PER_ROW = 32

_BEGIN = re.compile(r"^ai_rfc:struct:(?P<id>\S+)\s+begin$")
_END = re.compile(r"^ai_rfc:struct:(?P<id>\S+)\s+end$")
_OPEN = "{::comment}"
_CLOSE = "{:/comment}"


def _cell(text: object) -> str:
    """Escape a table cell so a literal pipe cannot add a column."""
    return str(text).replace("|", r"\|")


def _rule(bits: int) -> str:
    return "+" + "-+" * bits


def _ruler(bits: int) -> list[str]:
    tens = " " + " ".join(str(i // 10) if i % 10 == 0 else " " for i in range(bits))
    ones = " " + " ".join(str(i % 10) for i in range(bits))
    return [tens.rstrip(), ones.rstrip()]


def _rows(structure: Structure) -> list[list[tuple[str, int]]]:
    """Lay the fields out over 32-bit rows, splitting any that straddles."""
    rows: list[list[tuple[str, int]]] = []
    row: list[tuple[str, int]] = []
    used = 0
    for field in structure.fields:
        if field.width == VARIABLE_WIDTH:
            if row:
                rows.append(row)
                row, used = [], 0
            rows.append([(f"{field.name} (variable)", BITS_PER_ROW)])
            continue
        remaining = int(field.width or 0)
        first = True
        while remaining > 0:
            take = min(remaining, BITS_PER_ROW - used)
            row.append((field.name if first else f"{field.name} (cont.)", take))
            used += take
            remaining -= take
            first = False
            if used == BITS_PER_ROW:
                rows.append(row)
                row, used = [], 0
    if row:
        rows.append(row)
    return rows


def _diagram(structure: Structure) -> list[str]:
    rows = _rows(structure)
    if not rows:
        return []
    lines = _ruler(BITS_PER_ROW)
    for row in rows:
        bits = sum(width for _, width in row)
        lines.append(_rule(bits))
        cells = []
        for label, width in row:
            inner = width * 2 - 1
            cells.append(label[:inner].center(inner))
        lines.append(("|" + "|".join(cells) + "|").rstrip())
    lines.append(_rule(sum(width for _, width in rows[-1])))
    return lines


def _ladder(structure: Structure) -> list[str]:
    """Draw each state as a box, in declaration order, then its edges."""
    lines: list[str] = []
    for state in structure.states:
        box = f"| {state} |"
        lines.extend(["+" + "-" * (len(box) - 2) + "+", box, "+" + "-" * (len(box) - 2) + "+"])
    for transition in structure.transitions:
        arrow = f"{transition.source} --{transition.event}--> {transition.target}"
        lines.append(arrow)
    return [line.rstrip() for line in lines]
```

- [ ] **Step 4: Write the per-kind bodies and the block wrapper**

Append to `ai_rfc/draft/structures.py`:

```python
def _table(header: list[str], rows: list[list[str]]) -> list[str]:
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return lines


def _body(structure: Structure) -> list[str]:
    lines = [f"**{_cell(structure.title)}**", ""]
    if structure.kind is StructureKind.WIRE_FORMAT:
        lines += ["~~~"] + _diagram(structure) + ["~~~", ""]
        lines += _table(
            ["Field", "Bits", "Description", "Claim"],
            [
                [
                    _cell(field.name),
                    _cell(field.width if field.width is not None else "-"),
                    _cell(field.description or "-"),
                    f"`ai_rfc:{field.claim}`",
                ]
                for field in structure.fields
            ],
        )
    elif structure.kind in FIELD_KINDS:
        lines += _table(
            ["Field", "Type", "Size", "Description", "Claim"],
            [
                [
                    _cell(field.name),
                    _cell(field.type or "-"),
                    _cell(field.width if field.width is not None else "-"),
                    _cell(field.description or "-"),
                    f"`ai_rfc:{field.claim}`",
                ]
                for field in structure.fields
            ],
        )
    elif structure.kind is StructureKind.ENUM:
        lines += _table(
            ["Value", "Name", "Description", "Claim"],
            [
                [
                    _cell(value.value),
                    _cell(value.name),
                    _cell(value.description or "-"),
                    f"`ai_rfc:{value.claim}`",
                ]
                for value in structure.values
            ],
        )
    else:
        lines += ["~~~"] + _ladder(structure) + ["~~~", ""]
        lines += _table(
            ["From", "Event", "Guard", "To", "Claim"],
            [
                [
                    _cell(transition.source),
                    _cell(transition.event),
                    _cell(transition.guard or "-"),
                    _cell(transition.target),
                    f"`ai_rfc:{transition.claim}`",
                ]
                for transition in structure.transitions
            ],
        )
    return lines


def render(structure: Structure) -> str:
    """Render one structure as a delimited kramdown block.

    Args:
        structure: The structure to render.

    Returns:
        The block, delimiters included, ending in a newline. Every line is
        stripped of trailing whitespace so the template's ``lint-whitespace``
        target accepts it.
    """
    lines = [
        _OPEN,
        f"ai_rfc:struct:{structure.id} begin",
        _CLOSE,
        *_body(structure),
        _OPEN,
        f"ai_rfc:struct:{structure.id} end",
        _CLOSE,
    ]
    return "\n".join(line.rstrip() for line in lines) + "\n"


def render_all(manifest: Manifest) -> str:
    """Render every structure, ordered by id, as the frozen ``structures.md``."""
    blocks = [render(s) for s in sorted(manifest.structures, key=lambda s: s.id)]
    return "\n".join(blocks)
```

- [ ] **Step 5: Write the one reader**

Append to `ai_rfc/draft/structures.py`:

```python
def parse_blocks(text: str) -> tuple[dict[str, str], tuple[str, ...]]:
    """Read every delimited structure block out of a draft.

    The gate and the lint both call this rather than each matching their own
    pattern: two readers of one input drift, and a drifted reader reports a
    finding that is not there.

    Args:
        text: The draft source.

    Returns:
        A pair of the bodies by structure id, and findings describing every
        malformed delimiter. A malformed block contributes a finding and no
        body; it never raises.
    """
    lines = text.splitlines()
    bodies: dict[str, str] = {}
    findings: list[str] = []
    open_id: str | None = None
    collected: list[str] = []
    index = 0
    while index < len(lines):
        if lines[index].strip() == _OPEN and index + 2 < len(lines):
            marker = lines[index + 1].strip()
            begin, end = _BEGIN.match(marker), _END.match(marker)
            if (begin or end) and lines[index + 2].strip() == _CLOSE:
                if begin:
                    if open_id is not None:
                        findings.append(
                            f"structure block {open_id} was never closed before "
                            f"{begin.group('id')} opened"
                        )
                    open_id, collected = begin.group("id"), []
                else:
                    closing = end.group("id")
                    if open_id is None:
                        findings.append(
                            f"structure block {closing} was closed but never opened"
                        )
                    elif closing != open_id:
                        findings.append(
                            f"structure block {open_id} was closed by {closing}"
                        )
                        open_id = None
                    else:
                        bodies[open_id] = "\n".join(collected) + "\n"
                        open_id = None
                index += 3
                continue
        if open_id is not None:
            collected.append(lines[index])
        index += 1
    if open_id is not None:
        findings.append(f"structure block {open_id} was never closed")
    return bodies, tuple(findings)
```

- [ ] **Step 6: Freeze one golden per kind**

This plan's roadmap gate is "goldens per kind", and the property tests above do not deliver it. It
matters here more than anywhere else: the rendering is **frozen into every checkpoint**, so an
incidental change — one space in the ruler, a renamed table header — would stale every
`structures.md` already in production and fail every gate. Only a byte comparison catches that at
test time.

Register the regeneration switch in the **root** test conftest; `pytest_addoption` is honoured only
there, not in a subdirectory conftest:

```python
# tests/conftest.py
def pytest_addoption(parser):
    parser.addoption(
        "--update-goldens",
        action="store_true",
        default=False,
        help="Rewrite the structure goldens from the current renderer.",
    )
```

Append to `tests/substrate/draft/test_structures.py`:

```python
from pathlib import Path

GOLDENS = Path(__file__).parent / "goldens"


def _message():
    return Structure(
        id="hello",
        kind=StructureKind.MESSAGE,
        title="Hello",
        section="3.1",
        fields=(
            Field(name="token", claim="spec:3.1", type="opaque", width=64, description="Session token."),
        ),
    )


def _record():
    return Structure(
        id="entry",
        kind=StructureKind.RECORD,
        title="Log entry",
        section="7.2",
        fields=(Field(name="stamp", claim="spec:7.1", type="uint64", description="Milliseconds."),),
    )


@pytest.mark.parametrize(
    "name, build",
    [
        ("wire-format", _wire),
        ("message", _message),
        ("record", _record),
        ("enum", _enum),
        ("state-machine", _machine),
    ],
)
def test_each_kind_matches_its_golden(name, build, request):
    produced = render(build())
    path = GOLDENS / f"{name}.md"
    if request.config.getoption("--update-goldens"):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(produced)
    assert path.read_text() == produced, (
        f"the {name} rendering changed, so every structures.md frozen in every "
        f"checkpoint is now stale and every gate over them will fail. If the "
        f"change is intended, re-run with --update-goldens and say so in the "
        f"commit message."
    )
```

Generate them once, then **read each of the five files** and satisfy yourself it looks like a
specification figure before committing — a golden is only worth what its first review was worth:

```bash
cd $AIRFC && SSLKEYLOGFILE= $PY -m pytest tests/substrate/draft/test_structures.py -k golden --update-goldens
cd $AIRFC && cat tests/substrate/draft/goldens/wire-format.md
```

- [ ] **Step 7: Run the tests to verify they pass**

Run: `cd $AIRFC && SSLKEYLOGFILE= $PY -m pytest tests/substrate/draft/test_structures.py -v`
Expected: all PASS, goldens included, **without** `--update-goldens`. If `test_the_bit_diagram_wraps…` fails on the column bound, the ruler is not being `rstrip`ed — fix `_ruler`, not the assertion.

- [ ] **Step 8: Lint, type-check and commit**

```bash
cd $AIRFC && $PY -m black ai_rfc/draft/structures.py tests/substrate/draft/test_structures.py
cd $AIRFC && $PY -m flake8 --max-line-length=88 ai_rfc/draft/structures.py tests/substrate/draft/test_structures.py
cd $AIRFC && $PY -m mypy --follow-imports=silent ai_rfc/draft/structures.py
cd $AIRFC && git status --short
git add ai_rfc/draft/structures.py tests/substrate/draft/test_structures.py tests/substrate/draft/goldens tests/conftest.py
git commit -m "feat: render a manifest structure as one delimited block"
```

---

### Task 3: A structure's status, and where it shows up in the report

**Files:**
- Modify: `ai_rfc/promotion.py`, `ai_rfc/report.py`
- Test: `tests/substrate/test_promotion.py`, `tests/substrate/test_report.py`

**Interfaces:**
- Consumes: `models.{Manifest, Structure}` (Task 1); `promotion.adjudicate`, `models.STATUS_RANK` (**C16**); `report.to_markdown`'s `lines` idiom and `_payload` (**C17**).
- Produces: `promotion.structure_statuses(manifest) -> dict[str, tuple[Status, Status]]` mapping structure id to `(stored, supported)`; a `## Structures` section in `report.md`; a `structures` key in the JSON and YAML payloads.

**Why this shape.** D40 makes figure correctness reduce to claim correctness, so a structure gets no status of its own — it inherits the **minimum** over the claims it binds, on both axes. There is no existing "minimum over a set" helper (**C16**), and `Status` is a plain `Enum` with no ordering, so the minimum must go through `STATUS_RANK` exactly as the two existing comparison sites do.

- [ ] **Step 1: Write the failing tests**

Append to `tests/substrate/test_promotion.py`:

```python
def test_a_structure_is_only_as_strong_as_its_weakest_claim(tmp_path):
    from ai_rfc.promotion import structure_statuses
    from ai_rfc.schema import load

    path = tmp_path / "m.yaml"
    path.write_text(
        _manifest_text(with_second_claim=True)
        + "structures:\n"
        "  header:\n"
        "    kind: record\n"
        "    title: H\n"
        "    section: '4'\n"
        "    fields:\n"
        "      - name: a\n"
        "        claim: spec:1.1\n"
        "      - name: b\n"
        "        claim: spec:1.2\n"
    )
    manifest = load(path)
    stored, supported = structure_statuses(manifest)["header"]
    weakest_stored = min(
        (claim.status for claim in manifest.claims), key=lambda s: STATUS_RANK[s]
    )
    assert stored is weakest_stored
    assert STATUS_RANK[supported] <= STATUS_RANK[stored] or supported is not None


def test_a_manifest_without_structures_has_no_structure_statuses(tmp_path):
    from ai_rfc.promotion import structure_statuses
    from ai_rfc.schema import load

    path = tmp_path / "m.yaml"
    path.write_text(_manifest_text())
    assert structure_statuses(load(path)) == {}
```

Append to `tests/substrate/test_report.py`:

```python
def test_the_markdown_report_names_every_structure_and_its_status(tmp_path):
    from ai_rfc.report import build, to_markdown

    path = tmp_path / "m.yaml"
    path.write_text(
        _manifest_text(with_second_claim=True)
        + "structures:\n"
        "  header:\n"
        "    kind: record\n"
        "    title: Message header\n"
        "    section: '4'\n"
        "    fields:\n"
        "      - name: a\n"
        "        claim: spec:1.1\n"
    )
    text = to_markdown(build(load(path)))
    assert "## Structures" in text
    assert "header" in text and "Message header" in text


def test_a_structure_free_report_has_no_structures_section(tmp_path):
    from ai_rfc.report import build, to_markdown

    path = tmp_path / "m.yaml"
    path.write_text(_manifest_text())
    assert "## Structures" not in to_markdown(build(load(path)))
```

- [ ] **Step 2: Run them to verify they fail**

Run: `cd $AIRFC && SSLKEYLOGFILE= $PY -m pytest tests/substrate/test_promotion.py tests/substrate/test_report.py -k structure -v`
Expected: FAIL — `ImportError: cannot import name 'structure_statuses'`, and `## Structures` absent.

- [ ] **Step 3: Compute the statuses**

Append to `ai_rfc/promotion.py`:

```python
def structure_statuses(manifest: Manifest) -> dict[str, tuple[Status, Status]]:
    """Each structure's stored and supported status.

    A structure is exactly as strong as the weakest claim it binds, on both
    axes, so figure correctness reduces to claim correctness.

    Args:
        manifest: The manifest whose structures to score.

    Returns:
        Structure id to ``(stored, supported)``. Empty when the manifest
        declares no structures.
    """
    by_id = {claim.id: claim for claim in manifest.claims}
    statuses: dict[str, tuple[Status, Status]] = {}
    for structure in manifest.structures:
        bound = [by_id[claim_id] for claim_id in structure.claims if claim_id in by_id]
        if not bound:
            continue
        stored = min((claim.status for claim in bound), key=lambda s: STATUS_RANK[s])
        supported = min((adjudicate(claim) for claim in bound), key=lambda s: STATUS_RANK[s])
        statuses[structure.id] = (stored, supported)
    return statuses
```

Import `Manifest` and `STATUS_RANK` at the top if they are not already imported.

- [ ] **Step 4: Add the report section**

In `ai_rfc/report.py`, inside `to_markdown`, after the `## Promotable` block and before `## Normative` (re-anchor with `grep -n '"## Promotable"'`), matching that block's `lines` idiom exactly (**C17**):

```python
    statuses = structure_statuses(report.manifest)
    if statuses:
        lines += ["", "## Structures", ""]
        for structure in sorted(report.manifest.structures, key=lambda s: s.id):
            stored, supported = statuses[structure.id]
            lines.append(
                f"- `{structure.id}` ({structure.kind.value}) {structure.title} "
                f"§{structure.section}: stored {stored.value}, supported "
                f"{supported.value}, {len(structure.claims)} claims"
            )
```

and in `_payload`, add the parallel key so JSON and YAML carry it too:

```python
        "structures": {
            structure_id: {"stored": stored.value, "supported": supported.value}
            for structure_id, (stored, supported) in structure_statuses(report.manifest).items()
        },
```

Import `structure_statuses` from `.promotion` beside the existing import.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `cd $AIRFC && SSLKEYLOGFILE= $PY -m pytest tests/substrate/test_promotion.py tests/substrate/test_report.py -v`
Expected: all PASS, `test_json_is_byte_stable` included.

- [ ] **Step 6: Lint, type-check and commit**

```bash
cd $AIRFC && $PY -m black ai_rfc/promotion.py ai_rfc/report.py tests/substrate/test_promotion.py tests/substrate/test_report.py
cd $AIRFC && $PY -m flake8 --max-line-length=88 ai_rfc/promotion.py ai_rfc/report.py
cd $AIRFC && $PY -m mypy --follow-imports=silent ai_rfc/promotion.py ai_rfc/report.py
cd $AIRFC && git status --short
git add ai_rfc/promotion.py ai_rfc/report.py tests/substrate/test_promotion.py tests/substrate/test_report.py
git commit -m "feat: score a structure by the weakest claim it binds"
```

---

### Task 4: Freeze the rendering, and give consolidations their own root

**Files:**
- Modify: `ai_rfc/draft/checkpoint.py`
- Test: `tests/substrate/draft/test_checkpoint.py`

**Interfaces:**
- Consumes: `draft.structures.{render_all, STRUCTURES_FILE}` (Task 2); `schema.{load, dump}` (Task 1); the existing `write_checkpoint` / `verify_checkpoint` shape (**C20**, **C21**).
- Produces: `write_checkpoint` additionally writes `structures.md` and records `structures_sha256` when the manifest declares structures; `write_consolidation_checkpoint(manifest_path, ordinal, base_checkpoint, cluster_id, out) -> Path`; `requirements_digest(manifest) -> str`; `verify_checkpoint` covers both files and both kinds.

**Why this shape.** `write_checkpoint` hard-codes `out / cluster_id` and `_cluster_row` raises for any id absent from `clusters.jsonl` (**C21**), so a consolidation — which belongs to no new cluster — cannot reuse it; it gets a sibling writer instead of a flag, and the sibling writes under a **different root** so the four existing readers of `checkpoints/` keep enumerating cluster checkpoints only (D48).

`requirements_digest` exists so the writer and the gate cannot drift: D48's rule is that a consolidation's `requirements:` are byte-identical to its base's, and the 33 existing MARK checkpoints record no such digest, so it must be computed on the fly from stored bytes — by **one** function, called from both sides.

SP0's fix (`21aa06fdc`) made every input read precede the `mkdir`. Rendering is pure, so the new work slots in before the `mkdir` without weakening that; the tests assert it.

- [ ] **Step 1: Write the failing tests**

Append to `tests/substrate/draft/test_checkpoint.py`:

```python
STRUCTURED = (
    "structures:\n"
    "  header:\n"
    "    kind: record\n"
    "    title: Message header\n"
    "    section: '4'\n"
    "    fields:\n"
    "      - name: version\n"
    "        type: uint8\n"
    "        claim: spec:1.1\n"
)


def _structured_manifest(tmp_path):
    path = tmp_path / "structured.yaml"
    path.write_text(_manifest_text(with_second_claim=True) + STRUCTURED)
    return path


def test_a_structured_checkpoint_freezes_the_rendering_and_its_digest(tmp_path, timeline_dir):
    import hashlib

    from ai_rfc.draft.structures import STRUCTURES_FILE

    out = tmp_path / "checkpoints"
    directory = write_checkpoint(_structured_manifest(tmp_path), timeline_dir, "c1", out)
    frozen = (directory / STRUCTURES_FILE).read_bytes()
    assert b"ai_rfc:struct:header begin" in frozen
    record = json.loads((directory / "checkpoint.json").read_text())
    assert record["structures_sha256"] == hashlib.sha256(frozen).hexdigest()


def test_a_structure_free_checkpoint_writes_no_structures_file(tmp_path, timeline_dir, manifest_path):
    from ai_rfc.draft.structures import STRUCTURES_FILE

    directory = write_checkpoint(manifest_path, timeline_dir, "c1", tmp_path / "cp")
    assert not (directory / STRUCTURES_FILE).exists()
    assert "structures_sha256" not in json.loads((directory / "checkpoint.json").read_text())


def test_a_tampered_structures_file_is_caught(tmp_path, timeline_dir):
    from ai_rfc.draft.structures import STRUCTURES_FILE

    directory = write_checkpoint(
        _structured_manifest(tmp_path), timeline_dir, "c1", tmp_path / "cp"
    )
    assert verify_checkpoint(directory) is None
    target = directory / STRUCTURES_FILE
    target.write_bytes(target.read_bytes().replace(b"uint8", b"uint9"))
    problem = verify_checkpoint(directory)
    assert problem is not None and STRUCTURES_FILE in problem


def test_a_consolidation_checkpoint_lands_under_its_own_root(tmp_path, timeline_dir):
    out = tmp_path / "checkpoints"
    base = write_checkpoint(_structured_manifest(tmp_path), timeline_dir, "c1", out)
    consolidations = tmp_path / "consolidations"
    directory = write_consolidation_checkpoint(
        _structured_manifest(tmp_path), 1, base, "c1", consolidations
    )
    assert directory == consolidations / "01"
    record = json.loads((directory / "checkpoint.json").read_text())
    assert record["kind"] == "consolidation"
    assert record["cluster_id"] == "c1"
    assert record["base_checkpoint"] == "c1"
    # The cluster root keeps enumerating cluster checkpoints only.
    assert sorted(p.name for p in out.iterdir()) == ["c1"]


def test_a_consolidation_may_change_only_the_structures(tmp_path, timeline_dir):
    out = tmp_path / "checkpoints"
    base = write_checkpoint(_structured_manifest(tmp_path), timeline_dir, "c1", out)
    changed = tmp_path / "changed.yaml"
    changed.write_text(
        _manifest_text(with_second_claim=True).replace("level: MUST", "level: MAY") + STRUCTURED
    )
    with pytest.raises(CheckpointError) as error:
        write_consolidation_checkpoint(changed, 1, base, "c1", tmp_path / "consolidations")
    assert "requirements" in str(error.value)


def test_a_consolidation_checkpoint_verifies_like_any_other(tmp_path, timeline_dir):
    out = tmp_path / "checkpoints"
    base = write_checkpoint(_structured_manifest(tmp_path), timeline_dir, "c1", out)
    directory = write_consolidation_checkpoint(
        _structured_manifest(tmp_path), 7, base, "c1", tmp_path / "consolidations"
    )
    assert directory.name == "07"
    assert verify_checkpoint(directory) is None


def test_a_failed_consolidation_leaves_no_directory(tmp_path, timeline_dir):
    consolidations = tmp_path / "consolidations"
    missing = tmp_path / "nope.yaml"
    with pytest.raises((CheckpointError, OSError)):
        write_consolidation_checkpoint(missing, 1, tmp_path / "absent", "c1", consolidations)
    assert not (consolidations / "01").exists()
```

Import `write_consolidation_checkpoint` and `CheckpointError` at the top of the module beside the existing imports, and `json`/`pytest` if they are not already there.

- [ ] **Step 2: Run them to verify they fail**

Run: `cd $AIRFC && SSLKEYLOGFILE= $PY -m pytest tests/substrate/draft/test_checkpoint.py -k "structur or consolidation" -v`
Expected: FAIL — `ImportError: cannot import name 'write_consolidation_checkpoint'`.

- [ ] **Step 3: Add the shared digest and freeze the rendering**

In `ai_rfc/draft/checkpoint.py`, add the imports and the shared helper (re-anchor with `grep -n "^MANIFEST_FILE"`):

```python
from ai_rfc.draft.structures import STRUCTURES_FILE, render_all


def requirements_digest(manifest: Manifest) -> str:
    """Digest a manifest's requirements alone, ignoring its structures.

    D48 lets a consolidation change only ``structures:``. Existing checkpoints
    record no such digest, so it is computed from stored bytes here and reused
    by the gate — one function, so the writer and the checker cannot drift.

    Args:
        manifest: The manifest to digest.

    Returns:
        The hex sha256 of the manifest dumped without its structures.
    """
    return _digest_bytes(dump(replace(manifest, structures=())).encode())
```

with `from dataclasses import replace` at the top.

Then in `write_checkpoint`, **before** the `mkdir` (re-anchor with `grep -n "mkdir"`), render and digest:

```python
    structures_text = render_all(manifest) if manifest.structures else ""
    structures_sha256 = _digest_bytes(structures_text.encode()) if structures_text else None
```

and after the `mkdir`, beside the existing `manifest.yaml` write:

```python
    if structures_text:
        (checkpoint_dir / STRUCTURES_FILE).write_text(structures_text)
```

adding the key to the record only when there is one (so a structure-free `checkpoint.json` keeps its exact current keys):

```python
    if structures_sha256 is not None:
        record["structures_sha256"] = structures_sha256
```

- [ ] **Step 4: Write the consolidation writer**

Append to `ai_rfc/draft/checkpoint.py`:

```python
def write_consolidation_checkpoint(
    manifest_path: Path,
    ordinal: int,
    base_checkpoint: Path,
    cluster_id: str,
    out: Path,
) -> Path:
    """Freeze a consolidation's manifest under its own root.

    A consolidation belongs to no new cluster, so it cannot reuse
    :func:`write_checkpoint`, which resolves ``out / cluster_id`` and requires
    the id to appear in the timeline. It lands at ``out/<NN>`` instead, leaving
    the cluster checkpoint root to cluster rounds alone (D48).

    Args:
        manifest_path: The consolidation's manifest.
        ordinal: The consolidation's number; the directory is two digits.
        base_checkpoint: The cluster checkpoint this consolidation follows.
        cluster_id: The cluster the base checkpoint belongs to.
        out: The consolidations root.

    Returns:
        The directory written.

    Raises:
        CheckpointError: If the base is unreadable, or the manifest changes any
            requirement rather than only its structures.
    """
    manifest = load(manifest_path)
    base_manifest_path = base_checkpoint / MANIFEST_FILE
    if not base_manifest_path.is_file():
        raise CheckpointError(f"{base_checkpoint}: no {MANIFEST_FILE} to consolidate from")
    base = load(base_manifest_path)
    if requirements_digest(manifest) != requirements_digest(base):
        raise CheckpointError(
            f"consolidation {ordinal:02d}: requirements differ from "
            f"{base_checkpoint.name}; a consolidation may change only structures"
        )
    manifest_text = dump(manifest)
    structures_text = render_all(manifest) if manifest.structures else ""
    record = {
        "base_checkpoint": base_checkpoint.name,
        "cluster_id": cluster_id,
        "kind": "consolidation",
        "manifest_sha256": _digest_bytes(manifest_text.encode()),
        "ordinal": ordinal,
    }
    if structures_text:
        record["structures_sha256"] = _digest_bytes(structures_text.encode())

    checkpoint_dir = out / f"{ordinal:02d}"
    checkpoint_dir.mkdir(parents=True)
    (checkpoint_dir / MANIFEST_FILE).write_text(manifest_text)
    if structures_text:
        (checkpoint_dir / STRUCTURES_FILE).write_text(structures_text)
    (checkpoint_dir / CHECKPOINT_FILE).write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n"
    )
    return checkpoint_dir
```

Every read and every digest precedes the `mkdir`, exactly as `write_checkpoint` does since `21aa06fdc`.

- [ ] **Step 5: Teach `verify_checkpoint` about the second file**

In `verify_checkpoint`, after the existing `manifest.yaml` comparison (re-anchor with `grep -n "def verify_checkpoint"`):

```python
    expected = record.get("structures_sha256")
    frozen = checkpoint_dir / STRUCTURES_FILE
    if expected is None:
        if frozen.exists():
            return f"{checkpoint_dir.name}: {STRUCTURES_FILE} is present but unrecorded"
    else:
        if not frozen.is_file():
            return f"{checkpoint_dir.name}: {STRUCTURES_FILE} is recorded but missing"
        if _digest_bytes(frozen.read_bytes()) != expected:
            return (
                f"{checkpoint_dir.name}: {STRUCTURES_FILE} does not match the "
                f"digest recorded in {CHECKPOINT_FILE}"
            )
```

- [ ] **Step 6: Run the checkpoint suite**

Run: `cd $AIRFC && SSLKEYLOGFILE= $PY -m pytest tests/substrate/draft/test_checkpoint.py -v`
Expected: all PASS, including the pre-existing `test_two_checkpoints_of_same_manifest_are_byte_identical`.

- [ ] **Step 7: Prove the other three readers are untouched**

D48 requires that `pipeline/state.py`, `completeness.py` and the server's `queries.py` keep enumerating cluster checkpoints only. They are not edited by this plan; confirm nothing regressed:

```bash
cd $AIRFC && SSLKEYLOGFILE= $PY -m pytest tests/substrate/pipeline tests/substrate/test_completeness.py -n auto 2>&1 | tail -3
cd $AIRFC && grep -rn "checkpoints" ai_rfc/pipeline/state.py ai_rfc/completeness.py ai_rfc/server/core/queries.py
```

Expected: green, and each grep shows the same cluster-root enumeration it had before this task.

- [ ] **Step 8: Lint, type-check and commit**

```bash
cd $AIRFC && $PY -m black ai_rfc/draft/checkpoint.py tests/substrate/draft/test_checkpoint.py
cd $AIRFC && $PY -m flake8 --max-line-length=88 ai_rfc/draft/checkpoint.py tests/substrate/draft/test_checkpoint.py
cd $AIRFC && $PY -m mypy --follow-imports=silent ai_rfc/draft/checkpoint.py
cd $AIRFC && git status --short
git add ai_rfc/draft/checkpoint.py tests/substrate/draft/test_checkpoint.py
git commit -m "feat: freeze the structure rendering and give consolidations their own root"
```

---

### Task 5: The gate ties every block back to the frozen bytes

**Files:**
- Modify: `ai_rfc/draft/gate.py`
- Test: `tests/substrate/draft/test_gate.py`

**Interfaces:**
- Consumes: `draft.structures.{parse_blocks, STRUCTURES_FILE}` (Task 2); `draft.checkpoint.requirements_digest` (Task 4); `gate.draft_text` (**C1**); the existing `RevisionEntry` / `run_gate` shapes (**C18**, **C19**).
- Produces: `RevisionEntry.kind: str = "cluster"` and `RevisionEntry.checkpoint: str | None = None`; `run_gate(..., consolidations_dir: Path | None = None)`; the four spec checks 8–11.

**Why this shape.** `RevisionEntry` is frozen with six required fields (**C18**); the two new ones carry defaults and go last, so every existing construction site keeps working and an old `revisions.yaml` without `kind` still loads. `run_gate`'s five parameters have no defaults (**C19**), so `consolidations_dir` is added last with a default of `None`, resolved to the sibling of `checkpoints_dir` — every existing caller keeps its signature.

The checks are the spec's 8–11 by number, but the gate holds **no in-code numbering** (**C19**) and this task does not introduce one; the numbers live in the spec and in this plan's prose only. Findings keep the existing `f"{tag}: {reason}"` shape.

Checks 9–11 read blocks through `parse_blocks` (Task 2) rather than matching their own pattern, so the gate and the lint cannot disagree about what a block is.

- [ ] **Step 1: Write the failing tests**

Append to `tests/substrate/draft/test_gate.py`:

```python
def test_an_old_revisions_file_still_loads_as_cluster_rounds(tmp_path):
    path = tmp_path / "revisions.yaml"
    path.write_text(
        "revisions:\n"
        "  draft-test-01:\n"
        "    cluster_id: c1\n"
        "    checkpoint_manifest_sha256: " + "a" * 64 + "\n"
        "    normative_change: true\n"
        "    note: first\n"
    )
    entry = load_revisions(path)[0]
    assert entry.kind == "cluster"
    assert entry.checkpoint is None


def test_a_consolidation_entry_must_name_its_checkpoint(tmp_path):
    path = tmp_path / "revisions.yaml"
    path.write_text(
        "revisions:\n"
        "  draft-test-01:\n"
        "    cluster_id: c1\n"
        "    checkpoint_manifest_sha256: " + "a" * 64 + "\n"
        "    normative_change: false\n"
        "    note: consolidated\n"
        "    kind: consolidation\n"
    )
    with pytest.raises(GateError) as error:
        load_revisions(path)
    assert "checkpoint" in str(error.value)


def test_a_cluster_entry_may_not_name_a_consolidation_checkpoint(tmp_path):
    path = tmp_path / "revisions.yaml"
    path.write_text(
        "revisions:\n"
        "  draft-test-01:\n"
        "    cluster_id: c1\n"
        "    checkpoint_manifest_sha256: " + "a" * 64 + "\n"
        "    normative_change: true\n"
        "    note: first\n"
        "    checkpoint: consolidations/01\n"
    )
    with pytest.raises(GateError) as error:
        load_revisions(path)
    assert "only a consolidation" in str(error.value)


def test_an_unknown_kind_is_refused(tmp_path):
    path = tmp_path / "revisions.yaml"
    path.write_text(
        "revisions:\n"
        "  draft-test-01:\n"
        "    cluster_id: c1\n"
        "    checkpoint_manifest_sha256: " + "a" * 64 + "\n"
        "    normative_change: true\n"
        "    note: first\n"
        "    kind: editorial\n"
    )
    with pytest.raises(GateError) as error:
        load_revisions(path)
    assert "editorial" in str(error.value)


def test_a_block_naming_no_frozen_structure_is_a_finding(structured_workspace):
    # Check 9.
    ws = structured_workspace
    _append_to_draft(ws, "{::comment}\nai_rfc:struct:ghost begin\n{:/comment}\nx\n"
                         "{::comment}\nai_rfc:struct:ghost end\n{:/comment}\n")
    findings = run_gate(ws["repo"], ws["timeline"], ws["checkpoints"], ws["questions"], ws["revisions"])
    assert any("ghost" in f and "not a structure" in f for f in findings)


def test_a_one_byte_edit_to_a_rendered_block_is_a_finding(structured_workspace):
    # Check 10 — the property the whole design rests on.
    ws = structured_workspace
    _retag_draft_with(ws, lambda text: text.replace("uint8", "uint9"))
    findings = run_gate(ws["repo"], ws["timeline"], ws["checkpoints"], ws["questions"], ws["revisions"])
    assert any("does not match the frozen" in f for f in findings)


def test_an_untouched_structured_draft_gates_clean(structured_workspace):
    ws = structured_workspace
    assert run_gate(ws["repo"], ws["timeline"], ws["checkpoints"], ws["questions"], ws["revisions"]) == ()


def test_a_malformed_delimiter_is_a_finding(structured_workspace):
    # Check 11.
    ws = structured_workspace
    _retag_draft_with(
        ws, lambda text: text + "{::comment}\nai_rfc:struct:orphan end\n{:/comment}\n"
    )
    findings = run_gate(ws["repo"], ws["timeline"], ws["checkpoints"], ws["questions"], ws["revisions"])
    assert any("closed but never opened" in f for f in findings)


def test_a_consolidation_whose_requirements_moved_is_a_finding(consolidated_workspace):
    # Check 8.
    ws = consolidated_workspace
    target = ws["consolidations"] / "01" / "manifest.yaml"
    target.write_text(target.read_text().replace("level: MUST", "level: MAY"))
    findings = run_gate(
        ws["repo"], ws["timeline"], ws["checkpoints"], ws["questions"], ws["revisions"],
        consolidations_dir=ws["consolidations"],
    )
    assert any("requirements" in f for f in findings)


def test_the_first_revision_may_not_be_a_consolidation(consolidated_workspace):
    # The fixture writes no `kind:` on the first entry (it defaults to cluster),
    # so make it one by appending the two keys to that entry's block.
    ws = consolidated_workspace
    ws["revisions"].write_text(
        ws["revisions"].read_text().replace(
            "    note: 'initial reconstruction'\n",
            "    note: 'initial reconstruction'\n"
            "    kind: consolidation\n"
            "    checkpoint: consolidations/01\n",
        )
    )
    findings = run_gate(
        ws["repo"], ws["timeline"], ws["checkpoints"], ws["questions"], ws["revisions"],
        consolidations_dir=ws["consolidations"],
    )
    assert any("cannot be a consolidation" in f for f in findings)
```

- [ ] **Step 2: Add the two fixtures the tests need**

Append to `tests/substrate/draft/conftest.py`. These build on the existing `draft_workspace` (**C28**) rather than duplicating it:

```python
STRUCTURED_BLOCK = (
    "structures:\n"
    "  header:\n"
    "    kind: record\n"
    "    title: Message header\n"
    "    section: '4'\n"
    "    fields:\n"
    "      - name: version\n"
    "        type: uint8\n"
    "        claim: spec:1.1\n"
)


@pytest.fixture
def consolidated_workspace(structured_workspace, tmp_path):
    """`structured_workspace` plus one consolidation revision after it."""
    from ai_rfc.draft.checkpoint import write_consolidation_checkpoint

    workspace = structured_workspace
    consolidations = tmp_path / "consolidations"
    base = workspace["last_checkpoint"]
    write_consolidation_checkpoint(
        base / "manifest.yaml", 1, base, workspace["last_cluster"], consolidations
    )
    workspace["consolidations"] = consolidations
    _record_consolidation(workspace, ordinal=2, checkpoint="consolidations/01")
    return workspace
```

**Promote the existing fixture body first.** `draft_workspace` currently builds everything inline. Turn its body into a plain function with one added parameter and leave the fixture as a two-line caller, so every existing test is untouched:

```python
def _build_draft_workspace(tmp_path, timeline_dir, extra=""):
    """The `draft_workspace` body, with an optional extra manifest block.

    This is the existing fixture's code verbatim except for two changes, both
    marked below: the second manifest gains `extra`, and the returned mapping
    names the last checkpoint and cluster so a consolidation can be built on it.
    """
    ...  # every line of today's draft_workspace body, up to the return, with:
    #   second_manifest.write_text(_manifest_text(with_second_claim=True) + extra)
    return {
        "repo": repo,
        "timeline": timeline_dir,
        "checkpoints": checkpoints,
        "questions": questions,
        "revisions": revisions,
        "last_checkpoint": second_checkpoint,   # new, additive
        "last_cluster": pr_id,                  # new, additive
    }


@pytest.fixture
def draft_workspace(tmp_path: Path, timeline_dir: Path) -> dict[str, Path]:
    """A gate-clean workspace: draft repo, checkpoints, questions, revisions."""
    return _build_draft_workspace(tmp_path, timeline_dir)
```

The two new mapping keys are additive; every existing test indexes by name, so none sees a change.

The three helpers the tests above use, in full. The draft file is `draft-test-spec.md` and the last tag is `draft-test-spec-01`, both fixed by the fixture, so neither needs discovering:

```python
def _retag_draft_with(workspace, transform):
    """Rewrite the draft, commit, and move the last tag onto the new commit."""
    repo = workspace["repo"]
    draft_file = repo / "draft-test-spec.md"
    draft_file.write_text(transform(draft_file.read_text()))
    git(repo, "add", "draft-test-spec.md")
    git(repo, "commit", "-m", "edit")
    git(repo, "tag", "-f", "draft-test-spec-01")
    return repo


def _append_to_draft(workspace, text):
    return _retag_draft_with(workspace, lambda body: body + "\n" + text)


def _record_consolidation(workspace, ordinal, checkpoint):
    """Append one consolidation revision and tag the current HEAD."""
    directory = workspace["consolidations"] / Path(checkpoint).name
    sha = json.loads((directory / "checkpoint.json").read_text())["manifest_sha256"]
    tag = f"draft-test-spec-{ordinal:02d}"
    workspace["revisions"].write_text(
        workspace["revisions"].read_text()
        + f"  {tag}:\n"
        f"    cluster_id: {workspace['last_cluster']}\n"
        f"    checkpoint_manifest_sha256: {sha}\n"
        "    normative_change: false\n"
        "    note: 'consolidated'\n"
        "    kind: consolidation\n"
        f"    checkpoint: {checkpoint}\n"
    )
    git(workspace["repo"], "tag", tag)
    return tag
```

Add `import json` and `from pathlib import Path` at the top of `conftest.py` if they are not already there. `structured_workspace` writes into `draft-test-spec.md` and re-tags `draft-test-spec-01` the same way `_retag_draft_with` does — use that helper rather than repeating the git calls:

```python
@pytest.fixture
def structured_workspace(tmp_path, timeline_dir):
    """A workspace whose last checkpoint freezes one structure block, pasted."""
    from ai_rfc.draft.structures import render_all
    from ai_rfc.schema import load as load_manifest

    workspace = _build_draft_workspace(tmp_path, timeline_dir, extra=STRUCTURED_BLOCK)
    manifest = load_manifest(workspace["last_checkpoint"] / "manifest.yaml")
    _retag_draft_with(workspace, lambda body: body + "\n" + render_all(manifest))
    return workspace
```

Replace the two placeholder fixtures sketched earlier in this step with this one.

- [ ] **Step 3: Run them to verify they fail**

Run: `cd $AIRFC && SSLKEYLOGFILE= $PY -m pytest tests/substrate/draft/test_gate.py -k "kind or consolidat or block or frozen or delimiter" -v`
Expected: FAIL — `RevisionEntry` has no `kind`, and `run_gate` takes no `consolidations_dir`.

- [ ] **Step 4: Extend the entry and its loader**

In `ai_rfc/draft/gate.py`, add the two defaulted fields **last** on `RevisionEntry` (re-anchor with `grep -n "class RevisionEntry"`):

```python
    kind: str = "cluster"
    checkpoint: str | None = None
```

and add a constant beside `REVISION_TAG`:

```python
REVISION_KINDS = ("cluster", "consolidation")
```

In `load_revisions`, after the existing `note` read (re-anchor with `grep -n "def load_revisions"`):

```python
        kind = body.get("kind", "cluster")
        if kind not in REVISION_KINDS:
            raise GateError(
                f"{tag}: kind is {kind!r}; permitted values are {list(REVISION_KINDS)}"
            )
        checkpoint = body.get("checkpoint")
        if kind == "consolidation" and not checkpoint:
            raise GateError(f"{tag}: a consolidation must name its checkpoint")
        if kind != "consolidation" and checkpoint:
            raise GateError(f"{tag}: only a consolidation may name a checkpoint")
```

and pass `kind=kind, checkpoint=checkpoint` to the `RevisionEntry(...)` construction.

- [ ] **Step 5: Resolve a checkpoint directory in one place**

Add to `ai_rfc/draft/gate.py`:

```python
def _checkpoint_dir(entry: RevisionEntry, checkpoints_dir: Path, consolidations_dir: Path) -> Path:
    """Where this revision's checkpoint lives.

    Cluster rounds resolve under the cluster root; consolidations name their own
    directory under a separate root, so the cluster root keeps enumerating
    cluster checkpoints only (D48).
    """
    if entry.kind == "consolidation" and entry.checkpoint:
        return consolidations_dir / Path(entry.checkpoint).name
    return checkpoints_dir / entry.cluster_id
```

Change `run_gate`'s signature to add the new parameter last, defaulting to the sibling root:

```python
def run_gate(
    draft_repo: Path,
    timeline_dir: Path,
    checkpoints_dir: Path,
    questions_path: Path,
    revisions_path: Path,
    consolidations_dir: Path | None = None,
) -> tuple[str, ...]:
```

and near the top of its body:

```python
    consolidations_dir = consolidations_dir or checkpoints_dir.parent / "consolidations"
```

Then replace the single `checkpoint_dir = checkpoints_dir / entry.cluster_id` with a call to `_checkpoint_dir(entry, checkpoints_dir, consolidations_dir)`, so all four existing lookups (`checkpoint.json`, `manifest.yaml`, the digest comparison, `verify_checkpoint`) follow it.

- [ ] **Step 6: Add checks 8–11**

Inside `run_gate`'s per-entry loop, after the existing checkpoint comparisons:

```python
        # Spec check 8: a consolidation follows its base and changes only structures.
        # `record` is the checkpoint.json the loop already parsed for the
        # manifest-digest comparison; do not re-read it.
        if entry.kind == "consolidation":
            if previous is None:
                findings.append(f"{entry.tag}: the first revision cannot be a consolidation")
            else:
                if record.get("kind") != "consolidation":
                    findings.append(
                        f"{entry.tag}: {entry.checkpoint} is not a consolidation checkpoint"
                    )
                if record.get("cluster_id") != previous.cluster_id:
                    findings.append(
                        f"{entry.tag}: consolidates {record.get('cluster_id')!r} but "
                        f"follows {previous.cluster_id!r}"
                    )
                base_dir = _checkpoint_dir(previous, checkpoints_dir, consolidations_dir)
                if requirements_digest(load(checkpoint_dir / MANIFEST_FILE)) != (
                    requirements_digest(load(base_dir / MANIFEST_FILE))
                ):
                    findings.append(
                        f"{entry.tag}: requirements differ from {previous.tag}; a "
                        f"consolidation may change only structures"
                    )

        # Spec checks 9-11: every delimited block matches the frozen rendering.
        frozen_path = checkpoint_dir / STRUCTURES_FILE
        frozen, _ = parse_blocks(frozen_path.read_text()) if frozen_path.is_file() else ({}, ())
        bodies, malformed = parse_blocks(text)
        for finding in malformed:
            findings.append(f"{entry.tag}: {finding}")
        for structure_id, body in sorted(bodies.items()):
            if structure_id not in frozen:
                findings.append(
                    f"{entry.tag}: {structure_id} is not a structure frozen in this "
                    f"revision's checkpoint"
                )
            elif body != frozen[structure_id]:
                findings.append(
                    f"{entry.tag}: the {structure_id} block does not match the frozen "
                    f"rendering in {STRUCTURES_FILE}"
                )
```

Three details the loop needs, none of which exists today:

```python
    # Before the loop, beside `claim_ids_by_tag`:
    previous: RevisionEntry | None = None
    ...
    for entry in entries:
        ...
        # As the LAST statement of the loop body. The `continue` taken when a
        # checkpoint is missing deliberately leaves `previous` unchanged: a
        # revision with no checkpoint is not a valid base for a consolidation.
        previous = entry
```

`text` is the draft source at the tag. `cited_ids` reads that blob already; after SP7a it does so through `draft_text` (**C1**), so hoist one `_, text = draft_text(draft_repo, entry.tag)` above the checks and pass the text into `cited_ids` instead of letting it read again — one read, one parse. If the hoist turns out to change `cited_ids`'s signature more than a keyword, leave `cited_ids` alone and call `draft_text` once here; two reads of the same immutable blob are wasteful but not wrong, whereas two *parsers* would be.

Import `parse_blocks` and `STRUCTURES_FILE` from `.structures`, `requirements_digest` from `.checkpoint`, and `load` from `ai_rfc.schema`. `json` and `CHECKPOINT_FILE`/`MANIFEST_FILE` are already imported by this module.

- [ ] **Step 7: Run the gate suite**

Run: `cd $AIRFC && SSLKEYLOGFILE= $PY -m pytest tests/substrate/draft/test_gate.py -v`
Expected: all PASS. Every pre-existing gate test must still pass unchanged — if one fails, the defaulted fields or the resolver changed behaviour for cluster rounds, which they must not.

- [ ] **Step 8: Lint, type-check and commit**

```bash
cd $AIRFC && $PY -m black ai_rfc/draft/gate.py tests/substrate/draft/test_gate.py tests/substrate/draft/conftest.py
cd $AIRFC && $PY -m flake8 --max-line-length=88 ai_rfc/draft/gate.py tests/substrate/draft/test_gate.py
cd $AIRFC && $PY -m mypy --follow-imports=silent ai_rfc/draft/gate.py
cd $AIRFC && SSLKEYLOGFILE= $PY -m pytest tests -n auto 2>&1 | tail -3
cd $AIRFC && git status --short
git add ai_rfc/draft/gate.py tests/substrate/draft/test_gate.py tests/substrate/draft/conftest.py
git commit -m "feat: gate every rendered structure block against its frozen bytes"
```

---

### Task 6: Three substrate verbs — `render`, and two new flags

**Files:**
- Modify: `ai_rfc/draft/cli.py`, `ai_rfc/entrypoints.py`
- Test: `tests/substrate/draft/test_cli.py`

**Interfaces:**
- Consumes: `draft.structures.{render_all, STRUCTURES_FILE}` (Task 2); `draft.checkpoint.write_consolidation_checkpoint` (Task 4); `draft.gate.run_gate(consolidations_dir=…)` (Task 5); the argparse pattern in **C5**.
- Produces: `ai-rfc draft render MANIFEST [--out DIR]`; `ai-rfc draft checkpoint … --consolidation NN --base DIR`; `ai-rfc draft gate … --consolidations DIR`.

> **The hazard in this file.** `gate` is the **unguarded bottom fallthrough** of the dispatch (**C5**): a verb registered in the parser without its own `if args.verb == …` branch placed *before* the gate code runs gate's body and dies on `AttributeError`. Register and dispatch `render` in the same step, and put its branch above the fallthrough. The first test below exists to catch exactly this.

The substrate needs `--consolidation` before the server can offer it, because the server's checkpoint core shells out to this CLI (**C24**).

- [ ] **Step 1: Write the failing tests**

Append to `tests/substrate/draft/test_cli.py`:

```python
def test_render_prints_the_blocks_and_does_not_fall_through_to_gate(tmp_path, capsys):
    path = tmp_path / "m.yaml"
    path.write_text(_manifest_text(with_second_claim=True) + STRUCTURED_BLOCK)
    assert main(["render", str(path)]) == 0
    printed = capsys.readouterr().out
    assert "ai_rfc:struct:header begin" in printed
    assert "gate-report.json" not in printed


def test_render_can_also_write_the_file(tmp_path, capsys):
    from ai_rfc.draft.structures import STRUCTURES_FILE

    path = tmp_path / "m.yaml"
    path.write_text(_manifest_text(with_second_claim=True) + STRUCTURED_BLOCK)
    out = tmp_path / "out"
    assert main(["render", str(path), "--out", str(out)]) == 0
    capsys.readouterr()
    assert "ai_rfc:struct:header begin" in (out / STRUCTURES_FILE).read_text()


def test_render_of_a_structure_free_manifest_prints_nothing_and_succeeds(tmp_path, capsys):
    path = tmp_path / "m.yaml"
    path.write_text(_manifest_text())
    assert main(["render", str(path)]) == 0
    assert capsys.readouterr().out.strip() == ""


def test_checkpoint_writes_a_consolidation_when_asked(tmp_path, timeline_dir, capsys):
    path = tmp_path / "m.yaml"
    path.write_text(_manifest_text(with_second_claim=True) + STRUCTURED_BLOCK)
    checkpoints = tmp_path / "checkpoints"
    assert main([
        "checkpoint", str(path), "--timeline", str(timeline_dir),
        "--cluster", "c1", "--out", str(checkpoints),
    ]) == 0
    consolidations = tmp_path / "consolidations"
    assert main([
        "checkpoint", str(path), "--timeline", str(timeline_dir), "--cluster", "c1",
        "--out", str(consolidations), "--consolidation", "1",
        "--base", str(checkpoints / "c1"),
    ]) == 0
    capsys.readouterr()
    assert (consolidations / "01" / "checkpoint.json").is_file()


def test_consolidation_requires_a_base(tmp_path, timeline_dir, capsys):
    path = tmp_path / "m.yaml"
    path.write_text(_manifest_text())
    assert main([
        "checkpoint", str(path), "--timeline", str(timeline_dir), "--cluster", "c1",
        "--out", str(tmp_path / "c"), "--consolidation", "1",
    ]) == 2
    assert "--base" in capsys.readouterr().err
```

Import `STRUCTURED_BLOCK` from the suite's `conftest` (added in Task 5 Step 2).

- [ ] **Step 2: Run them to verify they fail**

Run: `cd $AIRFC && SSLKEYLOGFILE= $PY -m pytest tests/substrate/draft/test_cli.py -k "render or consolidation" -v`
Expected: FAIL — argparse rejects the unknown verb `render` with `SystemExit: 2`.

- [ ] **Step 3: Register the verb and its two flags**

In `ai_rfc/draft/cli.py`'s `_parser()` (re-anchor with `grep -n "add_subparsers"`), following the `checkpoint` verb's shape (**C5**):

```python
    render = verbs.add_parser("render", help="Render a manifest's structures as kramdown blocks.")
    render.add_argument("manifest", type=Path, help="Manifest to render.")
    render.add_argument(
        "--out", type=Path, default=None, help="Also write structures.md into this directory."
    )
```

and on the existing `checkpoint` parser:

```python
    checkpoint.add_argument(
        "--consolidation", type=int, default=None,
        help="Write a consolidation checkpoint with this ordinal instead of a cluster one.",
    )
    checkpoint.add_argument(
        "--base", type=Path, default=None,
        help="The cluster checkpoint a consolidation follows. Required with --consolidation.",
    )
```

and on the existing `gate` parser:

```python
    gate.add_argument(
        "--consolidations", type=Path, default=None,
        help="Consolidation checkpoint root. Default: the sibling of --checkpoints.",
    )
```

- [ ] **Step 4: Dispatch it above the fallthrough**

In `main()`, **before** the gate code at the bottom (re-anchor with `grep -n "args.verb =="`; place this beside the other `if` branches):

```python
    if args.verb == "render":
        try:
            text = render_all(load(args.manifest))
        except (SchemaError, OSError) as error:
            _report(f"error: {error}")
            return 1
        if text:
            print(text, end="")
        if args.out is not None:
            args.out.mkdir(parents=True, exist_ok=True)
            (args.out / STRUCTURES_FILE).write_text(text)
        return 0
```

Extend the `checkpoint` branch to route on the new flag:

```python
    if args.verb == "checkpoint":
        if args.consolidation is not None and args.base is None:
            _report("error: --consolidation requires --base")
            return 2
        try:
            if args.consolidation is not None:
                checkpoint_dir = write_consolidation_checkpoint(
                    args.manifest, args.consolidation, args.base, args.cluster, args.out
                )
            else:
                checkpoint_dir = write_checkpoint(
                    args.manifest, args.timeline, args.cluster, args.out
                )
        except (CheckpointError, SchemaError, OSError) as error:
            _report(f"error: {error}")
            return 1
        _report(f"note: checkpoint written to {checkpoint_dir}")
        return 0
```

and pass the new root through to the gate: `run_gate(..., consolidations_dir=args.consolidations)`.

`--consolidation` without `--base` returns **2** and reports through `_report` (which writes to stderr, as the module's other error paths do). Two flags cannot be made mutually required by argparse alone, so the check is in the branch; returning rather than raising keeps `main`'s contract "an int is the exit code", which the rest of the dispatch already follows.

- [ ] **Step 5: Check the registry**

`entrypoints.py` was untouched by SP7a (**C10**), so read its landed shape before deciding whether a new *sub*verb needs registering there — it lists top-level entry points, and `render` is a subverb of `draft`, which is already registered:

```bash
cd $AIRFC && grep -n "draft" ai_rfc/entrypoints.py
```

If `draft` appears as one entry, no change is needed; say so in the commit message. If the registry enumerates subverbs, add `render` alongside the others.

- [ ] **Step 6: Run the CLI suite and commit**

Run: `cd $AIRFC && SSLKEYLOGFILE= $PY -m pytest tests/substrate/draft/test_cli.py -v`
Expected: all PASS.

```bash
cd $AIRFC && $PY -m black ai_rfc/draft/cli.py tests/substrate/draft/test_cli.py
cd $AIRFC && $PY -m flake8 --max-line-length=88 ai_rfc/draft/cli.py tests/substrate/draft/test_cli.py
cd $AIRFC && $PY -m mypy --follow-imports=silent ai_rfc/draft/cli.py
cd $AIRFC && git status --short
git add ai_rfc/draft/cli.py tests/substrate/draft/test_cli.py
git commit -m "feat: render structures from the CLI and checkpoint a consolidation"
```

---

### Task 7: Four surfaces, each with its verb, its row and its twin

**Files:**
- Create: `ai_rfc/server/core/structures.py`
- Modify: `ai_rfc/server/tools.py`, `ai_rfc/server/cli.py`, `ai_rfc/server/core/revisions.py`, `ai_rfc/server/core/gates.py`, `docs/parity.md`
- Test: `tests/server/test_parity.py`, `tests/server/test_structures.py`, `tests/server/test_revisions.py`

**Interfaces:**
- Consumes: everything above; the "one core, two frontends" pattern and every asymmetry in **C22**–**C27**.
- Produces: tools `ai_rfc_structure_upsert`, `ai_rfc_draft_render`; `record_revision(..., kind="cluster", checkpoint=None)`; the server's checkpoint core gains `consolidation`/`base`; `ALL_TOOLS` grows from 18 to **20**; two new `parity.md` rows; two new twins.

**Why this ordering.** The server persists a manifest write by round-tripping it through `schema.load`/`schema.dump` (**C22**), so before Task 1 landed, anything written under `structures:` was destroyed on the next write. That is why this task is seventh and not first.

Three asymmetries this task must respect rather than discover:

- `draft_render` returns a **string**, so its CLI branch uses `print(...)`, not `_emit(...)` — `_emit` JSON-serialises and would wrap markdown in quotes (**C25**).
- `question_export` has **no** parity twin (**C26**). That is a gap, not a pattern: both new tools get one.
- A new core module must be added to **two** import sites — the module-level import in `tools.py` and the deferred import inside `cli.py`'s dispatch (**C25**). Missing one leaves the tool unreachable from that arm with no error at import time.

D42 freezes the raw arm C at its current surface, so both new rows carry an em dash in the third column with the reason in parentheses (**C27**).

- [ ] **Step 1: Write the failing tests**

Create `tests/server/test_structures.py`:

```python
"""The structure_upsert and draft_render cores."""

from __future__ import annotations

import pytest

from ai_rfc_server import tools
from ai_rfc_server.core import structures

pytestmark = pytest.mark.unit

FIELDS = {
    "kind": "record",
    "title": "Message header",
    "section": "4",
    "fields": [{"name": "version", "type": "uint8", "claim": "spec:1.1"}],
}


def test_a_structure_survives_the_manifest_round_trip(workspace):
    structures.upsert_structure(workspace, "header", FIELDS)
    text = workspace.manifest.read_text()
    assert "structures:" in text
    # The write path round-trips through schema.load/dump; a key the schema did
    # not know would be silently dropped here.
    structures.upsert_structure(workspace, "header", FIELDS)
    assert "header" in workspace.manifest.read_text()


def test_a_structure_binding_an_unknown_claim_is_refused(workspace):
    from ai_rfc_server.core import CoreError

    with pytest.raises(CoreError):
        structures.upsert_structure(
            workspace, "ghost", {**FIELDS, "fields": [{"name": "a", "claim": "spec:9.9"}]}
        )


def test_render_returns_the_blocks_as_text(workspace):
    structures.upsert_structure(workspace, "header", FIELDS)
    text = structures.render_structures(workspace)
    assert text.startswith("{::comment}")
    assert "ai_rfc:struct:header begin" in text


def test_the_tool_wrappers_reach_the_cores(workspace, monkeypatch):
    tools.ai_rfc_structure_upsert("header", FIELDS)
    assert "ai_rfc:struct:header begin" in tools.ai_rfc_draft_render()
```

Append to `tests/server/test_parity.py`, adding `import json` to the module's existing imports and
defining the body locally rather than importing it across test modules:

```python
FIELDS = {
    "kind": "record",
    "title": "Message header",
    "section": "4",
    "fields": [{"name": "version", "type": "uint8", "claim": "spec:1.1"}],
}


def test_structure_upsert_parity(make_workspace, capsys):
    tool_arm, cli_arm, use = _twins(make_workspace)
    use(tool_arm)
    tools.ai_rfc_structure_upsert("header", FIELDS)
    use(cli_arm)
    assert cli.main(["structure-upsert", "header", "--json", json.dumps(FIELDS)]) == 0
    capsys.readouterr()
    assert (tool_arm / "manifest.yaml").read_bytes() == (cli_arm / "manifest.yaml").read_bytes()


def test_draft_render_parity(make_workspace, capsys):
    tool_arm, cli_arm, use = _twins(make_workspace)
    use(tool_arm)
    tools.ai_rfc_structure_upsert("header", FIELDS)
    from_tool = tools.ai_rfc_draft_render()
    use(cli_arm)
    tools.ai_rfc_structure_upsert("header", FIELDS)
    assert cli.main(["draft-render"]) == 0
    from_cli = capsys.readouterr().out
    # print() adds no quotes; _emit would have.
    assert not from_cli.lstrip().startswith('"')
    assert from_cli.strip() == from_tool.strip()


def test_every_tool_still_appears_in_the_table():
    # ALL_TOOLS grew to 20; the table must have kept up.
    assert len(tools.ALL_TOOLS) == 20
```

Append to `tests/server/test_revisions.py`:

```python
def test_a_consolidation_revision_records_its_kind_and_checkpoint(workspace):
    from ai_rfc_server.core import revisions

    revisions.record_revision(workspace, "draft-test-01", "c1", True, "first")
    entry = revisions.record_revision(
        workspace, "draft-test-02", "c1", False, "consolidated",
        kind="consolidation", checkpoint="consolidations/01",
    )
    assert entry["kind"] == "consolidation"
    assert entry["checkpoint"] == "consolidations/01"


def test_a_cluster_may_not_be_recorded_twice(workspace):
    from ai_rfc_server.core import CoreError, revisions

    revisions.record_revision(workspace, "draft-test-01", "c1", True, "first")
    with pytest.raises(CoreError) as error:
        revisions.record_revision(workspace, "draft-test-02", "c1", True, "again")
    assert "already has a cluster revision" in str(error.value)
```

- [ ] **Step 2: Run them to verify they fail**

Run: `cd $AIRFC && SSLKEYLOGFILE= $PY -m pytest tests/server -k "structure or render or consolidation or twice" -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'ai_rfc_server.core.structures'`.

- [ ] **Step 3: Write the core**

Create `ai_rfc/server/core/structures.py`, mirroring `claims.upsert_claim`'s persistence path (**C22**):

```python
"""Declare and render manifest structures."""

from __future__ import annotations

from typing import Any

from ai_rfc.draft.structures import render_all
from ai_rfc.schema import SchemaError, load

from . import CoreError
from .claims import _document, _normalize_and_write
from ..paths import Context

_REQUIRED = ("kind", "title", "section")


def upsert_structure(ctx: Context, structure_id: str, fields: dict[str, Any]) -> dict[str, Any]:
    """Create or replace one structure in the manifest.

    Args:
        ctx: The resolved workspace.
        structure_id: The structure's id.
        fields: Its body — ``kind``, ``title``, ``section`` and the members its
            kind requires.

    Returns:
        The stored structure body.

    Raises:
        CoreError: If a required field is missing, or the schema refuses the
            result — which is where an unknown bound claim is caught.
    """
    missing = [key for key in _REQUIRED if key not in fields]
    if missing:
        raise CoreError(f"{structure_id}: missing required field(s) {', '.join(missing)}")
    document = _document(ctx)
    document.setdefault("structures", {})[structure_id] = dict(fields)
    try:
        _normalize_and_write(ctx, document)
    except SchemaError as error:
        raise CoreError(str(error)) from error
    # Return what was actually stored, re-read after the round trip, exactly as
    # upsert_claim does — the write normalises, so the input is not the record.
    return dict(_document(ctx)["structures"][structure_id])


def render_structures(ctx: Context) -> str:
    """Render every declared structure as delimited kramdown blocks.

    Args:
        ctx: The resolved workspace.

    Returns:
        The blocks, ready to paste into the draft. Empty when none are declared.
    """
    return render_all(load(ctx.manifest))
```

> `_document` and `_normalize_and_write` are private to `claims.py` today. Import them as above only if a grep confirms they are module-level and side-effect-free; if `claims.py` has since made them closures or methods, promote them to a shared `_manifest.py` in the same commit rather than duplicating the write path — two writers of one file is the bug class this whole plan exists to prevent.

- [ ] **Step 4: Thread `kind` through `record_revision`, with the guardrail**

In `ai_rfc/server/core/revisions.py`, extend the signature with two defaulted keywords and add the entry keys (re-anchor with `grep -n "def record_revision"`):

```python
def record_revision(
    ctx: Context,
    tag: str,
    cluster_id: str,
    normative_change: bool,
    note: str,
    kind: str = "cluster",
    checkpoint: str | None = None,
) -> dict[str, Any]:
```

Before writing, refuse a second cluster entry for one cluster — a cluster round happens once, and a silent second entry is how a sweep double-counts:

```python
    if kind == "cluster":
        for existing in load_revisions(ctx.revisions) if ctx.revisions.is_file() else ():
            if existing.kind == "cluster" and existing.cluster_id == cluster_id:
                raise CoreError(
                    f"{cluster_id} already has a cluster revision ({existing.tag}); "
                    f"a consolidation needs kind='consolidation'"
                )
```

and add the keys to the entry, omitting `checkpoint` when it is `None` so a cluster entry's bytes are unchanged:

```python
        "kind": kind,
    }
    if checkpoint is not None:
        entry["checkpoint"] = checkpoint
```

The substrate's `load_revisions` (Task 5) now validates both, so the existing round-trip validation catches a bad pair for free (**C23**).

- [ ] **Step 5: Add the consolidation pass-through to the checkpoint core**

The server's checkpoint core shells out to the substrate CLI (**C24**). Extend its argv, re-anchoring with `grep -n "checkpoint" ai_rfc/server/core/gates.py`:

```python
    argv = [..., "checkpoint", str(ctx.manifest), "--timeline", str(ctx.timeline),
            "--cluster", cluster_id, "--out", str(out)]
    if consolidation is not None:
        argv += ["--consolidation", str(consolidation), "--base", str(base)]
```

with `consolidation: int | None = None, base: Path | None = None` added as trailing keywords on the core's signature.

- [ ] **Step 6: Add the two tools and their CLI branches**

In `ai_rfc/server/tools.py`, add `structures` to the module-level core import, then two wrappers in the file's existing style:

```python
def ai_rfc_structure_upsert(structure_id: str, fields: dict[str, Any]) -> dict[str, Any]:
    """Declare or replace one structure in the manifest."""
    return structures.upsert_structure(resolve_context(), structure_id, fields)


def ai_rfc_draft_render() -> str:
    """Render every declared structure as blocks to paste into the draft."""
    return structures.render_structures(resolve_context())
```

and append both to `ALL_TOOLS` in the order they will appear in `docs/parity.md` (**C6** — the tuple's order is a soft contract with the table).

In `ai_rfc/server/cli.py`, add `structures` to the **deferred** import inside the dispatch (**C25**), register:

```python
    upsert = verbs.add_parser("structure-upsert", help="Declare or replace one structure.")
    upsert.add_argument("structure_id")
    upsert.add_argument("--json", required=True, help="The structure body as JSON.")
    verbs.add_parser("draft-render", help="Render the declared structures as blocks.")
```

and dispatch — note `print`, not `_emit`, for the string-returning verb:

```python
        elif args.verb == "structure-upsert":
            _emit(structures.upsert_structure(ctx, args.structure_id, json.loads(args.json)))
        elif args.verb == "draft-render":
            print(structures.render_structures(ctx), end="")
```

- [ ] **Step 7: Add the parity rows**

In `docs/parity.md`, after the `ai_rfc_revision_tag` row, matching the format character-for-character (**C27**):

```
| `ai_rfc_structure_upsert` | `ai_rfc structure-upsert ID --json …` | `python -m …ai_rfc.draft render …` (read side only) |
| `ai_rfc_draft_render` | `ai_rfc draft-render` | `python -m …ai_rfc.draft render MANIFEST` |
```

and record the arm-C freeze (D42) in the prose beneath the table: both rows are unavailable in the raw arm C, which stays at the 18-tool surface.

- [ ] **Step 8: Run the server suite and commit**

Run: `cd $AIRFC && SSLKEYLOGFILE= $PY -m pytest tests/server -v`
Expected: all PASS, `test_every_tool_is_in_the_parity_table` included.

```bash
cd $AIRFC && $PY -m black ai_rfc/server tests/server
cd $AIRFC && $PY -m flake8 --max-line-length=88 ai_rfc/server tests/server
cd $AIRFC && $PY -m mypy --follow-imports=silent ai_rfc/server
cd $AIRFC && SSLKEYLOGFILE= $PY -m pytest tests -n auto 2>&1 | tail -3
cd $AIRFC && git status --short
git add ai_rfc/server tests/server docs/parity.md
git commit -m "feat: declare and render structures through the tool and the verb"
```

---

### Task 8: What the lint says about structures

**Files:**
- Modify: `ai_rfc/draft/lint.py`, `ai_rfc/server/core/` (wherever `_METRIC_KEYS` lives)
- Test: `tests/substrate/draft/test_lint.py`, `tests/server/test_parity.py`

**Interfaces:**
- Consumes: `lint()` and `LintReport` (**C2**), the unpopulated frozen `extra` (**C3**), the closed `_METRIC_KEYS` (**C4**), `draft.structures.{parse_blocks, render}` (Task 2), `models.RequirementClass` (Task 1).
- Produces: `lint(text, *, manifest=None, manifest_error=None, source=None, structures=None) -> LintReport` where the new keyword carries the frozen `structures.md`; `LintReport.extra["structures"]`; a `structures` member of `_METRIC_KEYS`.

**Why this shape.** SP7a documented `LintReport.extra` as SP7b's hook but never populated it, and the dataclass is frozen (**C3**) — so the value must arrive as a constructor argument, which means a new `lint()` keyword. Separately, the server's `draft_lint` core filters the report through a **closed** `_METRIC_KEYS` tuple (**C4**): without extending it, every metric below is computed, written to `lint-report.json`, and then silently dropped before it reaches the tool and CLI output. That is the "partial gate that silently passes" failure mode, so the parity test asserts the key survives the filter.

D52 lands two rules here: a **data-model** claim bound to no structure is a lint finding (not a gate finding), and a manifest the schema refuses is reported as a finding rather than a crash. The second matters concretely: after Task 1 closed the `level` vocabulary, the aioquic pilot's run C1 manifest — which carries `level: descriptive` — no longer loads. Pilot workspaces are frozen evidence and are never re-gated, so the enum stays five members and the lint degrades gracefully instead.

- [ ] **Step 1: Write the failing tests**

Append to `tests/substrate/draft/test_lint.py`:

```python
def _structured_manifest_obj():
    from ai_rfc.models import Field, Manifest, RequirementClaim, RequirementClass
    from ai_rfc.models import Intent, Level, Status, Structure, StructureKind

    claim = RequirementClaim(
        id="spec:1.1", text="t", section="4", level=Level.MUST, layer="wire",
        req_class=RequirementClass.DATA_MODEL, intent=Intent.INTENDED, status=Status.GAP,
    )
    structure = Structure(
        id="header", kind=StructureKind.RECORD, title="H", section="4",
        fields=(Field(name="version", claim="spec:1.1", type="uint8"),),
    )
    return Manifest(rfc="spec", title="T", claims=(claim,), structures=(structure,))


def test_a_declared_but_unrendered_structure_is_a_finding():
    from ai_rfc.draft.structures import render_all

    manifest = _structured_manifest_obj()
    report = lint(_draft(), manifest=manifest, structures=render_all(manifest))
    assert report.extra["structures"]["unrendered"] == ["header"]
    assert any("header" in f and "not rendered" in f for f in report.findings)


def test_a_rendered_structure_that_matches_the_frozen_bytes_is_clean():
    from ai_rfc.draft.structures import render_all

    manifest = _structured_manifest_obj()
    frozen = render_all(manifest)
    report = lint(_draft(body=frozen), manifest=manifest, structures=frozen)
    assert report.extra["structures"]["rendered"] == 1
    assert report.extra["structures"]["stale"] == []
    assert report.extra["structures"]["unrendered"] == []


def test_a_stale_block_is_a_finding():
    from ai_rfc.draft.structures import render_all

    manifest = _structured_manifest_obj()
    frozen = render_all(manifest)
    report = lint(_draft(body=frozen.replace("uint8", "uint9")), manifest=manifest, structures=frozen)
    assert report.extra["structures"]["stale"] == ["header"]
    assert any("stale" in f for f in report.findings)


def test_a_block_naming_no_declared_structure_is_a_finding():
    manifest = _structured_manifest_obj()
    body = "{::comment}\nai_rfc:struct:ghost begin\n{:/comment}\nx\n{::comment}\nai_rfc:struct:ghost end\n{:/comment}\n"
    report = lint(_draft(body=body), manifest=manifest, structures="")
    assert report.extra["structures"]["unknown_blocks"] == ["ghost"]


def test_a_data_model_claim_bound_to_no_structure_is_a_finding():
    from ai_rfc.models import Manifest

    manifest = _structured_manifest_obj()
    orphaned = Manifest(rfc="spec", title="T", claims=manifest.claims, structures=())
    report = lint(_draft(), manifest=orphaned)
    assert report.extra["data_model_claims_unbound"] == ["spec:1.1"]
    assert any("spec:1.1" in f and "no structure" in f for f in report.findings)


def test_a_manifest_the_schema_refuses_is_a_finding_not_a_crash():
    # The aioquic pilot's run C1 carries `level: descriptive`, which the closed
    # enum no longer accepts. Pilot workspaces are frozen evidence and are never
    # re-gated, so the lint must degrade rather than raise.
    report = lint(_draft(), manifest=None, manifest_error="C1: level is 'descriptive'")
    assert any("descriptive" in f for f in report.findings)
    assert report.extra["structures"]["defined"] == 0
```

Append to `tests/server/test_parity.py`:

```python
def test_the_lint_metrics_carry_the_structures_block(workspace):
    # _METRIC_KEYS is a closed tuple; without `structures` in it the whole block
    # is computed and then silently dropped before the tool returns.
    from ai_rfc_server.core import structures as core_structures

    core_structures.upsert_structure(workspace, "header", FIELDS)
    metrics = tools.ai_rfc_draft_lint(worktree=True)["metrics"]
    assert "structures" in metrics
```

- [ ] **Step 2: Run them to verify they fail**

Run: `cd $AIRFC && SSLKEYLOGFILE= $PY -m pytest tests/substrate/draft/test_lint.py -k structur -v`
Expected: FAIL — `lint()` takes no `structures` keyword.

- [ ] **Step 3: Compute the block**

In `ai_rfc/draft/lint.py`, add the helper (re-anchor with `grep -n "^def lint"`):

```python
def _structures(text: str, manifest: Manifest | None, rendered: str | None) -> dict[str, Any]:
    """Compare the draft's delimited blocks with the manifest's rendering.

    ``rendered`` is what the manifest renders *now*, not a checkpoint's frozen
    bytes: the gate owns historical fidelity at a tag, the lint owns "this draft
    has drifted from its manifest".
    """
    declared = {s.id: s for s in manifest.structures} if manifest else {}
    bodies, malformed = parse_blocks(text)
    current, _ = parse_blocks(rendered) if rendered else ({}, ())
    stale = sorted(
        structure_id
        for structure_id, body in bodies.items()
        if structure_id in current and body != current[structure_id]
    )
    return {
        "defined": len(declared),
        "rendered": sum(1 for structure_id in bodies if structure_id in declared),
        "unrendered": sorted(set(declared) - set(bodies)),
        "stale": stale,
        "unknown_blocks": sorted(set(bodies) - set(declared)),
        "malformed": list(malformed),
    }


def _unbound_data_model_claims(manifest: Manifest | None) -> list[str]:
    """Data-model claims no structure binds (D52)."""
    if manifest is None:
        return []
    bound = {claim_id for s in manifest.structures for claim_id in s.claims}
    return sorted(
        claim.id
        for claim in manifest.claims
        if claim.req_class is RequirementClass.DATA_MODEL and claim.id not in bound
    )
```

- [ ] **Step 4: Add the keyword and the findings**

Add `structures: str | None = None` as the last keyword of `lint()`, then inside it:

```python
    structure_metrics = _structures(text, manifest, structures)
    unbound = _unbound_data_model_claims(manifest)
    for structure_id in structure_metrics["unrendered"]:
        findings.append(f"structure {structure_id} is declared but not rendered in the draft")
    for structure_id in structure_metrics["stale"]:
        findings.append(
            f"structure {structure_id} is stale: the block differs from the frozen rendering"
        )
    for structure_id in structure_metrics["unknown_blocks"]:
        findings.append(f"block {structure_id} names no structure this manifest declares")
    for problem in structure_metrics["malformed"]:
        findings.append(problem)
    for claim_id in unbound:
        findings.append(f"data-model claim {claim_id} is bound to no structure")
```

and pass them into the report:

```python
        extra={"structures": structure_metrics, "data_model_claims_unbound": unbound},
```

Import `parse_blocks` from `.structures`, and `Manifest`/`RequirementClass` from `ai_rfc.models`.

- [ ] **Step 5: Open the metric filter and feed the comparison**

**The lint and the gate compare against different things, deliberately.** The gate runs at a tag and
compares each block against the bytes *frozen in the paired checkpoint* — historical fidelity. The
lint runs on the working draft, where there is no paired checkpoint yet, and compares against what
the *current manifest renders now* — "your draft is out of date with your manifest". So the lint
core renders rather than reading a checkpoint, and needs no notion of which checkpoint is paired.

In the `draft_lint` core, pass the rendering alongside the manifest it already loads (re-anchor with
`grep -rn "def draft_lint\|lint(" ai_rfc/server/core/`):

```python
    report = lint(
        text,
        manifest=manifest,
        manifest_error=manifest_error,
        source=source,
        structures=render_all(manifest) if manifest is not None else None,
    )
```

with `from ai_rfc.draft.structures import render_all` at the top of that module.

Then open the filter, or every metric above is computed and thrown away (**C4**; re-anchor with
`grep -rn "_METRIC_KEYS" ai_rfc/server/`):

```python
_METRIC_KEYS = (
    ...,  # the seven SP7a keys, unchanged
    "structures",
    "data_model_claims_unbound",
)
```

If `_METRIC_KEYS` filters `report.to_json()`'s top level rather than a `metrics` sub-mapping, the two
new keys live under `extra` and the filter must reach into it — read the SP7a code before editing,
and make the parity test from Step 1 the thing that decides, since it asserts on the tool's actual
return value.

- [ ] **Step 6: Run both suites and commit**

Run: `cd $AIRFC && SSLKEYLOGFILE= $PY -m pytest tests/substrate/draft/test_lint.py tests/server -v`
Expected: all PASS.

```bash
cd $AIRFC && $PY -m black ai_rfc/draft/lint.py ai_rfc/server tests/substrate/draft/test_lint.py
cd $AIRFC && $PY -m flake8 --max-line-length=88 ai_rfc/draft/lint.py ai_rfc/server
cd $AIRFC && $PY -m mypy --follow-imports=silent ai_rfc/draft/lint.py
cd $AIRFC && git status --short
git add ai_rfc/draft/lint.py ai_rfc/server tests/substrate/draft/test_lint.py tests/server/test_parity.py
git commit -m "feat: measure declared, rendered, stale and orphaned structures"
```

---

### Task 9: Tell the agent what a structure is for

**Files:**
- Create: `plugins/ai-rfc/skills/ai-rfc-structures/SKILL.md`
- Test: `tests/experiment/test_render.py`

**Interfaces:**
- Consumes: the tool names from Task 7; the kinds from Task 1.
- Produces: a skill SP7c's `CONSOLIDATION_TEXTS` will bundle (**C9**).

- [ ] **Step 1: Write the failing test**

Append to `tests/experiment/test_render.py`:

```python
def test_the_structures_skill_names_every_kind_and_the_tool():
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    text = (root / "plugins/ai-rfc/skills/ai-rfc-structures/SKILL.md").read_text()
    for kind in ("wire-format", "message", "record", "enum", "state-machine"):
        assert kind in text
    assert "ai_rfc_structure_upsert" in text
    assert "ai_rfc_draft_render" in text
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd $AIRFC && SSLKEYLOGFILE= $PY -m pytest tests/experiment/test_render.py -k structures_skill -v`
Expected: FAIL — `FileNotFoundError`.

- [ ] **Step 3: Write the skill**

Create `plugins/ai-rfc/skills/ai-rfc-structures/SKILL.md`:

```markdown
---
name: ai-rfc-structures
description: Use when a cluster defines or changes a wire format, message, record, enumeration or state machine, and the draft needs a figure or table for it.
---

# Structures

A specification a reimplementer can use says what the bytes look like. Declare
those shapes in the manifest and let the tool draw them; never hand-write a
diagram or a field table in the draft.

## When to declare one

Declare a structure when a cluster's evidence pins the shape of something on
the wire or in memory: a packet or frame layout (`wire-format`), a
request/response (`message`), a stored record (`record`), a closed set of
codes (`enum`), or the states a connection moves through (`state-machine`).

Do not declare one for a shape you inferred but cannot cite. Every field,
value and transition names one claim, and a structure is only ever as strong
as its weakest claim — a structure built on a `gap` claim reports as a gap.

## How

1. `ai_rfc_structure_upsert` with the id, the kind, the title, the section it
   belongs to, and its members. Each member names a `claim:` that must already
   exist in `requirements:`; declare the claim first.
2. `ai_rfc_draft_render` returns the blocks. Paste them **verbatim** into the
   owning section, delimiters included.
3. Never edit inside the delimiters. The checkpoint freezes those bytes and
   every revision tag compares against them, so a single edited character is a
   gate finding. To change a figure, change the manifest and re-render.

## Widths

`width` is a bit count, or `variable` for a trailing field of unbounded
length. Only the last field of a structure may be `variable`.

## What not to draw

Architecture and sequence overviews are free-form figures, not structures —
see the figures skill. A structure describes data, not a story.
```

- [ ] **Step 4: Run the test and commit**

Run: `cd $AIRFC && SSLKEYLOGFILE= $PY -m pytest tests/experiment/test_render.py -v`
Expected: all PASS.

```bash
cd $AIRFC && git status --short
git add plugins/ai-rfc/skills/ai-rfc-structures/SKILL.md tests/experiment/test_render.py
git commit -m "feat: tell the agent when a shape deserves a structure"
```

---

### Task 10: Prove the loop, and record the surface change

**Files:**
- Modify: `docs/experiment-protocol.md`, `README.md`
- Create: `docs/experiments/2026-09-03-sp7b-structures-proof.md`
- Test: the whole suite, plus a scripted round trip

**Interfaces:**
- Consumes: everything above.
- Produces: the recorded protocol amendment (20 tools, the structures registry, the consolidation root) and evidence that the freeze actually catches a tamper.

- [ ] **Step 1: The whole suite**

Run: `cd $AIRFC && SSLKEYLOGFILE= $PY -m pytest tests -n auto 2>&1 | tail -3`
Expected: 0 failed, at the Task 0 baseline plus this plan's tests. Record the exact number for Step 5.

- [ ] **Step 2: Prove the MARK draft did not regress**

The MARK manifest declares no structures, so the new gate must be a no-op on it. Work on a copy — the campaign directory and the sealed snapshot are both evidence:

```bash
rm -rf /tmp/claude/mark-b && mkdir -p /tmp/claude
cp -R ~/ai-rfc-experiments/baselines/mark-a1-2026-09-03/workspace /tmp/claude/mark-b
chmod -R u+w /tmp/claude/mark-b
cd $AIRFC && SSLKEYLOGFILE= $PY -m ai_rfc.draft gate /tmp/claude/mark-b/draft \
  --timeline /tmp/claude/mark-b/timeline --checkpoints /tmp/claude/mark-b/checkpoints \
  --questions /tmp/claude/mark-b/questions.yaml --revisions /tmp/claude/mark-b/revisions.yaml \
  --out /tmp/claude/mark-b/out --strict
```

Expected: exit 0, exactly as it did before this plan. A finding here means the defaulted `kind` or the block scan changed behaviour for structure-free drafts, which it must not.

- [ ] **Step 3: Prove the round trip end to end**

On a scratch workspace, walk the loop the agent will walk — declare, render, paste, checkpoint, tag, gate:

```bash
cd $AIRFC && SSLKEYLOGFILE= $PY -m pytest tests/substrate/draft/test_gate.py -k "untouched_structured or one_byte" -v
```

Expected: `test_an_untouched_structured_draft_gates_clean` PASSES and `test_a_one_byte_edit_to_a_rendered_block_is_a_finding` PASSES. Together these are the gate of this plan: a faithful paste is clean, and a single changed character is caught.

- [ ] **Step 4: Protocol and README**

In `docs/experiment-protocol.md`, add a dated subsection "2026-09-03 — draft quality v2, SP7b" stating, in this order: (1) the tool surface is 20 tools (`ai_rfc_structure_upsert`, `ai_rfc_draft_render` added; `docs/parity.md` is the table); (2) the raw arm C stays frozen at the 18-tool surface (D42), so a v2 campaign compares arms A and B only; (3) the manifest carries a `structures:` registry whose every field, value and transition names a claim, and a structure's status is the minimum over those claims; (4) every revision tag compares each delimited block against the rendering frozen in the paired checkpoint, so a figure cannot drift from the manifest; (5) consolidation checkpoints live under `consolidations/<NN>/` and never under `checkpoints/`, and a consolidation may change only `structures:`; (6) `level` is now a closed enum, and a manifest the schema refuses is a lint finding rather than a crash.

In `README.md`: add `structure-upsert` and `draft-render` to the verb table, and a sentence under the manifest section saying that `structures:` is rendered by the tool and must never be hand-edited in the draft.

- [ ] **Step 5: Write the proof document**

Create `docs/experiments/2026-09-03-sp7b-structures-proof.md` with: the suite count from Step 1; the MARK gate result from Step 2 and an explicit statement that it is unchanged from the SP7a baseline; the two test names from Step 3 and their outcomes; and one rendered example of each of the five kinds, copied verbatim from the test output, so a reader can see what the tool draws without running it.

- [ ] **Step 6: Commit**

```bash
cd $AIRFC && git status --short
git add docs/experiment-protocol.md README.md docs/experiments/2026-09-03-sp7b-structures-proof.md
git commit -m "docs: record the structures registry and the block freeze"
```

Then bump the submodule pointer in PANTHER (one commit, `chore(ai_rfc): bump ai_rfc to SP7b (<old>..<new>)`), and push the submodule before the parent, each push confirmed with the user first.

---

## Self-review (run by the plan author on 2026-09-03)

1. **Spec coverage.** The roadmap row for SP7b names seven items; each has a task. `Level` enum → Task 1. Revision `kind`/`checkpoint` → Task 5 (substrate) and Task 7 (the writer). `structures:` schema → Task 1. Renderer → Task 2. Frozen `structures.md` → Task 4. Consolidation checkpoint → Task 4. Gate checks 8–11 → Task 5. `draft render` → Tasks 6 and 7. `structure upsert` → Task 7. `checkpoint --consolidation` → Tasks 6 (substrate, required first by **C24**) and 7 (server). The roadmap gate — "goldens per kind; a one-byte tamper is a finding" — is Task 2 Step 6 (five byte-exact goldens with a `--update-goldens` regeneration path) and Task 5 / Task 10 Step 3 (`test_a_one_byte_edit_to_a_rendered_block_is_a_finding`). D52's three SP7b clauses land in Tasks 1 (closed enum) and 8 (unloadable manifest, unbound data-model claim). Not in SP7b by design: the consolidation *round* and its prompts (D43 → SP7c), the instrument and the paid runs (D44, D47 → SP7d).
2. **Placeholder scan.** No "TBD"/"TODO"/"handle edge cases". A first pass of this review was too generous and claimed every code step showed its code; a second pass found seven places where it did not, and all seven are now fixed: Task 2 had property tests standing in for the goldens the roadmap gate demands; Task 5's `_build_draft_workspace`, `_retag_draft_with` and `_record_consolidation` were prose; Task 5 referenced a `_read_json` that does not exist (the gate parses `checkpoint.json` inline and already holds it as `record`) and hedged where `previous` is kept; Task 6's test asserted `SystemExit` while its code returned `2`; Task 7's `upsert_structure` returned `… .structures and dict(fields)`, a tuple on the empty path that would not typecheck; Task 7's parity tests used `FIELDS` and `json` without either; and Task 8's metric plumbing was a sentence.

   Three steps still say "read the landed shape first" rather than guessing, and that is deliberate: Task 0 Step 3 (the whole contract), Task 6 Step 5 (`entrypoints.py`, which SP7a never touches per **C10**), and Task 7 Step 3's note on `_document`/`_normalize_and_write`. Each names a symbol whose final location only SP1 and SP7a decide, and each says exactly what to grep and what to do with either answer. One more is a mechanical promotion rather than an invention: Task 5 Step 2 says to move today's `draft_workspace` fixture body into `_build_draft_workspace` verbatim, and marks the only two lines that change.
3. **Type consistency.** `render(structure) -> str` and `render_all(manifest) -> str` are used with those types in Tasks 2, 4, 6, 7 and 8. `parse_blocks(text) -> tuple[dict[str, str], tuple[str, ...]]` is unpacked as two values in Tasks 2, 5 and 8. `requirements_digest(manifest) -> str` is called on a `Manifest` in Tasks 4 and 5. `structure_statuses(manifest) -> dict[str, tuple[Status, Status]]` is unpacked as a pair in Task 3 twice. `Structure.claims -> tuple[str, ...]` is iterated in Tasks 1, 3 and 8. `write_consolidation_checkpoint(manifest_path, ordinal, base_checkpoint, cluster_id, out)` is called with those five in Tasks 4, 5 (fixture) and 6. `upsert_structure(ctx, structure_id, fields)` and `render_structures(ctx)` match between Task 7's core, its tools and its CLI branches.
4. **The one thing a reviewer should check hardest.** Task 5 Step 6 hoists `draft_text` so a tag's blob is read once per entry. If `cited_ids` still reads it separately, the gate reads the same blob twice per revision — harmless for correctness but the beginning of the two-readers-drift problem this plan otherwise avoids. Confirm one read, one parse.

## Execution

Subagent-driven, one fresh implementer per task and a reviewer between tasks. Tasks 1–4 touch only files SP7a leaves alone and may be dispatched in order without waiting on anything else. Task 5 needs Tasks 2 and 4. Task 6 needs Tasks 2, 4 and 5. Task 7 needs Task 1 (the schema, or its writes are destroyed — **C22**) and Task 6 (the substrate flag — **C24**). Task 8 needs Tasks 1, 2 and 7. Task 9 is independent of everything but names Task 7's tools. Task 10 is last.

Before dispatching anything, run Task 0 and repair the contract table. During execution, keep the same deviation log SP7a used: one row per step where reality differed, so SP7c's plan can be written against fact rather than prediction.
