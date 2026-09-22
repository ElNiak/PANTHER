# 19 — Land the arm-parity fixes

Type: task (AFK)
Status: open
Claimed: —
Blocked by: [Has the owed-fixes row landed](05-has-the-owed-fixes-row-landed.md)
Parent: [ai_rfc Main Campaign, Ready to Launch](../map.md)

## Question

Graduated on 2026-09-21 from
[Rule each arm asymmetry: equalize, fix or disclose?](04-rule-each-arm-asymmetry.md), whose
resolution holds the user's rulings. **This ticket makes arms A and B equal as ruled.** Nothing is
re-decided; if the code shows a ruling cannot be implemented as stated, stop and reopen that
ticket. The evidence is `prototypes/02-arm-prompt-diff/README.md` and
`prototypes/03-parity-audit/README.md`.

Execution is carried (map Notes). ai_rfc code lands RED-test first, committed by explicit path in
`<ai_rfc>`, at $0. It waits on the owed-fixes checkpoint because it touches files that row edits
(agent CLIs, server core, tests); find that row's session with `ListAgents` first.

**What lands:**
1. **Prompts** (`driver/render.py` `SLOT_TABLES`, arms A and B):
   - D1: both arms show the literal code and adr anchors;
   - D2: B's structure slot names the fields, with a JSON example, and `structure upsert --help`
     does too;
   - D3, D4, D5: the minor wording is equalized.

   Then re-render, and re-run the prompt diff: only invocation syntax may remain between A and B.
2. **The structures skill** (`plugins/ai-rfc/skills/ai-rfc-structures/SKILL.md`): its "How" names
   operations, not tool names. A test asserts that no bundled text in `NEUTRAL_TEXTS` or
   `CONSOLIDATION_TEXTS` contains `ai_rfc_` or `ai-rfc ` invocations.
3. **A workspace status verb** returning exactly `queries.status`, with a parity twin (replacing
   `test_status_parity`'s tool-against-core shape). B's consolidation slot uses it, and
   `docs/parity.md` gets its row. Tools against verbs becomes 20/20. Choose the name so it does
   not clash with the operator's `ai-rfc status`.
4. **The corpus schema** named in `ai_rfc_corpus_query`'s description and `corpus query --help`.
   **Arm A's half landed with the owed-fixes row's review-fix wave** (ai_rfc `0e0062f`,
   2026-09-22 11:56). `server/tools.py` appends `history.index.schema_summary()` to the tool's
   `__doc__`, and `tests/server/test_parity.py`'s
   `test_the_corpus_query_description_names_every_column_of_every_table` pins it. **Arm B's half
   is still owed.** At `0e0062f`, `agent/corpus/cli.py:32-33` says only "One SELECT over the
   index." and "A single SELECT; at most 200 rows come back." So until this lands, only A sees
   the schema, the reverse of the ruling. Use the same `schema_summary()` in B's `--help`, never
   a hand-written copy, and add a twin asserting that both surfaces carry the same schema text.
   Re-read the file after the push: the row may add B's half in the same wave.
5. **Parity twins** in `tests/server/test_parity.py`:
   - claim upsert with `--anchor` (code and adr);
   - revision tag's refusal on build findings and its rollback on citation findings;
   - structure upsert of the `enum` and `state-machine` kinds;
   - record status with explicit ids and a non-vacuity guard;
   - draft lint's guard and exit code;
   - corpus query's refusal and schema read;
   - the status and guardrail refusals, pinned across arms.
6. **Transport twins**: through an MCP client against the running server, and through the
   campaign's `bin/ai-rfc` shim in a subprocess, for claim upsert with anchors, structure upsert
   and revision tag.

7. **The guard's widened scope**, added on 2026-09-22. The Ground-Truth Yardstick map's
   prevention plan (ruled by the user; not landed; see
   [Freeze prompts, pin code, and dry-run](13-freeze-pin-and-dry-run.md)) makes the PreToolUse
   guard refuse `Read`/`Grep`/`Glob` paths outside the run's workspace for every arm. **If it
   lands before this ticket**, add a parity twin that pins that refusal identically for arms A and
   B. Also check that neither arm's prompt or skill points it at a path the guard now refuses. If
   it lands after, record here which ticket carries the twin.

**Done when**: each item has a RED-then-GREEN test; the full ai_rfc suite passes (report
collected, passed, failed and skipped separately); and a re-rendered prompt diff shows only
invocation syntax between arms A and B.
