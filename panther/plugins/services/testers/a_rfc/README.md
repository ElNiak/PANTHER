# a_rfc — claim manifests for reconstructed specifications

This module holds an implementation's *reconstructed* requirements — a
specification mined from code, history, papers and developer interviews rather
than written by a standards body — as a validated, anchored, reproducible
manifest in which a claim's evidential status is **computed from its evidence
rather than asserted by its author**.

It is a plain library module plus a CLI, deliberately **not** registered under
any `PluginType`. A tester executes scenarios against a live implementation;
this module executes nothing and never opens a socket. It validates a manifest
file that reconstruction agents (running entirely outside this framework)
wrote to disk.

## This module makes no model calls

Despite what the name may suggest: **nothing in this package calls a language
model, and nothing reaches the network.** Every operation is schema
validation, rule adjudication or anchor checking over local data. The tests
run against fixtures built in a temp directory. The framework's runtime
dependency set is unchanged (standard library plus PyYAML, already a
dependency). Generation — the model-driven part of the pipeline — lives in
agents outside the framework; this is the model-free substrate they emit into.

## The `history/` subpackage

`history/` extracts an implementation's repository into a deterministic,
citable JSONL corpus of commit metadata and per-file change rows, plus a
derived SQLite index — see `history/README.md`. The corpus feeds claim
mining, whose output is a manifest validated by the modules documented here.
**The handoff between the two subpackages is a file on disk, not an import.**
They share no domain code; a reader seeing a nested package will reasonably
assume otherwise, which is why it is stated here.

## The `forge/`, `timeline/`, `views/` and `draft/` subpackages

Four further stages carry the corpus toward a progressive, per-PR
reconstruction (design spec:
`docs/superpowers/specs/2026-08-25-arfc-progressive-rfc-design.md`):

- `forge/` is the package's ONLY networked stage: it fetches a repository's
  pull/merge requests, reviews and comments (GitHub and GitLab adapters,
  stdlib urllib, `GITHUB_TOKEN`/`GITLAB_TOKEN` from the environment and
  never stored) into an **immutable, sorted snapshot** — written once after
  a complete fetch, refused if the directory exists, consumed only by
  explicit path. Everything downstream stays offline and deterministic.
  Discussions are fetched for merged pulls only.

- `timeline/` clusters the corpus into a total-ordered first-parent
  timeline: every merge on the spine becomes a **PR cluster** (the merge
  plus its branch commits), every run of direct pushes an honest **epoch
  cluster**, and every commit appears exactly once — the partition is
  asserted, not assumed. Order is topological, never chronological. With
  `--forge`, merged pulls enrich their merge clusters with a PR number and
  a pull that landed as a single squash/rebase commit is **rescued** into
  its own one-member PR cluster (`provenance: forge_squash`) — on
  squash-heavy aioquic this turns 3 git-visible PRs into 238. A rebase
  merge is approximated by its final commit; earlier rebased commits stay
  epoch members. Pulls landing outside the corpus are counted and named,
  never guessed, and a snapshot fetched at a different HEAD is refused. A
  trailing ``(#N)`` in a subject NEVER clusters — GitHub renders issue
  references identically, and misattribution would be silent.
- `views/` emits one evidence folder per cluster — metadata, the member
  file set (a union over members, because merge commits carry no file rows
  of their own) and a byte-stable `span.diff` — digest-guarded against a
  moved corpus or clone, and re-verifiable with `--verify`. With `--forge`,
  each PR cluster's pull record, reviews and comments are copied into
  `evidence/pr.json`; `--patches members` adds one first-parent patch per
  member commit, all digest-recorded.
- `draft/` freezes the manifest per cluster (`checkpoint`), keeps the
  question register for the author-feedback loop, and gates a prose
  Internet-Draft's revision map (`gate`): revision tags must exist, map to
  clusters in increasing order, pin unedited checkpoints, and cite — as
  backticked `` `a_rfc:<claim-id>` `` tokens — only claims their
  checkpoint holds.

`timeline/` and `views/` are corpus-side: like `history/`, they share no
domain code with the manifest core and re-parse the JSONL themselves.
`draft/` is manifest-side: it imports `schema` and `promotion`, and reads
timeline artifacts only as files on disk.

## The `pipeline/` subpackage

`pipeline/` holds the sequence the six commands above do not: it runs the
deterministic stages in order and **stops** at the two that produce content —
mining claims and writing prose — because those need a model and nothing here
calls one. Reaching such a boundary exits 0 and names whose turn it is.

It records nothing. A workspace's state is derived on every call from the
digests the substrate already writes into its own outputs, because a run ledger
would start lying the first time somebody ran a sub-CLI by hand — which the
authoring loop below actively tells them to do. See `pipeline/README.md`.

It is a seventh caller of the same CLIs, not a seventh layer: it imports each
sub-package's `cli.main` and nothing else, so data still hands over on disk.

| Command | Purpose |
|---|---|
| `python -m …a_rfc.forge URL --repo CLONE --out DIR [--host github\|gitlab]` | Fetch pull data into an immutable snapshot (the only networked command) |
| `python -m …a_rfc.timeline CORPUS --out DIR [--repo CLONE] [--forge SNAPDIR]` | Cluster the corpus; `--repo` refuses a clone whose HEAD left the corpus tip; `--forge` enriches and rescues |
| `python -m …a_rfc.views TIMELINE --corpus DIR --repo CLONE --out DIR [--only ID] [--forge SNAPDIR] [--patches span\|members] [--verify]` | Emit evidence folders; `--verify` exits 3 on byte drift, and `--only` scopes both emission and verification |
| `python -m …a_rfc.draft checkpoint MANIFEST --timeline DIR --cluster ID --out DIR` | Freeze the manifest against one cluster |
| `python -m …a_rfc.draft gate DRAFTREPO --timeline DIR --checkpoints DIR --questions FILE --revisions FILE --out DIR [--strict]` | Citation gate; findings exit 3 under `--strict` |
| `python -m …a_rfc.pipeline status WORKSPACE [--json]` | Report every stage's state and what to do next |
| `python -m …a_rfc.pipeline run WORKSPACE [--from STAGE] [--until STAGE] [--forge-url URL] [--cluster ID] [--strict] [--json]` | Chain the deterministic stages; stop at the next agent stage |
| `python -m …a_rfc.coverage MANIFEST --coverage FILE --repo CLONE --commit SHA --out DIR` | Propose `runtime` anchors for cited lines a test run reached |

## CLI

```bash
python -m panther.plugins.services.testers.a_rfc \
  path/to/manifest.yaml \
  --out out/ \
  --repo path/to/pinned-clone \
  --strict
```

Writes `report.json`, `report.yaml` and `report.md` into `--out`. `--repo`
names a clone against which `code` and `runtime` anchors are verified at their
pinned commits; omit it and no anchor verification is attempted (an absence of
findings, not a clean bill of health). Without `--strict` the command is a
linter: it reports violations on stderr and exits 0. With `--strict` it is a
gate.

Exit codes:

| Code | Meaning |
|---|---|
| 0 | Success — reports written; findings, if any, reported but tolerated |
| 1 | The manifest could not be read, or `--repo` is not a git repository |
| 2 | Argument error, raised by `argparse` itself |
| 3 | Findings were reported and `--strict` was given |

Every command in the package holds to that table, so 2 always means the
invocation was malformed and never that the evidence was. Sharing one code
between the two left a scripted caller unable to tell a mistyped flag from a
real finding, and the responses are opposite: fix the command, or fix the
evidence.

A **finding** is either a promotion violation or an anchor that did not resolve
at its pinned commit. Both gate under `--strict`, and both are named on stderr
in either mode. An anchor citing code absent from the commit it names is weaker
evidence than an overstated status, not stronger, so it is not treated as
merely advisory.

## How to use

The pipeline has four stages, and this module is only the last one:

```
repository  ->  history/ corpus  ->  [ mining ]  ->  manifest  ->  this gate
                (this package)      (OUTSIDE the      (a file        (this package)
                                     framework)        on disk)
```

Nothing here writes a manifest. There is no `init`, no scaffold and no
generator; `dump()` exists for round-tripping an already-loaded manifest, not
for producing one. The manifest arrives as YAML that a miner — an agent, or a
person reading source — put on disk.

### Starting a manifest

Begin with the base schema and nothing else. The four required fields per
requirement are `text`, `section`, `level` and `layer`:

```yaml
rfc: SPEC-1
title: 'A reconstructed specification'
requirements:
  'spec:1.1':
    text: 'The system responds within the configured interval.'
    section: '1.1'
    level: MUST
    layer: timing
```

That loads and passes. Every extended field takes its most restrictive default,
so the claim reads `gap` — which is the honest description of a claim nobody has
yet found evidence for. An existing base-format requirement manifest can be
dropped in unchanged for the same reason.

### The authoring loop

**Do not decide a claim's status.** Write the claim and its evidence, and let
`adjudicate` tell you what that evidence supports. Concretely:

1. **Build the corpus first.** Beyond being the citable record, its index is how
   you decide what to read: querying `file_changes` for the highest-churn paths
   is a far better reading order than walking the source tree.
2. **Write claims with anchors and omit `status` entirely.** Omission is always
   safe — it defaults to `gap`, the lowest rank, and a violation is only ever
   raised when a *stored* status exceeds what the evidence supports.
   Understatement is permitted everywhere.
3. **Run without `--strict` first, and with `--repo`.** This is the linter mode:
   anchors are resolved against their pinned commits and any that do not exist
   are named on stderr, while the command still exits 0. Fix wrong paths and
   wrong commits here, before anything is built on top of them.
4. **Record the adjudicated status.** See the caveat below: the report tells you
   what is *stored*, not what is *supported*, so today this means calling
   `promotion.adjudicate` directly.
5. **Re-run with `--strict`.** It is now a gate: any overstated claim or
   unresolved anchor exits 3.

```bash
python -m panther.plugins.services.testers.a_rfc.history path/to/clone --out corpus/
# ... mining happens here, outside this framework ...
python -m panther.plugins.services.testers.a_rfc manifest.yaml --out out/ --repo path/to/clone
python -m panther.plugins.services.testers.a_rfc manifest.yaml --out out/ --repo path/to/clone --strict
```

### Reading the report

`report.md` is the human-facing specification: claims split into **Normative**
and **Descriptive**, the latter holding everything marked `intent: accidental`
so that recorded defects never become requirements.

The number to judge a reconstruction by is the **externally checked fraction**,
and every emitter carries it: `checked_fraction_by_req_class` in `report.json`
and `report.yaml`, and an "Externally checked fraction" section in `report.md`.
It is the fraction of *confirmed* claims that a non-model oracle — a developer
signature or a run — actually saw. For a specification mined by a model from
source and prose it is typically **0.0**, and that is the point: it measures how
much of what you are calling confirmed rests on nothing but a reading.

A bare `0.0` has two readings — nothing confirmed here was externally checked,
or nothing here is confirmed — so the denominator travels with it.
`confirmed_count_by_req_class` carries it in the structured emitters, and the
Markdown prints a class with no confirmed claims as `— (no confirmed claims)`
rather than as a fraction, so the two cases cannot be mistaken for each other.

The "Unverified anchors" section distinguishes the same way. Without `--repo`
it reads *Not checked* and names how many anchors went unverified; with one it
reads *None failed*. An empty finding list is only a clean bill of health in the
second case.

## What is not implemented

Separating what was left out on purpose from what is simply missing.

**Deliberately out of scope.** Generation. No part of this package proposes,
writes or edits a claim. Mining is model-driven and lives in agents outside the
framework, and the boundary is what lets everything here stay deterministic,
testable against fixtures and free of network access.

**No gap in this list remains open.**

The last one — nothing turned a test run into a `runtime` anchor, leaving the
headline metric aspirational — is closed by `runtime/`, which reads a coverage
report, binds it to a commit and proposes anchors for the cited lines a run
reached. It proposes rather than merges, because a runtime anchor beside a code
anchor takes a claim to `confirmed`.

Closing it exposed a sharper constraint, which belongs here rather than in a
footnote: **the adapter can only corroborate what a test suite actually
executes.** Run against MARK's own coverage it proposed zero anchors from eight
code anchors, because not one line MARK's claims cite is reached by MARK's
tests. Making `checked_fraction` non-zero for such a target needs tests written
first, which is a different undertaking from reconstructing a specification.
The criterion is also weaker than it looks: `line-executed` says a line ran, not
that anything asserted on what it did, and the promotion rule cannot tell those
apart — so every proposal records the criterion alongside the evidence.

Two earlier gaps are also closed. An anchor's `line` is now range-checked and,
when a `line_sha256` is present, digest-compared (`anchors.verify_detailed`);
and the report names what each claim's evidence *would* support, as a
`supported` field beside `stored` plus a `promotable` flag and a
`promotable_count` (`report.py`).

## Schema

The base shape is the existing requirement-manifest pattern; a manifest
carrying **none** of the extended fields must still load, with every extended
field taking its most restrictive default. Base fields per requirement:
`text`, `section`, `level`, `layer`, and optionally `testable`.

```yaml
rfc: SPEC-1
title: 'An Example Specification'
requirements:
  'spec:1.1':
    text: >-
      The system responds within the configured interval.
    section: '1.1'
    level: MUST
    layer: timing
    status: confirmed
    req_class: protocol-behavioral
    intent: intended
    signed_off_by: dev-01
    question-id: q-007
    anchors:
      - evidence_class: code
        locator: src/timer.py
        commit: '00112233445566778899aabbccddeeff00112233'
        line: 42
      - evidence_class: paper
        locator: 10.1000/xyz
```

Extended fields and their permitted values:

| Field | Permitted values | Default | Meaning |
|---|---|---|---|
| `status` | `gap`, `inferred`, `confirmed` | `gap` | Evidential standing, weakest to strongest |
| `req_class` | `protocol-behavioral`, `data-model`, `algorithmic` | `protocol-behavioral` | The verification story the requirement belongs to |
| `intent` | `intended`, `accidental`, `unknown` | `unknown` | Whether the behaviour is meant, incidental, or undetermined |
| `anchors` | list of anchor mappings (below) | `[]` | The evidence behind the claim |
| `signed_off_by` | string | absent | Developer sign-off identifier |
| `question-id` | string | absent | Pointer into an external question register |
| `testable` | boolean | absent | Compatibility read of the base field; nothing here depends on it |

Each anchor carries `evidence_class` (`code`, `paper`, `interview`, `adr`,
`runtime`) and `locator` (a repository path, a DOI, an interview id), plus an
optional `commit`, `line` and `line_sha256`. A `commit` is required before a
`code` or `runtime` anchor can be *verified* — see trap 2.

Verification depth rises with what the anchor records. A bare `locator` is
checked only for existence at the pinned commit. A `line` is additionally
range-checked against the file as it stood at that commit, so a citation past
the end of the file fails. A `line_sha256` is compared against the digest of
that line's bytes, newline stripped, so a citation that still resolves but no
longer says what it said fails too. `line_sha256` without `line` is rejected at
load: a digest of no particular line verifies nothing.

Identifiers (`section` and requirement keys) must be strings; an unquoted
`section: 4.2` is rejected loudly rather than coerced back — see trap 3.
Unknown values in any closed vocabulary raise `SchemaError`; nothing takes a
permissive default silently.

`dump()` is deterministic — `dump(load(dump(m))) == dump(m)` byte-for-byte,
which is what makes an emitted manifest citable. It does **not** reproduce a
hand-written file's bytes: PyYAML discards comments, folded scalars and key
order.

## The promotion rule

The single place a claim's evidential standing is decided is
`promotion.adjudicate`. The rule:

> A claim may be recorded as `confirmed` **only** through developer sign-off,
> runtime corroboration, or two distinct evidence classes **at least one of
> which is primary** — `code` or `runtime`. Claims resting only on mined
> decision records (`adr`) or paper prose (`paper`) are capped at `inferred`.
> A claim with no anchors at all is a `gap` — sign-off notwithstanding,
> because signing off on nothing records nothing. Understatement is always
> permitted; a stored status *above* what the evidence supports is a violation.

Adjudication is a pure function of the claim's own evidence, and every
unrecognised or absent input yields the most restrictive status. Statuses are
stored in the manifest and re-validated on load; disagreement is reported as a
violation rather than silently rewritten.

### Why the two-class route demands a primary artefact

`interview` and `paper` are two distinct classes, so a naive "any two classes"
rule promotes a claim resting on both. But a paper and an interview may be one
person speaking twice — and in the case this module was built for, the
published papers share authors with the developers who validate the claims.
Promoting on that basis launders the circularity that evidence-provenance
stratification exists to detect. `code` and `runtime` are evidence the system
itself produced rather than an account of it, so the two-class route requires
one of them present. `{interview, paper}` and `{adr, interview}` therefore
remain `inferred`; `{interview, code}` reaches `confirmed`.

## Four traps that fail silently rather than loudly

The module's strictness is not taste; each of these has a failure mode that
exits zero while producing wrong results.

1. **A promotion rule that fails open.** If `status` defaulted to `confirmed`,
   or absent evidence satisfied the rule, every claim would promote and the
   run would exit zero with a manifest that looks excellent and means nothing.
   The default is the most restrictive value, and absent evidence fails the
   predicate rather than skipping it.
2. **An anchor without a pinned commit is a plausible-looking lie.** A
   `path:line` reference into a moving tree points at different code as the
   tree advances, and nothing about it looks wrong. Verification refuses —
   raises rather than checks the working tree — when the commit is absent.
3. **YAML coerces types on load, and section numbers are the victim.**
   Unquoted `section: 4.2` loads as the float `4.2`, at which point `4.2` and
   `4.20` are the same value and `4.10` sorts before `4.9`. The same resolver
   turns bare `no`, `off` and `y` into booleans. This module rejects
   non-string identifiers loudly, because by the time the value is visible the
   collapse has already happened.
4. **`dataclasses.asdict` drops `@property` values.** Every derived quantity —
   counts, per-stratum checked fractions — vanishes from serialised output
   without complaint. Serialisation in `report.py` injects them explicitly.

### These traps are live in this codebase today

`ivy_lsp/semantic/rfc_annotations.py` (in the `ivy-lsp` nested submodule) is a
base-schema manifest loader that fails all three data-handling ways this
module guards against, and it is the reason this module is strict:

| Site | Behaviour | Trap |
|---|---|---|
| `rfc_annotations.py:88` | `except (yaml.YAMLError, OSError): return {}` | A malformed manifest reads as "no requirements" |
| `rfc_annotations.py:107` | `str(req_data.get("section", ""))` | Launders trap 3's float coercion instead of detecting it |
| `rfc_annotations.py:111` | `bool(req_data.get("testable", True))` | Fails **open** on the field deciding whether a requirement is checked |

### Integration hazard: never emit into `protocol-testing/`

`find_manifests` in that same file globs `*_requirements.yaml` under
`protocol-testing/`. A manifest with extended fields written there would have
every extended field — and the promotion rule with it — silently ignored by
that loader. That is a concrete reason, beyond the boundary rule, never to
emit this module's manifests into `protocol-testing/`.

## Known duplication to consolidate

**Several small helpers are duplicated across this package**, all
deliberately — the corpus-side subpackages share no code with the manifest
core or with each other, and hoisting a few lines would create exactly the
coupling the file-on-disk boundary exists to prevent:

| Helper | Copies |
|---|---|
| `_git` subprocess wrapper | `anchors.py` · `history/git_log.py` · `draft/gate.py` |
| stderr `_report` | `cli.py` · `history/cli.py` · `timeline/cli.py` · `views/cli.py` · `draft/cli.py` |
| SHA-256 `_digest` | `history/index.py` · `timeline/store.py` · `views/emit.py` · `draft/checkpoint.py` |
| JSONL corpus readers | `history/store.py` · `timeline/corpus.py` · `views/emit.py` |
| Forge snapshot readers | `forge/store.py` · `timeline/cli.py` · `views/emit.py` |

The `_git` wrappers deliberately omit `subprocess.run(check=True)`:
`CalledProcessError` raises without stderr attached, and every caller must
distinguish "no such path" (a result) from "no such commit" (an error). The
`_report` helpers write to stderr rather than logging, for the reason in the
next section.

They are duplicated rather than hoisted to a shared module because `history/`
and the manifest core share **no domain code** — the handoff between them is a
file on disk — and hoisting five lines would mean editing the shipped, tested
manifest core to create a coupling that buys nothing. The cost is accepted
knowingly, and recorded here in one place so the debt is legible rather than
discovered twice.

`anchors.py`'s `_git` additionally duplicates one the companion provenance
module will provide once it lands. When that arrives, consolidation should
consider all three call sites together — preserving the `check=True`
distinction in each.

## Framework gotcha: `panther.*` loggers swallow warnings

Every `panther.*` logger is configured with `propagate=False` and a handler
admitting only `ERROR`, so `logger.warning` from a plugin is silently
discarded. That is why `cli.py` writes diagnostics to stderr via its
`_report` helper rather than logging them: a gate that exits non-zero without
saying why is the exact failure this module exists to prevent. Any plugin
author emitting operator-facing diagnostics should assume the same.
