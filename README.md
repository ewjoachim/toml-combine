# Toml-combine

`toml-combine` is a Python lib and CLI-tool that reads a TOML configuration file
defining a default configuration alongside with overrides, and merges everything
following rules you define to get final configurations. Let's say: you have multiple
services, and environments, and you want to describe them all without repeating the
parts that are common to everyone.

## Concepts

### The config file

The configuration file is (usually) a TOML file. Here's a small example:

```toml
[dimensions]
environment = ["production", "staging"]

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

### Default

The common configuration to start from, before we start overlaying overrides on top.

### Overrides

Overrides define a set of condition where they apply (`when.<dimension> =
"<value>"`) and the values that are overriden. Overrides are applied in order from less
specific to more specific, each one overriding the values of the previous ones:

- In case 2 overrides are applicable, the more specific one (the one with more
  dimensions defined) has greater priority
- In case 2 overrides use the same number of dimensions, then it depends on how the
  dimensions are defined at the top of the file: dimensions defined last have a greater
  priority
- In case 2 overrides use the same dimensions, if they define the same configuration
  values, an error will be raised. If they define different configuation values, then
  the priority is irrelevant.

> [!Note]
> Defining a list as the value of one or more conditions in an override
> means that the override will apply to any of the dimension values of the list

### The configuration itself

Under the layer of `dimensions/default/override/mapping` system, what you actually define
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

[default]
fruits = [{name="apple", color="red"}]

[[override]]
when.environment = "staging"
fruits = [{name="orange", color="orange"}]
```

In this example, with `{"environment": "staging"}`, `fruits` is
`[{name="orange", color="orange"}]` and not
`[{name="apple", color="red"}, {name="orange", color="orange"}]`.
The only way to get multiple values to be merged is if they are dicts: you'll need
to chose an element to become the key:

```toml
[dimensions]
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

### Mapping

When you call the tool either with the CLI or the lib (see both below), you will have to
provide a mapping of the desired dimentions. These values will be compared to overrides
to apply overrides when relevant. It's ok to omit some dimensions, corresponding
overrides won't be selected.

By default, the output is `toml` though you can switch to `json` with `--format=json`

## CLI

Example with the config from the previous section:

```console
$ toml-combine path/to/config.toml --environment=staging
```

```toml
[fruits]
apple.color = "red"
orange.color = "orange"
```

## Lib

```python
import toml_combine


result = toml_combine.combine(config_file=config_file, environment="staging")

print(result)
{
  "fruits": {"apple": {"color": "red"}, "orange": {"color": "orange"}}
}
```

You can pass either `config` (TOML string or dict) or `config_file` (`pathlib.Path` or string path) to `combine()`. All other `kwargs` specify the mapping you want.

## A bigger example

```toml
[dimensions]
environment = ["production", "staging", "dev"]
service = ["frontend", "backend"]

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

[[override]]
when.environment = ["staging", "dev"]
when.service = "backend"
container.env.ENABLE_EXPENSIVE_MONITORING = false
```

This produces the following configs:

```console
$ toml-combine example.toml --environment=production --service=frontend
```

```toml
registry = "gcr.io/my-project/"
service_account = "my-service-account"
name = "service-frontend"

[container]
image_name = "my-image-frontend"
```

```console
$ toml-combine example.toml --environment=production --service=backend
```

```toml
registry = "gcr.io/my-project/"
service_account = "my-service-account"
name = "service-backend"

[container]
image_name = "my-image-backend"
port = 8080
```

```console
$ toml-combine example.toml --environment=staging --service=frontend
```

```toml
registry = "gcr.io/my-project/"
service_account = "my-service-account"
name = "service-frontend"

[container]
image_name = "my-image-frontend"
```

```console
$ toml-combine example.toml --environment=staging --service=backend
```

```toml
registry = "gcr.io/my-project/"
service_account = "my-service-account"
name = "service-backend"

[container]
image_name = "my-image-backend"
port = 8080

[container.env]
ENABLE_EXPENSIVE_MONITORING = false
```

```console
$ toml-combine example.toml --environment=dev --service=backend
```

```toml
registry = "gcr.io/my-project/"
service_account = "my-service-account"
name = "service-backend"

[container]
image_name = "my-image-backend"
port = 8080
[container.env]
DEBUG = true
ENABLE_EXPENSIVE_MONITORING = false
```
