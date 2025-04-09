from __future__ import annotations

import pytest

from toml_combine import combiner, exceptions, toml


@pytest.mark.parametrize(
    "small_override, large_override, dimensions",
    [
        pytest.param(
            {"env": "prod"},
            {"env": "prod", "region": "eu"},
            {"env": ["prod"], "region": ["eu"]},
            id="less_specific_override_comes_first",
        ),
        pytest.param(
            {"env": "prod", "region": "eu"},
            {"env": "prod", "service": "web"},
            {"env": ["prod"], "region": ["eu"], "service": ["web"]},
            id="different_dimensions_sorted_by_dimension",
        ),
        pytest.param(
            {"env": "prod"},
            {"region": "eu"},
            {"env": ["prod"], "region": ["eu"]},
            id="completely_different_dimensions",
        ),
    ],
)
def test_override_sort_key(small_override, large_override, dimensions):
    small_key = combiner.override_sort_key(
        combiner.Override(when=small_override, config={}), dimensions
    )
    large_key = combiner.override_sort_key(
        combiner.Override(when=large_override, config={}), dimensions
    )
    assert small_key < large_key


@pytest.mark.parametrize(
    "a, b, expected",
    [
        pytest.param(
            {"a": 1, "b": 2},
            {"b": 3, "c": 4},
            {"a": 1, "b": 3, "c": 4},
            id="normal_dicts",
        ),
        pytest.param(
            {"a": {"b": 1, "c": 2}},
            {"a": {"c": 3}},
            {"a": {"b": 1, "c": 3}},
            id="nested_dicts",
        ),
    ],
)
def test_merge_configs__dicts(a, b, expected):
    assert combiner.merge_configs(a, b) == expected


def test_merge_configs__dicts_error():
    with pytest.raises(ValueError):
        combiner.merge_configs({"a": 1}, {"a": {"b": 2}})


@pytest.mark.parametrize(
    "mapping, expected",
    [
        pytest.param(
            {"env": "dev"},
            {
                "a": 1,
                "b": 2,
                "c": 3,
                "d": {"e": {"h": {"i": {"j": 4}}}},
                "g": 6,
                "dimensions": {"env": "dev"},
            },
            id="no_matches",
        ),
        pytest.param(
            {"env": "prod"},
            {
                "a": 10,
                "b": 2,
                "c": 30,
                "d": {"e": {"h": {"i": {"j": 40}}}},
                "g": 60,
                "dimensions": {"env": "prod"},
            },
            id="single_match",
        ),
        pytest.param(
            {"env": "staging"},
            {
                "a": 1,
                "b": 200,
                "c": 300,
                "d": {"e": {"h": {"i": {"j": 400}}}},
                "f": 500,
                "g": 6,
                "dimensions": {"env": "staging"},
            },
            id="dont_override_if_match_is_more_specific",
        ),
    ],
)
def test_generate_for_mapping(mapping: dict, expected: dict[str, int]):
    default = {
        "a": 1,
        "b": 2,
        "c": 3,
        "d": {"e": {"h": {"i": {"j": 4}}}},
        "g": 6,
    }

    overrides = [
        combiner.Override(
            when={"env": ["prod"]},
            config={
                "a": 10,
                "c": 30,
                "d": {"e": {"h": {"i": {"j": 40}}}},
                "g": 60,
            },
        ),
        combiner.Override(
            when={"env": ["staging"]},
            config={
                "b": 200,
                "c": 300,
                "d": {"e": {"h": {"i": {"j": 400}}}},
                "f": 500,
            },
        ),
        combiner.Override(
            when={"env": ["staging"], "region": ["us"]},
            config={"f": 5000, "g": 6000},
        ),
    ]

    result = combiner.generate_for_mapping(
        default=default,
        overrides=overrides,
        mapping=mapping,
    )
    assert result == expected


@pytest.mark.parametrize(
    "mapping, override, expected",
    [
        (
            {"env": "dev"},
            combiner.Override(when={"env": ["dev"]}, config={}),
            True,
        ),
        (
            {"env": "dev"},
            combiner.Override(when={"env": ["staging"]}, config={}),
            False,
        ),
        (
            {"env": "dev"},
            combiner.Override(when={"env": ["dev", "staging"]}, config={}),
            True,
        ),
        (
            {"env": "staging"},
            combiner.Override(when={"region": ["us"]}, config={}),
            False,
        ),
        (
            {"env": "dev"},
            combiner.Override(when={"env": ["dev"], "region": ["us"]}, config={}),
            False,
        ),
        (
            {"env": "dev", "region": "us"},
            combiner.Override(when={"env": ["dev"]}, config={}),
            True,
        ),
    ],
)
def test_mapping_matches_override(mapping, override, expected):
    result = combiner.mapping_matches_override(mapping=mapping, override=override)
    assert result == expected


def test_build_config():
    raw_config = """
    [dimensions]
    env = ["dev", "staging", "prod"]

    [default]
    foo = "bar"

    [[override]]
    when.env = ["dev", "staging"]
    foo = "baz"

    [[override]]
    when.env = "prod"
    foo = "qux"
    """

    config_dict = toml.loads(raw_config)
    config = combiner.build_config(config_dict)

    assert config == combiner.Config(
        dimensions={"env": ["dev", "staging", "prod"]},
        default={"foo": "bar"},
        overrides=[
            combiner.Override(
                when={"env": ["dev", "staging"]},
                config={"foo": "baz"},
            ),
            combiner.Override(
                when={"env": ["prod"]},
                config={"foo": "qux"},
            ),
        ],
    )


def test_build_config__duplicate_overrides():
    raw_config = """
    [dimensions]
    env = ["dev", "prod"]

    [templates]
    foo = "bar"

    [[override]]
    when.env = "prod"
    foo = "baz"

    [[override]]
    when.env = "prod"
    foo = "qux"
    """

    config = toml.loads(raw_config)
    with pytest.raises(exceptions.DuplicateError):
        combiner.build_config(config)


def test_build_config__dimension_not_found_in_override():
    raw_config = """
    [dimensions]
    env = ["dev", "prod"]

    [[override]]
    when.region = "eu"
    """

    config = toml.loads(raw_config)
    with pytest.raises(exceptions.DimensionNotFound):
        combiner.build_config(config)


def test_build_config__dimension_value_not_found_in_override():
    raw_config = """
    [dimensions]
    env = ["dev", "prod"]

    [[override]]
    when.env = "staging"
    """

    config = toml.loads(raw_config)
    with pytest.raises(exceptions.DimensionValueNotFound):
        combiner.build_config(config)


@pytest.fixture
def config():
    return combiner.build_config(
        toml.loads(
            """
        [dimensions]
        env = ["dev", "prod"]

        [default]
        foo = "bar"
        """,
        )
    )
