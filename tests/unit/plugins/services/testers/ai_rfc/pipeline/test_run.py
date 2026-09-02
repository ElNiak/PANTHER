"""``perform`` refuses rather than improvises.

The CLI's own tests cover the chaining; these cover the three ways ``perform``
declines a stage. They are asserted directly because the CLI translates every
one of them into the same exit 1, so a refusal that stopped firing — or started
firing for the wrong stage — would look identical from outside.
"""

from pathlib import Path

import pytest

from panther.plugins.services.testers.ai_rfc.pipeline.run import (
    DISPATCH,
    PipelineError,
    perform,
    workspace_from,
)
from panther.plugins.services.testers.ai_rfc.pipeline.stages import (
    STAGES,
    Performer,
    stage,
)

pytestmark = pytest.mark.unit

HANDED_OVER = [
    item.name for item in STAGES if item.performer is not Performer.DETERMINISTIC
]


@pytest.mark.parametrize("name", HANDED_OVER, ids=HANDED_OVER)
def test_a_stage_the_pipeline_does_not_perform_is_refused(name: str, workspace: Path):
    """pin, mining and prose belong to a human or a model, and must stay there.

    The refusal names the performer, because a caller that asked for one of
    these needs to know it was handed over rather than that it failed.
    """
    with pytest.raises(PipelineError) as excinfo:
        perform(stage(name), workspace_from(workspace))
    message = str(excinfo.value)
    assert name in message
    assert stage(name).performer.value in message


def test_forge_without_a_url_is_refused_before_anything_is_written(workspace: Path):
    with pytest.raises(PipelineError) as excinfo:
        perform(stage("forge"), workspace_from(workspace))
    assert "--forge-url" in str(excinfo.value)
    assert not (workspace / "forge").exists()


def test_checkpoint_without_a_cluster_is_refused(workspace: Path):
    """Deferred from argparse, so this is the only place it is caught."""
    with pytest.raises(PipelineError) as excinfo:
        perform(stage("checkpoint"), workspace_from(workspace))
    assert "--cluster" in str(excinfo.value)


def test_a_deterministic_stage_runs_and_reports_the_argv_it_built(workspace: Path):
    """The argv is recorded because it is the command a person would have typed."""
    result = perform(stage("history"), workspace_from(workspace))
    assert result.ok and result.exit_code == 0
    assert result.stage is stage("history")
    assert str(workspace / "clone") in result.argv
    assert "--out" in result.argv


def test_every_deterministic_stage_has_a_builder():
    """``DISPATCH`` and ``STAGES`` are two lists that must not drift apart.

    A stage renamed in ``stages.py`` but missed in the dispatch table falls
    through to the refusal above, which would then call a deterministic stage
    handed-over — self-contradictory, and green in every other test here.
    """
    assert set(DISPATCH) == {
        item.name for item in STAGES if item.performer is Performer.DETERMINISTIC
    }
