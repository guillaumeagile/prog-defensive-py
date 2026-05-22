# Module 02 — Part 6 Conclusion: The `returns` Library

## What is `returns`?

Production-grade Railway Oriented Programming for Python from dry-python.

```bash
pip install returns
```

## Key types

| Type | Meaning |
|------|---------|
| `Success[T]` | The happy path value |
| `Failure[E]` | The error value |
| `Result[T, E]` | `Success[T] \| Failure[E]` |

## Key features

### 1. `flow()` — compose without nesting

```python
from returns.pipeline import flow
from returns.pointfree import bind

def process(user_id: int) -> Result[float, object]:
    return flow(
        user_id,
        get_user,
        bind(get_account),
        bind(get_balance),
    )
```

### 2. `@safe` — bridge from exceptions

```python
from returns.result import safe

@safe
def parse_json(raw: str) -> dict:
    return json.loads(raw)  # Raises on invalid JSON

parse_json('{"a": 1}')   # → Success({'a': 1})
parse_json('not json')   # → Failure(ValueError(...))
```

### 3. `value_or()` — unwrap with default

```python
balance = get_balance_flow(1).value_or(0.0)  # Never throws
```

### 4. `map()` — transform in context

```python
result = get_balance_flow(1).map(lambda b: b * 1.05)  # Add fee
```

## The spectrum of explicitness

```
Exceptions          Named returns       Result[T, E]        Full ADTs
(rude —             (honest but         (explicit,          (sealed types,
 invisible,          not chainable)      chainable,           nothing illegal)
 untyped)                               type-checked)

   ◄──────────────────────────────────────────────────────────────►
   most common                                           most explicit
   in Python today                                      in Python today
```

## When to use what

| Approach | Use when |
|----------|----------|
| Exceptions | Truly exceptional: DB down, network timeout, bug |
| Named tuple return | Stepping stone, team not ready for ROP |
| Hand-rolled Result | Learning/teaching, no deps allowed |
| `returns` library | Production, team bought in, complex chains |

## Integration with web frameworks

### FastAPI

```python
from fastapi import FastAPI, HTTPException

@app.get("/balance/{user_id}")
def get_balance_endpoint(user_id: int):
    match get_balance_flow(user_id):
        case Success(success_value=balance):
            return {"balance": balance}
        case Failure(failure_value=UserNotFound()):
            raise HTTPException(404, "User not found")
        case Failure(failure_value=AccountNotFound()):
            raise HTTPException(404, "Account not found")
        case Failure(failure_value=AccountSuspended()):
            raise HTTPException(403, "Account suspended")
```

## Static checking

```bash
poetry add --group dev returns pyright mypy

poetry run pyright --project pyright.returns.json
poetry run mypy --config-file mypy.returns.ini
```

## Further reading

- `returns` docs: https://returns.readthedocs.io
- Railway Oriented Programming: https://fsharpforfun.com/rop
- Domain Modeling Made Functional (Scott Wlaschin)

## Module 02 complete

You've seen the progression:
1. Hand-rolled `Result[T, E]`
2. Railway chains with `bind`
3. Production ROP with `returns`

Next: Module 03 — Illegal states unrepresentable (sum types and sealed hierarchies).
