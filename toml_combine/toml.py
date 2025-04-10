from __future__ import annotations

import json
from typing import Any

import tomlkit
import tomlkit.exceptions

from . import exceptions


def loads(raw_config: str) -> dict[str, Any]:
    try:
        return tomlkit.loads(raw_config)
    except tomlkit.exceptions.ParseError as e:
        raise exceptions.TomlDecodeError from e


def dumps(config: dict) -> str:
    # https://github.com/python-poetry/tomlkit/issues/411
    # While we're waiting for a fix, the workaround is to give up "style-preserving"
    # features. The easiest way to turn tomlkit objects into plain dicts and strings
    # is through a json round-trip.
    try:
        return tomlkit.dumps(json.loads(json.dumps(config)), sort_keys=False)
    except tomlkit.exceptions.TOMLKitError as e:
        raise exceptions.TomlEncodeError from e
