# ai_rfc — reconstructed specifications

`ai_rfc` reconstructs an RFC-style specification from a software project's own
history, and gates every claim against the evidence behind it. It lives at
`panther/plugins/services/testers/ai_rfc/`.

It makes **no model calls**. Mining a claim and writing prose are model work and
happen in agents outside the package; everything shipped here is deterministic,
fixture-testable and offline, which is what lets its output be checked rather
than trusted.

## The pipeline

Ten stages, of which eight are deterministic Python and two are not.

| # | Stage | Performer | Produces |
|---|---|---|---|
| 0 | pin | manual | a clone whose HEAD every anchor is verified against |
| 1 | history | deterministic | `corpus/*.jsonl` |
| 2 | forge | deterministic, optional, networked | PR and review evidence |
| 3 | timeline | deterministic | clusters and members |
| 4 | views | deterministic | per-cluster evidence bundles |
| 5 | **mining** | **agent** | claims in `manifest.yaml` |
| 6 | adjudicate | deterministic | `report.{json,yaml,md}` |
| 7 | **prose** | **agent** | the Internet-Draft |
| 8 | checkpoint | deterministic | a frozen manifest per cluster |
| 9 | gate | deterministic | `gate-report.json` |

`pipeline run` deliberately halts at the first non-deterministic stage and exits
0. Reaching that boundary is the pipeline working, not failing: the deterministic
substrate is current and the next move belongs to somebody else.

## Command surface

Each subpackage is its own `python -m` entry point, and all of them share one
exit-code contract.

| Command | Purpose |
|---|---|
| `a_rfc` | Validate a manifest; adjudicate claims; verify anchors |
| `a_rfc.pipeline` | `status`, `run` — drive the deterministic stages |
| `a_rfc.history` | Extract a commit corpus from a clone |
| `a_rfc.forge` | Fetch PR and review evidence from GitHub or GitLab |
| `a_rfc.timeline` | Cluster the corpus into an ordered timeline |
| `a_rfc.views` | Emit per-cluster evidence bundles |
| `a_rfc.draft` | `checkpoint`, `gate`, `completeness` |
| `a_rfc.coverage` | Propose runtime anchors from a coverage report |

## Exit codes

| Code | Meaning |
|---|---|
| 0 | Success — reports written; findings tolerated |
| 1 | An input could not be read or interpreted |
| 2 | Argument error, raised by `argparse` itself |
| 3 | Findings were reported and `--strict` was given |

Two always means the invocation was malformed and never that the evidence was.
Sharing one code between them left a scripted caller unable to tell a mistyped
flag from a real finding, and the two call for opposite responses: fix the
command, or fix the evidence.

## Consistency and completeness are different questions

`draft gate` checks that a draft is internally consistent — that each revision
cites only claims its checkpoint holds, that revision tags are monotone, that no
claim outranks its evidence. Consistency is preserved by doing nothing, so a
workspace that processed one cluster of sixty-nine and stopped passes it.

`draft completeness` asks the other question: which clusters produced no claim,
and which claims does no prose cite. It reports `unprocessed_clusters`,
`silent_clusters` (checkpointed but changed nothing), `uncited_at_head`,
`never_cited`, and `manifest_drift`.

Run both. Neither substitutes for the other.

## Further reading

The package README at `panther/plugins/services/testers/ai_rfc/README.md` carries
the claim schema, the promotion rule, and four traps in this domain that fail
silently rather than loudly.
