# Module 02 — Part 4 Conclusion: Hand-rolled Result[T, E]

## What we built

A minimal, production-quality `Result[T, E]` type in ~30 lines:

- `Ok[T]` — carries a success value, `bind` continues the chain
- `Err[E]` — carries an error value, `bind` short-circuits (returns `self`)
- Both are frozen dataclasses — immutable, comparable, hashable

## Why this matters

**Honest signatures:** `Result[User, UserNotFound]` tells you everything before you run the code.

**Explicit control flow:** No hidden stack unwinding. No surprises. Errors are values.

**Composability:** `bind` lets you chain without nesting. The happy path stays flat.

## The Result type at a glance

```python
@dataclass(frozen=True)
class Ok(Generic[T]):
    value: T
    def bind(self, fn): return fn(self.value)  # keep going

@dataclass(frozen=True)
class Err(Generic[E]):
    error: E
    def bind(self, fn): return self             # short-circuit

Result = Ok[T] | Err[E]
```

## Trade-offs

| Pros | Cons |
|------|------|
| Zero dependencies | Must implement helpers yourself |
| Full control over API | No ecosystem integration |
| Great for learning ROP | Reinventing what `returns` provides |

## When to use

- Teaching ROP concepts
- Codebases where adding dependencies is hard
- When you need custom `Result` behavior

## When to migrate to `returns`

- Production code with many Result chains
- Need `flow`, `pipe`, `curry`, `@safe` decorators
- Team already comfortable with ROP

## Static checking

```bash
poetry run pyright --project pyright.hand_rolled.json
poetry run mypy --config-file mypy.hand_rolled.ini
```

## Direction of travel

```
Exceptions  →  Hand-rolled Result  →  returns library  →  Full ADTs
(rude)          (explicit)            (composable)        (sealed types)
```

You're now at step 2. Part 5 adds Railway chains. Part 6 introduces `returns`.
