
## Code Style

We use [Black](https://black.readthedocs.io/en/stable/) (PEP 8 compliant) for code formatting.

Install it to format your code after writing code or use it in your IDE as code formatter.

To format run:

```sh
black dialect
```

We also use [isort](https://pycqa.github.io/isort/) for imports sorting.

```sh
isort dialect
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
