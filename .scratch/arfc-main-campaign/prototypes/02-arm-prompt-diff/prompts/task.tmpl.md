Reconstruct the specification of this repository progressively, following
the reconstruction loop in your instructions exactly.

- Process the clusters with ordinals $low through $high, in ordinal order,
  one full loop iteration each. Clusters outside that window are already
  marked processed by the harness, so the next-cluster rule starts at
  ordinal $low and reports none after ordinal $high.
- A cluster is finished only when its checkpoint exists, its revision entry
  and tag exist, and both strict gates exit 0.
- Stop when the next-cluster rule reports none. Never ask the user
  anything; there is no user in this session. If an operation is denied, do
  not retry it in another form — note the denial in your final summary and
  continue with what is permitted.
- End with a summary: clusters completed, claims added with their
  adjudicated statuses, revisions tagged, gate status, and every denied or
  failed operation.
