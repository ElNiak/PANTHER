import json

import pytest

from panther.plugins.services.testers.a_rfc.forge.fetch import (
    fetch_pull_data,
    parse_url,
)
from panther.plugins.services.testers.a_rfc.forge.store import ForgeError

pytestmark = pytest.mark.unit


def _transport(routes: dict, seen: list | None = None):
    def transport(url: str, headers: dict) -> tuple[int, dict, bytes]:
        if seen is not None:
            seen.append((url, headers))
        if url not in routes:
            return 404, {}, b"{}"
        status, response_headers, payload = routes[url]
        return status, response_headers, json.dumps(payload).encode()

    return transport


def test_parse_url_github():
    target = parse_url("https://github.com/aiortc/aioquic", None)
    assert (target.host, target.owner, target.repo, target.kind) == (
        "github.com",
        "aiortc",
        "aioquic",
        "github",
    )


def test_parse_url_gitlab_nested_group_and_git_suffix():
    target = parse_url("https://gitlab.cylab.be/cylab/mark.git", None)
    assert (target.host, target.owner, target.repo, target.kind) == (
        "gitlab.cylab.be",
        "cylab",
        "mark",
        "gitlab",
    )


def test_parse_url_host_override():
    target = parse_url("https://code.example.org/group/sub/project", "gitlab")
    assert target.kind == "gitlab"
    assert target.owner == "group/sub"
    assert target.repo == "project"


def test_parse_url_rejects_short_paths():
    with pytest.raises(ForgeError):
        parse_url("https://github.com/onlyowner", None)


def _github_pull(number: int, merged: bool = True) -> dict:
    return {
        "number": number,
        "title": f"pull {number}",
        "body": "does the thing",
        "state": "closed" if merged else "open",
        "user": {"login": "dev"},
        "created_at": "2026-01-01T00:00:00Z",
        "merged_at": "2026-01-02T00:00:00Z" if merged else None,
        "merge_commit_sha": "a" * 40,
        "head": {"sha": "b" * 40},
        "base": {"ref": "main"},
        "html_url": f"https://github.com/aiortc/aioquic/pull/{number}",
        "labels": [{"name": "bug"}],
    }


def test_github_paginates_and_fetches_merged_pr_discussions():
    api = "https://api.github.com/repos/aiortc/aioquic"
    page_one = f"{api}/pulls?state=all&per_page=100"
    page_two = f"{api}/pulls?state=all&per_page=100&page=2"
    routes = {
        page_one: (
            200,
            {"Link": f'<{page_two}>; rel="next"'},
            [_github_pull(1), _github_pull(2, merged=False)],
        ),
        page_two: (200, {}, [_github_pull(3)]),
        f"{api}/pulls/1/reviews?per_page=100": (
            200,
            {},
            [
                {
                    "id": 10,
                    "user": {"login": "reviewer"},
                    "state": "APPROVED",
                    "submitted_at": "2026-01-01T12:00:00Z",
                    "body": "ship it",
                }
            ],
        ),
        f"{api}/pulls/1/comments?per_page=100": (
            200,
            {},
            [
                {
                    "id": 20,
                    "user": {"login": "reviewer"},
                    "created_at": "2026-01-01T11:00:00Z",
                    "body": "typo here",
                    "path": "src/a.py",
                    "line": 5,
                }
            ],
        ),
        f"{api}/issues/1/comments?per_page=100": (
            200,
            {},
            [
                {
                    "id": 30,
                    "user": {"login": "dev"},
                    "created_at": "2026-01-01T10:00:00Z",
                    "body": "context",
                }
            ],
        ),
        f"{api}/pulls/3/reviews?per_page=100": (200, {}, []),
        f"{api}/pulls/3/comments?per_page=100": (200, {}, []),
        f"{api}/issues/3/comments?per_page=100": (200, {}, []),
    }
    target = parse_url("https://github.com/aiortc/aioquic", None)
    pulls, reviews, comments = fetch_pull_data(target, _transport(routes), token=None)
    assert [pull["number"] for pull in pulls] == [1, 2, 3]
    assert pulls[0]["state"] == "merged"
    assert pulls[1]["state"] == "open"
    assert pulls[0]["squash_commit_sha"] is None
    assert pulls[0]["labels"] == ["bug"]
    assert [review["pr_number"] for review in reviews] == [1]
    kinds = sorted(comment["kind"] for comment in comments)
    assert kinds == ["issue_comment", "review_comment"]
    assert all(comment["pr_number"] == 1 for comment in comments)


def test_github_token_sets_bearer_header():
    api = "https://api.github.com/repos/aiortc/aioquic"
    routes = {f"{api}/pulls?state=all&per_page=100": (200, {}, [])}
    seen: list = []
    target = parse_url("https://github.com/aiortc/aioquic", None)
    fetch_pull_data(target, _transport(routes, seen), token="secret-token")
    assert seen[0][1]["Authorization"] == "Bearer secret-token"


def test_rate_limit_raises_with_token_hint():
    api = "https://api.github.com/repos/aiortc/aioquic"
    routes = {f"{api}/pulls?state=all&per_page=100": (403, {}, {})}
    target = parse_url("https://github.com/aiortc/aioquic", None)
    with pytest.raises(ForgeError) as excinfo:
        fetch_pull_data(target, _transport(routes), token=None)
    assert "GITHUB_TOKEN" in str(excinfo.value)


def test_gitlab_maps_merge_requests_and_skips_system_notes():
    api = "https://gitlab.cylab.be/api/v4/projects/cylab%2Fmark"
    routes = {
        f"{api}/merge_requests?state=all&per_page=100&page=1": (
            200,
            {"x-next-page": ""},
            [
                {
                    "iid": 5,
                    "title": "mr five",
                    "description": "desc",
                    "state": "merged",
                    "author": {"username": "tdebatty"},
                    "created_at": "2026-01-01T00:00:00Z",
                    "merged_at": "2026-01-02T00:00:00Z",
                    "merge_commit_sha": "c" * 40,
                    "squash_commit_sha": None,
                    "sha": "d" * 40,
                    "target_branch": "master",
                    "web_url": "https://gitlab.cylab.be/cylab/mark/-/merge_requests/5",
                    "labels": [],
                }
            ],
        ),
        f"{api}/merge_requests/5/notes?per_page=100&page=1": (
            200,
            {"x-next-page": ""},
            [
                {
                    "id": 1,
                    "system": True,
                    "author": {"username": "bot"},
                    "created_at": "2026-01-01T00:00:00Z",
                    "body": "changed milestone",
                },
                {
                    "id": 2,
                    "system": False,
                    "author": {"username": "tdebatty"},
                    "created_at": "2026-01-01T01:00:00Z",
                    "body": "please rebase",
                },
            ],
        ),
    }
    target = parse_url("https://gitlab.cylab.be/cylab/mark", None)
    pulls, reviews, comments = fetch_pull_data(target, _transport(routes), token=None)
    assert pulls[0]["number"] == 5
    assert pulls[0]["state"] == "merged"
    assert reviews == []
    assert len(comments) == 1
    assert comments[0]["kind"] == "discussion_note"
    assert comments[0]["body"] == "please rebase"
