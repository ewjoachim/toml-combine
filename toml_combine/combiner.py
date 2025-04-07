from __future__ import annotations

import copy
import dataclasses
from collections.abc import Mapping, Sequence
from functools import partial
from typing import Any

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
    config = copy.deepcopy(config)
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
        when = clean_dimensions_dict(
            to_sort={k: v if isinstance(v, list) else [v] for k, v in when.items()},
            clean=dimensions,
            type="override",
        )

        conditions = tuple((k, tuple(v)) for k, v in when.items())
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

    return Config(
        dimensions=dimensions,
        default=default,
        overrides=overrides,
    )


def mapping_matches_override(mapping: dict[str, str], override: Override) -> bool:
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
    default: Mapping[str, Any],
    overrides: Sequence[Override],
    mapping: dict[str, str],
) -> dict[str, Any]:
    result = copy.deepcopy(default)
    # Apply each matching override
    for override in overrides:
        # Check if all dimension values in the override match

        if mapping_matches_override(mapping=mapping, override=override):
            result = merge_configs(result, override.config)

    return {"dimensions": mapping, **result}
