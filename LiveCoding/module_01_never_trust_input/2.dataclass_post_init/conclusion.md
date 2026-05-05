# Module 01 — Conclusion: dataclass + __post_init__

## Where this fits in Module 01

- **Live step:** `2.dataclass_post_init/` (fallback path)
- **Approach covered here:** Approach C
- **Compares against:** Approach B (recommended), with no Pydantic dependency
- **Concepts reinforced:** value objects, parse-don't-validate contract, explicit failures via `Result`

---

## What this approach shows

Approach B (Pydantic + Result) is the recommended path. But it requires an external dependency.
This step answers the question: **what if you can't or won't use Pydantic?**

The answer: the same pattern, with stdlib only.

---

## How it works

```python
@dataclass(frozen=True)
class UserInput:
    name: str
    age: int
    email: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", self.name.strip())
        if not self.name:
            raise ValueError("name cannot be blank")
        if not (0 <= self.age <= 150):
            raise ValueError(f"age must be 0–150, got {self.age}")
        if "@" not in self.email:
            raise ValueError(f"invalid email: {self.email!r}")


def parse_user_input(name: str, age: int, email: str) -> Result[UserInput, str]:
    try:
        return Success(UserInput(name=name, age=age, email=email))
    except ValueError as e:
        return Failure(str(e))
```

`__post_init__` runs automatically after `__init__`. It is the natural hook for invariant
enforcement in a dataclass. The `ValueError` it raises is immediately caught by `parse_user_input`
and converted to a `Failure` — it never reaches the caller.

**One subtlety:** `frozen=True` makes the dataclass immutable after construction, which means
normal attribute assignment (`self.name = ...`) raises `FrozenInstanceError`. To normalise
a field (strip whitespace) you must use `object.__setattr__(self, "name", ...)` instead.
This is a stdlib quirk worth knowing.

---

## Comparing the three approaches

| | Approach A (Pydantic + exceptions) | Approach B (Pydantic + Result) | Approach C (dataclass + Result) |
|---|---|---|---|
| External dependency | `pydantic` | `pydantic`, `returns` | `returns` only |
| Coercion (string → int) | Yes, automatic | Yes, automatic | Manual |
| Validation rules | Declarative (`Field`, validators) | Declarative | Imperative (`if` statements) |
| Error path in signature | No | Yes | Yes |
| Boilerplate | Low | Low | Medium |

## When to use this

- Legacy projects where adding Pydantic is not an option
- Small utilities or CLIs where a full validation library is overkill
- Teaching the principle without hiding it behind a framework

For production services with external inputs (HTTP, queues, files), prefer Approach B.
The declarative style of Pydantic scales better as the number of fields grows.

---

## The invariant stays the same

Regardless of the tool — Pydantic or `dataclass` — the contract is identical:

> `parse_user_input(...) -> Result[UserInput, str]`

`UserInput` is still an immutable value object, and the caller never needs `try/except`.
The error path is in the type.
