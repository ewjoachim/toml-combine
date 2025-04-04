from __future__ import annotations

import json
import pathlib

from toml_combine import cli


def test_cli(capsys):
    """Test the CLI."""
    cli.cli(argv=["tests/test.toml"])
    out, _ = capsys.readouterr()

    expected = json.loads((pathlib.Path(__file__).parent / "result.json").read_text())
    assert json.loads(out) == expected
