from __future__ import annotations

import pytest
import tomli

from toml_combine import combiner, exceptions


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
    "output, expected",
    [
        pytest.param(
            combiner.Output(dimensions={"env": "dev"}),
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
            combiner.Output(dimensions={"env": "prod"}),
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
            combiner.Output(dimensions={"env": "staging"}),
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
def test_generate_output(output: combiner.Output, expected: dict[str, int]):
    default = {
        "a": 1,
        "b": 2,
        "c": 3,
        "d": {"e": {"h": {"i": {"j": 4}}}},
        "g": 6,
    }

    overrides = [
        combiner.Override(
            when={"env": "prod"},
            config={
                "a": 10,
                "c": 30,
                "d": {"e": {"h": {"i": {"j": 40}}}},
                "g": 60,
            },
        ),
        combiner.Override(
            when={"env": "staging"},
            config={
                "b": 200,
                "c": 300,
                "d": {"e": {"h": {"i": {"j": 400}}}},
                "f": 500,
            },
        ),
        combiner.Override(
            when={"env": "staging", "region": "us"},
            config={"f": 5000, "g": 6000},
        ),
    ]

    result = combiner.generate_output(
        output=output,
        default=default,
        overrides=overrides,
    )
    assert result == expected


def test_build_config():
    raw_config = """
    [dimensions]
    env = ["dev", "staging", "prod"]

    [default]
    foo = "bar"

    [[output]]
    env = "dev"

    [[output]]
    env = ["staging", "prod"]

    [[override]]
    when.env = ["dev", "staging"]
    foo = "baz"

    [[override]]
    when.env = "prod"
    foo = "qux"
    """

    config_dict = tomli.loads(raw_config)
    config = combiner.build_config(config_dict)

    assert config == combiner.Config(
        dimensions={"env": ["dev", "staging", "prod"]},
        outputs=[
            combiner.Output(
                dimensions={"env": "dev"},
            ),
            combiner.Output(
                dimensions={"env": "staging"},
            ),
            combiner.Output(
                dimensions={"env": "prod"},
            ),
        ],
        default={"foo": "bar"},
        overrides=[
            combiner.Override(
                when={"env": ["dev", "staging"]},
                config={"foo": "baz"},
            ),
            combiner.Override(
                when={"env": "prod"},
                config={"foo": "qux"},
            ),
        ],
    )


def test_create_outputs__duplicate_overrides():
    raw_config = """
    [dimensions]
    env = ["dev", "prod"]

    [templates]
    foo = "bar"

    [[output]]
    env = "dev"

    [[override]]
    when.env = "prod"
    foo = "baz"

    [[override]]
    when.env = "prod"
    foo = "qux"
    """

    config = tomli.loads(raw_config)
    with pytest.raises(exceptions.DuplicateError):
        combiner.build_config(config)


def test_create_outputs__dimension_not_found_in_output():
    raw_config = """
    [dimensions]
    env = ["dev", "prod"]

    [[output]]
    region = "us"
    """

    config = tomli.loads(raw_config)
    with pytest.raises(exceptions.DimensionNotFound):
        combiner.build_config(config)


def test_create_outputs__dimension_value_not_found_in_output():
    raw_config = """
    [dimensions]
    env = ["dev", "prod"]

    [[output]]
    env = "staging"
    """

    config = tomli.loads(raw_config)
    with pytest.raises(exceptions.DimensionValueNotFound):
        combiner.build_config(config)


def test_create_outputs__dimension_not_found_in_override():
    raw_config = """
    [dimensions]
    env = ["dev", "prod"]

    [[output]]
    env = "dev"

    [[override]]
    when.region = "eu"
    """

    config = tomli.loads(raw_config)
    with pytest.raises(exceptions.DimensionNotFound):
        combiner.build_config(config)


def test_create_outputs__dimension_value_not_found_in_override():
    raw_config = """
    [dimensions]
    env = ["dev", "prod"]

    [[output]]
    env = "dev"

    [[override]]
    when.env = "staging"
    """

    config = tomli.loads(raw_config)
    with pytest.raises(exceptions.DimensionValueNotFound):
        combiner.build_config(config)


def test_output_id():
    output = combiner.Output(dimensions={"env": "dev", "region": "us"}).id
    assert output == "dev-us"


@pytest.fixture
def config():
    return combiner.build_config(
        tomli.loads(
            """
        [dimensions]
        env = ["dev", "prod"]

        [default]
        foo = "bar"

        [[output]]
        env = "dev"
        """,
        )
    )


def test_generate_outputs(config):
    # Generate final configurations for each output
    assert combiner.generate_outputs(config=config) == {
        "dev": {
            "foo": "bar",
            "dimensions": {"env": "dev"},
        }
    }


def test_generate_outputs__filter_wrong_dimension(config):
    with pytest.raises(exceptions.DimensionNotFound):
        combiner.generate_outputs(
            config=config,
            foo="bar",
        )


def test_generate_outputs__filter_wrong_dimension_value(config):
    with pytest.raises(exceptions.DimensionValueNotFound):
        combiner.generate_outputs(
            config=config,
            env="foo",
        )
