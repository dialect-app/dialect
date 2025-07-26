## Development environment

When developing Dialect it is encouraged to use the [uv](https://docs.astral.sh/uv/) project manager.

After installing uv, run `uv sync` to create or sync a venv with the projects dependencies.

## Code Style

We use the Ruff formatter (PEP 8 compliant) for code formatting.

To format the code run:

```sh
ruff check --select I --fix && ruff format
```

### Type Annotations

We try to use Python type annotations whenever is possible.

#### When to omit annotations?

- Explicit classes instantiation like:

  ```python
  var = Class()
  ```

- Non-nullable argument with default value:

  ```python
  # We omit `int` typing for `number`
  def method(text: str, number = 5, other: int | None = 20):
      ...
  ```
