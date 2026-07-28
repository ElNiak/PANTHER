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
| 0 | Success — reports written; violations, if any, reported but tolerated |
| 1 | The manifest could not be read, or `--repo` is not a git repository |
| 2 | Promotion violations were found and `--strict` was given |

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
optional `commit` and `line`. A `commit` is required before a `code` or
`runtime` anchor can be *verified* — see trap 2.

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
> runtime corroboration, or two distinct evidence classes at least one of
> which is not weak. Claims resting only on mined decision records (`adr`) or
> paper prose (`paper`) are capped at
> `inferred`. A claim with no anchors at all is a `gap` — sign-off
> notwithstanding, because signing off on nothing records nothing.
> Understatement is always permitted; a stored status *above* what the
> evidence supports is a violation.

Adjudication is a pure function of the claim's own evidence, and every
unrecognised or absent input yields the most restrictive status. Statuses are
stored in the manifest and re-validated on load; disagreement is reported as a
violation rather than silently rewritten.

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

`anchors.py` carries a private `_git` wrapper that duplicates the one the
companion provenance module will provide once it lands. It deliberately omits
`subprocess.run(check=True)`: `CalledProcessError` raises without stderr
attached, and this module must distinguish "no such path" (a verification
result, `False`) from "no such commit" (`UnknownCommitError`). When the
provenance module's `git()` wrapper is available, import it and delete the
duplicate — preserving that distinction.

## Framework gotcha: `panther.*` loggers swallow warnings

Every `panther.*` logger is configured with `propagate=False` and a handler
admitting only `ERROR`, so `logger.warning` from a plugin is silently
discarded. That is why `cli.py` writes diagnostics to stderr via its
`_report` helper rather than logging them: a gate that exits non-zero without
saying why is the exact failure this module exists to prevent. Any plugin
author emitting operator-facing diagnostics should assume the same.
