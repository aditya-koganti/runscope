import itertools

import pytest
from runscope_api.errors import AppError
from runscope_api.models import RunStatus
from runscope_api.state_machine import VALID_TRANSITIONS, validate_transition


@pytest.mark.parametrize(
    ("previous", "target"),
    tuple(itertools.product(RunStatus, RunStatus)),
)
def test_state_machine_accepts_exactly_declared_transitions(
    previous: RunStatus, target: RunStatus
) -> None:
    if target in VALID_TRANSITIONS[previous]:
        validate_transition(previous, target)
    else:
        with pytest.raises(AppError) as error:
            validate_transition(previous, target)
        assert error.value.code == "run_invalid_transition"
        assert error.value.status_code == 409
