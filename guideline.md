# Defensive & Pragmatic Python — Claude Code Guideline

> **Purpose**: Live coding session reference for clean, type-safe, functionally-oriented
> Python. Every piece of production code must be driven by tests. This document is the
> contract Claude Code follows throughout the session.

---

## 0. Philosophy

Three principles govern every design decision in this session:

| Principle | What it means in practice |
|---|---|
| **Parse, don't validate** | Transform untrusted data into rich types at the boundary. Never pass raw strings/dicts into domain logic. |
| **Make illegal states unrepresentable** | Model your domain so invalid combinations cannot be constructed — not just caught at runtime. |
| **Value Objects** | Wrap primitives in named types that carry their own invariants. `UserId` is not an `int`. |

Python's runtime won't enforce these for you. The toolchain will.

---

## 1. Toolchain (non-negotiable)

### Type checking — `pyright` in strict mode

Every project must have a `pyrightconfig.json` at the root:

```json
{
  "typeCheckingMode": "strict",
  "pythonVersion": "3.12",
  "reportMissingImports": true,
  "reportUnusedVariable": "warning"
}
```

Run before every commit. Treat type errors as build failures.

### Testing — `pytest` + `hypothesis`

```toml
# pyproject.toml
[tool.pytest.ini_options]
addopts = "--tb=short -q"

[tool.hypothesis]
max_examples = 200
```

Two kinds of tests always coexist:

- **Example-based** (`pytest`): specific cases, edge cases, happy path, known failures.
- **Property-based** (`hypothesis`): invariants that must hold for *any* valid input.

### Libraries

```bash
pip install pydantic returns expression pyright pytest hypothesis
```

| Library | Role |
|---|---|
| `pydantic` | Parsing and validation at system boundaries (HTTP, files, env) |
| `returns` | `Result`, `Maybe`, railway-oriented programming inside domain logic |
| `expression` | FP utilities: `pipe`, `Option`, tagged unions, immutable collections |
| `pyright` | Static type enforcement |

---

## 2. TDD Rules

### The only allowed workflow

```
Install deps → Tests collect & run → Watch them fail (right reason) → Write minimum code to pass → Refactor
```

No production code without a test first. No exceptions.

### Prerequisite: tests must be runnable before anything else

Before writing any solution code, verify:

1. **Dependencies are installed** — `pytest`, `hypothesis`, `pydantic`, `returns`, `expression` must all be importable. Run `pip install` if needed.
2. **Tests collect without import errors** — `pytest --collect-only` must succeed.
3. **Tests fail for the right reason** — the failure must be `ModuleNotFoundError: No module named 'solution'` (or equivalent), not a tooling/environment error.

Only once step 3 is confirmed is it valid to write `solution.py`.

### Test file structure

```
exercises/
  exercise_01_value_objects/
    README.md          ← what to implement and why
    test_solution.py   ← tests written first, solution import commented out
    solution.py        ← written after tests pass
  exercise_02_parse_dont_validate/
    ...
```

Each exercise is self-contained. Tests import from `solution.py` in the same directory.

### Naming convention

```python
# Example-based
def test_<unit>_<scenario>_<expected_outcome>():
    ...

# Property-based
@given(...)
def test_<unit>_property_<invariant_name>(...):
    ...
```

---

## 3. FP Concepts (explained for mixed audiences)

### 3.1 Value Objects

> A **Value Object** is an object whose identity is defined by its value, not its
> memory address. Two `Email("a@b.com")` instances are equal. It is immutable.
> It validates itself on construction — or refuses to be constructed.

```python
from dataclasses import dataclass
from returns.result import Result, Success, Failure


@dataclass(frozen=True)  # frozen = immutable after creation
class Email:
    value: str

    def __post_init__(self) -> None:
        if "@" not in self.value:
            raise ValueError(f"Invalid email: {self.value!r}")

    @classmethod
    def parse(cls, raw: str) -> Result["Email", str]:
        """Parse, don't validate: return a Result instead of raising."""
        if "@" not in raw:
            return Failure(f"Invalid email: {raw!r}")
        return Success(cls(raw))
```

Key point: `Email.parse()` returns a `Result` — the caller is **forced** to handle
the failure case. No silent `None`, no uncaught exception.

### 3.2 Parse, don't validate

> **Validate**: take a value, return `True/False`. The value is still untyped after.
> **Parse**: take a value, return a *richer type* or an explicit failure. After parsing,
> the type itself is the proof of validity.

```python
# ❌ Validate — caller can ignore the check
def is_valid_age(n: int) -> bool:
    return 0 <= n <= 150

age = int(input())
# nothing stops you from using `age` without calling is_valid_age first

# ✅ Parse — the type carries the proof
@dataclass(frozen=True)
class Age:
    value: int

    @classmethod
    def parse(cls, n: int) -> Result["Age", str]:
        if not (0 <= n <= 150):
            return Failure(f"Age must be 0–150, got {n}")
        return Success(cls(n))
```

### 3.3 Make illegal states unrepresentable

> If your type system allows constructing a value that has no valid meaning in your
> domain, you have a latent bug waiting for conditions to trigger it.

```python
# ❌ Allows nonsense: is_loading=True AND data=something
@dataclass
class FetchState:
    is_loading: bool
    data: str | None
    error: str | None

# ✅ Only valid combinations can exist
from typing import Literal
from expression import tagged_union, case, tag

@tagged_union
class FetchState:
    tag: Literal["loading", "success", "error"] = tag()
    loading: None = case()
    success: str = case()
    error: str = case()
```

Pattern match on it — pyright will warn you if a branch is missing.

### 3.4 Result & Railway-Oriented Programming

> **Railway-oriented programming** (ROP): imagine two tracks — a success track and a
> failure track. Once a computation derails onto the failure track, subsequent steps
> are skipped. You compose functions that can fail without nested `try/except`.

```python
from returns.result import Result, Success, Failure
from returns.pipeline import flow
from returns.pointfree import bind


def parse_email(raw: str) -> Result[Email, str]:
    ...

def check_not_banned(email: Email) -> Result[Email, str]:
    ...

def create_user(email: Email) -> Result[User, str]:
    ...

# Functions compose on the success track; failures short-circuit
register = flow(
    parse_email,
    bind(check_not_banned),
    bind(create_user),
)

result = register("user@example.com")

match result:
    case Success(user):
        print(f"Created: {user}")
    case Failure(error):
        print(f"Failed: {error}")
```

### 3.5 Option / Maybe

> Use `Maybe` when a value may legitimately be absent — not as an error, just as
> "nothing here". Replaces `None` returns with an explicit type you must unwrap.

```python
from returns.maybe import Maybe, Some, Nothing


def find_user(user_id: int) -> Maybe[User]:
    user = db.get(user_id)
    return Some(user) if user else Nothing

# Force the caller to handle absence
match find_user(42):
    case Some(user):
        print(user.name)
    case Nothing:
        print("Not found")
```

### 3.6 Pipe

> `pipe` passes a value through a sequence of functions left-to-right.
> It replaces `f(g(h(x)))` with something readable.

```python
from expression import pipe
from expression.collections import seq


result = pipe(
    [1, 2, 3, 4, 5],
    seq.map(lambda x: x * 2),
    seq.filter(lambda x: x > 4),
    list,
)
# result = [6, 8, 10]
```

---

## 4. Exercise Structure

Each exercise follows this pattern:

```
README.md        — concept explained, what to implement
test_solution.py — tests written BEFORE solution.py exists
solution.py      — written during the session, TDD-driven
```

### Exercise list

| # | Concept | Key tool |
|---|---|---|
| 01 | Value Objects — wrap a primitive, enforce invariants | `dataclass(frozen=True)` |
| 02 | Parse, don't validate — `Result` at the boundary | `returns` |
| 03 | Illegal states — model a state machine | `expression @tagged_union` |
| 04 | Railway — compose fallible functions | `returns flow + bind` |
| 05 | Pydantic at the boundary — parse external JSON | `pydantic BaseModel` |
| 06 | Property-based tests — find invariant violations | `hypothesis` |
| 07 | Putting it together — a small domain end-to-end | all of the above |

---

## 5. Exercise Templates

### Exercise 01 — Value Objects

**`test_solution.py`**

```python
import pytest
from hypothesis import given, strategies as st
from solution import Email, Age  # noqa: these don't exist yet — tests fail first


class TestEmail:
    def test_valid_email_is_created(self):
        email = Email("user@example.com")
        assert email.value == "user@example.com"

    def test_email_without_at_sign_raises(self):
        with pytest.raises(ValueError):
            Email("notanemail")

    def test_emails_with_same_value_are_equal(self):
        assert Email("a@b.com") == Email("a@b.com")

    def test_email_is_immutable(self):
        email = Email("a@b.com")
        with pytest.raises(Exception):  # frozen dataclass raises FrozenInstanceError
            email.value = "other@b.com"  # type: ignore

    @given(st.emails())
    def test_property_valid_email_always_parses(self, raw: str):
        email = Email(raw)
        assert "@" in email.value


class TestAge:
    def test_valid_age_is_created(self):
        assert Age(25).value == 25

    def test_negative_age_raises(self):
        with pytest.raises(ValueError):
            Age(-1)

    def test_age_over_150_raises(self):
        with pytest.raises(ValueError):
            Age(151)

    @given(st.integers(min_value=0, max_value=150))
    def test_property_any_valid_age_constructs(self, n: int):
        assert Age(n).value == n

    @given(st.integers().filter(lambda x: x < 0 or x > 150))
    def test_property_invalid_age_always_raises(self, n: int):
        with pytest.raises(ValueError):
            Age(n)
```

---

### Exercise 02 — Parse, don't validate

**`test_solution.py`**

```python
from returns.result import Success, Failure
from hypothesis import given, strategies as st
from solution import Email, Age


class TestEmailParse:
    def test_parse_valid_email_returns_success(self):
        result = Email.parse("user@example.com")
        assert isinstance(result, Success)

    def test_parse_invalid_email_returns_failure(self):
        result = Email.parse("notanemail")
        assert isinstance(result, Failure)

    def test_parse_empty_string_returns_failure(self):
        result = Email.parse("")
        assert isinstance(result, Failure)

    @given(st.emails())
    def test_property_valid_emails_always_succeed(self, raw: str):
        assert isinstance(Email.parse(raw), Success)

    @given(st.text().filter(lambda s: "@" not in s))
    def test_property_strings_without_at_always_fail(self, raw: str):
        assert isinstance(Email.parse(raw), Failure)


class TestAgeParse:
    def test_parse_valid_age_returns_success(self):
        assert isinstance(Age.parse(30), Success)

    def test_parse_negative_returns_failure(self):
        assert isinstance(Age.parse(-1), Failure)

    @given(st.integers(min_value=0, max_value=150))
    def test_property_valid_range_always_succeeds(self, n: int):
        assert isinstance(Age.parse(n), Success)
```

---

### Exercise 03 — Illegal States

**`test_solution.py`**

```python
import pytest
from solution import Order, OrderStatus


class TestOrderStateMachine:
    def test_new_order_is_pending(self):
        order = Order.new(item="Book", quantity=1)
        assert order.status == OrderStatus.PENDING

    def test_pending_order_can_be_confirmed(self):
        order = Order.new("Book", 1)
        confirmed = order.confirm()
        assert confirmed.status == OrderStatus.CONFIRMED

    def test_confirmed_order_can_be_shipped(self):
        order = Order.new("Book", 1).confirm()
        shipped = order.ship()
        assert shipped.status == OrderStatus.SHIPPED

    def test_pending_order_cannot_be_shipped_directly(self):
        order = Order.new("Book", 1)
        with pytest.raises(Exception):
            order.ship()

    def test_shipped_order_cannot_be_cancelled(self):
        order = Order.new("Book", 1).confirm().ship()
        with pytest.raises(Exception):
            order.cancel()

    def test_cancelled_order_cannot_be_confirmed(self):
        order = Order.new("Book", 1).cancel()
        with pytest.raises(Exception):
            order.confirm()
```

---

### Exercise 04 — Railway-Oriented Programming

**`test_solution.py`**

```python
from returns.result import Success, Failure
from solution import register_user


class TestRegisterUser:
    def test_valid_registration_succeeds(self):
        result = register_user(email="user@example.com", age=25)
        assert isinstance(result, Success)

    def test_invalid_email_fails_early(self):
        result = register_user(email="notanemail", age=25)
        assert isinstance(result, Failure)
        assert "email" in result.failure().lower()

    def test_invalid_age_fails(self):
        result = register_user(email="user@example.com", age=-5)
        assert isinstance(result, Failure)
        assert "age" in result.failure().lower()

    def test_banned_email_fails(self):
        result = register_user(email="banned@blacklist.com", age=25)
        assert isinstance(result, Failure)
        assert "banned" in result.failure().lower()

    def test_failure_is_descriptive(self):
        result = register_user(email="", age=25)
        assert isinstance(result, Failure)
        assert len(result.failure()) > 0
```

---

### Exercise 05 — Pydantic at the Boundary

**`test_solution.py`**

```python
import pytest
from pydantic import ValidationError
from solution import UserPayload, parse_user_payload


class TestUserPayload:
    def test_valid_payload_parses(self):
        raw = {"email": "user@example.com", "age": 30, "name": "Alice"}
        user = UserPayload.model_validate(raw)
        assert user.email == "user@example.com"

    def test_missing_field_raises(self):
        with pytest.raises(ValidationError):
            UserPayload.model_validate({"email": "user@example.com"})  # no age

    def test_wrong_type_raises(self):
        with pytest.raises(ValidationError):
            UserPayload.model_validate({"email": "user@example.com", "age": "old", "name": "Alice"})

    def test_invalid_email_raises(self):
        with pytest.raises(ValidationError):
            UserPayload.model_validate({"email": "notanemail", "age": 30, "name": "Alice"})

    def test_parse_returns_domain_object(self):
        raw = {"email": "user@example.com", "age": 30, "name": "Alice"}
        result = parse_user_payload(raw)
        # result should be a domain User, not a raw dict
        assert hasattr(result, "email")
```

---

### Exercise 06 — Property-Based Testing

**`test_solution.py`**

```python
from hypothesis import given, strategies as st, assume
from solution import Email, Age, merge_user_data


class TestProperties:
    @given(st.emails())
    def test_email_roundtrip(self, raw: str):
        """Parsing a valid email and reading back its value is lossless."""
        email = Email(raw)
        assert email.value == raw

    @given(st.integers(min_value=0, max_value=150))
    def test_age_value_preserved(self, n: int):
        """Age value is stored exactly as provided."""
        assert Age(n).value == n

    @given(st.dictionaries(st.text(), st.text()),
           st.dictionaries(st.text(), st.text()))
    def test_merge_is_associative_on_non_overlapping_keys(self, a: dict, b: dict):
        """Merging two dicts with no shared keys: order doesn't matter."""
        assume(not set(a.keys()) & set(b.keys()))
        assert merge_user_data(a, b) == merge_user_data(b, a)

    @given(st.text(min_size=1))
    def test_email_parse_failure_message_is_never_empty(self, raw: str):
        """A failed parse always produces a descriptive error message."""
        from returns.result import Failure
        assume("@" not in raw)
        result = Email.parse(raw)
        assert isinstance(result, Failure)
        assert len(result.failure()) > 0
```

---

### Exercise 07 — End-to-End Domain

**`README.md` (to write during session)**

Design and TDD a minimal `OrderService` that:

- Accepts raw JSON input (parse with `pydantic`)
- Creates `Order` value objects (parse, don't validate)
- Runs through a state machine (illegal states unrepresentable)
- Returns `Result[Order, str]` at every step (railway)
- Has both example-based and property-based tests

This is the integration exercise — no new concepts, only composition.

---

## 6. Code Style Rules for Claude Code

These rules apply to **all generated code** in this session.

```
1. Every public function has a return type annotation.
2. No bare `except:` — always catch specific types.
3. No `Optional[X]` — use `X | None` (Python 3.10+ syntax).
4. No mutable default arguments.
5. No `dict` or `list` as domain types — wrap them in named types.
6. `dataclass(frozen=True)` for all value objects.
7. `Result` for operations that can fail. Never return `None` as an error signal.
8. `Maybe/Option` for optional presence. Never return `None` as "not found".
9. Pydantic models live at the boundary only — never passed into domain logic.
10. Tests use `assert` directly — no `assertEqual`, no unittest style.
```

---

## 7. Project Setup

```bash
# Bootstrap a session exercise directory
mkdir python_fp_session && cd python_fp_session
python -m venv .venv && source .venv/bin/activate

pip install pydantic "returns[compatible-mypy]" expression pytest hypothesis

# pyright
pip install pyright
cat > pyrightconfig.json << 'EOF'
{
  "typeCheckingMode": "strict",
  "pythonVersion": "3.12"
}
EOF

# Run all tests
pytest exercises/ -v

# Type check
pyright exercises/
```

---

## 8. Quick Reference Card

```
CONCEPT                  TOOL                    PATTERN
─────────────────────────────────────────────────────────────────
Value Object             dataclass(frozen=True)  Wrap + validate in __post_init__
Parse boundary           pydantic BaseModel      model_validate(raw_dict)
Parse domain             returns Result          @classmethod parse() → Result[Self, str]
Absent value             returns Maybe           Some(x) | Nothing
Composing failures       returns flow + bind     flow(parse, bind(validate), bind(save))
Illegal states           expression tagged_union match on tag, pyright checks exhaustion
Pipelines                expression pipe         pipe(value, fn1, fn2, fn3)
Immutable collections    expression Block/Map    Block([1,2,3])
Example tests            pytest                  def test_<unit>_<scenario>_<outcome>
Property tests           hypothesis @given       @given(st.text()) def test_invariant(...)
Type checking            pyright strict          pyrightconfig.json typeCheckingMode=strict
```
