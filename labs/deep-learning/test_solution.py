import pytest

from solution import train


def test_training_converges():
    losses, accuracy = train()
    assert losses[-1] < 0.3 * losses[0]
    assert accuracy > 0.95


@pytest.mark.parametrize(
    "arguments",
    [
        {"steps": 0},
        {"steps": True},
        {"learning_rate": 0},
        {"learning_rate": float("nan")},
        {"learning_rate": "0.2"},
        {"learning_rate": 1 + 2j},
    ],
)
def test_invalid_training_configuration_is_rejected(arguments):
    with pytest.raises(ValueError):
        train(**arguments)
