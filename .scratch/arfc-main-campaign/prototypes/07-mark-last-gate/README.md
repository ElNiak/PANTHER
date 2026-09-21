# MARK last-gate dry run, ai_rfc `c5e4a6c` (2026-09-21)

The asset of the ticket
[Can the rebuilt MARK pristine carry a v2 cluster through its last gate?](../../issues/07-can-the-mark-pristine-pass-its-last-gate.md).
Every command, its exit code and its output are in `transcript.txt`, in order.

## Answer

**Yes. The rebuilt MARK pristine is ready for a v2 campaign**, as far as its repository and the
gates are concerned. On a copy, the draft builds with no findings, and one cluster goes through
checkpoint, revision record, **tag** (strict manifest gate, build at the tag, tag, strict citation
gate) and the strict citation gate, all exiting 0. The pre-D45 build failure that stopped SP7d's
paid consolidation round (R90) does not occur: the rebuilt `draft/` has a root `Makefile`.

**But this session's own sandbox cannot run the build.** That is an environment fact, not a MARK
fact, and it matters to "Freeze prompts, pin code, and dry-run".

## Provenance

- **Code:** ai_rfc `c5e4a6c`, the owed-fixes row's HEAD at 12:17, exported with `git archive`
  into the session scratchpad and run through `PYTHONPATH`.
- **Pristine:** `~/ai-rfc-experiments/rebuild-sp7d/pristine/mark-w01-69` (63 MB, window
  [1, 69], no pre-seeded clusters). It was read only. `verify_digest` reported **none** before and
  **none** after.
- **Copy:** `copy_workspace` into the scratchpad. **Before any write**, `resolve_context()` from the
  copy's `recon.yaml` named the copy, not the pristine its `workspace:` line points at, and named
  the toolchain `~/ai-rfc-experiments/tools/toolchain.json` (`scripts/mark_copy.py`).
- There were no claims and no prose. The question was whether this repository and the gates carry
  a revision to its tag. A real session's claims and prose can still raise lint and build
  findings, which is the session's work, not the repository's.

## What ran

| Step | Sandbox | Exit | Result |
|---|---|---|---|
| `toolchain verify` (control) | on | 3 | "the example did not build offline": venue, kramdown-rfc and v2v3 exit 1 |
| `draft build` (MARK copy) | on | 0 | 3 findings (the same three stages), **make exited 2** (report), no outputs |
| `make … txt`, re-run from the report's own argv (`scripts/rerun_make.py`) | on | 2 | **`mktemp: mkstemp failed on /var/folders/…/T/…: Operation not permitted`** and **`trace.sh: line 36: /dev/fd/62: Operation not permitted`** |
| `toolchain verify` (control) | **off** | 0 | `ok` |
| `draft build` (MARK copy) | **off** | 0 | **no findings**; `.txt` and `.html` built (commit `bdd4241`) |
| `cluster next` | on | 0 | `c0001-epoch-c84a5f082e40` ("Initial commit", 6 members) |
| `checkpoint c0001-epoch-c84a5f082e40` | on | 0 | manifest `9c40c238…` |
| `revision record draft-elniak-mark-reconstructed-00 --no-normative` | on | 0 | entry written |
| `revision tag draft-elniak-mark-reconstructed-00` | **off** | 0 | **findings `[]`, `rolled_back: false`**, the tag exists |
| `citation-gate --strict` | on | 0 | "note: gate clean" |

The sandbox was disabled only for the three commands that run the build, on the evidence in row
3. They wrote only inside the scratchpad copy.

## Findings for other tickets

- **The build cannot run inside this Claude Code sandbox.** i-d-template's `trace.sh` calls
  `mktemp` in the macOS user temp directory (`/var/folders/…/T`) and writes to `/dev/fd/62`, and
  the sandbox refuses both. Every stage then fails with **empty stderr in the build report**, so
  the report cannot say why. This explains the `campaign init` verification refusal recorded on
  "Freeze prompts, pin code, and dry-run". The toolchain itself verifies (`ok`) outside the
  sandbox.
- **Whether arms B and C can build inside a campaign session is unmeasured.** Arm A builds through
  the MCP server process; B and C build through their session's Bash tool. The campaign profile
  (`~/ai-rfc-experiments/profile/`) has no `settings.json` and no sandbox key, and sessions launch
  with `--setting-sources project`, so their Bash is *probably* unsandboxed. But no arm-B session
  has built a v2 draft yet (SP7d's Phase 5 ran arm A only). If a session's Bash were sandboxed,
  **B's and C's builds would fail where A's pass**: an arm asymmetry no prompt diff or parity twin
  can see.
- **`draft build` exits 0 with findings, by contract.** The sandboxed run reported
  `"exit_code": 0` with three findings, while its own note says "build … exited 2". Exit 0 with
  findings is what `test_draft_build_parity` pins (`tests/server/test_parity.py:841`, a stub with a
  finding), and the tag refuses on findings. Only the findings list carries the verdict.
