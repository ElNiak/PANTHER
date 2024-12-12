from hypothesis import given, strategies as st

from panther.config.config_experiment_schema import (
    StepConfig,
    AssertionConfig,
    AssertionType,
    TestConfig,
    ExperimentConfig,
)


@given(st.builds(StepConfig))
def test_step_config(step_config):
    assert 1 <= step_config.wait <= 3600


@given(
    st.builds(
        AssertionConfig,
        type=st.sampled_from(list(AssertionType)),
        service=st.text(),
        endpoint=st.text(),
        expected_status=st.integers(),
    )
)
def test_assertion_config(assertion_config):
    assert assertion_config.type in AssertionType
    assert isinstance(assertion_config.service, str)
    assert isinstance(assertion_config.endpoint, str)
    assert isinstance(assertion_config.expected_status, int)


@given(st.builds(TestConfig))
def test_test_config(test_config):
    assert isinstance(test_config.name, str)
    assert isinstance(test_config.description, str)
    assert isinstance(test_config.network_environment, object)
    assert isinstance(test_config.execution_environments, list)
    assert all(isinstance(env, object) for env in test_config.execution_environments)
    assert 1 <= test_config.iterations <= 1000
    assert isinstance(test_config.services, dict)
    assert all(isinstance(service, object) for service in test_config.services.values())
    assert test_config.steps is None or isinstance(test_config.steps, StepConfig)
    assert test_config.assertions is None or all(
        isinstance(assertion, AssertionConfig) for assertion in test_config.assertions
    )


@given(st.builds(ExperimentConfig))
def test_experiment_config(experiment_config):
    assert isinstance(experiment_config.tests, list)
    # assert all(isinstance(test, TestConfig) for test in experiment_config.tests)
