from __future__ import annotations

import copy
import dataclasses
import itertools
from collections.abc import Iterable, Mapping, Sequence
from functools import partial
from typing import Any, TypeVar

from . import exceptions


@dataclasses.dataclass()
class Override:
    when: Mapping[str, list[str]]
    config: Mapping[str, Any]

    def __str__(self) -> str:
        return f"Override({self.when})"


@dataclasses.dataclass()
class Config:
    dimensions: Mapping[str, list[str]]
    default: Mapping[str, Any]
    overrides: Sequence[Override]


def clean_dimensions_dict(
    to_sort: Mapping[str, list[str]], clean: dict[str, list[str]], type: str
) -> dict[str, list[str]]:
    """
    Recreate a dictionary of dimension values with the same order as the
    dimensions list.
    """
    result = {}
    if invalid_dimensions := set(to_sort) - set(clean):
        raise exceptions.DimensionNotFound(
            type=type,
            id=to_sort,
            dimension=", ".join(invalid_dimensions),
        )

    # Fix the order of the dimensions
    for dimension, valid_values in clean.items():
        if dimension not in to_sort:
            continue

        original_values = to_sort[dimension]
        if invalid_values := set(original_values) - set(valid_values):
            raise exceptions.DimensionValueNotFound(
                type=type,
                id=to_sort,
                dimension=dimension,
                value=", ".join(invalid_values),
            )
        # Fix the order of the values
        result[dimension] = [e for e in valid_values if e in original_values]

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

    Parameters:
    -----------
    override: An Override object that defines the condition when it applies
                (override.when)
    dimensions: The dict of all existing dimensions and their values, in order of
                definition

    Returns:
    --------
    A tuple that supports comparisons. Less specific Overrides should return smaller
    values and vice versa.
    """
    result = [len(override.when)]
    for i, dimension in enumerate(dimensions):
        if dimension in override.when:
            result.append(i)

    return tuple(result)


T = TypeVar("T", dict, list, str, int, float, bool)


def merge_configs(a: T, b: T, /) -> T:
    """
    Recursively merge two configuration dictionaries, with b taking precedence.
    """
    if isinstance(a, dict) != isinstance(b, dict):
        raise ValueError(f"Cannot merge {type(a)} with {type(b)}")

    if not isinstance(a, dict):
        return b

    result = a.copy()
    for key, b_value in b.items():  # type: ignore
        if a_value := a.get(key):
            result[key] = merge_configs(a_value, b_value)
        else:
            result[key] = b_value
    return result


def extract_keys(config: Any) -> Iterable[tuple[str, ...]]:
    """
    Extract the keys from a config.
    """
    if isinstance(config, dict):
        for key, value in config.items():
            for sub_key in extract_keys(value):
                yield (key, *sub_key)
    else:
        yield tuple()


def extract_conditions_and_keys(
    when: dict[str, list[str]], config: dict[str, Any]
) -> Iterable[tuple[Any, ...]]:
    """
    Extract the definitions from an override.
    """
    when_definitions = []
    for key, values in when.items():
        when_definitions.append([(key, value) for value in values])

    when_combined_definitions = list(itertools.product(*when_definitions))
    config_keys = extract_keys(config)
    for config_key in config_keys:
        for when_definition in when_combined_definitions:
            yield (when_definition, *config_key)


def build_config(config: dict[str, Any]) -> Config:
    config = copy.deepcopy(config)
    # Parse dimensions
    dimensions = config.pop("dimensions")

    # Parse template
    default = config.pop("default", {})

    # The rule is: the same exact set of conditions cannot be used twice to define
    # the same values (on the same or different overrides)
    seen_conditions_and_keys = set()
    overrides = []
    for override in config.pop("override", []):
        try:
            when = override.pop("when")
        except KeyError:
            raise exceptions.MissingOverrideCondition(id=override)
        when = clean_dimensions_dict(
            to_sort={k: v if isinstance(v, list) else [v] for k, v in when.items()},
            clean=dimensions,
            type="override",
        )

        conditions_and_keys = set(
            extract_conditions_and_keys(when=when, config=override)
        )
        if duplicates := (conditions_and_keys & seen_conditions_and_keys):
            duplicate_str = ", ".join(sorted(key for *_, key in duplicates))
            raise exceptions.DuplicateError(id=when, details=duplicate_str)

        seen_conditions_and_keys |= conditions_and_keys

        overrides.append(Override(when=when, config=override))

    # Sort overrides by increasing specificity
    overrides = sorted(
        overrides,
        key=partial(override_sort_key, dimensions=dimensions),
    )

    return Config(
        dimensions=dimensions,
        default=default,
        overrides=overrides,
    )


def mapping_matches_override(mapping: Mapping[str, str], override: Override) -> bool:
    """
    Check if the values in the override match the given dimensions.
    """
    for dim, values in override.when.items():
        if dim not in mapping:
            return False

        if mapping[dim] not in values:
            return False

    return True


def generate_for_mapping(
    config: Config,
    mapping: Mapping[str, str],
) -> Mapping[str, Any]:
    result = copy.deepcopy(config.default)
    # Apply each matching override
    for override in config.overrides:
        # Check if all dimension values in the override match

        if mapping_matches_override(mapping=mapping, override=override):
            result = merge_configs(result, override.config)

    return result
