# Module 01 — Conclusion: Result with stronger types

## Where this fits in Module 01

- **Live step:** `3.result_stronger_types/` (optional deep dive after Approaches A/B/C)
- **Approach covered here:** Approach D
- **Builds on:** `1.quick_first_view/results/solution_results.py`
- **Goal:** replace `Result[UserInput, str]` with `Result[ParsedUserInput, ParseUserError]`

---

## What changed

Approach B made the error path explicit using `Result`, but used `str` for failures.
Approach D keeps the same flow and makes failures typed.

```python
# Approach B
parse_user_input(...) -> Result[UserInput, str]

# Approach D
parse_user_input(...) -> Result[ParsedUserInput, ParseUserError]
```

That shift gives you compiler/type-checker help and safer pattern matching at call sites.

---

## Why this is more FP-style

- Parse at the boundary once (`parse_raw_user_input` with Pydantic)
- Parse domain primitives into value objects (`Name`, `Age`, `Email`)
- Compose fallible steps with `flow(..., bind(...))`
- Represent each expected failure as a variant, not as a free-form string
- Differentiate error intent precisely (`NameEmpty` vs `NameBlank`)

```python
match result:
    case Success(user):
        ...
    case Failure(NameBlank()):
        ...
    case Failure(AgeOutOfRange(raw_age=age)):
        ...
    case Failure(PayloadError(field=field, message=message)):
        ...
```

---

## Trade-off

Typed errors are more explicit and safer, but they add a bit more ceremony
(dataclasses + mapping functions).

Use this style when:

- error handling logic matters (different UI/API response by error type)
- you want robust refactoring support
- a simple `str` failure is no longer enough

---

## Why dedicated PBT helps

Regular unit tests usually check a few representative strings (like `""` or `"Alice"`).
They can miss whitespace-only edge cases (`"   "`, `"\t\n"`, mixed whitespace).

In this step, a dedicated PBT class exercises that input space and verifies whitespace-only
names are rejected with `NameBlank`, while `""` remains a distinct `NameEmpty` case.

---

## Rule of thumb

Start with `Result[T, str]` for teaching and quick prototypes.
Move to `Result[T, ErrorADT]` when behavior depends on *which* failure happened.
