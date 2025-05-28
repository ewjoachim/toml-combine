## Development

This project uses [uv](https://docs.astral.sh/uv/).

If you don't have uv installed, install it with:

```console
$ curl -LsSf https://astral.sh/uv/install.sh | sh
```

or using a package manager, such as [brew](https://brew.sh/):

```console
$ brew install uv
```

### Work with UV (will handle the venv for you)

**Run tests**

```console
$ uv run pytest
```

**Run the command**

```console
$ uv run toml-combine --help
```

### Work with a classic virtual environment

**Create and activate a virtual environment**

```console
$ uv sync
$ source .venv/bin/activate
```

**Run tests**

```console
$ pytest
```

**Run the command**

```console
$ toml-combine --help
```

> [!NOTE]
> In this venv, if you need `pip` you can use `uv pip` instead, it works the same.
