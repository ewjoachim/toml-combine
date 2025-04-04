from __future__ import annotations

import json
import pathlib

import pytest

import toml_combine
from toml_combine import toml

config_file = pathlib.Path(__file__).parent / "test.toml"


@pytest.fixture
def expected():
    return json.loads((pathlib.Path(__file__).parent / "result.json").read_text())


@pytest.mark.parametrize(
    "kwargs",
    [
        {"config_file": config_file},
        {"config_file": str(config_file)},
        {"config": config_file.read_text()},
        {"config": toml.loads(config_file.read_text())},
    ],
)
def test_full(kwargs, expected):
    result = toml_combine.combine(**kwargs)
    assert set(result) == set(expected)
    for key in result:
        assert result[key] == expected[key], f"Failed for {key}"


# environment = ["staging", "production"]
# type = ["service", "job"]
# stack = ["next", "django"]
# service = ["api", "admin"]
# job = ["manage", "special-command"]


def test_filter__str(expected):
    result = toml_combine.combine(
        config_file=config_file, environment="production", stack="next"
    )
    assert result == {"production-service-next": expected["production-service-next"]}


def test_filter__list(expected):
    result = toml_combine.combine(
        config_file=config_file,
        environment=["production", "staging"],
        type="job",
        job=["manage", "special-command"],
    )
    assert result == {
        "staging-job-django-manage": expected["staging-job-django-manage"],
        "staging-job-django-special-command": expected[
            "staging-job-django-special-command"
        ],
        "production-job-django-manage": expected["production-job-django-manage"],
        "production-job-django-special-command": expected[
            "production-job-django-special-command"
        ],
    }
