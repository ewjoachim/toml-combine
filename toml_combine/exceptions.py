from __future__ import annotations


class TomlCombineError(Exception):
    """There was an error in the toml-combine library."""

    def __init__(self, message: str = "", **kwargs) -> None:
        message = message or type(self).__doc__ or ""
        message = message.format(**kwargs)

        super().__init__(message)


class TomlDecodeError(TomlCombineError):
    """Error while decoding configuration file."""


class TomlEncodeError(TomlCombineError):
    """Error while encoding configuration file."""


class IncompatibleOverrides(TomlCombineError):
    """Incompatible overrides `{id}` and `{other_override}`: When they're both applicable, overrides defining a common overridden key ({key}) must be a subset of one another"""


class DimensionNotFound(TomlCombineError):
    """In {type} {id}: Dimension {dimension} not found."""


class DimensionValueNotFound(TomlCombineError):
    """In {type} {id}: Value {value} for dimension {dimension} not found."""


class MissingOverrideCondition(TomlCombineError):
    """In override {id}: Missing 'when' key in override configuration"""
