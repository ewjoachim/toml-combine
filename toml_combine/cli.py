from __future__ import annotations

import argparse
import json
import pathlib
import sys
from collections.abc import Mapping

from . import combiner, exceptions, lib, toml


def get_argument_parser(
    dimensions: Mapping[str, list[str]] | None,
) -> argparse.ArgumentParser:
    """Get the command-line argument parser."""
    arg_parser = argparse.ArgumentParser(
        description="Create combined configurations from a TOML file",
        add_help=(dimensions is not None),
    )
    arg_parser.add_argument(
        "--format",
        choices=["json", "toml"],
        default="toml",
        help="Output format",
    )
    arg_parser.add_argument(
        "config",
        type=pathlib.Path,
        help="Path to the TOML configuration file",
    )
    if dimensions is None:
        arg_parser.epilog = (
            "Additional arguments will be provided with a valid config file."
        )
    else:
        group = arg_parser.add_argument_group(
            "dimensions",
            "Output the file with these dimensions",
        )

        for name, values in dimensions.items():
            group.add_argument(
                f"--{name}", choices=values, help=f"Provide value for {name}"
            )

    return arg_parser


def cli(argv) -> int:
    """Main entry point."""

    # Parse the config file argument to get the dimensions
    arg_parser = get_argument_parser(dimensions=None)
    try:
        args, _ = arg_parser.parse_known_args(argv)
    except SystemExit:
        # If the user didn't provide a config file, print the help message
        arg_parser.print_help()
        return 1

    try:
        dict_config = toml.loads(args.config.read_text())
    except FileNotFoundError:
        print(f"Configuration file not found: {args.config}", file=sys.stderr)
        return 1
    except exceptions.TomlDecodeError as exc:
        print(exc, file=sys.stderr)
        return 1

    try:
        config = combiner.build_config(dict_config)
    except exceptions.TomlCombineError as exc:
        print(exc, file=sys.stderr)
        return 1

    # Parse all arguments
    arg_parser = get_argument_parser(dimensions=config.dimensions)
    args = arg_parser.parse_args(argv)

    mapping = {
        key: value
        for key, value in vars(args).items()
        if key in config.dimensions and value
    }
    # Generate final configurations for requested mapping
    try:
        result = lib.combine(config=dict_config, **mapping)
    except exceptions.TomlCombineError as exc:
        print(exc, file=sys.stderr)
        return 1

    if args.format == "toml":
        # Convert the result to TOML format

        print(toml.dumps(result))
    else:
        # Convert the result to JSON format
        print(json.dumps(result, indent=2))

    return 0


def run_cli():
    sys.exit(cli(sys.argv[1:]))
