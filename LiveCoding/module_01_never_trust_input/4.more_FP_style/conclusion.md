# Module 01 — Conclusion: More FP Style

## Where this fits in Module 01

- **Live step:** `4.more_FP_style/` (deepening the FP approach)
- **Approach covered here:** Approach E
- **Builds on:** `3.result_stronger_types/` (Approach D — `Result[T, ErrorADT]`)
- **Goal:** go further by parsing each field into its own value object (`Name`, `Age`, `Email`) and composing the steps with `flow` + `bind`

---

## What changed vs. Approach D

Approach D wrapped the full validated model in a `Result` with typed errors.
Approach E breaks validation into one function per field, each returning a `Result`, then composes them.

```python
# Approach D — one big parse function
parse_user_input(...) -> Result[ParsedUserInput, ParseUserError]

# Approach E — three small parsers composed with flow/bind
parse_name(raw_name)   -> Result[Name, ParseUserError]
parse_age(raw_age)     -> Result[Age, ParseUserError]
parse_email(raw_email) -> Result[Email, ParseUserError]

parse_user_input(name, age, email) -> Result[ParsedUserInput, ParseUserError]:
    return flow(
        parse_name(name),
        bind(_bind_parse_age(age)),
        bind(_bind_parse_email(email)),
    )
```

Each domain concept is a distinct type. `ParsedUserInput` holds `Name`, `Age`, `Email` — not raw strings.
This means a function that accepts a `Name` can never accidentally receive a raw unvalidated string.

---

## Why value objects matter

```python
# Without value objects — silent bug possible
def greet(name: str) -> str:
    return f"Hello, {name}"

greet(user.email)   # compiles and runs — wrong data, no error

# With value objects — caught by the type checker
def greet(name: Name) -> str:
    return f"Hello, {name.value}"

greet(user.email)   # TypeError at the call site
```

The type system enforces what the data *means*, not just what it *is*.

---

## The composition pattern

`flow` and `bind` (from the `returns` library) thread a `Result` through a pipeline.
If any step returns a `Failure`, the rest of the pipeline is short-circuited — no exceptions, no nested `if` checks.

```python
parse_user_input("Alice", 30, "alice@example.com")
# → Success(ParsedUserInput(Name("Alice"), Age(30), Email("alice@example.com")))

parse_user_input("", 30, "alice@example.com")
# → Failure(NameEmpty())   — pipeline stopped at step 1
```

---

## Comparing all five approaches

| | A (exceptions) | B (Result + str) | C (dataclass + Result) | D (Result + ADT) | E (value objects + flow) |
|---|---|---|---|---|---|
| Error path in signature | No | Yes | Yes | Yes | Yes |
| Error type | implicit | `str` | `str` | typed ADT | typed ADT |
| Domain types | raw strings | raw strings | raw strings | raw strings | value objects |
| Composable pipeline | No | Partially | Partially | Partially | Yes (`flow`/`bind`) |
| Type-safe field usage | No | No | No | No | Yes |
| Boilerplate | Low | Low | Medium | Medium | Higher |

---

## When to use this style

Use Approach E when:

- the same domain concept (name, email, age) appears in many functions — value objects prevent mixing them up
- you want to build larger pipelines from smaller validated parts
- the team is comfortable with functional composition (`flow`, `bind`, `map`)

For most CRUD services Approach D is a good balance.
Approach E shines in domain-rich models where field identity matters.

---

## Rule of thumb

> Parse raw input at the boundary once.
> Each field gets its own type; invalid strings never enter the domain.
> Compose small trusted parsers rather than writing one large validator.
>
> `parse_name`, `parse_age`, `parse_email` each do one thing.
> `parse_user_input` just wires them together.
> No layer needs `try/except`.
