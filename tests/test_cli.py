from __future__ import annotations

import json
import pathlib

from toml_combine import cli, toml


def test_cli__json(capsys):
    """Test the CLI."""
    exit_code = cli.cli(
        argv=[
            "tests/test.toml",
            "--format",
            "json",
            "--environment",
            "staging",
            "--type",
            "service",
            "--stack",
            "django",
            "--service",
            "admin",
        ]
    )
    out, err = capsys.readouterr()
    print("out:")
    print(out)
    print("err:")
    print(err)
    assert exit_code == 0

    expected = json.loads((pathlib.Path(__file__).parent / "result.json").read_text())
    assert json.loads(out) == expected["staging-service-django-admin"]


def test_cli__toml(capsys):
    """Test the CLI."""
    cli.cli(
        argv=[
            "tests/test.toml",
            "--environment",
            "staging",
            "--type",
            "service",
            "--stack",
            "django",
            "--service",
            "admin",
        ]
    )
    out, err = capsys.readouterr()
    print("out:")
    print(out)
    print("err:")
    print(err)

    expected = json.loads((pathlib.Path(__file__).parent / "result.json").read_text())
    assert toml.loads(out) == expected["staging-service-django-admin"]
