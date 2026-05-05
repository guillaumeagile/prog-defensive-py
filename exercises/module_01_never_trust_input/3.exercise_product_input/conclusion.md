# Module 01 — Conclusion: ProductInput Exercise

## Where this fits in Module 01

- **Lesson timeline:** Exercise after Part 3
- **Approach used here:** Approach B (Pydantic + Result)
- **Purpose:** Apply the same boundary contract to a richer input model

---

## What this exercise adds

`UserInput` was a warm-up: three fields, straightforward constraints.
`ProductInput` introduces real-world complications that appear constantly at system boundaries:

| Challenge | Field | What happens |
|---|---|---|
| Type coercion | `price` | arrives as `"29.99"` (string from JSON), must become `float` |
| Whitelist validation | `category` | only 4 values allowed, case-insensitive input |
| Absent-vs-blank | `description` | `"  "` and `None` are both "not provided" — stored as `None` |
| Non-negative constraint | `stock` | `-3` is a plausible accident, must be rejected |

---

## Key patterns introduced

### Coercion at the boundary

```python
@field_validator("price", mode="before")
@classmethod
def coerce_price(cls, v: object) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        raise ValueError(f"price must be a number, got {v!r}")
```

`mode="before"` runs the validator on the raw input, before Pydantic attempts its own type
conversion. This is where you handle the gap between "what the outside world sends"
and "what your domain expects."

### Whitelist over blacklist

```python
VALID_CATEGORIES = {"electronics", "clothing", "food", "other"}

@field_validator("category")
@classmethod
def normalise_category(cls, v: str) -> str:
    lower = v.strip().lower()
    if lower not in VALID_CATEGORIES:
        raise ValueError(f"category must be one of {VALID_CATEGORIES}, got {v!r}")
    return lower
```

Define what is valid. Reject everything else. Never enumerate what is invalid —
you will always miss a case (`"ADMIN"`, `"Admin"`, `" admin"`...).

### Blank strings are absent values

```python
@field_validator("description")
@classmethod
def blank_to_none(cls, v: str | None) -> str | None:
    if v is None:
        return None
    stripped = v.strip()
    return stripped if stripped else None
```

`""` and `"   "` are not descriptions. They are the absence of a description.
Normalise at the boundary so domain logic never has to ask `if description and description.strip()`.

---

## The boundary contract, fully stated

After `parse_product_input(...)` returns a `Success`, the caller holds a `ProductInput` with
these guarantees — no further checking needed anywhere in the codebase:

- `name` is non-blank, stripped, ≤ 200 chars
- `price` is a positive float
- `stock` is a non-negative integer
- `category` is one of `{"electronics", "clothing", "food", "other"}`, lowercase
- `description` is either a non-blank stripped string or `None`

This is **parse, don't validate** in action: the type itself is the proof.
Once you have a `ProductInput`, you trust it completely.

---

## What comes next

Module 02 goes deeper into what happens when failures need to compose — chaining multiple
fallible operations without nesting `if isinstance(result, Failure)` checks everywhere.
That is Railway-Oriented Programming, and it builds directly on the `Result` type introduced here.
