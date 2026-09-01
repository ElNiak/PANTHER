"""The stage table's own invariants.

``stages.py`` states its design outright: the distinction between what the
runner performs and what it hands over is kept "in the data rather than in
control flow", which is what lets the runner stop at an agent boundary without
knowing anything about agents. Everything downstream — the ``--from``/``--until``
choices, ``next_stage``, the boundary message a reader acts on — trusts that
data, so the table's shape is asserted here rather than assumed.
"""

import pytest

from panther.plugins.services.testers.ai_rfc.pipeline.stages import (
    BY_NAME,
    STAGES,
    Performer,
    stage,
)

pytestmark = pytest.mark.unit


def test_ordinals_are_contiguous_and_in_order():
    """``--from``/``--until`` compare ordinals, so a gap would silently skip."""
    assert [item.ordinal for item in STAGES] == list(range(len(STAGES)))


def test_every_stage_is_reachable_by_name():
    assert set(BY_NAME) == {item.name for item in STAGES}
    assert len(BY_NAME) == len(STAGES)
    for item in STAGES:
        assert stage(item.name) is item


def test_an_unknown_stage_name_raises():
    with pytest.raises(KeyError):
        stage("no-such-stage")


def test_exactly_the_content_stages_are_the_agent_s():
    """Mining and prose produce content; nothing else may claim to.

    A stage newly marked AGENT stops the runner where it used to work, and one
    newly marked DETERMINISTIC hands a model's job to code that cannot do it.
    """
    by_performer: dict[Performer, set[str]] = {}
    for item in STAGES:
        by_performer.setdefault(item.performer, set()).add(item.name)
    assert by_performer[Performer.AGENT] == {"mining", "prose"}
    assert by_performer[Performer.MANUAL] == {"pin"}


def test_a_stage_the_runner_stops_at_tells_the_reader_what_to_do():
    """The instruction is the whole user interface at a boundary.

    ``perform`` refuses these stages and the CLI prints the instruction instead,
    so one left empty would stop a run with no way to learn what unblocks it.
    """
    for item in STAGES:
        handed_over = item.performer is not Performer.DETERMINISTIC
        assert bool(item.instruction) is handed_over, item.name


def test_the_first_stage_is_the_manual_pin():
    """Every anchor is verified against the clone stage 0 leaves behind."""
    assert STAGES[0].name == "pin"
    assert STAGES[0].performer is Performer.MANUAL


def test_mining_precedes_adjudication_and_prose_precedes_its_gate():
    """Order is the contract: nothing adjudicates claims that were never mined."""
    order = [item.name for item in STAGES]
    assert order.index("mining") < order.index("adjudicate")
    assert order.index("prose") < order.index("checkpoint") < order.index("gate")
