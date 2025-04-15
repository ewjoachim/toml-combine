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
    "mapping, expected_key",
    [
        pytest.param(
            {
                "environment": "staging",
                "type": "service",
                "stack": "next",
            },
            "staging-service-next",
            id="staging-service-next",
        ),
        pytest.param(
            {
                "environment": "staging",
                "type": "service",
                "stack": "django",
                "service": "api",
            },
            "staging-service-django-api",
            id="staging-service-django-api",
        ),
        pytest.param(
            {
                "environment": "staging",
                "type": "service",
                "stack": "django",
                "service": "admin",
            },
            "staging-service-django-admin",
            id="staging-service-django-admin",
        ),
        pytest.param(
            {
                "environment": "staging",
                "type": "job",
                "stack": "django",
                "job": "manage",
            },
            "staging-job-django-manage",
            id="staging-job-django-manage",
        ),
        pytest.param(
            {
                "environment": "staging",
                "type": "job",
                "stack": "django",
                "job": "special-command",
            },
            "staging-job-django-special-command",
            id="staging-job-django-special-command",
        ),
        pytest.param(
            {
                "environment": "production",
                "type": "service",
                "stack": "next",
            },
            "production-service-next",
            id="production-service-next",
        ),
        pytest.param(
            {
                "environment": "production",
                "type": "service",
                "stack": "django",
                "service": "api",
            },
            "production-service-django-api",
            id="production-service-django-api",
        ),
        pytest.param(
            {
                "environment": "production",
                "type": "service",
                "stack": "django",
                "service": "admin",
            },
            "production-service-django-admin",
            id="production-service-django-admin",
        ),
        pytest.param(
            {
                "environment": "production",
                "type": "job",
                "stack": "django",
                "job": "manage",
            },
            "production-job-django-manage",
            id="production-job-django-manage",
        ),
        pytest.param(
            {
                "environment": "production",
                "type": "job",
                "stack": "django",
                "job": "special-command",
            },
            "production-job-django-special-command",
            id="production-job-django-special-command",
        ),
    ],
)
def test_full_config(mapping, expected, expected_key):
    result = toml_combine.combine(config_file=config_file, **mapping)
    assert result == expected[expected_key]


@pytest.mark.parametrize(
    "kwargs",
    [
        pytest.param({"config_file": config_file}, id="path"),
        pytest.param({"config_file": str(config_file)}, id="path_str"),
        pytest.param({"config": config_file.read_text()}, id="text"),
        pytest.param({"config": toml.loads(config_file.read_text())}, id="parsed"),
    ],
)
def test_full_load_kwargs(kwargs, expected):
    result = toml_combine.combine(
        **kwargs,
        environment="production",
        type="service",
        stack="django",
        service="api",
    )
    assert result == expected["production-service-django-api"]
