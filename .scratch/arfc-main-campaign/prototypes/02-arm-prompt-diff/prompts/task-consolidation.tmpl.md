Consolidate the draft of this reconstruction, following the consolidation
round in your instructions exactly.

- This is consolidation $ordinal. It consolidates from the cluster
  checkpoint $base, and covers every revision recorded since the previous
  consolidation — not the whole sweep.
- Change no claim and add no evidence. The requirements in the consolidation
  checkpoint MUST be byte-identical to those in $base; only the structures
  may differ.
- Keep every citation the previous revision carried. Adding one — a new
  figure's caption, a reference the body already relies on — is expected;
  losing one is a normative change, and this round is not one.
- Record the revision with `kind: consolidation` and
  `normative_change: false`, then tag it. A consolidation is a revision like
  any other: it needs its entry and its tag before the round is finished.
- Never ask the user anything; there is no user in this session. If an
  operation is denied, do not retry it in another form — note the denial in
  your final summary and continue with what is permitted.
- End with a summary: structures declared, sections regrouped, what moved to
  each appendix, citations added, gate and lint status, and every denied or
  failed operation.
