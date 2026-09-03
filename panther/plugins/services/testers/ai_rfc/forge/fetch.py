"""Fetch pull/merge-request data from GitHub or GitLab.

The transport is injected so every test runs against canned pages: a
transport takes ``(url, headers)`` and returns ``(status, response_headers,
body_bytes)``. The default transport wraps :mod:`urllib.request`. Tokens are
read by the caller and passed in; they end up in a request header and
nowhere else.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable

from .store import ForgeError

Transport = Callable[[str, dict[str, str]], tuple[int, dict[str, str], bytes]]

_NEXT_LINK = re.compile(r"<([^>]+)>;\s*rel=\"next\"")
_PAGE_CAP = 1000


class ForgeAuthError(ForgeError):
    """Raised when the forge refuses a request for lack of authorisation."""


class ForgeThrottled(ForgeAuthError):
    """Raised when the forge refuses a request for now rather than for good.

    Separated from its parent because the two refusals have opposite
    remedies: no credential recovers a 401, while a 429 recovers by waiting.
    Counting them together would let a throttled fetch be reported as having
    reached everything its route can deliver.
    """


class ForgeDenied(ForgeAuthError):
    """A forge refused a request permanently.

    Distinct from :class:`ForgeThrottled` because the remedies differ and the
    snapshot's fidelity grading reads which one occurred: waiting clears a 429
    and never clears a 403. Inherits ``ForgeAuthError`` so the per-pull
    handlers keep counting it as a denied sub-fetch.
    """


@dataclass(frozen=True)
class ForgeTarget:
    """One repository on one forge."""

    host: str
    owner: str
    repo: str
    kind: str

    @property
    def api_base(self) -> str:
        """The REST base URL for this repository on its forge."""
        if self.kind == "github":
            return f"https://api.github.com/repos/{self.owner}/{self.repo}"
        project = f"{self.owner}/{self.repo}".replace("/", "%2F")
        return f"https://{self.host}/api/v4/projects/{project}"


def parse_url(url: str, host_kind: str | None) -> ForgeTarget:
    """Resolve a repository URL to a forge target.

    Args:
        url: The repository URL, e.g. ``https://github.com/aiortc/aioquic``.
        host_kind: Explicit ``github``/``gitlab`` override; ``None`` infers
            ``github`` for github.com and ``gitlab`` for everything else.

    Returns:
        The parsed target.

    Raises:
        ForgeError: If the URL does not name a host and a repository path.
    """
    stripped = url.rstrip("/")
    if stripped.endswith(".git"):
        stripped = stripped[: -len(".git")]
    matched = re.match(r"^[a-z+]+://([^/]+)/(.+)$", stripped)
    if not matched:
        raise ForgeError(f"{url!r} is not a repository URL")
    host, path = matched.group(1), matched.group(2)
    segments = [segment for segment in path.split("/") if segment]
    if len(segments) < 2:
        raise ForgeError(
            f"{url!r} does not name an owner and a repository; got {path!r}"
        )
    kind = host_kind or ("github" if host == "github.com" else "gitlab")
    if kind not in ("github", "gitlab"):
        raise ForgeError(f"unknown forge kind {kind!r}")
    return ForgeTarget(
        host=host, owner="/".join(segments[:-1]), repo=segments[-1], kind=kind
    )


def _default_transport(
    url: str, headers: dict[str, str]
) -> tuple[int, dict[str, str], bytes]:
    request = urllib.request.Request(url, headers=headers)
    try:
        # forge is the pipeline's only networked stage; a forge that accepts
        # the connection and never answers would otherwise block forever.
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, dict(response.headers), response.read()
    except urllib.error.HTTPError as error:
        return error.code, dict(error.headers or {}), error.read()
    except urllib.error.URLError as error:
        raise ForgeError(f"could not reach {url}: {error.reason}") from None


def _get_json(
    url: str, transport: Transport, token: str | None
) -> tuple[Any, dict[str, str]]:
    headers = {"Accept": "application/json", "User-Agent": "panther-a-rfc"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    status, response_headers, body = transport(url, headers)
    if status == 429:
        raise ForgeThrottled(
            f"{url} answered 429 (rate limited); wait for the rate-limit "
            f"window and retry, or set GITHUB_TOKEN or GITLAB_TOKEN to "
            f"raise it"
        )
    if status == 403:
        raise ForgeDenied(
            f"{url} answered 403 (access denied); set GITHUB_TOKEN or "
            f"GITLAB_TOKEN to a credential with access, or check that the "
            f"existing one has it — retrying will not help"
        )
    if status == 401:
        raise ForgeAuthError(f"{url} answered 401 (authentication required)")
    if status != 200:
        raise ForgeError(f"{url} answered {status}")
    lowered = {key.lower(): value for key, value in response_headers.items()}
    return json.loads(body), lowered


def _paginated_github(
    url: str, transport: Transport, token: str | None
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    start = urllib.parse.urlsplit(url)
    scheme, host = start.scheme, start.netloc
    current_url: str | None = url
    pages = 0
    while current_url:
        pages += 1
        if pages > _PAGE_CAP:
            raise ForgeError(
                f"{url} did not finish paginating after {_PAGE_CAP} pages; "
                f"refusing to keep following it"
            )
        payload, headers = _get_json(current_url, transport, token)
        items.extend(payload)
        matched = _NEXT_LINK.search(headers.get("link", ""))
        next_url = matched.group(1) if matched else None
        if next_url:
            next_split = urllib.parse.urlsplit(next_url)
            if next_split.scheme != scheme or next_split.netloc != host:
                raise ForgeError(
                    f"{current_url}'s Link header pointed from "
                    f"{scheme}://{host} to "
                    f"{next_split.scheme}://{next_split.netloc}; refusing "
                    f"to send its token to another origin"
                )
        current_url = next_url
    return items


def _paginated_gitlab(
    url: str, transport: Transport, token: str | None
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    page = 1
    pages = 0
    while True:
        pages += 1
        if pages > _PAGE_CAP:
            raise ForgeError(
                f"{url} did not finish paginating after {_PAGE_CAP} pages; "
                f"refusing to keep following it"
            )
        payload, headers = _get_json(f"{url}&page={page}", transport, token)
        items.extend(payload)
        next_page = headers.get("x-next-page", "")
        if not next_page:
            return items
        try:
            page = int(next_page)
        except ValueError:
            raise ForgeError(
                f"{url} returned a non-numeric x-next-page header {next_page!r}"
            ) from None


def _actor(record: dict[str, Any] | None, key: str, field: str = "login") -> str:
    """Return a nested actor handle, or the empty string when absent."""
    return str(((record or {}).get(key) or {}).get(field, "") or "")


def _github_pull(raw: dict[str, Any]) -> dict[str, Any]:
    """Map a GitHub pull payload onto a snapshot record."""
    merged = bool(raw.get("merged_at"))
    return {
        "number": raw["number"],
        "title": raw.get("title") or "",
        "body": raw.get("body") or "",
        "state": "merged" if merged else raw.get("state") or "",
        "author": _actor(raw, "user"),
        "created_at": raw.get("created_at"),
        "merged_at": raw.get("merged_at"),
        "merge_commit_sha": raw.get("merge_commit_sha"),
        "squash_commit_sha": None,
        "head_sha": (raw.get("head") or {}).get("sha"),
        "base_ref": (raw.get("base") or {}).get("ref"),
        "url": raw.get("html_url"),
        "labels": [label.get("name", "") for label in raw.get("labels") or []],
    }


def _github_review(raw: dict[str, Any], pr_number: int) -> dict[str, Any]:
    """Map a GitHub review payload onto a snapshot record."""
    return {
        "pr_number": pr_number,
        "id": raw["id"],
        "reviewer": _actor(raw, "user"),
        "state": raw.get("state") or "",
        "submitted_at": raw.get("submitted_at"),
        "body": raw.get("body") or "",
    }


def _github_comment(
    raw: dict[str, Any],
    pr_number: int,
    kind: str,
    path: str | None = None,
    line: int | None = None,
) -> dict[str, Any]:
    """Map a GitHub comment payload onto a snapshot record.

    Issue comments anchor to no source location, so ``path`` and ``line``
    default to None.
    """
    return {
        "pr_number": pr_number,
        "id": raw["id"],
        "kind": kind,
        "author": _actor(raw, "user"),
        "created_at": raw.get("created_at"),
        "body": raw.get("body") or "",
        "path": path,
        "line": line,
    }


def _gitlab_pull(raw: dict[str, Any]) -> dict[str, Any]:
    """Map a GitLab merge-request payload onto a snapshot record."""
    return {
        "number": raw["iid"],
        "title": raw.get("title") or "",
        "body": raw.get("description") or "",
        "state": raw.get("state") or "",
        "author": _actor(raw, "author", "username"),
        "created_at": raw.get("created_at"),
        "merged_at": raw.get("merged_at"),
        "merge_commit_sha": raw.get("merge_commit_sha"),
        "squash_commit_sha": raw.get("squash_commit_sha"),
        "head_sha": raw.get("sha"),
        "base_ref": raw.get("target_branch"),
        "url": raw.get("web_url"),
        "labels": list(raw.get("labels") or []),
    }


def _gitlab_comment(raw: dict[str, Any], pr_number: int) -> dict[str, Any]:
    """Map a GitLab discussion note onto a snapshot record."""
    return {
        "pr_number": pr_number,
        "id": raw["id"],
        "kind": "discussion_note",
        "author": _actor(raw, "author", "username"),
        "created_at": raw.get("created_at"),
        "body": raw.get("body") or "",
        "path": None,
        "line": None,
    }


@dataclass(frozen=True)
class FetchResult:
    """Everything one fetch produced, plus what it was refused.

    ``denied_subfetches`` counts per-pull discussion endpoints the forge
    refused for lack of authorisation (some instances gate notes and
    reviews even on public projects). The pull list itself is never
    degraded — without it there is nothing to snapshot — but discussion is
    enrichment, so a denial is counted and reported rather than fatal.

    ``throttled`` says whether any of those refusals was a rate limit rather
    than a lack of authorisation. It is not written to the snapshot; the
    caller uses it to decide whether the fetch reached its route's ceiling,
    because a throttled run has not — waiting would have got more.
    """

    pulls: list[dict[str, Any]]
    reviews: list[dict[str, Any]]
    comments: list[dict[str, Any]]
    denied_subfetches: int
    throttled: bool = False


def _fetch_github(
    target: ForgeTarget, transport: Transport, token: str | None
) -> FetchResult:
    api = target.api_base
    pulls: list[dict[str, Any]] = []
    reviews: list[dict[str, Any]] = []
    comments: list[dict[str, Any]] = []
    denied = 0
    throttled = False
    for raw in _paginated_github(
        f"{api}/pulls?state=all&per_page=100", transport, token
    ):
        number = raw["number"]
        pulls.append(_github_pull(raw))
        if not raw.get("merged_at"):
            continue
        try:
            for review in _paginated_github(
                f"{api}/pulls/{number}/reviews?per_page=100", transport, token
            ):
                reviews.append(_github_review(review, number))
        except ForgeAuthError as error:
            denied += 1
            throttled = throttled or isinstance(error, ForgeThrottled)
        try:
            for comment in _paginated_github(
                f"{api}/pulls/{number}/comments?per_page=100", transport, token
            ):
                comments.append(
                    _github_comment(
                        comment,
                        number,
                        "review_comment",
                        path=comment.get("path"),
                        line=comment.get("line"),
                    )
                )
            for comment in _paginated_github(
                f"{api}/issues/{number}/comments?per_page=100", transport, token
            ):
                comments.append(_github_comment(comment, number, "issue_comment"))
        except ForgeAuthError as error:
            denied += 1
            throttled = throttled or isinstance(error, ForgeThrottled)
    return FetchResult(pulls, reviews, comments, denied, throttled)


def _fetch_gitlab(
    target: ForgeTarget, transport: Transport, token: str | None
) -> FetchResult:
    api = target.api_base
    pulls: list[dict[str, Any]] = []
    comments: list[dict[str, Any]] = []
    denied = 0
    throttled = False
    for raw in _paginated_gitlab(
        f"{api}/merge_requests?state=all&per_page=100", transport, token
    ):
        number = raw["iid"]
        pulls.append(_gitlab_pull(raw))
        if raw.get("state") != "merged":
            continue
        try:
            for note in _paginated_gitlab(
                f"{api}/merge_requests/{number}/notes?per_page=100",
                transport,
                token,
            ):
                if note.get("system"):
                    continue
                comments.append(_gitlab_comment(note, number))
        except ForgeAuthError as error:
            denied += 1
            throttled = throttled or isinstance(error, ForgeThrottled)
    return FetchResult(pulls, [], comments, denied, throttled)


def fetch_pull_data(
    target: ForgeTarget, transport: Transport | None = None, token: str | None = None
) -> FetchResult:
    """Fetch every pull/merge request, with reviews and comments for merged ones.

    Args:
        target: The repository to fetch.
        transport: Transport to use; ``None`` uses :mod:`urllib`.
        token: Bearer token, or ``None`` for anonymous access.

    Returns:
        The fetch result, unsorted — the snapshot store owns ordering. A
        forge that refuses per-pull discussion endpoints (401/403) degrades
        to counted denials; a refused pull list raises.

    Raises:
        ForgeError: On network failure, a non-200 answer to the pull list,
            or a rate limit on it.
    """
    chosen = transport or _default_transport
    if target.kind == "github":
        return _fetch_github(target, chosen, token)
    return _fetch_gitlab(target, chosen, token)
