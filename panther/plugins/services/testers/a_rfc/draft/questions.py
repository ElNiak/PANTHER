"""The question register for the author-feedback loop.

One YAML file per reconstruction records every question drafted for the
implementation's authors, which claims each one blocks, and the answer once
it arrives. Loading is deliberately strict, in the manifest schema's mould: a
register that loads wrong — an "answered" question with no answer, a question
tied to no claim — is worse than one that fails to load.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Sequence

import yaml


class QuestionError(ValueError):
    """Raised when a question register cannot be interpreted as written."""


class QuestionStatus(Enum):
    """Where a question stands with the people it was asked of."""

    OPEN = "open"
    ANSWERED = "answered"
    WITHDRAWN = "withdrawn"


@dataclass(frozen=True)
class Question:
    """One question put to the implementation's authors."""

    id: str
    question: str
    claim_ids: tuple[str, ...]
    status: QuestionStatus
    asked_at: str
    answer: str | None = None
    answered_by: str | None = None
    answered_at: str | None = None


def _question(question_id: Any, raw: Any) -> Question:
    if not isinstance(question_id, str):
        raise QuestionError(
            f"{question_id!r}: question ids must be strings; quote it in the "
            f"document so YAML does not coerce its type"
        )
    if not isinstance(raw, dict):
        raise QuestionError(f"{question_id}: question body must be a mapping")

    for required in ("question", "status", "asked_at"):
        if required not in raw:
            raise QuestionError(f"{question_id}: missing required field {required}")

    try:
        status = QuestionStatus(raw["status"])
    except ValueError:
        permitted = ", ".join(member.value for member in QuestionStatus)
        raise QuestionError(
            f"{question_id}: status is {raw['status']!r}; permitted values "
            f"are {permitted}"
        ) from None

    claim_ids = raw.get("claim_ids")
    if not isinstance(claim_ids, list) or not claim_ids:
        raise QuestionError(
            f"{question_id}: claim_ids must be a non-empty list; a question "
            f"tied to no claim blocks nothing"
        )

    answer = raw.get("answer")
    if status is QuestionStatus.ANSWERED and (
        answer is None or raw.get("answered_at") is None
    ):
        raise QuestionError(
            f"{question_id}: an answered question must carry answer and "
            f"answered_at; recording the status without them loses the evidence"
        )
    if status is QuestionStatus.OPEN and answer is not None:
        raise QuestionError(
            f"{question_id}: an open question must not carry an answer; "
            f"record it as answered or drop the text"
        )

    return Question(
        id=question_id,
        question=str(raw["question"]).strip(),
        claim_ids=tuple(str(claim_id) for claim_id in claim_ids),
        status=status,
        asked_at=str(raw["asked_at"]),
        answer=None if answer is None else str(answer),
        answered_by=(
            None if raw.get("answered_by") is None else str(raw["answered_by"])
        ),
        answered_at=(
            None if raw.get("answered_at") is None else str(raw["answered_at"])
        ),
    )


def load_questions(path: Path) -> tuple[Question, ...]:
    """Read a question register from disk.

    Args:
        path: Path to the YAML register.

    Returns:
        The questions, ordered by identifier.

    Raises:
        QuestionError: If the document is malformed or breaks a status rule.
        OSError: If the file cannot be read.
    """
    document = yaml.safe_load(Path(path).read_text())
    if not isinstance(document, dict) or "questions" not in document:
        raise QuestionError(f"{path}: top level must be a mapping with questions")
    questions = document["questions"]
    if not isinstance(questions, dict):
        raise QuestionError(f"{path}: questions must be a mapping of id to body")
    return tuple(
        _question(question_id, body) for question_id, body in sorted(questions.items())
    )


def dump_questions(questions: Sequence[Question]) -> str:
    """Emit a question register as YAML, deterministically.

    Args:
        questions: The questions to emit.

    Returns:
        The YAML document as text; unset optional fields are omitted.
    """
    rendered: dict[str, Any] = {}
    for question in questions:
        body: dict[str, Any] = {
            "question": question.question,
            "claim_ids": list(question.claim_ids),
            "status": question.status.value,
            "asked_at": question.asked_at,
        }
        if question.answer is not None:
            body["answer"] = question.answer
        if question.answered_by is not None:
            body["answered_by"] = question.answered_by
        if question.answered_at is not None:
            body["answered_at"] = question.answered_at
        rendered[question.id] = body
    return yaml.safe_dump(
        {"questions": rendered},
        sort_keys=True,
        default_flow_style=False,
        allow_unicode=True,
        width=88,
    )
