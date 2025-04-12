from __future__ import annotations

import pathlib
from typing import Any, cast, overload

from . import combiner, toml


# Provide already parsed config
@overload
def combine(
    *, config: dict[str, Any], **mapping: str | list[str]
) -> dict[str, Any]: ...
# Provide toml config content
@overload
def combine(*, config: str, **mapping: str | list[str]) -> dict[str, Any]: ...
# Provide toml config file path
@overload
def combine(
    *, config_file: str | pathlib.Path, **mapping: str | list[str]
) -> dict[str, Any]: ...


def combine(*, config=None, config_file=None, **mapping):
    """
    Generate outputs of configurations based on the provided TOML
    configuration and a mapping of dimensions values.

    Args:
        config: The TOML configuration as a string or an already parsed dictionary.
        OR:
        config_file: The path to the TOML configuration file.
        **mapping: Define the values you want for dimensions {"<dimension>": "<value>", ...}.

    Returns:
        dict[str, Any]: The combined configuration.
    """
    if (config is None) is (config_file is None):
        raise ValueError("Either 'config' or 'config_file' must be provided.")

    if isinstance(config, dict):
        dict_config = config
    else:
        if config_file:
            config_string = pathlib.Path(config_file).read_text()
        else:
            config = cast(str, config)
            config_string = config

        dict_config = toml.loads(config_string)

    config_obj = combiner.build_config(dict_config)

    return combiner.generate_for_mapping(
        config=config_obj,
        mapping=mapping,
    )
