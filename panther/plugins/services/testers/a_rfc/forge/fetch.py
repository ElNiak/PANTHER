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
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable

from .store import ForgeError

Transport = Callable[[str, dict[str, str]], tuple[int, dict[str, str], bytes]]

_NEXT_LINK = re.compile(r"<([^>]+)>;\s*rel=\"next\"")


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
        with urllib.request.urlopen(request) as response:
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
    if status in (403, 429):
        raise ForgeError(
            f"{url} answered {status} (rate limited or forbidden); set "
            f"GITHUB_TOKEN or GITLAB_TOKEN and retry"
        )
    if status != 200:
        raise ForgeError(f"{url} answered {status}")
    lowered = {key.lower(): value for key, value in response_headers.items()}
    return json.loads(body), lowered


def _paginated_github(
    url: str, transport: Transport, token: str | None
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    next_url: str | None = url
    while next_url:
        payload, headers = _get_json(next_url, transport, token)
        items.extend(payload)
        matched = _NEXT_LINK.search(headers.get("link", ""))
        next_url = matched.group(1) if matched else None
    return items


def _paginated_gitlab(
    url: str, transport: Transport, token: str | None
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    page = 1
    while True:
        payload, headers = _get_json(f"{url}&page={page}", transport, token)
        items.extend(payload)
        next_page = headers.get("x-next-page", "")
        if not next_page:
            return items
        page = int(next_page)


def _login(record: dict[str, Any] | None, key: str) -> str:
    return str(((record or {}).get(key) or {}).get("login", "") or "")


def _fetch_github(
    target: ForgeTarget, transport: Transport, token: str | None
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    api = target.api_base
    pulls: list[dict[str, Any]] = []
    reviews: list[dict[str, Any]] = []
    comments: list[dict[str, Any]] = []
    for raw in _paginated_github(
        f"{api}/pulls?state=all&per_page=100", transport, token
    ):
        number = raw["number"]
        merged = bool(raw.get("merged_at"))
        pulls.append(
            {
                "number": number,
                "title": raw.get("title") or "",
                "body": raw.get("body") or "",
                "state": "merged" if merged else raw.get("state") or "",
                "author": _login(raw, "user"),
                "created_at": raw.get("created_at"),
                "merged_at": raw.get("merged_at"),
                "merge_commit_sha": raw.get("merge_commit_sha"),
                "squash_commit_sha": None,
                "head_sha": (raw.get("head") or {}).get("sha"),
                "base_ref": (raw.get("base") or {}).get("ref"),
                "url": raw.get("html_url"),
                "labels": [label.get("name", "") for label in raw.get("labels") or []],
            }
        )
        if not merged:
            continue
        for review in _paginated_github(
            f"{api}/pulls/{number}/reviews?per_page=100", transport, token
        ):
            reviews.append(
                {
                    "pr_number": number,
                    "id": review["id"],
                    "reviewer": _login(review, "user"),
                    "state": review.get("state") or "",
                    "submitted_at": review.get("submitted_at"),
                    "body": review.get("body") or "",
                }
            )
        for comment in _paginated_github(
            f"{api}/pulls/{number}/comments?per_page=100", transport, token
        ):
            comments.append(
                {
                    "pr_number": number,
                    "id": comment["id"],
                    "kind": "review_comment",
                    "author": _login(comment, "user"),
                    "created_at": comment.get("created_at"),
                    "body": comment.get("body") or "",
                    "path": comment.get("path"),
                    "line": comment.get("line"),
                }
            )
        for comment in _paginated_github(
            f"{api}/issues/{number}/comments?per_page=100", transport, token
        ):
            comments.append(
                {
                    "pr_number": number,
                    "id": comment["id"],
                    "kind": "issue_comment",
                    "author": _login(comment, "user"),
                    "created_at": comment.get("created_at"),
                    "body": comment.get("body") or "",
                    "path": None,
                    "line": None,
                }
            )
    return pulls, reviews, comments


def _fetch_gitlab(
    target: ForgeTarget, transport: Transport, token: str | None
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    api = target.api_base
    pulls: list[dict[str, Any]] = []
    comments: list[dict[str, Any]] = []
    for raw in _paginated_gitlab(
        f"{api}/merge_requests?state=all&per_page=100", transport, token
    ):
        number = raw["iid"]
        pulls.append(
            {
                "number": number,
                "title": raw.get("title") or "",
                "body": raw.get("description") or "",
                "state": raw.get("state") or "",
                "author": str((raw.get("author") or {}).get("username", "") or ""),
                "created_at": raw.get("created_at"),
                "merged_at": raw.get("merged_at"),
                "merge_commit_sha": raw.get("merge_commit_sha"),
                "squash_commit_sha": raw.get("squash_commit_sha"),
                "head_sha": raw.get("sha"),
                "base_ref": raw.get("target_branch"),
                "url": raw.get("web_url"),
                "labels": list(raw.get("labels") or []),
            }
        )
        if raw.get("state") != "merged":
            continue
        for note in _paginated_gitlab(
            f"{api}/merge_requests/{number}/notes?per_page=100", transport, token
        ):
            if note.get("system"):
                continue
            comments.append(
                {
                    "pr_number": number,
                    "id": note["id"],
                    "kind": "discussion_note",
                    "author": str((note.get("author") or {}).get("username", "") or ""),
                    "created_at": note.get("created_at"),
                    "body": note.get("body") or "",
                    "path": None,
                    "line": None,
                }
            )
    return pulls, [], comments


def fetch_pull_data(
    target: ForgeTarget, transport: Transport | None = None, token: str | None = None
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Fetch every pull/merge request, with reviews and comments for merged ones.

    Args:
        target: The repository to fetch.
        transport: Transport to use; ``None`` uses :mod:`urllib`.
        token: Bearer token, or ``None`` for anonymous access.

    Returns:
        ``(pulls, reviews, comments)`` in snapshot record shape, unsorted —
        the snapshot store owns ordering.

    Raises:
        ForgeError: On network failure, a rate limit, or a non-200 answer.
    """
    chosen = transport or _default_transport
    if target.kind == "github":
        return _fetch_github(target, chosen, token)
    return _fetch_gitlab(target, chosen, token)
