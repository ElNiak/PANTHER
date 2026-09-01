import json
from pathlib import Path

import pytest

from panther.plugins.services.testers.ai_rfc.forge.adopt import read_records
from panther.plugins.services.testers.ai_rfc.forge.store import (
    ForgeError,
    write_snapshot,
)

pytestmark = pytest.mark.unit


def _write(path: Path, payload: object) -> Path:
    path.write_text(json.dumps(payload))
    return path


def test_records_round_trip_through_the_snapshot_writer(tmp_path: Path):
    """Adopt must reuse the writer, not reimplement the on-disk contract.

    Four downstream readers re-parse these bytes directly, so a second
    producer that hand-wrote them would drift from the one that is tested.
    """
    pull = {"number": 2, "merged_at": "x", "merge_commit_sha": "b" * 40}
    src = _write(
        tmp_path / "records.json",
        {"pulls": [pull], "reviews": [], "comments": []},
    )

    pulls, reviews, comments = read_records(src)
    assert pulls == [pull]
    assert reviews == [] and comments == []

    snapshot = write_snapshot(
        tmp_path / "out",
        host="gitlab.example",
        owner="o",
        repo="r",
        kind="gitlab",
        clone_head="a" * 40,
        fetched_at="2026-09-01T00-00-00Z",
        authenticated=False,
        pulls=pulls,
        reviews=reviews,
        comments=comments,
        acquisition="adopt",
        fidelity_ceiling="pulls",
    )
    meta = json.loads((snapshot / "meta.json").read_text())
    assert meta["acquisition"] == "adopt"
    assert meta["fidelity_ceiling"] == "pulls"
    assert json.loads((snapshot / "pulls.jsonl").read_text().strip()) == pull


def test_a_records_file_that_is_not_an_object_is_refused(tmp_path: Path):
    src = _write(tmp_path / "records.json", [1, 2, 3])
    with pytest.raises(ForgeError, match="object"):
        read_records(src)


def test_a_section_that_is_not_a_list_of_objects_is_refused(tmp_path: Path):
    src = _write(tmp_path / "records.json", {"pulls": ["not-an-object"]})
    with pytest.raises(ForgeError, match="pulls"):
        read_records(src)


def test_absent_sections_read_as_empty(tmp_path: Path):
    """A forge that has no reviews omits the key rather than writing null."""
    src = _write(tmp_path / "records.json", {"pulls": []})
    assert read_records(src) == ([], [], [])


def test_an_unknown_comment_kind_is_refused_by_the_writer(tmp_path: Path):
    """Validation is inherited from write_snapshot, not duplicated here.

    read_records deliberately passes the row through; the refusal must come
    from the one writer that owns the contract, so that an adopted snapshot
    cannot carry anything a fetched one could not.
    """
    src = _write(
        tmp_path / "records.json",
        {"comments": [{"pr_number": 1, "id": 1, "kind": "gossip"}]},
    )
    _, _, comments = read_records(src)
    assert comments[0]["kind"] == "gossip"

    with pytest.raises(ForgeError, match="gossip"):
        write_snapshot(
            tmp_path / "out",
            host="gitlab.example",
            owner="o",
            repo="r",
            kind="gitlab",
            clone_head="a" * 40,
            fetched_at="2026-09-01T00-00-02Z",
            authenticated=False,
            pulls=[],
            reviews=[],
            comments=comments,
            acquisition="adopt",
            fidelity_ceiling="pulls",
        )
