# history — a citable commit-history corpus

This module extracts a repository into a structured, citable record of its
history: a deterministic JSONL corpus of commit metadata and per-file change
rows, plus a derived SQLite index for querying. It exists to feed claim
mining; deciding *which* commits carry intent is the miner's judgement, not
this module's.

**It makes no model calls and opens no sockets.** The only external process
it touches is `git`, run against a local clone.

## CLI

```bash
python -m panther.plugins.services.testers.a_rfc.history \
  path/to/pinned-clone \
  --out corpus/ \
  --cap 1000 \
  --no-index
```

`--out` is the destination directory, created if absent. `--cap` bounds the
file rows recorded per commit (default 1000, see below). `--no-index` writes
the JSONL corpus without building the SQLite index.

Exit codes:

| Code | Meaning |
|---|---|
| 0 | Corpus written; any capped commits are reported on stderr |
| 1 | The repository could not be read — including a shallow clone, whose truncated history would otherwise pass silently |

## How to use

### Clone at full depth

```bash
git clone https://host/org/project.git clone/      # NOT --depth 1
python -m panther.plugins.services.testers.a_rfc.history clone/ --out corpus/
```

Extraction refuses a shallow clone rather than extracting a truncated history
(trap 4), so `--depth 1` fails at the first step. Pin what you extracted:
record `git rev-parse HEAD` alongside the corpus, because every anchor a miner
writes later names a commit, and the corpus is what justifies the choice.

Cost is dominated by the file-changes pass, so extraction is roughly linear in
`(commits x files touched)` rather than in repository size. A 969-commit Java
project with 3,611 file rows extracts in about half a second.

### Query the index to decide what to read

This is the corpus's main use during mining. Open it through `open_index`
rather than with `sqlite3` directly — the digest check that refuses a stale
index (trap 5) lives in that function, and bypassing it is how you get
confident answers from superseded data.

```python
from pathlib import Path
from panther.plugins.services.testers.a_rfc.history.index import open_index

conn = open_index(Path("corpus"))            # raises StaleIndexError if the JSONL moved on
rows = conn.execute("""
    SELECT path, COUNT(*) AS churn
    FROM file_changes
    WHERE path LIKE '%.java'
    GROUP BY path ORDER BY churn DESC LIMIT 20
""").fetchall()
conn.close()
```

Churn ranks files by how often they changed, which is a better reading order
than the directory tree: the code that moved most is usually the code carrying
the design decisions. Two cautions. A high-churn path may have been **deleted**,
so intersect the result with `git cat-file -e <sha>:<path>` before anchoring to
it. And a rename shows up as *two* paths with split histories — the corpus
preserves the link in `previous_path`, but a naive churn query does not follow
it.

### Mine the history itself, not only the tree

`commits.jsonl` carries subjects and bodies, and a commit message stating a
design decision is a mined decision record — evidence class `adr` in the
manifest schema. Searching subjects for a behaviour is often how an otherwise
unexplainable piece of code becomes explicable, and dating a file's first
appearance or deletion answers questions the working tree cannot.

```sql
SELECT sha, authored_at, subject FROM commits
WHERE lower(subject) LIKE '%<term>%' ORDER BY authored_at DESC;
```

Remember that `adr` is weak evidence: on its own it caps a claim at `inferred`,
because a commit message is an account of the system rather than the system.

### Re-measure before trusting the constants

The figures under *Measured design constants* and *The per-commit cap* were
taken on one reference history and do not transfer. On a repository whose
largest commit touches fewer files than the cap, the cap never fires and
`truncated_count` is zero; on one with vendored imports it may drop most rows.
`report.json` states what actually happened for the run you did, and that is the
number to quote.

## Artifacts

Four files land in `--out`. Two extractions of the same repository produce
identical bytes: commits are sorted by `(authored_at, sha)`, file rows by
`(sha, path)`, and every record is serialised with sorted keys. Byte-stability
is what makes an extraction citable at all.

**`commits.jsonl`** — one commit per line:

| Field | Meaning |
|---|---|
| `sha`, `parents` | Commit id and parent ids |
| `author_name`, `author_email` | Author identity as recorded |
| `authored_at`, `committed_at` | ISO-8601 timestamps as git renders them (see trap 1b) |
| `subject`, `body` | Message split |
| `is_merge` | Derived: more than one parent |
| `file_count` | The **true** number of paths the commit touched, cap or no cap |
| `files_recorded` | Rows actually written to `files.jsonl` |
| `files_truncated` | True exactly when the cap dropped rows |

**`files.jsonl`** — one path-touch per line:

| Field | Meaning |
|---|---|
| `sha` | The commit that touched this path |
| `path` | The path *after* the change; for a rename or copy this is the destination, never the source (see trap 2) |
| `status` | Bare git status letter (`A`, `C`, `D`, `M`, `R`, `T`), similarity score stripped |
| `previous_path` | The source path for a rename or copy; `null` otherwise |

**`report.json`** — what the extraction produced and dropped: `commit_count`,
`file_row_count`, `truncated` (the shas whose file lists were capped), and
`truncated_count`.

**`index.sqlite`** — tables `commits`, `file_changes` (indexed on `path`),
and `corpus_source`, which records SHA-256 digests of the two JSONL files at
build time. The index is **derived and disposable: rebuild, never migrate.**
`open_index` re-hashes the JSONL files and refuses with `StaleIndexError`
when either digest no longer matches (trap 5).

## Measured design constants

Taken on a 1,276-commit reference history close in shape to the intended
target. Re-measure before trusting them on another repository.

| Pass | Command shape | Time | Size | Default |
|---|---|---|---|---|
| Metadata incl. body | `git log -z --format=…` | **0.02 s** | 553 KB | always on |
| File changes + status | `--name-status` | **4 s** | 120 MB | on, **capped** |
| Line counts | `--numstat` | **60 s** | 124 MB | **not implemented** |

Metadata is effectively free; everything expensive is per-file.

**`--numstat` is not implemented, and the 60 s figure is why.** On a small
fixture the cost is invisible; on a real repository it is a minute per run —
a defect that passes its own tests. If line counts are ever needed they must
be opt-in, never ambient.

**Recorded dead end: `--no-renames` was measured and changed nothing.** The
cost of the file-changes pass is diffing content, not rename detection.
Anyone optimising this pass will reach for that flag first; it is recorded
here so nobody spends the hour.

## The per-commit cap

`DEFAULT_FILE_CAP` is **1000**, overridable per run with `--cap`. The
measurement behind it: of the 1,276 reference commits, 23 exceed a thousand
files — vendoring and submodule imports, genuine history but near-pure noise
for intent mining — and one touches **247,455** on its own. Uncapped, those
few commits dominate a corpus of 1.52 million rows.

Confirmed on the first real run: 1,295 commits extracted in 4.85 s, storing
**40,106 rows against 1,395,469 true (commit, file) pairs — a 97.1%
reduction — by truncating 23 commits.** Nothing about the repository's shape
is lost: `file_count` preserves the true magnitude on every affected record;
only the row-by-row enumeration of bulk imports is dropped.

There is deliberately **no `is_bulk_change` field.** The cap is a storage
bound. "Is this commit intent-bearing" is a mining judgement, and freezing it
into the corpus would bake one miner's threshold into every future consumer.
Any such flag can be recovered from `file_count` at mining time.

## Eight traps that fail silently rather than loudly

Each of these produces plausible-looking output while being wrong. Traps 1a
and 1b are sub-items of trap 1 because they are the same lesson at a finer
grain: every delimiter you choose can appear in the data, and every format
you assert against is a rendering that can change.

1. **A commit message containing your record separator splits one commit
   into two well-formed-looking records.** Bodies are arbitrary text; any
   printable delimiter can appear in one. When it fires, the commit count
   inflates, a body ends mid-sentence, and every resulting record still
   parses. The fix is NUL (`git log -z`) — the one byte git guarantees
   cannot appear in a message. Validated on all 1,276 reference commits:
   1,276 records, zero wrong field counts.

   **1a. NUL protects the record boundary, not the fields — the body can
   contain the *field* separator too.** This fired during construction: the
   fixture written to prove trap 1 carries `\x1f` in its body, and `\x1f` is
   also the field delimiter, so a plain `split` yielded nine fields for an
   eight-field format. With the field-count guard in place it fires loudly —
   `GitError: expected 8 fields …, got 9`. Without the guard it is silent:
   the body is truncated at its first `\x1f` and nothing looks wrong. The
   fix is `split(_UNIT, _METADATA_FIELDS - 1)` — the body is the last field,
   so the remainder keeps embedded separators while a short record is still
   caught. The guard stays even though `maxsplit` now prevents the case it
   caught; the residual — a separator inside an *earlier* field, such as an
   author name — remains unhandled and is pathological enough to accept.

   **1b. Git renders a UTC `%aI` as `…Z`, not `+00:00`, and the spelling has
   changed across git versions.** Feeding
   `GIT_AUTHOR_DATE="2026-03-01T00:00:00+00:00"` and asserting
   `authored_at == "2026-03-01T00:00:00+00:00"` matches nothing on git 2.55.
   When it fires it looks like a broken extractor; it is a rendering
   difference. **Never assert a timestamp against a literal.** Compare
   against what the corpus itself returned, or assert a date prefix. Fixture
   *inputs* may use any form git accepts; only assertions are affected.

2. **`--name-status` emits three fields for renames and copies; a two-field
   parser corrupts far more than the rename row.** A rename row is `R100`,
   the *old* path, then the *new* one. Measured: 124,082 rows — **8% of the
   total** — are rename rows. The damage cascades: the unconsumed
   destination token is read as the *next* status, which swallows the
   following commit marker, so that commit's rows are attributed to the
   rename's sha and its own sha never appears in the file table. One
   mis-parsed rename therefore corrupts an unbounded run of later commits,
   not one row. When the break-test forced the two-field path, one wrong
   fixture path became three simultaneous failures — a missing sha, a wrong
   file list, and a truncation count of 2 where 1 was correct. At 8% of rows
   on a real repository, a two-field parser does not produce a slightly
   wrong corpus; it produces an unusable one. Parse by status letter: `R`
   and `C` consume two path tokens, `path` keeps the destination,
   `previous_path` the source.

3. **A silent per-commit cap makes a 247,455-file import look like a small
   commit.** When it fires, nothing fires — the record simply looks modest.
   `file_count`, `files_recorded` and `files_truncated` make the truncation
   visible on every affected record, and the CLI reports the total on
   stderr at the end of the run.

4. **`git log` on a shallow clone returns a truncated history that looks
   complete.** No error, no warning, just fewer commits — and every
   aggregate computed downstream is quietly wrong. Extraction refuses up
   front: `git rev-parse --is-shallow-repository` answering `true` raises
   `ShallowRepositoryError`, and the CLI exits 1.

5. **A stale SQLite index answers confidently from old data.** Nothing about
   the answer looks wrong. The index carries SHA-256 digests of the JSONL
   files it was built from; `open_index` re-hashes them and raises
   `StaleIndexError` rather than guessing.

6. **Git's commit order has no tiebreak.** Default output is
   reverse-chronological, and commits sharing a timestamp order
   arbitrarily, so byte-stability is not free. When it fires it looks like
   a test that flakes on one machine and passes everywhere else. Sort
   explicitly — `(authored_at, sha)` for commits, `(sha, path)` for file
   rows. `--date-order` and `--reverse` constrain traversal, not ties; they
   would pass on most repositories and flake on one.

## Composition: a file on disk, not an import

The corpus feeds claim mining, which runs in agents outside this framework.
The miner's output is a manifest, validated by the manifest modules at the
`a_rfc` package root. The corpus is also read by the sibling `timeline/`
subpackage (and, through the timeline, by `views/`) — corpus-side stages
that, like this one, re-parse the JSONL themselves rather than importing it. **The handoff between the two is a file on disk, not
an import** — `history/` deliberately shares no domain code with its parent
package, stated plainly here because a reader seeing a subpackage will
reasonably assume otherwise. The only repetition is two small utilities
(`_git`, `_report`), duplicated rather than hoisted; the parent README's
consolidation note records all four copies.

## Framework gotcha: `panther.*` loggers swallow warnings

Every `panther.*` logger is configured with `propagate=False` and a handler
admitting only `ERROR`, so a logged warning from this module would be
discarded before anyone saw it. Diagnostics therefore go to stderr through
`cli.py`'s `_report` helper — the truncation note and every error message
included.
