from __future__ import annotations

import copy
import dataclasses
from collections.abc import Iterable, Mapping, Sequence
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
    # List of overrides, in order of increasing specificity
    overrides: Sequence[Override]


def clean_dimensions_dict(
    to_sort: Mapping[str, list[str]], clean: dict[str, list[str]], type: str
) -> dict[str, list[str]]:
    """
    Recreate a dictionary of dimension values with the same order as the
    dimensions list.
    Also check that the values are valid.
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


T = TypeVar("T", dict, list, str, int, float, bool)


def merge_configs(a: T, b: T, /) -> T:
    """
    Recursively merge two configuration dictionaries a and b, with b taking precedence.
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


def are_conditions_compatible(
    a: Mapping[str, list[str]], b: Mapping[str, list[str]], /
) -> bool:
    """
    `a` and `b` are dictionaries representing override conditions (`when`). Return
    `True` if the conditions represented by `a` are compatible with `b`. Conditions are
    compatible if one is stricly more specific than the other or if they're mutually
    exclusive.
    """
    # Subset
    if set(a) < set(b) or set(b) < set(a):
        return True

    # Disjoint or overlapping sets
    if set(a) != set(b):
        return False

    # Equal sets: it's only compatible if the values are disjoint
    if any(set(a[key]) & set(b[key]) for key in a.keys()):
        return False
    return True


def build_config(config: dict[str, Any]) -> Config:
    """
    Build a finalized Config object from the given configuration dictionary.
    """
    config = copy.deepcopy(config)
    # Parse dimensions
    dimensions = config.pop("dimensions")

    # Parse template
    default = config.pop("default", {})

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

        overrides.append(Override(when=when, config=override))

    # Sort overrides by increasing specificity
    overrides = sorted(overrides, key=lambda override: len(override.when))

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
    """
    Generate a configuration based on the provided mapping of dimension values.
    The mapping should contain only the dimensions defined in the config.
    If a dimension is not defined in the mapping, the default value for that
    dimension will be used.
    """

    result = copy.deepcopy(config.default)
    keys_to_conditions: dict[tuple[str, ...], list[Mapping[str, list[str]]]] = {}
    # Apply each matching override
    for override in config.overrides:
        # Check if all dimension values in the override match

        if mapping_matches_override(mapping=mapping, override=override):
            # Check that all applicableoverrides are compatible
            keys = extract_keys(override.config)

            for key in keys:
                previous_conditions = keys_to_conditions.setdefault(key, [])

                for previous_condition in previous_conditions:
                    if not are_conditions_compatible(previous_condition, override.when):
                        raise exceptions.IncompatibleOverrides(
                            id=override.when,
                            key=".".join(key),
                            other_override=previous_condition,
                        )

                keys_to_conditions[key].append(override.when)

            result = merge_configs(result, override.config)

    return result
