# `coverage/` — turning a test run into anchors

`runtime` is the strongest evidence class the promotion rule recognises and,
short of a developer signature, the only route that moves
`checked_fraction_by_req_class` off zero. Producing one used to be entirely
manual, so a reconstruction was measured against a number nothing in the
package could raise.

This subpackage reads a coverage report, binds it to the commit the run came
from, and proposes a `runtime` anchor wherever the manifest **already** cites
that exact file and line as `code` evidence and the run reached it.

## What it deliberately does not do

**It proposes; it does not merge.** A runtime anchor beside a code anchor is
two evidence classes with one primary, which takes a claim to `confirmed`. That
is a decision, so it is left looking like one: the output is
`runtime-anchors.yaml`, a mergeable fragment, and `manifest.yaml` is never
touched.

**It corroborates claims; it does not make them.** Anchors are emitted only for
lines a claim already cites. Emitting them for every covered line would grow a
manifest out of coverage, which is backwards — coverage corroborates what
somebody claimed.

**It never runs a build.** The report is ingested out of band, so `forge`
remains the only stage that reaches the network and nothing here executes the
implementation under reconstruction.

## The criterion, and its limit

Every proposal records `criterion: line-executed`. A covered line is a line
that **ran**; no coverage format records whether an assertion examined what it
did. The promotion rule cannot tell a careful runtime anchor from a lazy one,
so the criterion travels with the evidence rather than living in someone's
head.

## Binding

A report is bound to a commit or refused. The checkout must be at that commit
and hold no uncommitted changes — otherwise the lines that ran are not the
lines the commit contains, and an anchor citing it describes something else.

Coverage tools report paths relative to their own source roots, so
`be/cylab/mark/detection/OWAverage.java` has to be resolved against the
repository's `server/src/main/java/be/cylab/…`. Resolution is by longest
matching suffix over `git ls-tree` at the commit, and **ambiguity is refused**:
MARK's aggregate report merges seven modules, so the same package path under
`core/` and `server/` is a live possibility, and guessing would attach a
claim's evidence to the wrong file with nothing downstream able to tell.

`line_sha256` is computed from the blob at the commit, with the same split and
newline handling `anchors.verify_detailed` uses — so a proposed anchor verifies
by construction rather than by coincidence.

## Command

```bash
python -m …ai_rfc.coverage MANIFEST --coverage jacoco.xml --format jacoco \
    --repo path/to/clone --commit <sha> --out out/
```

Writes `runtime-anchors.yaml` (the mergeable fragment) and
`runtime-anchors.json` (the provenance: tool, report digest, criterion, every
proposal, and every code anchor that got nothing with the reason).

Exit 0 even when a run corroborates nothing — a report that reached none of the
cited lines is a finding about the test suite, not a failure of this command.

## Formats

The internal model is tool-agnostic (`ExecutedLine`, `CoverageReport`); a
reader is any callable from a path. That is not speculation: MARK is Maven with
JaCoCo and aioquic is Python with coverage.py, and both are targets today. Only
the JaCoCo reader exists so far.

It handles both shapes JaCoCo emits — a per-module `report` holding `package`
elements directly, and `report-aggregate` wrapping them in one `group` per
module — by walking `package` at any depth rather than branching on which it
is. MARK's build produces both.

## What this found about MARK

Run against MARK's own `mvn -pl server verify` coverage at
`b901f36095d7`, it proposed **zero** anchors from eight code anchors. Not one
line MARK's claims cite is executed by MARK's own test suite: the three
detection agents, `RequestHandler` and `Evidence` have no covered lines at all.

That is worth stating plainly, because it is not a defect in this adapter. It
means the depth pass for MARK needs **tests to be written first** — which is a
different undertaking from reconstructing a specification.
