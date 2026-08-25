from pathlib import Path

import pytest

from panther.plugins.services.testers.a_rfc.draft.questions import (
    QuestionError,
    QuestionStatus,
    dump_questions,
    load_questions,
)

pytestmark = pytest.mark.unit


def _write(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "questions.yaml"
    path.write_text(body)
    return path


def test_loads_open_and_answered_questions_sorted_by_id(tmp_path: Path):
    path = _write(
        tmp_path,
        "questions:\n"
        "  q-002:\n"
        "    question: 'Is the ordering deliberate?'\n"
        "    claim_ids: ['spec:2.1']\n"
        "    status: answered\n"
        "    asked_at: '2026-08-01'\n"
        "    answer: 'Yes, decreasing order was intended.'\n"
        "    answered_by: dev-01\n"
        "    answered_at: '2026-08-02'\n"
        "  q-001:\n"
        "    question: 'Is the default weight shared?'\n"
        "    claim_ids: ['spec:1.1', 'spec:1.2']\n"
        "    status: open\n"
        "    asked_at: '2026-08-01'\n",
    )
    questions = load_questions(path)
    assert [question.id for question in questions] == ["q-001", "q-002"]
    assert questions[0].status is QuestionStatus.OPEN
    assert questions[0].claim_ids == ("spec:1.1", "spec:1.2")
    assert questions[1].answer is not None
    assert questions[1].answered_by == "dev-01"


def test_dump_is_idempotent(tmp_path: Path):
    path = _write(
        tmp_path,
        "questions:\n"
        "  q-001:\n"
        "    question: 'Is the default weight shared?'\n"
        "    claim_ids: ['spec:1.1']\n"
        "    status: open\n"
        "    asked_at: '2026-08-01'\n",
    )
    text = dump_questions(load_questions(path))
    rewritten = _write(tmp_path, text)
    assert dump_questions(load_questions(rewritten)) == text


def test_unknown_status_is_refused(tmp_path: Path):
    path = _write(
        tmp_path,
        "questions:\n"
        "  q-001:\n"
        "    question: 'x'\n"
        "    claim_ids: ['spec:1.1']\n"
        "    status: maybe\n"
        "    asked_at: '2026-08-01'\n",
    )
    with pytest.raises(QuestionError) as excinfo:
        load_questions(path)
    assert "q-001" in str(excinfo.value)
    assert "maybe" in str(excinfo.value)


def test_answered_without_answer_is_refused(tmp_path: Path):
    path = _write(
        tmp_path,
        "questions:\n"
        "  q-001:\n"
        "    question: 'x'\n"
        "    claim_ids: ['spec:1.1']\n"
        "    status: answered\n"
        "    asked_at: '2026-08-01'\n",
    )
    with pytest.raises(QuestionError) as excinfo:
        load_questions(path)
    assert "answer" in str(excinfo.value)


def test_open_with_an_answer_is_refused(tmp_path: Path):
    path = _write(
        tmp_path,
        "questions:\n"
        "  q-001:\n"
        "    question: 'x'\n"
        "    claim_ids: ['spec:1.1']\n"
        "    status: open\n"
        "    asked_at: '2026-08-01'\n"
        "    answer: 'premature'\n",
    )
    with pytest.raises(QuestionError) as excinfo:
        load_questions(path)
    assert "open" in str(excinfo.value)


def test_empty_claim_ids_are_refused(tmp_path: Path):
    path = _write(
        tmp_path,
        "questions:\n"
        "  q-001:\n"
        "    question: 'x'\n"
        "    claim_ids: []\n"
        "    status: open\n"
        "    asked_at: '2026-08-01'\n",
    )
    with pytest.raises(QuestionError) as excinfo:
        load_questions(path)
    assert "claim_ids" in str(excinfo.value)
