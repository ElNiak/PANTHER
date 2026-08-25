# Reconstructing Specification Documents from Implementation History: A Multivocal Related-Work Map and Experiment-Protocol Foundation for a_rfc / ai_rfc

**Pipeline**: ARS deep-research, Phase 4 (Report) | **Agent**: report_compiler_agent
**Date**: 2026-08-25 (snapshot date T for all claims) | **Status**: Full report, compiled from the Revision-1 synthesis (`10-synthesis.md`) after Devil's-Advocate re-gate PASS (`11-da-checkpoint2.md`)
**Commissioned by**: the PANTHER project, as the citable related-work grounding and experiment-protocol foundation for an ICSE 2027 tool-track paper on the `a_rfc` evidence substrate and the `ai_rfc` plugin.

<!--claim_intent_manifest
{
  "manifest_version": "1.0",
  "manifest_id": "M-2026-08-25T00:00:00Z-rep1",
  "emitted_by": "report_compiler_agent",
  "emitted_at": "2026-08-25T00:00:00Z",
  "claims": [
    {"claim_id": "R-001", "claim_text": "The gap verdict is reported in its full three-part structure: OCCUPIED under the codebook letter (occupant DynaMine at pattern granularity), UNOCCUPIED under the disclosed post-hoc glosses, and the dated re-scoped conjunction P-prime unoccupied under all three codings, over-determined by the corpus-wide absence of per-statement evidence gating.", "intended_evidence_kind": "concept-matrix coding + full-text verification", "planned_refs": ["livshits2005", "mockus2026", "idnits", "idtemplate"], "negative_constraints": [{"constraint_id": "NC-R001-1", "rule": "Never report the gloss verdict without the letter verdict; never present P-prime as the original criterion."}]},
    {"claim_id": "R-002", "claim_text": "The RQ3 negative claim appears only in parity-qualified form with its N1 denominator and near-miss register; the bare no-MCP-vs-CLI-comparison claim is reported as dead.", "intended_evidence_kind": "denominator-screened negative claim", "planned_refs": ["scaffolding2026", "devil2026", "yang2026exec", "sweagent2024", "tas2026", "bitterlesson2026"], "negative_constraints": [{"constraint_id": "NC-R002-1", "rule": "Never state the claim without denominator and near-misses."}]},
    {"claim_id": "R-003", "claim_text": "The RQ4 thin-precedent claim appears only in count form with its N2 denominator and bounding caveats: zero authoring precedents for RFC/I-D normative text.", "intended_evidence_kind": "denominator-screened count claim", "planned_refs": ["staron2024", "jimenez2024ietf", "li2024specllm", "rfc9405", "fengfar2026"], "negative_constraints": [{"constraint_id": "NC-R003-1", "rule": "Consumption-class work never counts toward the authoring verdict."}]},
    {"claim_id": "R-004", "claim_text": "Interface claims are scoped to structured-typed versus hybrid shell-via-tool; a true class-3 arm may not exist inside a Claude-Code harness.", "intended_evidence_kind": "taxonomy application", "planned_refs": ["miniswe2025", "yang2026exec", "mcpspec2025"], "negative_constraints": [{"constraint_id": "NC-R004-1", "rule": "No protocol implication rests solely on Tier C."}]},
    {"claim_id": "R-005", "claim_text": "Every experiment-protocol implication traces to coded sources; contradictions (including Tam vs dottxt) are disclosed, not averaged; no pooling of recovery numbers across link definitions; no exhaustiveness claims.", "intended_evidence_kind": "register traceability + contradiction register", "planned_refs": ["tam2024", "dottxt2024", "kalliamvakou2016"], "negative_constraints": [{"constraint_id": "NC-R005-1", "rule": "No meta-analytic pooling; every negative claim carries its denominator."}]}
  ],
  "manifest_negative_constraints": [
    {"constraint_id": "MNC-R1", "rule": "No simulated audits; the only audits referenced are 09-verification.md and the two DA checkpoints, which ran."},
    {"constraint_id": "MNC-R2", "rule": "Vendor sources capped at Tier B; no comparative claim rests on Tier C alone."}
  ]
}
-->

## Abstract

Tool papers that reconstruct specification documents from repository history need related-work grounding across four literatures that rarely meet: repository mining, artifact generation from history, agent tool interfaces, and standards authoring. This report maps those literatures and derives experiment-protocol implications for an ICSE 2027 tool-track paper on PANTHER's `a_rfc` evidence substrate and `ai_rfc` plugin. The method is a structured multivocal literature review over four commissioned research questions, executed on a single snapshot date (2026-08-25) with logged queries, three-tier source grading, an independent verification audit (26 references sampled, zero existence failures; two gradings corrected, one figure re-attributed), a second-screener audit of screening decisions, and two adversarial checkpoints. Across 87 coded sources, forge merge records undercount true integrations in the 2014-2016 platform measurements, generated documentation is evaluated against reference texts rather than against its evidence, interface class moves agent cost and consistency more than task success, and the RFC toolchain machine-gates document form while leaving claim support entirely to humans. Under the pre-committed occupation criterion, the reference position is occupied by DynaMine (2005) at mined-pattern granularity. A dated, re-gated conjunction P′ (adjudicated statuses, generated versioned normative document, per-revision evidence gating, explicit orphans) is unoccupied under every coding, a verdict over-determined by the corpus-wide absence of per-statement evidence gating. The report closes with a parity-enforced protocol sketch for a structured-versus-hybrid interface experiment: arms, enforcement, metrics, and threats.

**Keywords**: specification mining; mining software repositories; commit-PR linkage; LLM coding agents; Model Context Protocol; Internet-Draft authoring; multivocal literature review

---

## 1. Introduction

Version-control history records how an implementation came to behave the way it does, yet the documents that state what the implementation is supposed to do are usually written elsewhere and drift. Reconstructing specification-like documents from that history is an old ambition scattered across several research communities: repository miners recover the linkage structure of history, documentation researchers generate release notes and comments from it, agent researchers study how language models should operate tools over it, and the IETF maintains the discipline any normative output document must satisfy. None of the four question-scoped searches surfaced a synthesis reading these literatures against one another, and no dedicated search for prior cross-literature syntheses was run; this report reads them together, in service of a specific system.

The system under description is PANTHER's `a_rfc` substrate: a deterministic corpus-to-timeline-to-views-to-checkpoint/gate pipeline over a repository's history that produces evidence-adjudicated claim manifests, in which a claim's status is computed from its evidence and never asserted by its author. Its timeline stage clusters a first-parent commit spine into pull-request and epoch clusters, rescues squash-merged pulls through forge data, and carries orphaned history explicitly rather than dropping it. The substrate has been exercised on two targets that span the forge and merge-strategy axes: CyLab MARK (GitLab, merge-commit history, 69 clusters) and aioquic (GitHub, squash-heavy, where 238 of 342 commit clusters are recoverable only through forge data).

The companion `ai_rfc` plugin exposes that substrate to LLM coding agents through two frontends over one shared core: an MCP server with typed tools and a parity command-line interface, kept capability-identical by construction and checked by a standing parity test suite. The pairing is a design position in a live debate, and the planned experiment compares the two frontends under controlled conditions.

The overarching question, as amended at Phase 1, is: what does prior work establish, and leave open, about faithfully reconstructing specification documents from a repository's implementation history? Four commissioned questions operationalize it: how accurately commit-PR linkage can be recovered under merge, squash, and rebase integration, heuristics versus forge-API ground truth (RQ1); how prior work has reconstructed specification-like artifacts from history and review discussions, with respect to evidence modeling and fidelity evaluation (RQ2); what empirical evidence compares structured tool interfaces against CLI/shell for LLM coding agents on success, cost, error modes, and guardrails (RQ3); and what authoring discipline and toolchain automation govern RFC and Internet-Draft production, and what machine-assistance precedent exists inside it (RQ4). Two deliverables follow: a citable related-work map with a gap analysis (Sections 3-5), and design implications for an AI+MCP versus AI+CLI experiment protocol (Section 6).

## 2. Method

### 2.1 Design

The study is a structured multivocal literature review (MLR) with systematic-mapping elements, explicitly not a PRISMA systematic review. The design blueprint, committed before any search executed, gives four reasons: the question is a mapping-and-gap question rather than a focused effect question, grey literature is load-bearing for RQ3 and RQ4, the retrieval substrate cannot support exhaustiveness claims, and RQ3's velocity favors a snapshot-dated, refreshable review. Retained systematic elements: per-question search strings, logged queries, explicit inclusion/exclusion criteria, PRISMA-style flow accounting as transparency rather than compliance, and three-tier grading (A: peer-reviewed venues and RFC-series consensus documents; B: preprints with artifacts, official specifications, and documentation of the system described; C: attributable blogs and write-ups). Vendor sources about their own products are capped at Tier B, and no comparative claim may rest on Tier C alone. All four questions passed a FINER screen (averages 4.2-4.4 of 5; the RQ3 feasibility floor of 3 was mitigated by tagged grey literature).

### 2.2 Amendment before execution

A first Devil's-Advocate checkpoint returned REVISE, and a dated pre-execution amendment fixed the protocol in five ways. First, the gap claim was made falsifiable: a reference position P = {D2 adjudicated-statuses, D4 citation/evidence gating, D5 orphans-explicit} with a pre-committed three-valued verdict whose OCCUPIED condition is deliberately looser than the system's exact mechanism, admitting execution/runtime validation as an alternative to citation gating. Second, coding became three-valued (code, unstated, n/a), with agent-interface studies defaulting to n/a on history dimensions so that region cannot read as sparse by construction. Third, the false structured-versus-CLI binary was replaced by a binding three-class interface axis: structured-typed tools (class 1), hybrid shell-via-tool (class 2, including Bash executed through function calling), and raw shell (class 3). Fourth, the two negative claims were given uncapped denominators (N1 for RQ3, N2 for RQ4), turning both into counted claims over stated search universes. Fifth, a second-screener audit of include/exclude decisions was mandated, refutation-framed in both directions, with excludes over-sampled.

### 2.3 Execution and verification

Searches executed on 2026-08-25. RQ1 and RQ2 ran web-mediated with per-record verification fetches; RQ3 ran the arXiv API plus complete Semantic Scholar forward-citation sets; RQ4 ran the IETF datatracker API, arXiv, rfc-editor records, and repository fetches (full denominators appear in Section 5). Included: 15 (RQ1), 18 (RQ2), 18 (RQ3, plus tracked near-miss and secondary registers), 35 (RQ4); with the one audit-added source noted below, 87 sources entered the concept matrix.

An independent verification agent then sampled 26 references weighted toward load-bearing and Tier B/C items: zero failed existence verification, and in 14 of 26 cases the annotations reproduced source numbers verbatim. The audit corrected two gradings (RFC 9405 to Tier B as Independent-stream satire; RFC 9307 to Tier B as an IAB-stream report, pending a tier-rule amendment), fixed citation metadata, and re-attributed one figure (the "protections mitigate under 30%" finding belongs to MCPSecBench, not MSB). The second-screener audit re-screened the itemized decision layer with disagreement rates of 12.5% (RQ1), 0% (RQ2), 9.1% (RQ3), and 0% (RQ4), all below the 15% re-screen trigger. Its two flips shared one root cause, exclusion on instruments the protocol never defined, and both remedies were adopted: Petrulio et al. entered the coded set, and the Bitter Lesson comparison was promoted from the near-miss register into the coded set.

A second Devil's-Advocate checkpoint on the synthesis returned REVISE on one Critical issue: the refusal protecting the headline gap verdict rested on a characterization of DynaMine that the paper's full text contradicts. The synthesis agent fetched and read the full DynaMine paper, retracted the refusal, restructured the verdict (Section 4), and passed the delta re-gate. Three non-gating re-gate notes are folded into this report: the mandatory independent full-text re-code is extended to the P′ application, the D4 over-determination is stated, and a formal P′ delta table is added (Section 4.4).

### 2.4 Honest coverage limits

The claims in this report are documented-procedure claims, never exhaustiveness claims. The ACM Digital Library and IEEE Xplore legs of the RQ3 denominator were not executed (HTTP 403, no API access), a structural gap softened by arXiv preprint coverage of those venues. Google Scholar blocked the automated cited-by cross-check. The datatracker API exposes no body full-text search, and the IETF mail archive returned HTTP 403, leaving the mailing-list leg to secondary evidence. One denominator query was screened to depth 100 against the uncapped rule (logged), two RQ3 recall-net strings were screened only at their relevance-ranked heads, and RQ1/RQ2 recall is bounded by a single web engine returning at most ten result blocks per query. Sources are English-only, and the corpus is snapshot-dated in a field where the RQ3 literature moves monthly. A structural conflict of interest is disclosed and instrumented rather than removed: this review positions its own commissioners' artifact, the committed blueprint is an audit anchor documenting pre-search decisions rather than a blind preregistration, and the disciplining instruments are anchoring controls (the artifact's own numbers stripped from every coding instrument), adversarial checkpoints, and the independent verification audit.

## 3. Findings

### 3.1 RQ1: Commit-PR linkage under merge, squash, and rebase

Three converging studies establish that GitHub's API-visible merge record systematically missed true integrations in the platform's 2014-2016 state. Corpus-wide, only 44% of 2.55 million pull requests carried the Merged flag, four git-level heuristics recovered an extra 42% of merged PRs in a 434-project sample, and manual inspection of heuristic negatives found roughly 18.6% residual false negatives (Kalliamvakou et al., 2016) <!--ref:kalliamvakou2016--><!--anchor:quote:almost%2040%25%20of%20all%20pull%20requests%20do%20not%20appear%20as%20merged%2C%20even%20though%20they%20were-->. The heuristics originate in the first large-scale study of pull-based development, where 65% of PRs merged through GitHub facilities and heuristics added 19% (Gousios, Pinzger, & van Deursen, 2014) <!--ref:gousios2014--><!--anchor:section:abstract-->, and 24% of the field's standard PR dataset rests on the same heuristic inference in the cross-reported accounting (Gousios & Zaidman, 2014) <!--ref:gousioszaidman2014--><!--anchor:page:368-371-->. The strongest per-project validation re-labeled 798 of 1,657 "not merged" PRs as merged with only seven verified false positives, and fixed the merge-type distribution of an industrial squash-dominant workflow: squash 41.5%, merge button 24.9%, cherry-pick 8.4%, not merged 25.2% (Kononenko et al., 2018) <!--ref:kononenko2018--><!--anchor:section:Table%202-->. Each percentage keeps its own link definition and sample (never pooled) and is dated as a 2014-2016 platform measurement, per the currency audit.

The mechanism is documented: GitHub "can only detect and report merges happening through its pull request merge facilities" (Kalliamvakou et al., 2016) <!--ref:kalliamvakou2016--><!--anchor:quote:can%20only%20detect%20and%20report%20merges%20happening%20through%20its%20pull%20request%20merge%20facilities-->, its rebase-and-merge "always updates the committer information and creates new commit SHAs" (GitHub, 2026) <!--ref:githubdocs2026--><!--anchor:quote:Always%20updates%20the%20committer%20information%20and%20creates%20new%20commit%20SHAs-->, and GitLab exposes `merge_commit_sha` and `squash_commit_sha` as mutually exclusive API outcomes, keeping squash deterministically linkable from the API even where git-side heuristics fail (GitLab, 2026) <!--ref:gitlabdocs2026--><!--anchor:section:merge_requests%20API-->.

Published history is also a survivorship record. The perils lineage identified rebase as identity-destroying (Bird et al., 2009) <!--ref:bird2009--><!--anchor:page:1-10-->; developers "modify and filter the history of changes," so single-snapshot mining misses what continuous observation still sees (German et al., 2016) <!--ref:german2016--><!--anchor:quote:modify%20and%20filter%20the%20history%20of%20changes-->; and rebasing during review is a "severe threat to empirical studies that employ code review data" (Paixão & Maia, 2019) <!--ref:paixao2019--><!--anchor:quote:severe%20threat%20to%20empirical%20studies%20that%20employ%20code%20review%20data-->. The 2026 capstone measures it at ecosystem scale: of 1,118,116,350 advertised commits, 6.47% were rewritten away by force-push and 40.18% were never ingested, with history editing alone causing a 10.82% undercount in commit-based metrics (Mockus, 2026, Tier B) <!--ref:mockus2026--><!--anchor:quote:1%2C118%2C116%2C350-->. Mockus is the first source to separate "never collected" from "erased by the project," the orphan-versus-loss distinction the a_rfc substrate models per repository.

Accuracy evaluation, finally, is asymmetric. A 15-year tradition measures issue-commit link recovery: biased manual annotations against exhaustive ground truth (Bachmann et al., 2010) <!--ref:bachmann2010--><!--anchor:page:97-106-->, heuristics at 91% precision and 64% recall against a learned recovery at 89% and 78% (Wu et al., 2011) <!--ref:wu2011--><!--anchor:page:15-25-->, the finding that "on average only 60% of the commits were linked to specific issues" with probabilistic repair (Rath et al., 2018) <!--ref:rath2018--><!--anchor:quote:on%20average%20only%2060%25%20of%20the%20commits%20were%20linked%20to%20specific%20issues-->, and PR-context-aware SZZ variants (Bludau & Pretschner, 2022 <!--ref:bludau2022--><!--anchor:section:abstract-->; Petrulio et al., 2022 <!--ref:petrulio2022--><!--anchor:section:abstract-->). No equivalent exists for PR-to-commit-set recovery under squash and rebase. Tangling research supplies the damage estimate the linkage papers do not: 6-15% of changesets are tangled and at least 16.6% of files are misassociated when tangles are ignored (Herzig & Zeller, 2013) <!--ref:herzig2013--><!--anchor:page:121-130-->, and squash manufactures tangled commits by construction (a flagged inference). Traversal choice provably changes recovered histories, "consistently deliver[ing] different results," while downstream damage varies by consumer task (Kovalenko et al., 2018) <!--ref:kovalenko2018--><!--anchor:quote:consistently%20deliver%20different%20results-->; per-claim provenance consumers sit in the damage-sensitive class.

### 3.2 RQ2: Reconstructing specification-like artifacts from history

The generation lineage evaluates against reference texts and human rubrics, never against the underlying evidence. ARENA reconstructs release notes from AST-level change facts joined to issues by heuristics and evaluates with human studies against developer-written notes (Moreno et al., 2017) <!--ref:moreno2017--><!--anchor:page:106-127-->. DeepRelease learns end-to-end generation from pull requests, motivated by the finding that "more than 54% of projects produce their release notes with pull requests," and scores by ROUGE-style overlap (Jiang et al., 2021) <!--ref:jiang2021--><!--anchor:quote:more%20than%2054%25%20of%20projects%20produce%20their%20release%20notes%20with%20pull%20requests-->. PR-description generation makes the circularity explicit by directly optimizing the metric it is evaluated on (Liu et al., 2019) <!--ref:liu2019--><!--anchor:page:176-188-->. The 2025 frontier repeats the pattern: SmartNote wins on completeness and organization under comparative human rubric evaluation (Daneshyan et al., 2025) <!--ref:daneshyan2025--><!--anchor:page:1663-1686-->, and the 94,987-note ReleaseEval benchmark operationalizes fidelity as reference overlap plus human assessment across commit, tree, and diff granularities, with models best at tree granularity (Meng et al., 2025, Tier B) <!--ref:meng2025--><!--anchor:section:abstract-->. Two methodology anchors sharpen the indictment: reference-based scores over uncurated history are untrustworthy, since after dataset cleaning a retrieval baseline beat the neural systems (Liu et al., 2018) <!--ref:liu2018--><!--anchor:page:373-384-->, and change documentation has a content model, what changed and why, orthogonal to overlap, with about 40% of real commit messages deficient on it (Tian et al., 2022) <!--ref:tian2022--><!--anchor:page:2389-2401-->.

The field's evidence-model maxima exist but never co-occur in one system. DeltaDoc derives change documentation by symbolic execution, so every statement is entailed by the diff's path predicates, yet its evaluation reverts to human judgment and its scope is a single change (Buse & Weimer, 2010) <!--ref:buse2010--><!--anchor:page:33-42-->. Source Sticky Notes deterministically attaches real modification records to the dependency edges they explain, the corpus's only provenance-tracked design, evaluated only by case study (Hassan & Holt, 2004) <!--ref:hassan2004--><!--anchor:page:183-192-->. DynaMine mines co-added call pairs from revision histories and validates mined patterns by execution, computing a per-pattern status for every reported pattern (Livshits & Zimmermann, 2005) <!--ref:livshits2005--><!--anchor:section:4.2.3-->; its role in the gap verdict is examined in Section 4. Rath et al. quantify the orphan problem as their premise and then repair probabilistically rather than propagating the loss (Rath et al., 2018) <!--ref:rath2018--><!--anchor:section:abstract-->. The traceability lineage, from IR ranking (Antoniol et al., 2002) <!--ref:antoniol2002--><!--anchor:page:970-983--> to model-mediated transitive linking with a full replication package (Keim et al., 2024) <!--ref:keim2024--><!--anchor:section:abstract-->, evaluates precision and recall against gold link sets, but the object is the link set, not a generated document's claims.

Normative content demonstrably lives in PR discussions: design-pertinent paragraphs are locatable at AUC 0.87 with 81% developer agreement, surfaced but never assembled into a maintained artifact (Viviani et al., 2021) <!--ref:viviani2021--><!--anchor:page:1402-1413-->. Comment co-evolution is the nearest neighbor to versioning a reconstructed document alongside history, and its artifact is an embedded comment, not a standalone specification (Panthaplackel et al., 2020) <!--ref:panthaplackel2020--><!--anchor:page:1853-1868-->. The term "specification mining" itself defaults to execution traces: it was coined for probabilistic FSM learning from dynamic API traces with expert vetting (Ammons et al., 2002) <!--ref:ammons2002--><!--anchor:page:4-16-->, in the lineage of likely-invariant detection over executions (Ernst et al., 2001) <!--ref:ernst2001--><!--anchor:page:99-123-->; as of the 2013 survey of more than 60 API-property-inference techniques, corroborated by this review's 2026 search probe rather than asserted in present tense, version-control history is a marginal input to that field (Robillard et al., 2013) <!--ref:robillard2013--><!--anchor:page:613-637-->. Four bounded negative findings triangulate one absence: no academic system reconstructs a specification-like document and versions it with the history it derives from, no system combines computed statuses with a gated generated document, no work recovers an RFC-style normative document from VCS history, and no generation system propagates linkage loss into its output's fidelity story.

### 3.3 RQ3: Structured tool interfaces versus CLI/shell for coding agents

Interface class moves cost, consistency, and exploration far more than headline task success at current model strength. The founding agent-computer-interface result lifted GPT-4 Turbo from 11.0% to 18.0% resolved on SWE-bench Lite by interface design alone (Yang et al., 2024) <!--ref:sweagent2024--><!--anchor:section:Tables%201%20and%203-->, on the benchmark substrate of real GitHub issues (Jimenez et al., 2024) <!--ref:swebench2024--><!--anchor:section:abstract-->. By 2026 the picture inverts on success and sharpens on economics: across six tool architectures and 11,700 trajectories with capabilities held similar, interface changes consistency by a factor of 4.7, steps by -41.6%, and tokens by -56.3%, while success moves little (Xu et al., 2026, Tier B) <!--ref:devil2026--><!--anchor:section:abstract-->; a three-surface ablation holding model, harness, and prompts fixed finds pass rates interface-invariant, with the signal in cache-adjusted cost (Yang et al., 2026, Tier B) <!--ref:yang2026exec--><!--anchor:section:abstract-->; and the ACI authors' own minimal agent, which "does not have any tools other than bash," scores above 74% on SWE-bench Verified, comparable to elaborate interfaces per the maintainers' self-reported leaderboard (mini-swe-agent, Tier C, corroborated by that public leaderboard) <!--ref:miniswe2025--><!--anchor:quote:Does%20not%20have%20any%20tools%20other%20than%20bash-->. Executable code actions beat JSON tool calls by up to 20% across 17 models (Wang et al., 2024) <!--ref:wang2024codeact--><!--anchor:section:abstract-->, a result replicated on typed function-calling stubs (Bitter Lesson of Tool Calling, 2026, Tier B) <!--ref:bitterlesson2026--><!--anchor:section:abstract-->, and the vendor-side accounting of MCP token mechanics reports a 150,000-to-2,000-token reduction on one illustrative workflow (Anthropic, 2025, Tier C, corroborated) <!--ref:anthropic2025--><!--anchor:quote:150%2C000%20tokens%20to%202%2C000%20tokens-->. One mandatory disclosure: SWE-bench, SWE-agent, and mini-swe-agent share one Princeton/Stanford team, the 74% figure is self-reported on that team's leaderboard, and the independent harness-confound corpus is the mitigation.

The scaffold confound dominates. The one study built to measure exactly the MCP-versus-CLI comparison found scaffolding effects of 5-28x on cost dwarfing an unstable paired interface ratio (0.43x-29x), equal failure frequencies, failure-cost shares of 12.9% (MCP) versus 2.2% (CLI), and, decisively, that "agents frequently ignored the interface they were assigned," so unverified comparisons measure an unknown mixture (Scaffolding Matters, 2026, Tier B) <!--ref:scaffolding2026--><!--anchor:quote:Agents%20frequently%20ignored%20the%20interface%20they%20were%20assigned-->. A cross-system study argues terminal-only agents match MCP-augmented agents at a fraction of the cost, though its arms are different systems with no parity control (Terminal Agents Suffice, 2026, Tier B) <!--ref:tas2026--><!--anchor:section:abstract-->. Cost-metric discipline matters independently: raw token counts correlate weakly with billed cost because cache traffic dominates (Token Reduction Is Not Cost Reduction, 2026, Tier B) <!--ref:tokenreduction2026--><!--anchor:section:abstract-->.

Guardrail enforcement is structurally two-sided. The MCP specification states that "MCP itself cannot enforce these security principles at the protocol level" (Model Context Protocol, 2025, Tier B) <!--ref:mcpspec2025--><!--anchor:quote:MCP%20itself%20cannot%20enforce%20these%20security%20principles%20at%20the%20protocol%20level-->, and measurement finds hosts failing: across 12 MCP-specific attack types, 2,000 instances, 9 agents, and 405 real tools, every attack surface yields compromises and stronger tool-calling models are more vulnerable (Zhang et al., 2025) <!--ref:zhang2025msb--><!--anchor:section:abstract-->, with existing protections mitigating fewer than 30% of attacks (MCPSecBench, 2025, Tier B) <!--ref:mcpsecbench2025--><!--anchor:section:abstract-->. On the shell side, 69.0-98.6% of 1,709 real-world denylists (13,332 rules) are bypassable in sandbox validation, including Claude Code's built-in denylist (ShellSieve, 2026, Tier B) <!--ref:shellsieve2026--><!--anchor:section:abstract-->. Structured-tool success at realistic scale is itself low: the best model reaches 38.6% on 604 mostly-real MCP tools under execution-verified scoring (Li et al., 2025) <!--ref:li2025toolathlon--><!--anchor:section:abstract-->, and the earliest MCP-versus-function-call measurement found no automatic accuracy advantage plus measurable token and latency overhead (Luo et al., 2025, Tier B) <!--ref:luo2025mcpbench--><!--anchor:section:abstract-->. Frontier agents stay under 65% on Terminal-Bench's 89 hard tasks (Merrill et al., 2026, Tier B) <!--ref:merrill2026--><!--anchor:section:abstract-->, and process-level error anatomy over 3,977 SWE-bench-agent trajectories supplies the taxonomy for attributing failures to interface, environment, or reasoning (Beyond Final Code, 2026) <!--ref:beyondfinalcode2026--><!--anchor:section:abstract-->. Function-calling reliability has its own metric vocabulary (AST-match and executable-call accuracy, hallucinated-call detection), standardized by BFCL (Patil et al., 2025) <!--ref:patil2025bfcl--><!--anchor:page:48371-48392-->.

One divergence stays unresolved and is reported rather than averaged: format restriction degrades reasoning, with stricter constraints degrading more (Tam et al., 2024) <!--ref:tam2024--><!--anchor:page:1218-1236-->, against a structured-generation vendor's constrained-decoding rebuttal (dottxt, 2024, Tier C) <!--ref:dottxt2024--><!--anchor:section:Say%20What%20You%20Mean-->. Section 7.3 returns to it.

### 3.4 RQ4: RFC/Internet-Draft authoring discipline and machine-assistance precedent

The authoring discipline is a stack of machine-checkable constraints. Normative keywords are uppercase-only with mandatory verbatim boilerplate (RFC 2119 §6; RFC 8174) <!--ref:rfc2119--><!--anchor:section:6--> <!--ref:rfc8174--><!--anchor:section:abstract-->; document structure and split normative/informative references follow the RFC Style Guide (RFC 7322) <!--ref:rfc7322--><!--anchor:section:abstract-->; citation identity is structural, machine-resolvable data in the RFCXML v3 vocabulary (RFC 7991) <!--ref:rfc7991--><!--anchor:section:abstract-->; and even the maturity of normatively cited documents is process-regulated through the downref rules, a direct precedent for treating citation quality as a gate (RFC 3967) <!--ref:rfc3967--><!--anchor:section:abstract-->. The toolchain automates exactly the mechanical layer: kramdown-rfc converts markdown to RFCXML (Bormann, 2026, Tier B) <!--ref:kramdownrfc--><!--anchor:section:README-->, i-d-template runs CI-gated per-revision builds with lint and a pre-commit hook, publishes diffs, and submits to the datatracker by API (Thomson, 2026, Tier B) <!--ref:idtemplate--><!--anchor:section:FEATURES.md-->, and idnits mechanically enforces boilerplate, required sections, and bidirectional reference consistency (IETF Tools, 2026, Tier B) <!--ref:idnits--><!--anchor:section:README-->. Working groups already operate repository-native, per-revision workflows by consensus guidance (RFC 8874) <!--ref:rfc8874--><!--anchor:section:abstract-->, and author sign-off (AUTH48) under the RFC Editor model is the terminal human gate (RFC 9280) <!--ref:rfc9280--><!--anchor:section:abstract-->. A load-bearing negative fact follows from the toolchain documentation: idnits checks that references exist and are used, and no tool in the chain checks that a cited source supports the claim citing it. Claim-evidence support is the one allocation the discipline leaves wholly to humans.

Machine assistance around the RFC series is consumption-dominant. The consumption frontier extracts FSMs from RFCs for attack synthesis (Pacheco et al., 2022) <!--ref:pacheco2022--><!--anchor:section:abstract-->, drives protocol fuzzing from RFC grammar knowledge (Meng et al., 2024) <!--ref:meng2024chatafl--><!--anchor:section:abstract-->, and performs LLM-era extraction (Sharma & Yegneswaran, 2023) <!--ref:sharma2023--><!--anchor:section:abstract-->; an IETF-insider assessment flags LLM reliability limits for standards contexts (Arkko et al., 2024) <!--ref:arkko2024--><!--anchor:page:1-->. None of it authors normative text, and by protocol rule none of it counts toward authoring precedent. On the authoring side, the three nearest items are adjacent, not on point: LLM support for 3GPP work-package triage, by authors embedded in the organization leading those work packages, an institutional conflict named per the audit (Staron et al., 2024, Tier B) <!--ref:staron2024--><!--anchor:section:abstract-->; LLM-generated reports about IETF activity that anchor summaries to source data, but produce no Internet-Draft text (Jiménez, 2024, Tier B) <!--ref:jimenez2024ietf--><!--anchor:section:abstract-->; and VLSI specification drafting outside any SDO discipline (Li et al., 2024, Tier B) <!--ref:li2024specllm--><!--anchor:section:abstract-->. The sole machine-credited RFC is the April-1 satire, ChatGPT-drafted and human-edited in the Independent stream, Tier B under the audit's grading correction (RFC 9405, 2023) <!--ref:rfc9405--><!--anchor:page:1-->. Policy is a 2026-vintage vacuum: three individual Internet-Drafts and zero consensus documents, headlined by the recommendation that "the IETF should develop guidelines for use of AI tooling" (Farrell & Feng, 2026, Tier C) <!--ref:fengfar2026--><!--anchor:quote:the%20IETF%20should%20develop%20guidelines%20for%20use%20of%20AI%20tooling-->, alongside a survey of AI's potential in IETF specification work (Farrel, 2026, Tier C) <!--ref:farrel2026--><!--anchor:section:abstract--> and a proposed "Agent Considerations" section serving machine consumption of specs (Steele & Birkholz, 2026, Tier C) <!--ref:steele2026--><!--anchor:section:abstract-->. The empirical layer legitimizes mining IETF process data (the IAB's own workshop report, Tier B) <!--ref:rfc9307--><!--anchor:section:abstract--> and documents a mailing-list-centred production process at scale, 2.4 million emails and 8,711 RFCs (McQuistin et al., 2021) <!--ref:mcquistin2021imc--><!--anchor:page:137-149-->.

## 4. The Gap Analysis

### 4.1 Concept matrix and pre-committed criterion

The concept matrix covers 87 sources (the 86 included across the four bibliographies plus the audit-added Petrulio et al.), each coded on the five frozen dimensions (D1 input granularity, D2 evidence model, D3 output artifact, D4 fidelity evaluation, D5 honesty about unlinked data) under the Section 2.2 three-valued semantics. The reference position P = {D2 adjudicated-statuses, D4 citation/evidence gating, D5 orphans-explicit} carried a verdict criterion pre-committed before any search ran. OCCUPIED requires a single prior system coded D2 adjudicated-statuses with D4 in {citation/evidence gating, execution/runtime validation}, regardless of D5. The criterion was written deliberately looser than the a_rfc mechanism so that the evidence could satisfy it and an "unoccupied" verdict would carry information. One D4 vocabulary value was added within the dimension and logged: citation-consistency gating, the mechanical per-revision reference checking the RFC toolchain performs, kept distinct from citation/evidence gating, which gates content on per-statement support. Collapsing those two values would have manufactured a false occupation.

### 4.2 The occupation story, told honestly

The story has three stages, and this report presents all three, under a standing constraint never to present fewer. Three coding regimes recur throughout, and the table below fixes them before the narrative uses them.

| Coding | Definition | Verdict on P |
|---|---|---|
| P2 | The Phase-2 annotations as the bibliographies delivered them | UNOCCUPIED (D2 attested nowhere) |
| L | The frozen codebook's letter, applied to full text after adversarial review; **controlling** | OCCUPIED (DynaMine: D2 adjudicated-statuses, D4 execution/runtime validation) |
| G | The letter plus two post-hoc glosses logged at Revision 1 | UNOCCUPIED (DynaMine de-coded to statistical-likelihood) |

The adjudication rule is one sentence: the criterion was pre-committed against the frozen codebook's letter before any search ran, so the letter controls over both the coder's delivered annotations and any gloss minted during adjudication.

Stage one: under the Phase-2 annotations as delivered (Coding P2), no system attested D2 adjudicated-statuses and the verdict read UNOCCUPIED. The occupation-directed adversarial pass then argued each near neighbor into P as hard as possible. One recode succeeded at once: Mockus (2026) computes a status for each of 1.1 billion commits by explicit rules over two independent evidence streams, satisfying the letter of "adjudicated statuses" <!--ref:mockus2026--><!--anchor:section:abstract-->, yet occupation still failed because Mockus gates nothing (D4 none).

Stage two: the decisive refusal, of DynaMine's recode, rested on a characterization (a selection filter whose rejects vanish) that the Devil's-Advocate checkpoint tested against the paper's full text and found false. Read in full, DynaMine's §4.2.3 defines a machine-evaluable rule system over runtime evidence, "We define an error threshold" α with explicit inequalities, classifying every mined pattern as Likely usage, Likely error, or Unlikely (Livshits & Zimmermann, 2005) <!--ref:livshits2005--><!--anchor:quote:We%20define%20an%20error%20threshold-->. The statuses are carried per claim in the reported artifact: Figure 5 lists all 52 selected pairs with validated/violated counts and a computed TYPE column, unconfirmed rows included, and "empty cells represent patterns that have not been observed at runtime" <!--ref:livshits2005--><!--anchor:quote:Empty%20cells%20represent%20patterns%20that%20have%20not%20been%20observed%20at%20runtime-->. Under the codebook letter (Coding L, controlling because the criterion was pre-committed on it), DynaMine codes D2 adjudicated-statuses with D4 execution/runtime validation. **The pre-committed verdict on P is therefore OCCUPIED, with DynaMine as occupant at mined-pattern granularity.** A disclosed alternative reading exists: under two post-hoc glosses logged at Revision 1 (confirmation-versus-likelihood semantics, and rules-over-evidence-records versus human-assigned statuses), DynaMine codes statistical-likelihood and the verdict would be UNOCCUPIED (Coding G). The paper itself mixes the two semantics: thresholds "obtained empirically to match our intuition" <!--ref:livshits2005--><!--anchor:quote:obtained%20empirically%20to%20match%20our%20intuition-->, output labeled "confirmed patterns." Written during adjudication by the interested coder, after the counterexample surfaced, the glosses may be disclosed but may not control. The letter controls, and the letter says occupied.

Stage three: a dated criterion amendment (R1-A, 2026-08-25), reviewed and passed by the Devil's-Advocate re-gate, defines the conjunction the paper's novelty claim actually needs. **P′** = {D2 adjudicated-statuses on any reading, D3 generated versioned normative document, D4 per-revision citation/evidence gating, D5 orphans-explicit}. P′ enters D3 into the point and tightens D4 from one-shot validation to per-revision gating, exactly the two dimensions separating the P-occupant from the a_rfc position. The honesty note travels with it: a criterion re-scoped after the evidence is weaker than one that survived pre-commitment, P′'s components pre-exist in the frozen Phase-2 record (verified by the re-gate's gerrymander test), but their assembly is post-hoc, and presenting P′ as the original criterion would be exactly the silent narrowing the amendment regime exists to prevent. **P′ is unoccupied under all three codings.**

### 4.3 Over-determination

The re-gate added a strengthening observation: P′'s unoccupancy does not depend on the contested D2 or the added D3 at all. The D4 value citation/evidence gating, admission or refusal of generated content on per-statement evidence, is attested by no corpus system whatsoever, the surviving clause of negative finding N-RQ2-2. Any future coding dispute about DynaMine's statuses or about what counts as a document leaves the single-dimension absence intact, and with it the conjunction's emptiness.

### 4.4 Formal P′ delta table

Distances count P′ dimensions whose code differs, over applicable (non-n/a) dimensions only.

| System (tier) | D2 adjudicated-statuses | D3 generated versioned normative document | D4 per-revision evidence gating | D5 orphans-explicit | P′ distance |
|---|---|---|---|---|---|
| DynaMine 2005 (A) <!--ref:livshits2005--><!--anchor:section:4.2.3--> | Letter: yes; gloss: no | No: a pattern table, nothing versioned or document-shaped | No: one-shot runtime validation, no revision structure | No: input-side mining filters discard evidence without accounting | 3 of 4 (letter); 4 of 4 (gloss) |
| idnits / i-d-template chain (B) <!--ref:idnits--><!--anchor:section:README--> <!--ref:idtemplate--><!--anchor:section:FEATURES.md--> | No claim-evidence model | Yes: normative document with first-class revisions | No: gates reference form and consistency, never claim support | n/a | 2 of 3 |
| Mockus 2026 (B) <!--ref:mockus2026--><!--anchor:section:abstract--> | Yes (both readings) | No: a provenance dataset | No: gates nothing | Yes | 2 of 4 |
| Kononenko 2018 (A) <!--ref:kononenko2018--><!--anchor:section:Table%202--> | Contested: statuses assigned by human protocol, not computed by rules | No: link dataset with labels | No: manual verification of a dataset | Yes: full accounting | 2-3 of 4 |
| Jiménez 2024 (B) <!--ref:jimenez2024ietf--><!--anchor:section:abstract--> | No: anchoring to source data stated, mechanics unstated | No: non-normative activity reports | No | Unstated | 3 of 4 |

### 4.5 Nearest-neighbor narratives

The a_rfc position is the conjunction of three separated ancestries that no single system joins. DynaMine is the ancestor on the adjudication-plus-runtime side: computed statuses over evidence, validated by execution, attached to pattern hypotheses rather than to the claims of a maintained document. The idnits/i-d-template chain is the ancestor on the per-revision document-gating side: the only system in the corpus that gates a normative document at every revision, and it gates form, so a draft whose every citation is well-formed and irrelevant passes. The failed recode still informs: it proves per-revision gating of normative documents is normalized practice, so an evidence gate extends a real gate culture rather than landing in vacuum. Mockus is the ancestor on the adjudication-plus-orphans side: statuses computed at ecosystem scale, the rewritten-away/never-ingested distinction explicit, nothing generated downstream. One obligation carries forward with these narratives: the synthesis's mandatory independent, full-text-grounded re-code of the five delta rows extends, per the re-gate, to the P′ application itself, which was coded by the same single coder; that re-code remains outstanding (Section 7.2).

## 5. The Two Negative Claims, in Surviving Form

### 5.1 RQ3: the parity-qualified claim (the bare claim is dead)

The bare claim "no direct MCP-versus-CLI comparison exists" is dead at the snapshot date. The 2025-2026 literature contains at least four controlled two-class comparisons on coding or agentic tasks (Xu et al., 2026 <!--ref:devil2026--><!--anchor:section:abstract-->; Scaffolding Matters, 2026 <!--ref:scaffolding2026--><!--anchor:section:abstract-->; Terminal Agents Suffice, 2026 <!--ref:tas2026--><!--anchor:section:abstract-->; Yang et al., 2026 <!--ref:yang2026exec--><!--anchor:section:abstract-->). What survives is:

> Within the screened portion of the N1 denominator as of 2026-08-25, no included study directly compares class-1 (structured-typed tools) against class-2 (hybrid shell-via-tool) or class-3 (raw shell) arms under capability parity enforced by construction (capability-identical arms plus parity tests); no study compares all three classes in one design; and none operates in a specification or document-authoring domain.

The denominator travels with the claim: 1,251 unique arXiv records title-screened at 100% (four of six strings enumerated completely; the two recall nets capped at relevance-ranked heads of 120/1,743 and 120/676), complete forward-citation sets of SWE-agent and SWE-bench (5,140 records, keyword-assisted screening), a 100% enumeration of the 509 arXiv records naming the Model Context Protocol as proxy for spec citations, and two legs not executed (ACM DL and IEEE Xplore blocked; Google Scholar cross-check blocked). So do the near-misses. The six-architecture comparison holds capabilities "similar" without parity tests and has no class-3 arm <!--ref:devil2026--><!--anchor:section:abstract-->. The paired MCP/CLI study is state-verified but its arm assignment leaked <!--ref:scaffolding2026--><!--anchor:quote:Agents%20frequently%20ignored%20the%20interface%20they%20were%20assigned-->. The execute_code ablation is integrity-clean but both restricted surfaces are class 2 <!--ref:yang2026exec--><!--anchor:section:abstract-->. The ACI ablation contrasts class 2 against a class-3-leaning arm while adding capabilities, blurring the affordance/capability boundary <!--ref:sweagent2024--><!--anchor:section:Tables%201%20and%203-->. The terminal-sufficiency study compares different agent systems with parity unaddressed <!--ref:tas2026--><!--anchor:section:abstract-->, and the programmatic-versus-JSON comparison runs on benchmark tasks with typed stubs <!--ref:bitterlesson2026--><!--anchor:section:abstract-->. Every pairwise axis of the three-class construct is attested somewhere. The conjunction, three classes, parity-engineered, document domain, is attested nowhere. Describing this as thin occupation borrows the criterion vocabulary analogically only; the pre-committed criterion applies solely to the Section 4 map position.

### 5.2 RQ4: the count-form claim (zero authoring precedents)

"Thin" is a reported count, not an adjective:

> Within the N2 denominator as of 2026-08-25 (224 unique datatracker drafts matching the AI/LLM term set over title, abstract, and name, reduced to 136 on-topic drafts after removing 88 lexical false positives; 215 arXiv records fully screened across eight conjunction queries, plus 100 of 7,105 for the logged deviating ninth; 26 rfc-editor documents; one targeted RFC-series check — the source bibliography also carries a looser "at least 218 screened papers" aggregate whose extra records it does not itemize, so this report uses the itemized 215), there are zero authoring precedents for RFC or Internet-Draft normative text.

The residue: three authoring-class precedents in adjacent territory (3GPP contribution triage <!--ref:staron2024--><!--anchor:section:abstract-->, reports about IETF activity <!--ref:jimenez2024ietf--><!--anchor:section:abstract-->, VLSI specifications <!--ref:li2024specllm--><!--anchor:section:abstract-->), one machine-credited satirical RFC entered through a human editor <!--ref:rfc9405--><!--anchor:page:1-->, three individual policy drafts with zero consensus documents <!--ref:fengfar2026--><!--anchor:quote:the%20IETF%20should%20develop%20guidelines%20for%20use%20of%20AI%20tooling-->, and a consumption-dominant remainder of roughly twenty papers that never counts toward authoring. Three caveats bound the claim. The datatracker exposes no body full-text, so undisclosed AI-authored drafts without AI-topic metadata are invisible to the instrument, and the screening pass observed (as a labeled observation, not a sourced claim) stylistic hallmarks of LLM drafting already inside the subject-matter bucket. The mailing-list leg rests on secondary evidence after an HTTP 403. And a counter-reading is voiced rather than suppressed: the community's own policy signals are uniformly cautionary, so the zero count partly reflects that the discipline's owners have not endorsed the activity, while the undisclosed-drafting observation cuts back, since the activity is entering without the discipline, which argues for building the gate.

## 6. Experiment-Protocol Implications

This section elevates the analysis phase's design-implication register into a protocol sketch for the AI+MCP versus AI+CLI experiment on the a_rfc substrate, targeting MARK (GitLab, merge commits) and aioquic (GitHub, squash-heavy). Every element traces to coded sources, and none rests on Tier C alone.

### 6.1 Arms

Under the binding three-class taxonomy, the three surfaces available in a Claude-Code harness code as follows.

| Arm | Surface | Interface class |
|---|---|---|
| A | `arfc_*` MCP tools | Class 1: schema-declared, typed, validated per-operation arguments |
| B | `arfc` CLI invoked through the Bash tool | Class 2: hybrid shell-via-tool (structured wrapper, free-form command payload) |
| C | Raw substrate `python -m` commands through the Bash tool | Also class 2: same wrapper, different command family |

The honest consequence: a true class-3 arm (agent text piped to a terminal with no function-calling layer, the mini-swe-agent construction <!--ref:miniswe2025--><!--anchor:quote:Does%20not%20have%20any%20tools%20other%20than%20bash-->) may not exist inside a Claude-Code harness, because every shell interaction there transits the Bash function-calling tool. Headline claims must therefore say "structured-typed versus hybrid shell-via-tool," never "MCP versus raw shell." Adding a genuine class-3 arm would require a different harness, and the harness-confound evidence (scaffold effects of 5-28x on cost <!--ref:scaffolding2026--><!--anchor:section:abstract-->) prohibits mixing harnesses inside one comparison; a class-3 datapoint, if wanted, runs as a separate, explicitly harness-confounded companion measurement, never pooled. The B-versus-C contrast is cheap and informative on its own: it isolates within-class affordance (curated command vocabulary versus generic module invocation) with the wrapper held constant. Parity remains the backbone: both frontends drive one core, the parity suite is the standing construct check, any capability delta is a stop-ship, and the parity evidence ships with the paper; every near-miss had parity asserted at best and leaked at worst.

### 6.2 Enforcement

The assignment-leakage finding <!--ref:scaffolding2026--><!--anchor:quote:Agents%20frequently%20ignored%20the%20interface%20they%20were%20assigned--> converts into three mandatory elements. Arm assignment is enforced by removal or allowlist, not by denylist or prompt instruction, because string-level denylists are 69.0-98.6% bypassable <!--ref:shellsieve2026--><!--anchor:section:abstract-->: the MCP arm runs with Bash absent or its substrate invocations denied, and the CLI arms run with the MCP server unmounted. Every transcript is mechanically audited for out-of-arm invocations, the assignment-integrity rate is a reported metric per cell, and integrity-violated runs are excluded by pre-registered rule. Attempts to reach the forbidden surface are counted and taxonomized as data, connecting to the two-sided guardrail literature <!--ref:zhang2025msb--><!--anchor:section:abstract--> <!--ref:mcpsecbench2025--><!--anchor:section:abstract-->; enforcement is measured under identical policies on both sides rather than assumed.

### 6.3 Metrics

One primary metric per hypothesis, pre-registered; the rest descriptive or corrected.

| Family | Protocol element | Motivating evidence |
|---|---|---|
| Task success (primary outcome) | State-verified outcomes recomputed from the substrate's own checkpoints (final checked_fraction; gate exits as raw counts with uncertainty), never agent self-report | Execution-verified scoring <!--ref:li2025toolathlon--><!--anchor:section:abstract-->; containerized verification <!--ref:merrill2026--><!--anchor:section:abstract-->; self-report unreliability <!--ref:scaffolding2026--><!--anchor:section:abstract--> |
| Cost (primary cost metric) | Cache-adjusted billed cost per run and per completed unit; raw tokens secondary; failure-cost share per arm | Cache-adjusted cost carries the signal <!--ref:yang2026exec--><!--anchor:section:abstract-->; cache traffic dominates billed cost <!--ref:tokenreduction2026--><!--anchor:section:abstract-->; failure-cost shares 12.9% versus 2.2% <!--ref:scaffolding2026--><!--anchor:section:abstract--> |
| Reliability | pass^k over at least k repeats per arm-target cell, plus consistency across repeats; single-run comparisons rejected | Consistency is where interface effects live (factor 4.7) <!--ref:devil2026--><!--anchor:section:abstract--> |
| Trajectory | Pre-registered aggregations only (final checked_fraction, tokens-to-threshold, trajectory AUC), all recomputable from checkpoints by reviewers | Blueprint conclusion-validity constraints; substrate determinism |
| Error taxonomy (two-sided) | Class-1 channel: invalid or hallucinated calls, argument-validation failures, format violations; class-2 channel: command syntax and composition failures; process-level attribution to interface, environment, or reasoning | Function-calling metric vocabulary <!--ref:patil2025bfcl--><!--anchor:page:48371-48392-->; process-level error anatomy <!--ref:beyondfinalcode2026--><!--anchor:section:abstract--> |
| Guardrails | Bypass-attempt counts and outcomes per arm under identical policies; any hardening's cost reported | Attack-surface measurement <!--ref:zhang2025msb--><!--anchor:section:abstract-->; denylist fragility <!--ref:shellsieve2026--><!--anchor:section:abstract--> |
| Latency / wall time | Secondary only, API conditions logged | Corpus-wide practice; token cost is the stable metric |

### 6.4 Threats to validity, pre-stated

| Class | Threat | Mitigation |
|---|---|---|
| Construct | Arm difference is capability, not affordance | Parity by construction plus parity tests; capability delta is a stop-ship; affordance/capability boundary defined ex ante |
| Construct | "CLI arm" misread as raw shell | Three-class taxonomy applied and disclosed; claims scoped to structured versus hybrid (Section 6.1) |
| Construct | Success gameable by self-report | State-verified outcomes only <!--ref:li2025toolathlon--><!--anchor:section:abstract--> |
| Internal | Arm-assignment leakage | Removal/allowlist enforcement, transcript audits, integrity rate reported <!--ref:scaffolding2026--><!--anchor:quote:Agents%20frequently%20ignored%20the%20interface%20they%20were%20assigned--> |
| Internal | Prompt or skill asymmetry | Identical-modulo-syntax prompts, published diff, versioned freeze |
| Internal | Time-varying API conditions; cache asymmetry | Interleaved randomized run order; cache-adjusted cost primary <!--ref:yang2026exec--><!--anchor:section:abstract--> |
| External | n = 2 targets | Characterize both targets on the map's dimensions; scope claims to these regimes; determinism makes replication cheap; never generalize |
| External | Model churn | Interface-level framing; model pinned; snapshot-dated map |
| Conclusion | Variance; multiplicity; rare gate exits; post-hoc aggregation | Repeats with non-parametric tests and effect sizes; one primary metric per hypothesis; raw counts with uncertainty; aggregations pre-registered and recomputable |

The experiment should be preregistered (OSF) with these designations fixed ex ante. Task-suite validity is inherited from the substrate rather than from benchmark curation, which matters because more than 15% of popular terminal-benchmark tasks were found reward-hackable (What Makes a Good Terminal-Agent Benchmark Task, 2026, Tier B) <!--ref:taskquality2026--><!--anchor:section:abstract-->.

## 7. Discussion

### 7.1 What the map means for the paper's claims

On RQ1, every design commitment in the a_rfc timeline stage (forge records as ground truth, heuristic links labeled as such, squash rescue from forge data, orphans carried explicitly) corresponds to a measured failure mode of the alternative documented in Section 3.1. What the literature does not supply is an accuracy number for the reconstruction itself: no published precision/recall exists for pre-squash commit-cluster recovery, so the aioquic 238/342 disclosure has no published comparison point and the artifact's own accounting is contribution and limitation at once. On RQ2, a per-revision citation gate is not a refinement of the reference-overlap evaluation tradition but a different fidelity construct, one the field's own methodology papers motivate <!--ref:liu2018--><!--anchor:page:373-384--> <!--ref:tian2022--><!--anchor:page:2389-2401-->. On RQ3, the one-core-two-frontends design answers the literature's two loudest warnings, parity leakage and the harness confound, and the experiment's expected effects sit in cost, consistency, and error taxonomy rather than headline success; if the domain-transfer mechanisms (gate density, long horizon, evidence-volume cost mechanics) prove wrong, the contribution is instrument quality and domain transfer, not effect discovery. Each mechanism extrapolates from coded sources: a schema-dense, gate-mediated workflow exercises the class-1 invalid-call and argument-validation error channel and the class-2 command-composition channel on nearly every step (Patil et al., 2025 <!--ref:patil2025bfcl--><!--anchor:page:48371-48392-->; Zhang et al., 2025 <!--ref:zhang2025msb--><!--anchor:section:abstract-->); structured-tool success collapses precisely on long-horizon multi-step workflows, where consistency effects also compound (Li et al., 2025 <!--ref:li2025toolathlon--><!--anchor:section:abstract-->; Xu et al., 2026 <!--ref:devil2026--><!--anchor:section:abstract-->); and the documented token mechanics of definition overhead and round-tripped intermediate results bind hardest when the payload is a corpus of evidence records (Anthropic, 2025, Tier C, corroborated) <!--ref:anthropic2025--><!--anchor:quote:150%2C000%20tokens%20to%202%2C000%20tokens-->. On RQ4, the novelty claim is a counted claim over a stated denominator, and the gate occupies the one allocation the toolchain's own structure leaves human <!--ref:idnits--><!--anchor:section:README-->.

The gap statement the paper can defend is the three-part structure of Section 4, and only that structure: P occupied under the pre-committed letter by DynaMine at pattern granularity, unoccupied under disclosed post-hoc glosses, and P′ unoccupied under every coding with the D4 over-determination as insurance. Dropping the letter verdict would re-open the wound the adversarial process closed.

### 7.2 Limitations

Three limitations are methodological. First, the post-counterexample re-scope is the report's structural weakness: P′ was assembled after DynaMine occupied P, and although its components pre-date the counterexample and the re-gate's gerrymander and de-qualification tests passed, a criterion that survives pre-commitment is stronger than one amended after the evidence, and the paper must say which claim it makes. Second, the concept-matrix codes were assigned by a single coder; the independent verification audit checked sources, gradings, and screening decisions but not the Phase-3 matrix codes, and the mandated independent, full-text-grounded re-code of the five delta rows, extended to the P′ application, has not yet run. Third, coverage is bounded as Section 2.4 states, and a snapshot refresh is required before camera-ready.

Several evidential hedges carry into any downstream use. The precise Kalliamvakou corpus figures rest on the bibliography's logged full-PDF read; the audit corroborated the direction but hit an authwall on the numbers <!--ref:kalliamvakou2016--><!--anchor:page:2035-2071-->. The Herzig-and-Zeller squash connection is an inference, flagged at every use <!--ref:herzig2013--><!--anchor:page:121-130-->. Venue labels for 2026 preprints other than the three independently confirmed (Toolathlon, MSB, Beyond Final Code) rest on arXiv comment fields. Jiménez's anchoring mechanics are coded from its abstract <!--ref:jimenez2024ietf--><!--anchor:section:abstract-->. The MCPSecBench under-30% figure still awaits a full-text check <!--ref:mcpsecbench2025--><!--anchor:section:abstract-->. Security-fragility findings (ShellSieve, MSB, MCPSecBench) are cited at aggregate-statistics level only; no bypass strings, payloads, or attack procedures are reproduced in this report. Author lists for several 2026 preprints are carried by first author plus the arXiv identifier as the verified handle. Three conflict-of-interest lines are part of the record: the single-team concentration behind SWE-bench, SWE-agent, and mini-swe-agent <!--ref:sweagent2024--><!--anchor:section:Tables%201%20and%203-->; Staron et al.'s embedding in the organization leading the 3GPP work packages they study <!--ref:staron2024--><!--anchor:section:abstract-->; and the structural meta-conflict that this review positions its commissioners' own artifact, disciplined by the instruments named in Section 2.4.

### 7.3 Unresolved contradictions

Two disagreements remain open at the snapshot and are reported rather than averaged. The structured-output cost dispute is live: a Tier-A industry-track study finds format restriction degrades reasoning, with stricter formats degrading more <!--ref:tam2024--><!--anchor:page:1218-1236-->, while a structured-generation vendor's rebuttal reports constrained decoding without degradation <!--ref:dottxt2024--><!--anchor:section:Say%20What%20You%20Mean-->. The quality asymmetry favors Tam et al., but the mechanisms differ (prompt-constrained versus decoder-constrained emission), so both may hold in their own regimes; the protocol consequence is to measure format-violation and schema-error rates directly in the class-1 arm rather than import either conclusion. Second, the interface-versus-model-strength story rests at one point on an informal, intra-team comparison: mini-swe-agent's self-reported leaderboard score set against the same team's SWE-agent ACI results (Section 3.3). No controlled, cross-team replication of the raw-shell-versus-hybrid contrast exists, part of the RQ3 gap stated in Section 5.1, and the proposed experiment cannot itself close it inside one harness (Section 6.1).

## 8. Conclusion

Across four literatures and 87 coded sources, the map shows a field that measures linkage loss but does not propagate it, generates documents but evaluates them against other documents, studies agent interfaces on code tasks with parity asserted rather than enforced, and machine-gates every mechanical property of normative documents except whether their claims are supported. The pre-committed occupation criterion did what pre-commitment is for: pressed adversarially, it found a 2005 occupant at pattern granularity, and the surviving novelty claim moved, by dated and re-gated amendment, to a conjunction that is unoccupied under every coding and over-determined by a single dimension no system attests. The experiment protocol distilled here inherits the field's hardest-won lessons: fix the harness, enforce and verify arm assignment, spend primary attention on cache-adjusted cost and consistency rather than headline success, verify outcomes from substrate state, and report enforcement two-sidedly. The remaining obligations before camera-ready are known and finite: the independent full-text re-code including P′, the MCPSecBench full-text check, the tier-rule stream amendment decision, and a snapshot refresh.

## AI-Assistance Disclosure

This report was produced by an AI multi-agent research pipeline (ARS deep-research) comprising scoping, methodology, bibliography, verification, synthesis, adversarial-review, and report-compilation agents, gated by adversarial checkpoints: a Devil's-Advocate review of the protocol (REVISE, amendment adopted), an independent source-verification and second-screener audit (26 references sampled, zero existence failures; two gradings corrected, one figure re-attributed), and a Devil's-Advocate review of the synthesis (REVISE on one critical factual error, corrected against primary full text; re-gate PASS). The pipeline ran on Claude (Anthropic; model id claude-fable-5, "Claude Fable 5") orchestrating general-purpose subagents, under the ARS deep-research skill v2.9.4; the Tier-C Anthropic engineering source cited in Section 3.3 is a publication of the model vendor. Human involvement comprised commissioning the research questions, approving checkpoint resolutions, and final review of this report by the commissioning researcher. Within the logged limits of Sections 2.3-2.4 and 7.2, all findings were verified against cited sources, and human oversight applies to any downstream use in the ICSE 2027 submission.

## Revision 2 Changelog (2026-08-25, Phase 6)

Applied per `13-editorial.md` (MINOR REVISION: Majors 1-3, Minors 1-6), `14-ethics.md` (CONDITIONAL: C-1; advisories A-1, A-3), and `15-da-checkpoint3.md` (REVISE delta: Major 1, Minors 1-3).

1. **§5.2 traveling denominator** (Editorial Major 1): "at least 218 fully screened arXiv records" corrected to the bibliography's itemized 215 across the eight conjunction queries; the source's un-itemized "at least 218" aggregate is named and set aside explicitly.
2. **§4.2 coding legibility** (Editorial Major 2): three-row P2/L/G coding-definition table added with per-coding P verdicts, plus a standalone adjudication-rule sentence (the letter controls because the criterion was pre-committed on it).
3. **§7.3 dangling reference** (Editorial Major 3): "Gap 3" replaced by the named gap ("the RQ3 gap stated in Section 5.1"); the informal intra-team comparison identified as mini-swe-agent's self-reported leaderboard score against the same team's SWE-agent ACI results.
4. **Coded-source count unified** (Editorial Minor 1; DA-3 Minor 2): 87 coded sources (86 included plus the audit-added Petrulio et al.), composition stated once in §2.3 and §4.1; abstract and §8 updated.
5. **Abstract audit line** (Editorial Minor 2; DA-3 Minor 1): "zero failures" replaced by "zero existence failures; two gradings corrected, one figure re-attributed"; the same completion applied in the Disclosure.
6. **Pipeline jargon excised** (Editorial Minor 3): "extraction rollup" → toolchain documentation; "anchoring strip" glossed as anchoring controls; "plus registers" glossed at first use; "promoted from the register" expanded; "the synthesis binds downstream prose" replaced by a standing-constraint phrasing; §6 intro's "synthesis's design-implication register" → "analysis phase's design-implication register".
7. **§6 opening comma splice fixed** (Editorial Minor 4): "targets MARK" → "targeting MARK".
8. **§3.3 Tier-C hedge** (Editorial Minor 5): "within noise of elaborate interfaces" → "comparable to elaborate interfaces per the maintainers' self-reported leaderboard".
9. **Spelling** (Editorial Minor 6): "organisation" → "organization".
10. **§1 negative claim denominated** (DA-3 Major 1): the "no prior synthesis" sentence re-scoped to the logged searches, with the absence of a dedicated cross-literature-synthesis search stated.
11. **§7.1 Gap-3 mechanism grounding** (DA-3 Minor 3): one sentence tracing gate density, long horizon, and evidence-volume cost mechanics to their coded sources (Patil et al., 2025; Zhang et al., 2025; Li et al., 2025; Xu et al., 2026; Anthropic, 2025).
12. **AI-Assistance Disclosure extended** (Ethics C-1, mandatory): foundation model and versions named (Claude, model id claude-fable-5, "Claude Fable 5"; general-purpose subagents; ARS deep-research skill v2.9.4); the vendor nexus with the Tier-C Anthropic source disclosed; human roles specified (commissioning, checkpoint approvals, final review).
13. **Qualifier made non-detachable** (Ethics A-1): the Disclosure's verification sentence now leads with "Within the logged limits of Sections 2.3-2.4 and 7.2".
14. **Aggregate-only security citation note added to §7.2** (Ethics A-3).

Not changed, deliberately: the three-stage occupation story, both bolded verdicts, the occupant-before-gap ordering in the abstract, the §5 denominator-and-near-miss structure, the Tam-versus-dottxt non-resolution, and the outstanding-obligations list (per `15-da-checkpoint3.md` Observation 2, these survive intact). The Claim Intent Manifest is left byte-intact per the one-shot pre-commitment rule; none of the fourteen changes alters a manifest claim.

## References

All entries were existence-verified during Phase 2 or the verification audit; the verification channel per entry is logged in the Phase-2 bibliographies. For several 2022-2026 preprints the full author list was not independently disambiguated in-session; there the arXiv identifier is the verified handle and entries appear title-first or with "et al." (Section 7.2). Tier gradings (A/B/C) live in the map artifact, with corrections G1/G2 applied (RFC 9405 and RFC 9307 as Tier B).

Ammons, G., Bodík, R., & Larus, J. R. (2002). Mining specifications. *Proceedings of POPL 2002*, 4-16. https://doi.org/10.1145/503272.503275

Anthropic. (2025, November 4). *Code execution with MCP: Building more efficient agents* [Engineering blog post]. https://www.anthropic.com/engineering/code-execution-with-mcp

Antoniol, G., Canfora, G., Casazza, G., De Lucia, A., & Merlo, E. (2002). Recovering traceability links between code and documentation. *IEEE Transactions on Software Engineering, 28*(10), 970-983. https://doi.org/10.1109/TSE.2002.1041053

Arkko, J., Lindbo, D., & Klitte, M. (2024). Do large language models dream of sockets? [Extended abstract]. *ACM/IRTF Applied Networking Research Workshop (ANRW '24)*.

Bachmann, A., Bird, C., Rahman, F., Devanbu, P., & Bernstein, A. (2010). The missing links: Bugs and bug-fix commits. *Proceedings of FSE-18*, 97-106. https://doi.org/10.1145/1882291.1882308

*Beyond final code: A process-oriented error analysis of software development agents in real-world GitHub scenarios*. (2026). ICSE 2026 Research Track. arXiv:2503.12374. (Authors Chen, Ma, & Jiang per verification audit.)

Bird, C., Rigby, P. C., Barr, E. T., Hamilton, D. J., German, D. M., & Devanbu, P. (2009). The promises and perils of mining Git. *Proceedings of MSR 2009*, 1-10. https://doi.org/10.1109/MSR.2009.5069475

*The bitter lesson of tool calling* [Preprint]. (2026). arXiv:2608.06370.

Bludau, P., & Pretschner, A. (2022). PR-SZZ: How pull requests can support the tracing of defects in software repositories. *Proceedings of SANER 2022*. IEEE. https://doi.org/10.48550/arXiv.2206.09967

Bormann, C. (2026). *kramdown-rfc* [Software repository, as of 2026-08-25]. GitHub. https://github.com/cabo/kramdown-rfc

Bradner, S. (1997). *Key words for use in RFCs to indicate requirement levels* (RFC 2119, BCP 14). RFC Editor. https://www.rfc-editor.org/info/rfc2119

Bush, R., & Narten, T. (2004). *Clarifying when standards track documents may refer normatively to documents at a lower level* (RFC 3967, BCP 97). RFC Editor. https://www.rfc-editor.org/info/rfc3967

Buse, R. P. L., & Weimer, W. (2010). Automatically documenting program changes. *Proceedings of ASE 2010*, 33-42. https://doi.org/10.1145/1858996.1859005

Daneshyan, F., He, R., Wu, J., & Zhou, M. (2025). SmartNote: An LLM-powered, personalised release note generator that just works. *Proceedings of the ACM on Software Engineering, 2*(FSE), 1663-1686. https://doi.org/10.1145/3729345 (Corrigendum: https://doi.org/10.1145/3771920)

dottxt. (2024). *Say what you mean* [Vendor blog post].

Ernst, M. D., Cockrell, J., Griswold, W. G., & Notkin, D. (2001). Dynamically discovering likely program invariants to support program evolution. *IEEE Transactions on Software Engineering, 27*(2), 99-123.

Farrel, A. (2026). *The emerging application of AI in IETF specifications* (Internet-Draft draft-farrel-catalist-ai4all-00). IETF Datatracker.

Farrell, S., & Feng, C. (2026). *Dealing with LLMs in IETF discussions* (Internet-Draft draft-fengfar-led-01). IETF Datatracker.

Flanagan, H., & Ginoza, S. (2014). *RFC style guide* (RFC 7322). RFC Editor. https://www.rfc-editor.org/info/rfc7322

German, D. M., Adams, B., & Hassan, A. E. (2016). Continuously mining distributed version control systems: An empirical study of how Linux uses Git. *Empirical Software Engineering, 21*(1), 260-299. https://doi.org/10.1007/s10664-014-9356-2

GitHub, Inc. (2026). *Pull request merges* [Documentation, as of 2026-08-25]. https://docs.github.com/en/pull-requests/reference/pull-request-merges

GitLab, Inc. (2026). *Merge requests API* [Documentation, as of 2026-08-25]. https://docs.gitlab.com/ee/api/merge_requests.html

Gousios, G., Pinzger, M., & van Deursen, A. (2014). An exploratory study of the pull-based software development model. *Proceedings of ICSE 2014*. ACM. (Record: TU Delft repository.)

Gousios, G., & Zaidman, A. (2014). A dataset for pull-based development research. *Proceedings of MSR 2014*, 368-371. https://doi.org/10.1145/2597073.2597122

GPT, C., & Barnes, R. L. (Ed.). (2023). *AI sarcasm detection: Insult your AI without offending it* (RFC 9405, Independent stream, April 1). RFC Editor. https://www.rfc-editor.org/info/rfc9405

Hassan, A. E., & Holt, R. C. (2004). Using development history sticky notes to understand software architecture. *Proceedings of IWPC 2004*, 183-192. https://doi.org/10.1109/WPC.2004.1311060

Herzig, K., & Zeller, A. (2013). The impact of tangled code changes. *Proceedings of MSR 2013*, 121-130. https://doi.org/10.1109/MSR.2013.6624018

Hoffman, P. (2016). *The "xml2rfc" version 3 vocabulary* (RFC 7991). RFC Editor. https://www.rfc-editor.org/info/rfc7991

IETF Tools. (2026). *idnits* [Software repository, as of 2026-08-25]. GitHub. https://github.com/ietf-tools/idnits

Jiang, H., Zhu, J., Yang, L., Liang, G., & Zuo, C. (2021). DeepRelease: Language-agnostic release notes generation from pull requests of open-source software. *Proceedings of APSEC 2021*. IEEE. arXiv:2201.06720.

Jimenez, C. E., Yang, J., Wettig, A., Yao, S., Pei, K., Press, O., & Narasimhan, K. (2024). SWE-bench: Can language models resolve real-world GitHub issues? *ICLR 2024*. arXiv:2310.06770.

Jiménez, J. (2024). Automating IETF insights generation with AI. arXiv:2410.13301.

Kalliamvakou, E., Gousios, G., Blincoe, K., Singer, L., German, D. M., & Damian, D. (2016). An in-depth study of the promises and perils of mining GitHub. *Empirical Software Engineering, 21*(5), 2035-2071. https://doi.org/10.1007/s10664-015-9393-5

Keim, J., Corallo, S., Fuchß, D., Hey, T., Telge, T., & Koziolek, A. (2024). Recovering trace links between software documentation and code. *Proceedings of ICSE 2024*. https://doi.org/10.1145/3597503.3639130

Knodel, M., et al. (2022). *Report from the IAB workshop on Analyzing IETF Data (AID) 2021* (RFC 9307, IAB stream). RFC Editor. https://www.rfc-editor.org/info/rfc9307

Kononenko, O., Rose, T., Baysal, O., Godfrey, M. W., Theisen, D., & de Water, B. (2018). Studying pull request merges: A case study of Shopify's Active Merchant. *Proceedings of ICSE-SEIP 2018*, 124-133. https://doi.org/10.1145/3183519.3183542

Kovalenko, V., Palomba, F., & Bacchelli, A. (2018). Mining file histories: Should we consider branches? *Proceedings of ASE 2018*, 202-213. https://doi.org/10.1145/3238147.3238169

Leiba, B. (2017). *Ambiguity of uppercase vs lowercase in RFC 2119 key words* (RFC 8174, BCP 14). RFC Editor. https://www.rfc-editor.org/info/rfc8174

Li, J., et al. (2025). The Tool Decathlon: Benchmarking language agents for diverse, realistic, and long-horizon task execution. *ICLR 2026* (poster). arXiv:2510.25726.

Li, M., Fang, W., Zhang, Q., & Xie, Z. (2024). SpecLLM: Exploring generation and review of VLSI design specification with large language model. arXiv:2401.13266.

Liu, Z., Xia, X., Hassan, A. E., Lo, D., Xing, Z., & Wang, X. (2018). Neural-machine-translation-based commit message generation: How far are we? *Proceedings of ASE 2018*, 373-384. https://doi.org/10.1145/3238147.3238190

Liu, Z., Xia, X., Treude, C., Lo, D., & Li, S. (2019). Automatic generation of pull request descriptions. *Proceedings of ASE 2019*, 176-188. https://doi.org/10.1109/ASE.2019.00026

Livshits, B., & Zimmermann, T. (2005). DynaMine: Finding common error patterns by mining software revision histories. *Proceedings of ESEC/FSE 2005*, 296-305. https://doi.org/10.1145/1081706.1081754

Luo, Z., et al. (2025). Evaluation report on MCP servers. arXiv:2504.11094.

McQuistin, S., Karan, M., Khare, P., Perkins, C., Tyson, G., Purver, M., Healey, P., Iqbal, W., Qadir, J., & Castro, I. (2021). Characterising the IETF through the lens of RFC deployment. *Proceedings of IMC '21*, 137-149. https://doi.org/10.1145/3487552.3487821

*MCPSecBench* [Preprint]. (2025). arXiv:2508.13220.

Meng, Q., Ren, Z., & Visser, J. (2025). ReleaseEval: A benchmark for evaluating language models in automated release note generation. arXiv:2511.02713.

Meng, R., Mirchev, M., Böhme, M., & Roychoudhury, A. (2024). Large language model guided protocol fuzzing. *Proceedings of NDSS 2024*.

Merrill, M. A., Shaw, A. G., Carlini, N., Li, B., Raj, H., et al. (2026). Terminal-Bench: Benchmarking agents on hard, realistic tasks in command line interfaces. arXiv:2601.11868.

*mini-swe-agent: The minimal AI software engineering agent* (v2). (2025-2026). [Software repository, as of 2026-08-25]. GitHub. https://github.com/SWE-agent/mini-swe-agent

Mockus, A. (2026). Was it never collected, or rewritten away? A commit-provenance dataset separating ingestion gaps from upstream history edits across the World of Code. arXiv:2607.02774. https://doi.org/10.48550/arXiv.2607.02774

*Model Context Protocol specification* (Revision 2025-06-18). (2025). https://modelcontextprotocol.io/specification

Moreno, L., Bavota, G., Di Penta, M., Oliveto, R., Marcus, A., & Canfora, G. (2017). ARENA: An approach for the automated generation of release notes. *IEEE Transactions on Software Engineering, 43*(2), 106-127. https://doi.org/10.1109/TSE.2016.2591536

*One goal, many commands: Characterizing denylist fragility in AI agents* [ShellSieve; Preprint]. (2026). arXiv:2606.15549.

Pacheco, M. L., von Hippel, M., Weintraub, B., Goldwasser, D., & Nita-Rotaru, C. (2022). Automated attack synthesis by extracting finite state machines from protocol specification documents. *IEEE Symposium on Security and Privacy 2022*. arXiv:2202.09470.

Paixão, M., & Maia, P. H. (2019). Rebasing in code review considered harmful: A large-scale empirical investigation. *Proceedings of SCAM 2019*. IEEE. https://ieeexplore.ieee.org/document/8930883

Panthaplackel, S., Nie, P., Gligoric, M., Li, J. J., & Mooney, R. (2020). Learning to update natural language comments based on code changes. *Proceedings of ACL 2020*, 1853-1868. https://aclanthology.org/2020.acl-main.168/

Patil, S. G., et al. (2025). The Berkeley Function Calling Leaderboard (BFCL): From tool use to agentic evaluation of large language models. *Proceedings of ICML 2025, PMLR 267*, 48371-48392.

Petrulio et al. (2022). SZZ in the time of pull requests [Preprint]. arXiv:2209.03311.

Rath, M., Rendall, J., Guo, J. L. C., Cleland-Huang, J., & Mäder, P. (2018). Traceability in the wild: Automatically augmenting incomplete trace links. *Proceedings of ICSE 2018*, 834-845. https://doi.org/10.1145/3180155.3180207

Robillard, M. P., Bodden, E., Kawrykow, D., Mezini, M., & Ratchford, T. (2013). Automated API property inference techniques. *IEEE Transactions on Software Engineering, 39*(5), 613-637. https://doi.org/10.1109/TSE.2012.63

Saint-Andre, P. (Ed.). (2022). *RFC editor model (version 3)* (RFC 9280). RFC Editor. https://www.rfc-editor.org/info/rfc9280

*The scaffolding matters more than the interface: A controlled comparison of MCP and CLI tool use across seven agent scaffoldings, five language models, and one software task*. (2026). arXiv:2608.08654. (First author resolvable as M. Alier Forment per verification audit; artifact: https://doi.org/10.5281/zenodo.21851992)

Sharma, P., & Yegneswaran, V. (2023). PROSPER: Extracting protocol specifications using large language models. *Proceedings of HotNets '23*. https://doi.org/10.1145/3626111.3628205

Staron, M., Ström, J., Karlsson, A., & Meding, W. (2024). Using generative AI to support standardization work: The case of 3GPP. arXiv:2408.12611.

Steele, O., & Birkholz, H. (2026). *Agent considerations* (Internet-Draft draft-steele-agent-considerations-00). IETF Datatracker.

Tam, Z. R., Wu, C.-K., Tsai, Y.-L., Lin, C.-Y., Lee, H.-y., & Chen, Y.-N. (2024). Let me speak freely? A study on the impact of format restrictions on performance of large language models. *EMNLP 2024 Industry Track*, 1218-1236. arXiv:2408.02442.

*Terminal agents suffice for enterprise automation* [Preprint]. (2026). arXiv:2604.00073.

Thomson, M. (2026). *i-d-template* [Software repository, as of 2026-08-25]. GitHub. https://github.com/martinthomson/i-d-template

Thomson, M., & Stark, B. (2020). *Working group GitHub usage guidance* (RFC 8874). RFC Editor. https://www.rfc-editor.org/info/rfc8874

Tian, Y., Zhang, Y., Stol, K.-J., Jiang, L., & Liu, H. (2022). What makes a good commit message? *Proceedings of ICSE 2022*, 2389-2401. https://doi.org/10.1145/3510003.3510205

*Token reduction is not cost reduction* [Preprint]. (2026). arXiv:2607.12161.

Viviani, G., Famelis, M., Xia, X., Janik-Jones, C., & Murphy, G. C. (2021). Locating latent design information in developer discussions: A study on pull requests. *IEEE Transactions on Software Engineering, 47*(7), 1402-1413. https://doi.org/10.1109/TSE.2019.2924006

Wang, X., Chen, Y., Yuan, L., Zhang, Y., Li, Y., Peng, H., & Ji, H. (2024). Executable code actions elicit better LLM agents. *ICML 2024*. arXiv:2402.01030.

*What makes a good terminal-agent benchmark task* [Preprint]. (2026). arXiv:2604.28093.

Wu, R., Zhang, H., Kim, S., & Cheung, S.-C. (2011). ReLink: Recovering links between bugs and changes. *Proceedings of ESEC/FSE 2011*, 15-25. https://doi.org/10.1145/2025113.2025120

Xu, X., et al. (2026). The devil is in the interface: Evaluating how tool architecture shapes coding agent behavior. arXiv:2608.11386.

Yang, H., et al. (2026). When does restricting a coding agent to execute_code help? A regime and agent-design ablation. *KDD 2026 Agentic SE workshop* (non-archival). arXiv:2607.10569.

Yang, J., Jimenez, C. E., Wettig, A., Lieret, K., Yao, S., Narasimhan, K., & Press, O. (2024). SWE-agent: Agent-computer interfaces enable automated software engineering. *NeurIPS 2024*. arXiv:2405.15793.

Zhang, D., et al. (2025). MCP Security Bench (MSB): Benchmarking attacks against Model Context Protocol in LLM agents. *ICLR 2026*. arXiv:2510.15994.

---

*End of 12-report.md. Compiled 2026-08-25 by report_compiler_agent from the Revision-1 synthesis after DA re-gate PASS; Revision 2 applied same day per the Phase-5 reviews (13-editorial.md, 14-ethics.md, 15-da-checkpoint3.md). Word count and self-gate results recorded in the compilation log returned to the coordinator.*
