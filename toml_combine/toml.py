from __future__ import annotations

from typing import Any

import tomli

from . import exceptions


def loads(raw_config: str) -> dict[str, Any]:
    try:
        return tomli.loads(raw_config)
    except tomli.TOMLDecodeError as e:
        raise exceptions.TomlDecodeError(
            message="Syntax error in TOML configuration file",
            context=str(e),
        ) from e
