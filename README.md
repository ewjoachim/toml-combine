# Toml-combine

`toml-combine` is a Python lib and CLI-tool that reads a TOML configuration file
defining a default configuration alongside with overrides, and merges everything
following rules you define to get final configurations. Let's say: you have multiple
services, and environments, and you want to describe them all without repeating the
parts that are common to everyone.

## Concepts

### The config file

The configuration file is usually a TOML file. Here's a small example:

```toml
[dimensions]
environment = ["production", "staging"]

[[output]]
environment = "production"

[[output]]
environment = "staging"

[default]
name = "my-service"
registry = "gcr.io/my-project/"
container.image_name = "my-image"
container.port = 8080
service_account = "my-service-account"

[[override]]
when.environment = "staging"
service_account = "my-staging-service-account"
```

### Dimensions

Consider all the configurations you want to generate. Each one differs from the others.
Dimensions lets you describe the main "thing" that makes the outputs differents, e.g.:
`environment` might be `staging` or `production`, region might be `eu` or `us`, and
service might be `frontend` or `backend`. Some combinations of dimensions might not
exists, for example, maybe there's no `staging` in `eu`.

### Outputs

Create a `output` for each configuration you want to generate, and specify the
dimensions relevant for this output. It's ok to omit some dimensions when they're not
used for a given output.

> [!Note]
> Defining a list as the value of one or more dimensions in a output
> is a shorthand for defining all combinations of dimensions

### Default

The common configuration to start from, before we start overlaying overrides on top.

### Overrides

Overrides define a set of condition where they apply (`when.<dimension> =
"<value>"`) and the values that are overriden. Overrides are applied in order from less
specific to more specific, each one overriding the values of the previous ones:

- If an override contains conditions on more dimensions than another one, it's applied
  later
- In case 2 overrides contain the same number of dimensions and they're a disjoint set,
  then it depends on how the dimensions are defined at the top of the file: dimensions
  defined last have a greater priority

> [!Note]
> Defining a list as the value of one or more conditions in an override
> means that the override will apply to any of the dimension values of the list

### The configuration itself

Under the layer of `dimensions/output/default/override` system, what you actually define
in the configuration is completely up to you. That said, only nested
"dictionnaries"/"objects"/"tables"/"mapping" (those are all the same things in
Python/JS/Toml lingo) will be merged between the default and the overrides, while
arrays will just replace one another. See `Arrays` below.

In the generated configuration, the dimensions of the output will appear in the generated
object as an object under the `dimensions` key.

### Arrays

Let's look at an example:

```toml
[dimensions]
environment = ["production", "staging"]

[[output]]
environment = ["production", "staging"]

[default]
fruits = [{name="apple", color="red"}]

[[override]]
when.environment = "staging"
fruits = [{name="orange", color="orange"}]
```

In this example, on staging, `fruits` is `[{name="orange", color="orange"}]` and not `[{name="apple", color="red"}, {name="orange", color="orange"}]`.
The only way to get multiple values to be merged is if they are tables: you'll need
to chose an element to become the key:

```toml
[dimensions]
environment = ["production", "staging"]

[[output]]
environment = ["production", "staging"]

[default]
fruits.apple.color = "red"

[[override]]
when.environment = "staging"
fruits.orange.color = "orange"
```

In this example, on staging, `fruits` is `{apple={color="red"}, orange={color="orange"}}`.

This example is simple because `name` is a natural choice for the key. In some cases,
the choice is less natural, but you can always decide to name the elements of your
list and use that name as a key. Also, yes, you'll loose ordering.

### A bigger example

```toml
[dimensions]
environment = ["production", "staging", "dev"]
service = ["frontend", "backend"]

# All 4 combinations of those values will exist
[[output]]
environment = ["production", "staging"]
service = ["frontend", "backend"]

# On dev, the "service" is not defined. That's ok.
[[output]]
environment = "dev"

[default]
registry = "gcr.io/my-project/"
service_account = "my-service-account"

[[override]]
when.service = "frontend"
name = "service-frontend"
container.image_name = "my-image-frontend"

[[override]]
when.service = "backend"
name = "service-backend"
container.image_name = "my-image-backend"
container.port = 8080

[[override]]
name = "service-dev"
when.environment = "dev"
container.env.DEBUG = true
```

### CLI

```console
$ toml-combine {path/to/config.toml}
```

Generates all the outputs described by the given TOML config.

Note that you can restrict generation to some dimension values by passing
`--{dimension}={value}`

## Lib

```python
import toml_combine


result = toml_combine.combine(
        config_file=config_file,
        environment=["production", "staging"],
        type="job",
        job=["manage", "special-command"],
    )

print(result)
{
  "production-job-manage": {...},
  "production-job-special-command": {...},
  "staging-job-manage": {...},
  "staging-job-special-command": {...},
}
```

You can pass either `config` (TOML string or dict) or `config_file` (`pathlib.Path` or string path) to `combine()`. Additional `kwargs` restrict the output.
