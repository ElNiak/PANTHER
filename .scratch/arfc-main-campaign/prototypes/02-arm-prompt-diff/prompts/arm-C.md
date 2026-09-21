# The reconstruction loop

One iteration turns one timeline cluster into evidence-honest claims and,
when it changed normative behaviour, a new draft revision. Work through the
clusters in ordinal order; never skip silently. Finish the cluster you
were given: claims recorded, checkpoint written, prose committed when the
change is normative, and a revision recorded and tagged. Claims without a
tagged revision leave the reconstruction incomplete however good they are,
so never stop before the tag.

The evidence-hygiene, RFC-style and claim-citation rules follow this procedure; apply them throughout.

This session has no MCP server and no `ai_rfc` command: drive the workspace with the raw substrate commands through Bash, exactly as written below, and edit YAML by hand where no command exists.

## Preconditions

- `AI_RFC_WORKSPACE` is set; `python` on `PATH` imports `ai_rfc`; run every `python -m ai_rfc …` command as written.
- The workspace holds `corpus/`, `timeline/`, `clusters/` and the pinned
  `clone/`. When a forge snapshot exists, the timeline MUST have been built
  with `--forge` **before any checkpoint is written**. Forge data
  restructures cluster ids, and checkpoints pin them.
- Use only the tools offered. Never hand-edit the claim register, the
  question register or any interview transcript; every change goes through
  a verb. Never shell out to reach what a verb already does.

## What a good iteration produces

A small set of claims, each stating only what the cluster's own diff
shows, anchored to a file that cluster changed, and cited once in a
normative sentence carrying that claim's keyword. One claim the diff
proves beats three it only suggests. Spread claims across the cluster's
changed source files, one or two per file, so the claims cover what the
cluster changed rather than one corner of it. Spend turns on reading the
diff, not on re-running tools: batch independent calls into one turn, and
never repeat a call whose result you already hold.

## One iteration

1. **Pick the next cluster**: read `$AI_RFC_WORKSPACE/timeline/clusters.jsonl` in ordinal order and take the lowest-ordinal in-window cluster that is not done. A cluster is done when `checkpoints/<id>/` holds its checkpoint, `revisions.yaml` holds an entry for it whose `kind` is `cluster` or absent (an entry with no `kind` is a cluster entry), and that entry's tag exists in `$AI_RFC_WORKSPACE/draft`; pre-seeded clusters count as done.
2. **Read its evidence once**: read `$AI_RFC_WORKSPACE/clusters/<id>/view.json` (file set, PR number), `span.diff` (paginate long diffs with `sed -n`) and `evidence/pr.json` when present. Write down the changed file
   paths exactly as the evidence prints them, and the member commit shas;
   anchors use those paths at those commits (no guessed prefixes such as
   `src/`). Skip test, fixture and build files as anchors unless nothing
   else changed. Query the corpus only when the diff alone cannot tell you
   what a changed line does: `sqlite3 $AI_RFC_WORKSPACE/corpus/index.sqlite "SELECT path, COUNT(*) c FROM file_changes GROUP BY path ORDER BY c DESC LIMIT 20"`.
3. **Mine claims**: behaviours the cluster introduces or changes, each with
   pinned anchors on a file the cluster changed (a member commit is the
   pin, and `line` is a line the diff added or changed) and NO `status`:
   edit `$AI_RFC_WORKSPACE/manifest.yaml` by hand — quote every id and section, never write `status`. Before each upsert, check the claim text against the
   diff line by line (see evidence hygiene: *Scope the claim to the
   diff*). A commit message stating a decision is an `adr` anchor; PR
   discussion explaining intent supports `intent:` but is not itself an
   anchor class. Issue all independent upserts together in one turn.
3b. If this cluster defines or changes a wire format, message, record,
    enumeration or state machine, register it, binding every field, value
    or transition to a claim you just recorded: not available in arm C — skip this step
    Then render the block and paste it into its owning section:
    not available in arm C — skip this step. Skip this step when the cluster describes only
    behaviour.
4. **Lint once, after all claims exist**: `python -m ai_rfc check $AI_RFC_WORKSPACE/manifest.yaml --out $AI_RFC_WORKSPACE/out --repo $AI_RFC_WORKSPACE/clone`. Fix every unverified
   anchor (wrong paths, commits, lines) in one pass, then lint again only
   if you changed something. If an anchor cannot be verified, narrow or
   drop that claim rather than moving it onto an untouched file.
5. **Record statuses**: read `$AI_RFC_WORKSPACE/out/report.json` (`claims[]`) and set each claim's `status` in `manifest.yaml` to exactly its `supported` value. Record exactly the supported
   value the report shows, never more. Then the strict gate: `python -m ai_rfc check $AI_RFC_WORKSPACE/manifest.yaml --out $AI_RFC_WORKSPACE/out --repo $AI_RFC_WORKSPACE/clone --strict`.
   Exit 0 is the bar.
6. **Decide spec relevance**:
   - Normative behaviour changed → write the prose in one edit per
     section, per the RFC-style rules. Every new claim gets exactly one
     normative sentence that states it, carries the keyword its `level`
     maps to (that exact keyword, capitalised) and ends with its backticked
     citation. That includes structure claims: a table or figure needs its
     own sentence such as "Senders MUST use the values in Table 2
     `claim-id`." Prose goes to the owning section (Protocol Operation,
     Data Model and Structures, Configuration and Defaults, Error
     Handling), never the Introduction. Before committing, check the list
     of new claim ids against the prose: each appears once, in a sentence
     with its own keyword.
   - Nothing normative → no prose edit; the revision entry will say so.
7. **Checkpoint**: `python -m ai_rfc draft checkpoint $AI_RFC_WORKSPACE/manifest.yaml --timeline $AI_RFC_WORKSPACE/timeline --cluster <id> --out $AI_RFC_WORKSPACE/checkpoints`.
8. **Record, build and tag the revision**: append the entry to `$AI_RFC_WORKSPACE/revisions.yaml` under `revisions:` (`cluster_id`, `checkpoint_manifest_sha256` copied from the checkpoint's `checkpoint.json`, `normative_change`, `note`). Record the
   tag `draft-<name>-NN` (two digits, monotone in cluster ordinal), the
   cluster id, an explicit `normative_change` and a one-line note. Commit
   any prose change (`git -C $AI_RFC_WORKSPACE/draft add -A && git -C $AI_RFC_WORKSPACE/draft commit -m "<message>"`), then build it: not available in this arm — skip this step and note it in the summary.
   Fix any finding it reports (long lines, non-ASCII, unused or undeclared
   references) before tagging. Then create the annotated tag
   (`git -C $AI_RFC_WORKSPACE/draft tag -a draft-<name>-NN -m "<message>"` — only after the strict manifest gate exited 0). Every revision entry needs its tag, no-change
   revisions included.
9. **Gate**: `python -m ai_rfc draft gate $AI_RFC_WORKSPACE/draft --timeline $AI_RFC_WORKSPACE/timeline --checkpoints $AI_RFC_WORKSPACE/checkpoints --questions $AI_RFC_WORKSPACE/questions.yaml --revisions $AI_RFC_WORKSPACE/revisions.yaml --out $AI_RFC_WORKSPACE/out --strict`. Exit 0 before advancing.
10. **Open questions**: a claim stuck at `gap`/`inferred` that blocks a
    section gets a question: append a `q-NNN` entry (`question`, `claim_ids`, `status: open`, `asked_at`) to `$AI_RFC_WORKSPACE/questions.yaml`.

## Failure recovery

| Failure | Response |
|---|---|
| Strict gate exit 3 | The system working. Fix anchors first (weakest link), re-adjudicate, re-run. Never hand-edit a status upward, never bypass. |
| `StaleIndexError` | Rebuild the index (`build_index`), never migrate. If the corpus itself moved, STOP, because every anchor needs re-verification. |
| Citation-gate finding | Reconcile prose or claims. Never delete a claim to silence a citation. |
| Checkpoint refused (exists) | The cluster was processed; re-running is a new decision, so investigate before deleting anything. |
| Build finding | Fix the prose or front matter, commit, rebuild once; never run `make` or edit template files. |
| Giant epoch cluster | Mine the changes whose diff lines plainly show the behaviour, one or two per changed source file; claims may cover a subset, since understatement is safe. |
| Clone HEAD ≠ corpus tip | Someone moved the clone. Restore the pin; never re-anchor to the new HEAD. |

# RFC prose for a reconstructed specification

The draft lives in `$AI_RFC_WORKSPACE/draft/`, a git repository laid out as an
adopter of `ElNiak/auto-i-d-template` (kramdown-rfc markdown; a `Makefile`
that includes the template's `main.mk`). The prose is yours; every claim of
fact in it is not. It must cite a claim the paired checkpoint manifest
holds, and the citation gate verifies that mechanically.

## Document structure

One source file `draft-<name>.md` at the repo root (exactly one; the gate
refuses zero or several). The skeleton fixes the sections; fill them, never
rename or reorder them:

| Section | Holds |
|---|---|
| Abstract, Introduction, Scope, Organization | What the system is, for a reader who never saw it. No cluster ordinals, no counts of claims added or withdrawn. |
| Conventions and Definitions, Terminology | BCP 14 boilerplate, the citation convention, the system's own terms. |
| Architecture Overview | Components and their interactions, with a cited figure. |
| Data Model and Structures | Records, messages, enumerations, state machines, as tables and figures, each introduced by a cited normative sentence. |
| Protocol Operation | Behaviour by concern, one subsection each; the normative core. |
| Configuration and Defaults, Error Handling | Keys and defaults as a table; failure behaviour. |
| Observed Accidental Behaviour | `intent: accidental` claims, described and never as requirements. |
| Security Considerations | Real analysis of the interface's exposure, even when the answer is "nothing protects it". |
| Change Log (appendix) | One entry per revision tag: the per-cluster narration goes here and nowhere else. |
| Implementation Notes (appendix) | Facts that are not requirements: class paths, test doubles, packaging, `/tmp` paths, literal return strings. Move them here; never drop a cited sentence. |

## What is not specification material

A test double, a fixture value, a class or file path, a build artefact, a
literal return string or a temporary path describes the implementation, not
the behaviour a second implementation must reproduce. It goes to
Implementation Notes with its citation, or nowhere.

## Keywords

A normative statement's keyword comes from the cited claim's `level` and the
keyword policy in `references/keyword-policy.md`: MUST needs enforcing
evidence, a default is a SHOULD, an option is a MAY. Use **exactly** the
keyword the claim's level maps to, capitalised, in the same sentence as the
citation. A weaker or missing keyword leaves the claim cited but unstated.
If the prose should be weaker, the claim's level is wrong; fix the claim
instead. Keywords appear only in normative sections, one behaviour per
sentence, one keyword per sentence.

## Claim citations

Every normative statement carries a backticked token naming its claim, as
`references/claim-citation.md` describes; read it before writing prose.
Cite each claim where it is stated: the sentence that carries its keyword
and says what it requires, worded no broader than the claim itself. A
citation in a bullet list, a Change Log entry or a caption alone does not
count as stating it. Enumerations, records and default values need a real
sentence too, for example "A sender MUST encode frame types with the
values in the table below `claim-id`." or "The default connection ID
length SHOULD be 8 bytes `claim-id`." A figure's caption additionally
cites the claims the figure depicts.

## References

The front matter's `normative:` and `informative:` lists are the document's
references. RFC and Internet-Draft entries are resolved from a sealed cache
the workspace carries. An entry the cache does not hold breaks the build and
must be written inline (`title`, `author`, `target`) instead of by number.
Never list RFC 2119 or RFC 8174: the BCP 14 boilerplate adds them itself, and
listing them again is a build warning. Cite every listed reference in the
text (`{{?RFC9000}}`-style) and list every reference you cite; an unused or
undeclared reference is an idnits warning. When no reference is needed,
add none.

## Clean compilation

idnits warns on lines over 72 characters inside artwork and tables, on
non-ASCII characters (including curly quotes and dashes), on unused
references and on keywords outside the boilerplate's reach. Keep figures
narrow, use ASCII only, and leave no empty section headings.

## Revisions

- One revision per spec-relevant round: extend the prose, commit, build, then
  tag with an **annotated** tag `draft-<name>-NN` (two digits, monotone across
  the sweep).
- Record every revision in `$AI_RFC_WORKSPACE/revisions.yaml` with, at minimum:
  `cluster_id`, `checkpoint_manifest_sha256` (from the checkpoint's
  `checkpoint.json`), an explicit boolean `normative_change`, a one-line
  `note`. A round may carry further fields; this list is not closed.
- A round that changes nothing normative still gets a revision entry with
  `normative_change: false` and a rationale. In a cluster round its citations
  are exactly the previous revision's; the gate checks. A consolidation round
  is the carve-out: it keeps every citation the previous revision carried and
  may add one, never drop one.

## The build

Before every revision tag, the draft is compiled once through the
template's own toolchain (`make txt html lint idnits`), offline, in a
scratch clone of the committed draft. It must exit 0 with no findings
before the tag is created. The reconstruction loop's own step names the
exact command for the arm in use, and the tagging step runs the build
again and refuses on findings. Never run `make` yourself and never edit
the template's own files.

# The claim-citation convention

## Form

A citation is a backticked token: `` `ai_rfc:<claim-id>` `` — for example
`` `ai_rfc:mark:proto.1` ``. The gate extracts citations with the regex
``  `ai_rfc:([^`\s]+)`  `` from the draft file **as committed at each
revision tag**, so only tagged content counts.

The backticks are load-bearing: they keep kramdown-rfc's own `{{ }}` and
`{: }` machinery away from the token, and they render as code in the
produced document, visually separating evidence pointers from prose.

## Dos

- One citation per normative statement, placed at the end of the sentence
  it supports.
- Cite the claim id exactly as it appears in the manifest, including its
  prefix (`mark:proto.1`, not `proto.1`).
- When one paragraph makes several normative statements, cite each.
- Descriptive (accidental) statements cite their claims too — the gate does
  not distinguish; the section placement does.

## Don'ts

- Never cite a claim that is not in the checkpoint manifest paired with the
  revision — the gate names every such citation and `--strict` exits 3.
- Never delete a claim from the manifest to silence a citation finding;
  reconcile the prose or fix the claim.
- Never put a citation inside a heading or the front matter.

## The no-change rule

A cluster revision recorded with `normative_change: false` carries exactly
the citations the previous revision carried. Adding or removing one there IS
a normative change; record it as one.

A consolidation is the carve-out. It keeps every citation the previous
revision carried — the gate reports drops and nothing else — so adding one,
a new figure's caption or a reference the body already relies on, is
allowed. Losing one is still a normative change.

# Keyword policy

A claim's `level` is chosen when the claim is mined and becomes the keyword
of every sentence that cites it. Choose it from the evidence, not from the
fact that the code does something:

| Level | Requires | Example evidence |
|---|---|---|
| MUST / MUST NOT | The implementation *enforces* it: a rejection, an exception, an assertion, a validation error, or a test that fails without it. | `throw new IllegalArgumentException`, a schema check, a test asserting the refusal. |
| SHOULD / SHOULD NOT | A default, a documented recommendation, or a behaviour the code prefers but does not enforce. | A default parameter value; a retry the caller may disable. |
| MAY | An option, an extension point, a behaviour behind a flag. | A configuration key with no default effect; a plugin hook. |

Implementation facts — how a value is computed, which class holds it, what a
mock returns — carry no keyword: they are descriptive, cited, and placed in
Implementation Notes or omitted.

A document in which most keywords are MUST is a mining problem, not a prose
problem: it means "the code does X" was recorded as "the system MUST X". The
lint reports the MUST fraction; treat a fraction above 0.8 as a signal to
re-examine levels, not to reword sentences.

# Figures in a reconstructed specification

A figure is prose the reader sees at once; it obeys the same rule as a
sentence: what it asserts, a claim supports.

## Form

- Fence the artwork with `~~~` on its own lines. Plain ASCII, at most 69
  columns, no tabs, no trailing whitespace (the template's lint refuses it).
- Give it an anchor and a title on the line after the closing fence:
  `{: #fig-overview title="Components of the system"}`.
- Draw boxes with `+---+` and `|`, arrows with `--->` and `<---`, and keep
  every label a term from Terminology.

## The caption cites

Within three lines after the closing fence — the attribute line counts as
the first of the three — one sentence states what the figure shows and
cites the claims it depicts, one backticked token per claim, exactly as a
normative sentence would. A figure without such a sentence is a lint
finding. A worked example is in `references/figure-example.md`.

## What not to draw

Nothing the evidence does not support: no boxes for components no claim
names, no arrows for exchanges no claim describes. Structure blocks rendered
by the substrate (bit diagrams, field tables, state tables) are pasted
verbatim and never redrawn by hand.

# Evidence hygiene for reconstruction manifests

The substrate (the installed ai_rfc package, python -m ai_rfc --help) is
built so that a claim's evidential standing is **computed from its evidence,
never asserted by its author**. These rules keep you on the right side of
that design. Each exists because the failure it prevents exits zero while
producing wrong results.

## Never write `status`

Omit `status` on every claim you write or edit. Omission is always safe: it
defaults to `gap`, the lowest rank, and a violation only fires when a
*stored* status exceeds what the evidence supports. When the report's
`claims` payload shows `supported` above `stored`, record exactly the
supported value, never more. Understatement is always permitted;
overstatement is a gate finding. The single authority is
`promotion.adjudicate`:

> `confirmed` requires developer sign-off, runtime corroboration, or two
> distinct evidence classes **at least one of which is primary** (`code` or
> `runtime`). Claims resting only on `adr` or `paper` cap at `inferred`. No
> anchors means `gap`, sign-off notwithstanding.

## Scope the claim to the diff

A reviewer reads the cluster's diff and asks whether it implements the
claim as worded. Every word beyond the diff is a claim the evidence does
not support. Before recording a claim:

- **Name only what changed.** If the diff touches one class, do not name a
  sibling it left alone. If the diff adds logging for some frame types, say
  "for the frame types it handles", not "every frame type".
- **Declaration is not behaviour.** A new field, parameter or docstring
  shows that the field exists and what it means. It does not show that it
  is populated, consulted or released unless the diff contains the line
  that does so. Claim the declaration, or anchor the line that uses it.
- **No lifecycle you did not see.** Do not add "released", "removed",
  "validated" or "in order" unless a changed line does it.
- **No numbers you did not read.** A value, size, timeout or count in the
  claim must appear literally in a changed line.
- **Level follows enforcement.** A behaviour the code performs
  unconditionally, or guards with an assert or raise, is `MUST`. A
  configurable default is `SHOULD`. An opt-in option or an API a caller
  may choose to use is `MAY`. A hard-coded value with no opt-out is not a
  SHOULD.
- **One behaviour per claim.** Split compound claims, so that a partially
  shown half does not sink the shown half.
- **Anchor where the behaviour lives.** The anchor path must be a file the
  cluster changed, spelled exactly as in the cluster evidence, and the
  `line` should be the changed line that performs the behaviour. An anchor
  on an untouched file earns nothing.

When in doubt, state less. A narrower claim the diff fully proves is worth
more than a broader one it half proves.

## Why interview + paper stays `inferred`

A paper and an interview are two classes but may be one person speaking
twice. In the case this substrate was built for, the papers share authors
with the developers who validate the claims. Promoting on two narrative
sources launders exactly the circularity that evidence-provenance
stratification exists to detect. `{interview, code}` reaches `confirmed`;
`{interview, paper}` does not.

## Anchor discipline

- Pin every `code`/`runtime` anchor to a **corpus commit**, never HEAD or a
  branch name. A `path:line` reference into a moving tree silently points
  at different code as the tree advances; verification refuses commit-less
  anchors rather than checking the working tree.
- Record `line` where the claim is about a specific statement, and
  `line_sha256` (hex digest of the line's bytes, newline stripped) when the
  citation must survive file drift. Both are verified at the pinned commit.
- `adr` locators are commit shas whose message states a decision; `paper`
  locators are DOIs; `interview` locators are transcript ids
  (`int-NNN`). None of these carries a `commit` field.

## The honesty metric

`checked_fraction_by_req_class` (report.json) is the fraction of *confirmed*
claims a non-model oracle (a person or a run) actually saw. For a spec
mined from source and prose it starts at **0.0, and that is expected**: it
measures how much of what is called confirmed rests on nothing but a
reading. It moves only through sign-offs and runtime anchors, never through
more reading.

## Four silent-failure traps (why the substrate is strict)

| Trap | Consequence if relaxed |
|---|---|
| Promotion failing open | Every claim promotes; the manifest looks excellent and means nothing |
| Anchors without pinned commits | Plausible-looking citations into a moving tree |
| YAML type coercion of identifiers | `4.10` sorts before `4.9`; quote every section and id |
| Serialisation dropping derived values | Counts and fractions vanish silently |

Treat a gate exit 3 as the system working, never as an obstacle: fix the
anchors first (they are the weakest link), re-adjudicate, re-run.
