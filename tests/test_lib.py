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
@pytest.mark.parametrize(
    "mapping, expected_key",
    [
        (
            {"environment": "staging", "type": "service", "stack": "next"},
            "staging-service-next",
        ),
        (
            {
                "environment": "staging",
                "type": "service",
                "stack": "django",
                "service": "api",
            },
            "staging-service-django-api",
        ),
        (
            {
                "environment": "staging",
                "type": "service",
                "stack": "django",
                "service": "admin",
            },
            "staging-service-django-admin",
        ),
        (
            {
                "environment": "staging",
                "type": "job",
                "stack": "django",
                "job": "manage",
            },
            "staging-job-django-manage",
        ),
        (
            {
                "environment": "staging",
                "type": "job",
                "stack": "django",
                "job": "special-command",
            },
            "staging-job-django-special-command",
        ),
        (
            {"environment": "production", "type": "service", "stack": "next"},
            "production-service-next",
        ),
        (
            {
                "environment": "production",
                "type": "service",
                "stack": "django",
                "service": "api",
            },
            "production-service-django-api",
        ),
        (
            {
                "environment": "production",
                "type": "service",
                "stack": "django",
                "service": "admin",
            },
            "production-service-django-admin",
        ),
        (
            {
                "environment": "production",
                "type": "job",
                "stack": "django",
                "job": "manage",
            },
            "production-job-django-manage",
        ),
        (
            {
                "environment": "production",
                "type": "job",
                "stack": "django",
                "job": "special-command",
            },
            "production-job-django-special-command",
        ),
    ],
)
def test_full(kwargs, mapping, expected, expected_key):
    result = toml_combine.combine(**kwargs, **mapping)
    assert result == expected[expected_key]
