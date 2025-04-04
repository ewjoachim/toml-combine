from __future__ import annotations

import copy
import dataclasses
import itertools
from collections.abc import Mapping, Sequence
from functools import partial
from typing import Any

from . import exceptions


@dataclasses.dataclass()
class Output:
    dimensions: Mapping[str, str]

    @property
    def id(self) -> str:
        return f"{'-'.join(self.dimensions.values())}"

    def __str__(self) -> str:
        return f"Output(id={self.id})"


@dataclasses.dataclass()
class Override:
    when: Mapping[str, str | list[str]]
    config: Mapping[str, Any]

    def __str__(self) -> str:
        return f"Override({self.when})"


@dataclasses.dataclass()
class Config:
    dimensions: Mapping[str, list[str]]
    outputs: list[Output]
    default: Mapping[str, Any]
    overrides: Sequence[Override]


def wrap_in_list(value: str | list[str]) -> list[str]:
    """
    Wrap a string in a list if it's not already a list.
    """
    if isinstance(value, str):
        return [value]
    return value


def clean_dimensions_dict(
    to_sort: Mapping[str, str | list[str]], clean: dict[str, list[str]], type: str
) -> dict[str, str]:
    """
    Recreate a dictionary of dimension values with the same order as the
    dimensions list.
    """
    result = {}
    remaining = dict(to_sort)

    for dimension, valid_values in clean.items():
        valid_values = set(valid_values)
        if dimension not in to_sort:
            continue

        original_value = remaining.pop(dimension)
        values = set(wrap_in_list(original_value))
        if invalid_values := values - valid_values:
            raise exceptions.DimensionValueNotFound(
                type=type,
                id=to_sort,
                dimension=dimension,
                value=", ".join(invalid_values),
            )
        result[dimension] = original_value

    if remaining:
        raise exceptions.DimensionNotFound(
            type=type,
            id=to_sort,
            dimension=", ".join(to_sort),
        )

    return result


def override_sort_key(
    override: Override, dimensions: dict[str, list[str]]
) -> tuple[int, ...]:
    """
    We sort overrides before applying them, and they are applied in the order of the
    sorted list, each override replacing the common values of the previous overrides.

    override_sort_key defines the sort key for overrides that ensures less specific
    overrides come first:
    - Overrides with fewer dimensions come first (will be overridden
      by more specific ones)
    - If two overrides have the same number of dimensions but define different
      dimensions, we sort by the definition order of the dimensions.

    Example:
    dimensions = {"env": ["dev", "prod"], "region": ["us", "eu"]}

    - Override with {"env": "dev"} comes before override with
      {"env": "dev", "region": "us"} (less specific)
    - Override with {"env": "dev"} comes before override with {"region": "us"} ("env"
      is defined before "region" in the dimensions list)
    """
    result = [len(override.when)]
    for i, dimension in enumerate(dimensions):
        if dimension in override.when:
            result.append(i)

    return tuple(result)


def merge_configs(a: Any, b: Any, /) -> Any:
    """
    Recursively merge two configuration dictionaries, with b taking precedence.
    """
    if isinstance(a, dict) != isinstance(b, dict):
        raise ValueError(f"Cannot merge {type(a)} with {type(b)}")

    if not isinstance(a, dict):
        return b

    result = a.copy()
    for key, b_value in b.items():
        if a_value := a.get(key):
            result[key] = merge_configs(a_value, b_value)
        else:
            result[key] = b_value
    return result


def build_config(config: dict[str, Any]) -> Config:
    # Parse dimensions
    dimensions = config.pop("dimensions")

    # Parse template
    default = config.pop("default", {})

    seen_conditions = set()
    overrides = []
    for override in config.pop("override", []):
        try:
            when = override.pop("when")
        except KeyError:
            raise exceptions.MissingOverrideCondition(id=override)

        conditions = tuple((k, tuple(wrap_in_list(v))) for k, v in when.items())
        if conditions in seen_conditions:
            raise exceptions.DuplicateError(type="override", id=when)

        seen_conditions.add(conditions)

        overrides.append(
            Override(
                when=clean_dimensions_dict(
                    to_sort=when, clean=dimensions, type="override"
                ),
                config=override,
            )
        )
    # Sort overrides by increasing specificity
    overrides = sorted(
        overrides,
        key=partial(override_sort_key, dimensions=dimensions),
    )

    outputs = []
    seen_conditions = set()

    for output in config.pop("output", []):
        for key in output:
            output[key] = wrap_in_list(output[key])

        for cartesian_product in itertools.product(*output.values()):
            # Create a dictionary with the same keys as when
            single_output = dict(zip(output.keys(), cartesian_product))

            conditions = tuple(single_output.items())
            if conditions in seen_conditions:
                raise exceptions.DuplicateError(type="output", id=output.id)
            seen_conditions.add(conditions)

            outputs.append(
                Output(
                    dimensions=clean_dimensions_dict(
                        single_output, dimensions, type="output"
                    ),
                )
            )

    return Config(
        dimensions=dimensions,
        outputs=outputs,
        default=default,
        overrides=overrides,
    )


def generate_output(
    default: Mapping[str, Any], overrides: Sequence[Override], output: Output
) -> dict[str, Any]:
    result = copy.deepcopy(default)
    # Apply each matching override
    for override in overrides:
        # Check if all dimension values in the override match
        if all(
            override.when.get(dim) == output.dimensions.get(dim)
            for dim in override.when.keys()
        ):
            result = merge_configs(result, override.config)

    return {"dimensions": output.dimensions, **result}


def generate_outputs(config: Config, **filter: str | list[str]) -> dict[str, Any]:
    result = {}
    filter_with_lists: dict[str, list[str]] = {}

    for key, value in list(filter.items()):
        if key not in config.dimensions:
            raise exceptions.DimensionNotFound(type="arguments", id="", dimension=key)

        value = wrap_in_list(value)

        if set(value) - set(config.dimensions[key]):
            raise exceptions.DimensionValueNotFound(
                type="arguments",
                id="",
                dimension=key,
                value=", ".join(set(value) - set(config.dimensions[key])),
            )
        filter_with_lists[key] = value

    for output in config.outputs:
        if all(
            output.dimensions.get(key) in value
            for key, value in filter_with_lists.items()
        ):
            result[output.id] = generate_output(
                default=config.default,
                overrides=config.overrides,
                output=output,
            )

    return result
