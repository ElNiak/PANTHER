# a_rfc Forge Stage (P4) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The `forge/` fetch stage (GitHub + GitLab adapters, immutable disk snapshots), forge-informed timeline restructuring (PR enrichment + squash rescue), and per-member patch/evidence emission in views — validated live on aioquic (GitHub); the live GitLab fetch for MARK is a user-confirmation point.

**Architecture:** `forge/` is the ONLY networked stage: it fetches once, writes an immutable sorted snapshot, and everything downstream reads only the cache. `timeline/` gains an optional forge input that enriches merge-commit PR clusters with their PR numbers and re-clusters single-parent merge commits (squash/rebase results) into one-member PR clusters (`provenance: forge_squash`); everything else stays an epoch member, honestly. `views/` copies each PR cluster's forge evidence beside the diffs and can emit per-member patches.

**Tech Stack:** stdlib `urllib.request` only (no new deps); tokens via `GITHUB_TOKEN`/`GITLAB_TOKEN` env (never stored); tests use an injected transport — no network in tests, canned JSON pages only.

**Spec:** `docs/superpowers/specs/2026-08-25-arfc-progressive-rfc-design.md` (D2, D3, forge schemas, traps 1/3).

## Global Constraints

Same as the vertical-slice plan: worktree root, `PY=<master>/.venv/bin/python`, `SSLKEYLOGFILE=` prefix on pytest, black/isort before commit, stderr `_report`, byte-stable sorted output, break-tests for every trap, commit style `feat(a_rfc): …`, explicit `git add` paths. New:
- The fetcher NEVER prints or stores a token; `meta.json` records only `authenticated: true|false`.
- Snapshot writer refuses an existing snapshot directory; consumers take an explicit snapshot path (no implicit "latest").
- A `(#N)` subject hint is NEVER used to cluster (trap 1) — only a forge sha-match restructures.
- The live `gitlab.cylab.be` fetch is a USER CONFIRMATION point; the GitLab adapter is otherwise validated by canned-page tests.
- aioquic live run needs a token: use `GITHUB_TOKEN=$(gh auth token)` at invocation, never persisted.

### Interfaces produced (used by every task)

```python
# forge/fetch.py
class ForgeError(RuntimeError): ...
@dataclass(frozen=True)
class ForgeTarget: host: str; owner: str; repo: str; kind: str  # github|gitlab
def parse_url(url: str, host_kind: str | None) -> ForgeTarget
def fetch_pull_data(target, transport, token) -> tuple[pulls, reviews, comments]
# transport: Callable[[str, dict[str, str]], tuple[int, dict[str, str], bytes]]
#   (url, headers) -> (status, response_headers, body); default wraps urllib.
# forge/store.py
def write_snapshot(out_root: Path, target, clone_head: str, fetched_at: str,
                   authenticated: bool, pulls, reviews, comments) -> Path
def read_snapshot(snapshot_dir: Path) -> dict  # meta + record lists
# timeline/build.py (extended)
def build_timeline(commits, forge_pulls=None) -> tuple[Cluster, ...]
#   forge_pulls: list of pull dicts (from read_snapshot) or None
# timeline/cli.py: --forge SNAPDIR; guards meta.clone_head == corpus tip
# views/emit.py: emit_views(..., forge_snapshot: Path | None = None,
#                           patches: str = "span")  # span|members|both
```

Record fields (sorted keys, one JSON per line): `pulls.jsonl` by number — number, title, body, state, author, created_at, merged_at, merge_commit_sha, squash_commit_sha, head_sha, base_ref, url, labels. `reviews.jsonl` by (pr_number, id) — pr_number, id, reviewer, state, submitted_at, body. `comments.jsonl` by (pr_number, created_at, id) — pr_number, id, kind ∈ review_comment|issue_comment|discussion_note (closed vocab, raise otherwise), author, created_at, body, path, line. `meta.json` — api_base, authenticated, clone_head, complete, fetched_at, host, kind, owner, repo, tool_version.

Rescue semantics (timeline): for each MERGED pull whose `merge_commit_sha` (or GitLab `squash_commit_sha`) is a corpus commit: ≥2 parents → attach `pr_number` to the existing PR cluster (provenance stays `merge_commit`); exactly 1 parent → that spine commit becomes a one-member PR cluster, `provenance: forge_squash` (epochs split around it; rebase-merges are approximated by their final commit — recorded in the README). Pull not matching any corpus commit → counted in `unmatched`, reported on stderr, never guessed. `timeline.json.forge_snapshot` becomes `{dir_name, meta_sha256}`.

---

### Task F1: Snapshot store

**Files:** Create `panther/plugins/services/testers/a_rfc/forge/__init__.py`, `.../forge/store.py`. Test: `tests/unit/plugins/services/testers/a_rfc/forge/{__init__.py,test_store.py}`.

Steps (TDD as established): tests — `write_snapshot` creates `forge/<host>__<owner>__<repo>/snapshot-<fetched_at>/` with the four files, sorted as specified, byte-identical for permuted input lists; refuses an existing snapshot dir (`ForgeError`); `read_snapshot` round-trips; unknown comment `kind` raises at write. Implement with the established `_digest`-free writer (sorting + `json.dumps(sort_keys=True)`); `fetched_at` must be filesystem-safe (`2026-08-25T10-00-00Z` — colons replaced). Commit `feat(a_rfc): immutable forge snapshot store`.

### Task F2: Fetch adapters with injected transport

**Files:** Create `.../forge/fetch.py`. Test: `.../forge/test_fetch.py`.

Key code (the novel parts — transport injection, pagination, both adapters):

```python
def _default_transport(url, headers):
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request) as response:
            return response.status, dict(response.headers), response.read()
    except urllib.error.HTTPError as error:
        return error.code, dict(error.headers or {}), error.read()
    except urllib.error.URLError as error:
        raise ForgeError(f"could not reach {url}: {error.reason}") from None

def _get_json(url, transport, token, api_kind):
    headers = {"Accept": "application/json", "User-Agent": "panther-a-rfc"}
    if token:
        headers["Authorization"] = (
            f"Bearer {token}" if api_kind == "github" else f"Bearer {token}"
        )
    status, response_headers, body = transport(url, headers)
    if status == 403 or status == 429:
        raise ForgeError(
            f"{url} answered {status} (rate limit or forbidden); set "
            f"GITHUB_TOKEN/GITLAB_TOKEN and retry"
        )
    if status != 200:
        raise ForgeError(f"{url} answered {status}")
    return json.loads(body), response_headers
```

- GitHub pagination: follow `Link` header `rel="next"`; GitLab: `x-next-page` header. Both loop with `per_page=100`.
- GitHub endpoints: `/repos/{o}/{r}/pulls?state=all`, per merged PR `/pulls/{n}/reviews`, `/pulls/{n}/comments` (kind review_comment), `/issues/{n}/comments` (kind issue_comment). `squash_commit_sha` is always null (GitHub reuses merge_commit_sha).
- GitLab endpoints: `/api/v4/projects/{owner}%2F{repo}/merge_requests?state=all`, per MR `/merge_requests/{iid}/notes` (skip `system: true`; kind discussion_note); reviews list stays empty.
- Tests: canned page dicts; a two-page pull list via fake Link/x-next-page headers; 403 raises with the token hint; token present ⇒ Authorization header sent (assert via recording transport); GitLab system notes skipped.

Commit `feat(a_rfc): forge fetch adapters for GitHub and GitLab`.

### Task F3: Forge CLI

**Files:** Create `.../forge/cli.py`, `.../forge/__main__.py`. Test: `.../forge/test_cli.py`.

`python -m …a_rfc.forge URL --repo CLONE --out DIR [--host github|gitlab]`. Reads token from env by kind; `clone_head` = `git rev-parse HEAD` of `--repo` (refuse non-repo); `fetched_at` = `datetime.now(timezone.utc)` formatted filesystem-safe; exit 1 on `ForgeError`/`OSError`; summary note (pull/review/comment counts + authenticated flag). Tests use a monkeypatched transport via a seam: `cli.main(argv, transport=...)` parameter defaulting to `_default_transport`. Commit `feat(a_rfc): forge fetch CLI with immutable snapshots`.

### Task F4: Timeline restructuring with forge data

**Files:** Modify `.../timeline/build.py` (`build_timeline(commits, forge_pulls=None)`), `.../timeline/cli.py` (`--forge`), `.../timeline/store.py` (forge_snapshot record). Test: extend `.../timeline/test_build.py`, `test_cli.py`.

Core rescue code (inside `build_timeline`, after the git-only pass — restructure by re-walking with a `forced_pr: dict[sha, pull]` set):

```python
    forced: dict[str, dict] = {}
    enriched: dict[str, dict] = {}
    unmatched: list[int] = []
    for pull in forge_pulls or ():
        if pull["state"] not in ("merged", "closed") or not pull.get("merged_at"):
            continue
        sha = pull.get("squash_commit_sha") or pull.get("merge_commit_sha")
        commit = by_sha.get(sha or "")
        if commit is None:
            unmatched.append(pull["number"])
        elif len(commit.parents) > 1:
            enriched[commit.sha] = pull
        else:
            forced[commit.sha] = pull
```

Spine walk change: a spine commit in `forced` flushes the open epoch and emits a one-member PR cluster (`provenance="forge_squash"`, `pr_number=pull["number"]`, title = pull title). Merge-commit clusters whose anchor is in `enriched` get `pr_number` set. `Cluster` record: `pr_number` already exists — ensure emitted for both paths. Return also the unmatched list: change signature to return `(clusters, unmatched)`? NO — keep `build_timeline` returning clusters; add module-level `RescueReport` returned by a new wrapper `build_timeline_with_forge(commits, pulls) -> tuple[tuple[Cluster,...], tuple[int,...]]` so the git-only signature stays stable. CLI: with `--forge`, read snapshot, guard `meta.clone_head == tip` (refuse — trap 3), report `unmatched` count on stderr, record `forge_snapshot: {dir_name, meta_sha256}` in `timeline.json`.

Tests: squash fixture (single-parent spine commit + pull with that merge_commit_sha) → one-member PR cluster, epochs split correctly, partition still holds; enrichment fixture (2-parent anchor) → pr_number attached, provenance unchanged; unmatched pull → reported, nothing restructured; head-mismatch snapshot → CLI exit 1; `(#N)` subject alone still never clusters (re-assert trap 1 with forge present but empty).

Commit `feat(a_rfc): forge-informed timeline enrichment and squash rescue`.

### Task F5: Views evidence + per-member patches

**Files:** Modify `.../views/emit.py` (params `forge_snapshot=None, patches="span"`), `.../views/cli.py` (`--forge`, `--patches span|members|both`). Test: extend views tests.

- `evidence/pr.json` per PR cluster with a `pr_number`: the pull record + its reviews + its comments (filtered, sorted) — written only when a snapshot is given; digest-recorded in `view.json` (`evidence` block: {pr_number, review_count, comment_count, sha256}).
- `members/<position:02d>-<sha12>.patch`: `git diff <first-parent-or-EMPTY_TREE> <sha>` per member with the same `_DIFF_ARGS`; every patch digest lands in `view.json.patches[]`; `--verify` covers them (re-emit compares all).
- Tests: member patches exist + digests verified for the merge fixture; `--patches span` (default) unchanged bytes vs previous emission (backward compat); evidence copied when snapshot given.

Commit `feat(a_rfc): per-member patches and forge evidence in views`.

### Task F6: aioquic live smoke (GitHub; token via `gh auth token`)

1. `git clone https://github.com/aiortc/aioquic reconstructions/aioquic/clone` (full depth; sandbox-off for nested .git).
2. `history` → corpus; record commit count.
3. `GITHUB_TOKEN=$(gh auth token) $PY -m …a_rfc.forge https://github.com/aiortc/aioquic --repo …/clone --out reconstructions/aioquic/forge` → expect ≈311 pulls; note request volume and authenticated=true.
4. `timeline … --forge <snapshot>` → expect a large `forge_squash` count (aioquic squash-merges); compare pr_count with/without `--forge`; partition invariant holds (member rows == commit count).
5. `views … --forge <snapshot> --only <one rescued cluster>` → evidence/pr.json present with real discussion.
6. Record numbers in `reconstructions/aioquic/RUN.md`. Nothing committed from `reconstructions/`.

### Task F7: Docs + wrap

README: forge section (CLI row exists — extend with fetch depth, token env, immutability, rescue semantics incl. the rebase approximation), traps table additions (1 and 3 now live), duplication table if any new copies. CHANGELOG entry. Full a_rfc suite + repo-wide unit suite; commit `docs(a_rfc): document the forge stage`.

**Deferred from P4 (recorded):** GitLab live fetch for MARK (user confirmation — sandbox + third-party host); fast-forward/rebase run reconstruction (needs per-PR commit lists AND post-rebase sha mapping — revisit with real aioquic data in hand); reviews for GitLab (approvals API).
