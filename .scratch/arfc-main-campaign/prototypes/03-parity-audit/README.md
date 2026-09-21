# Parity suite audit, ai_rfc `571355c` (2026-09-21)

The asset of the ticket [Audit the parity suite](../../issues/03-audit-the-parity-suite.md). For
each of the 20 MCP tools, it records what its twin in `tests/server/test_parity.py` compares, and
which inputs the arms' prompts use that no twin exercises. **It rules nothing and adds no test**:
closing a gap is a ruling for
[Rule each arm asymmetry](../../issues/04-rule-each-arm-asymmetry.md), next to the
[prompt diff](../02-arm-prompt-diff/README.md).

## Provenance

- **Code:** ai_rfc `571355c` ("validate a campaign id at the argparse boundary"), the owed-fixes
  row's HEAD at 12:07, two commits past the prompt diff's `8358238`. It was exported with
  `git archive` into the session scratchpad, because the live tree was mid-edit.
  `test_parity.py` is 908 lines, unchanged from `8358238` in length.
- **The suite, run from the snapshot:** **25 passed, 0 failed, 0 skipped** in 34.52 s
  (`pytest-output.txt`, `-v`, the snapshot as rootdir and on `PYTHONPATH`).
- **Three probes** (`probe/test_zz_parity_probe.py`, output in `probe-output.txt`) drove inputs no
  twin exercises, through arm A's tool and arm B's verb over twin workspaces. They were run in the
  snapshot only. **They record outcomes and assert none**, and they are not proposed as tests.

## The 20 twins

Line numbers are in the snapshot's `tests/server/test_parity.py`. "Class" is about the inputs
sessions use (from the prompts in the prompt diff): **full** means the twin covers them, and
**partial** names what it does not. "Guard" is a non-vacuity assertion, one that fails when both
arms silently do nothing.

| Tool | Twin | Compares | Guard | Exercised | Not exercised (sessions use it) | Class |
|---|---|---|---|---|---|---|
| `ai_rfc_status` | `:481-500` | tool against `queries.status`, **not against a verb** (D16) | `clusters_total == 2` | — | — | **none, as A against B** (by design: B has no verb) |
| `ai_rfc_corpus_query` | `:503-513` | payload | 4 rows | one SELECT over `commits` | a schema read; the non-SELECT refusal (both probed, see below) | **partial** |
| `ai_rfc_cluster_next` | `:516-526` | payload | an id is returned | the next cluster | the `null` when all are done | full |
| `ai_rfc_cluster_get` | `:529-562` | payload | an interior 40-byte slice | `--patch`, offset, limit | no `--patch`; an unknown id | full |
| `ai_rfc_claim_upsert` | `:47-87` | manifest bytes | the claim id is present | text, section, level, layer, `intent` | **`--anchor` (probed: byte-equal for code plus adr)**; `req_class`; the `status` refusal (pinned per arm in `tests/agent/test_verbs.py:47-49`, not twinned) | **partial** |
| `ai_rfc_claim_adjudicate` | `:102-112` | payload | the fixture's two ids | no arguments | — | full |
| `ai_rfc_claim_record_status` | `:90-99` | manifest bytes | **none**: two no-ops compare equal | no ids (all claims) | explicit claim ids | **partial** |
| `ai_rfc_question_draft` | `:568-584` | payload, `questions.yaml`, manifest | linked id; pinned day | question with `--claim` | — | full |
| `ai_rfc_question_export` | `:587-618` | stdout against the return value | the question is present | — | — (no loop prompt uses it) | full |
| `ai_rfc_answer_record` | `:621-668` | payload, both files | anchored and signed off | `--exact-wording-confirmed` | the unconfirmed path (interview profile only) | full |
| `ai_rfc_revision_record` | `:335-435` (shared) | `revisions.yaml` bytes | the entry is present | cluster `--normative`; consolidation `--no-normative --kind --checkpoint` | cluster `--no-normative` | full |
| `ai_rfc_checkpoint` | `:335-435` (shared) | the consolidation's `checkpoint.json` bytes; each arm's note names its own directory | `kind`, `structures_sha256` | cluster; `--consolidation`, `--base` | the cluster checkpoint's own files, compared only through `revisions.yaml`'s manifest sha | full |
| `ai_rfc_gate` | `:686-721` | payload, `report.json` bytes, exit 0 and 3 | the violation quoted verbatim | default, `--strict` | — | full |
| `ai_rfc_citation_gate` | `:724-764` | payload, `gate-report.json` bytes, exit 0 and 3 | the finding quoted verbatim | default, `--strict` | — | full |
| `ai_rfc_draft_commit` | `:244-259` | payload, `HEAD` sha | prose edited in both | `-m` | the "nothing to commit" refusal | full |
| `ai_rfc_revision_tag` | `:262-279` | payload, the tag object | exit 0 | the success path | **refusal on build findings; tag deletion on citation findings** (sessions hit these; the 2026-09-21 MARK round did) | **partial** |
| `ai_rfc_draft_build` | `:818-867` | calls to a stubbed build, payload, report bytes, exit 0 and 1 | the call list | `--ref` | a real toolchain (stubbed at the seam by design) | full |
| `ai_rfc_draft_lint` | `:282-292` | metrics and findings (**not the exit code**) | **none** | no arguments | — | **partial** |
| `ai_rfc_structure_upsert` | `:303-316` | manifest bytes | the title is present | kind `record`, with `fields:` | kinds `enum` (`values:`) and `state-machine` (`states:`, `transitions:`) | **partial** |
| `ai_rfc_draft_render` | `:319-332` | stdout against the return value, byte for byte | none explicit | one structure | — | full |

**Totals: 13 full, 6 partial, 1 none by design.** Three twins carry no non-vacuity guard: record
status, draft lint and draft render. For comparison, the pilot counted 5 of 16 rows with a
cross-arm behavioural assertion.

The table checks behind the twins: `:118` (every tool is in `docs/parity.md`), `:208` (every
row's CLI cell names a leaf verb the parser owns, and no tool is listed twice; its own docstring
says it cannot check that tool and verb *correspond*) and `:438` (20 tools). `:900-908` checks
that `TWINS` covers `tools.ALL_TOOLS` and that every named twin exists. That is completeness of
*names*: the table above is what each twin actually pins.

## Probes: inputs no twin covers

| Probe | Arm A (tool) | Arm B (verb) | Reading |
|---|---|---|---|
| `SELECT name, sql FROM sqlite_master WHERE type = 'table'` | returns `commits`, `corpus_source`, `file_changes` with their `CREATE` statements | exit 0, the same rows | **Both arms can read the corpus schema.** The prompt diff's D7 is about what arms A and B are *shown*, not what they *can do*: the guardrail (`server/core/queries.py:15,40`) admits any lone SELECT. |
| `DELETE FROM commits` | raises `GuardrailError` ("corpus_query accepts exactly one SELECT statement …") | exit 1 | Both refuse. The verb's message is pinned for arm B alone (`tests/agent/test_verbs.py:40-44`). |
| claim upsert with a code **and** an adr anchor | writes both anchors | exit 0 | **Manifests byte-equal**; the claim is written. The anchor path the ARM-B fix relies on keeps parity today. No twin would notice it breaking. |

## Limits of the construct (the whole suite)

- **L1, no transport is tested.** The arm-A side calls the Python tool functions
  (`tools.ai_rfc_*`), not the MCP server: FastMCP's argument handling and serialisation sit
  outside every twin. The arm-B side calls `cli.main` in-process, not the campaign's
  `bin/ai-rfc` shim through Bash. Both frontends share one core, so the twins mainly pin
  argument parsing and output shaping, which is exactly where the partial rows sit.
- **L2, arm C has no twin at all.** Its raw substrate commands and hand edits are argued only by
  D42's disclosure.
- **L3, some inputs are pinned per arm, never across arms**: the `status` refusal, and the
  guardrail message.

## Capability differences the suite shows, or cannot see

- **K1, status (D16).** A has `ai_rfc_status`; B has no verb for it (`ai-rfc status` is the
  operator's ledger and needs a `recon.yaml`). Disclosed in `<protocol>` §1. It surfaces in
  consolidation rounds (prompt diff, D6).
- **K2, arm C.** C does by hand what A and B do by verb: choosing the cluster, claim upserts,
  recording statuses, recording revisions, drafting questions. It has no structures, render,
  lint, build or consolidation (D42). No twin covers any C path.
- **K3, the schema: capability equal, exposure unequal.** All three arms can read it; only C is
  shown how (prompt diff, D7).
- **K4, corpus writes.** A and B are SELECT-only; C's `sqlite3` is unrestricted (prompt diff,
  D14).
