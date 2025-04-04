from __future__ import annotations

import pathlib
from typing import Any, cast, overload

from . import combiner, toml


# Provide already parsed config
@overload
def combine(
    *, config: dict[str, Any], **filters: str | list[str]
) -> dict[str, Any]: ...
# Provide toml config content
@overload
def combine(*, config: str, **filters: str | list[str]) -> dict[str, Any]: ...
# Provide toml config file path
@overload
def combine(
    *, config_file: str | pathlib.Path, **filters: str | list[str]
) -> dict[str, Any]: ...


def combine(*, config=None, config_file=None, **filters):
    """
    Generate outputs of configurations based on the provided TOML
    configuration.

    Args:
        config: The TOML configuration as a string or an already parsed dictionary.
        OR:
        config_file: The path to the TOML configuration file.
        **filters: Filters to apply to the combined configuration
            (dimension="value" or dimension=["list", "of", "values"]).

    Returns:
        dict[str, Any]: The combined configuration ({"output_id": {...}}).
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

    return combiner.generate_outputs(config_obj, **filters)
