# Consolidation round

The draft has grown one cluster at a time and now reads like the order it was
written in. This round changes no claim and adds no evidence. It makes the
document read like a specification.

Work only from what is already in the manifest and the draft. Do not open the
corpus, do not adjudicate, do not answer questions. If you find yourself wanting
a fact that is not already a claim, stop and record it as a question instead.

1. Read every revision recorded since the last consolidation, and the draft as
   it stands: read `$AI_RFC_WORKSPACE/revisions.yaml` for every entry recorded after the last `kind: consolidation` one — each entry is keyed by its own tag, and `git -C $AI_RFC_WORKSPACE/draft tag --list` for the tags they carry
2. Declare any structure the clusters described in prose but never registered —
   a format, message, record, enumeration or state machine whose fields you can
   each bind to an existing claim: not available in arm C — skip this step
3. Render the structures and paste each block verbatim into its owning section,
   delimiters included: not available in arm C — skip this step
4. The editorial pass. In this order:
   - Rewrite the abstract so it says what the protocol does, not how the
     document was produced.
   - Rewrite the Introduction: scope, method, organization. No cluster
     ordinals, no counts of statements added or withdrawn, no "this revision".
   - Regroup the body by concern, not by the order clusters were processed.
   - Move every per-cluster narration sentence into Appendix A, Change Log.
   - Move implementation trivia into Appendix B, Implementation Notes.
   - **Move, never drop.** A sentence you cannot place goes to an appendix. A
     citation that disappears is a normative change, and this round is not one.
   - Add the references the body already relies on, and a figure where a
     reader would otherwise have to imagine the shape. A figure's caption
     cites the claims it depicts.
5. Freeze a consolidation checkpoint. Its requirements must be byte-identical
   to the checkpoint you consolidate from; only the structures may
   differ: not available in arm C — skip this step
6. Record the revision as a consolidation, commit, build and tag:
   not available in arm C — skip this step
   `git -C $AI_RFC_WORKSPACE/draft add -A && git -C $AI_RFC_WORKSPACE/draft commit -m "<message>"`
   `git -C $AI_RFC_WORKSPACE/draft tag -a draft-<name>-NN -m "<message>"` — only after the strict manifest gate exited 0
7. Lint the result and fix what it finds: not available in arm C — skip this step

`normative_change` is `false` for this round, and it must not lose a citation the
previous revision carried. The gate rejects drops; adding a citation is allowed.

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
   belongs to, and its members under the key its kind takes: `fields:` for
   `wire-format`, `message` and `record`, `values:` for `enum`, `states:` and
   `transitions:` for `state-machine`. (The tool's second parameter is named
   `fields`, but it carries the whole body, members included.) Each field,
   value and transition names a `claim:` that must already exist in
   `requirements:`; declare the claim first, and a state is just a name.
2. `ai_rfc_draft_render` returns one block per declared structure, ordered by
   id. Paste each block **verbatim** into the section that structure names,
   delimiters included.
3. Never edit inside the delimiters. The checkpoint freezes those bytes and
   every revision tag compares against them, so a single edited character is a
   gate finding. To change a figure, change the manifest and re-render.

## Widths

`width` is a bit count, or `variable` for a trailing field of unbounded
length. Every `wire-format` field needs one, because it is drawn as a bit
diagram; a `message` or `record` field may omit it. Only the last field of a
structure may be `variable`.

## What not to draw

Architecture and sequence overviews are free-form figures, not structures —
see `ai-rfc-figures`. A structure describes data, not a story.

# Editorial

A consolidation round changes how the document reads, never what it asserts.
You are reorganising evidence that is already adjudicated.

## The rule that governs everything

**Move, never drop.** Every sentence you remove from the body goes somewhere:
narration to Appendix A, Change Log; implementation trivia to Appendix B,
Implementation Notes. If a sentence belongs nowhere, it is telling you the
document is missing a section — add the section.

A citation that disappears is a normative change, and this round records
`normative_change: false`. So your edit must keep every citation the
previous revision carried: the gate rejects a drop, and adding one — a new
figure's caption, a reference the body already relies on — is allowed. If
you genuinely believe a claim should no longer be cited, stop: that is a
cluster round's decision, not yours.

## The order

1. **Abstract.** Say what the protocol does. A reader should not learn from it
   that the document was reconstructed.
2. **Introduction.** Scope, method, organization. Strip every cluster ordinal,
   every count of statements added or withdrawn, every "this revision".
3. **Body.** Regroup by concern. The order clusters were processed is an
   artefact of how the work happened and means nothing to a reimplementer.
4. **Appendices.** Change Log first, Implementation Notes second.
5. **Figures and references.** Add a figure where a reader would otherwise have
   to imagine a shape; its caption cites the claims it depicts. Add the
   references the body already relies on.

## What you may not do

Do not adjudicate, do not open the corpus, do not answer an open question, do
not add a claim. If you want a fact that is not already a claim, record a
question and leave the prose alone.
