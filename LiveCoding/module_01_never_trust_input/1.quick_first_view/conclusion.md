# Module 01 — Conclusion: Two Approaches to Boundary Parsing

We implemented the same boundary parser twice. Here is why one is cleaner than the other.

---

## Where this fits in Module 01

- **Live step:** `1.quick_first_view/` (comparison pass)
- **Approaches covered here:** Approach A and Approach B
- **Concepts reinforced:** parse, don't validate; explicit failure contracts
- **Next step:** `../2.dataclass_post_init/` introduces Approach C
- **Larger exception-chain demo:** `exceptions/processing_chain_with_exceptions.py`
- **Matching Result-chain demo:** `results/processing_chain_with_results.py`

---

## Approach A — Exceptions (`exceptions/solution_with_exceptions.py`)

```python
user = UserInput(name="", age=30, email="alice@example.com")
# raises ValidationError — but nothing in the signature tells you that
```

The caller has no way to know this can fail without reading the implementation or the docs.
They must wrap every call in `try/except ValidationError` — or forget to, and get a runtime crash.

**The error path is invisible.**

---

## Approach B — Result (`results/solution_results.py`)

```python
result = parse_user_input(name="", age=30, email="alice@example.com")
# returns Result[UserInput, str] — the signature tells the whole story
match result:
    case Success(user): ...
    case Failure(msg):  ...
```

The return type `Result[UserInput, str]` is a contract: "this operation can produce a value
or an error message." The caller is forced to handle both cases — not by convention, by the type.

**The error path is explicit.**

---

## The clean code argument

| | Approach A | Approach B |
|---|---|---|
| Error path visible in signature | No | Yes |
| Caller can ignore failures | Yes (forget try/except) | No (must unwrap Result) |
| Composable with other fallible ops | No (exception breaks the chain) | Yes (bind chains Results) |
| Tests read like specs | No (`pytest.raises` is noisy) | Yes (`isinstance(result, Failure)`) |
| Surprises in production | Likely | Unlikely |

Clean code is code where **reading the signature is enough** to understand what can happen.
`parse_user_input(...) -> Result[UserInput, str]` tells you everything.
`UserInput(...)` tells you nothing about failure.

---

## The rule going forward

> Parse raw boundary input into trusted typed objects as early as possible.
>
> Exceptions are for **unexpected** failures — things that should never happen in normal operation
> (a bug, a corrupted environment, an unreachable code path).
>
> Expected failures — invalid input, missing records, constraint violations — belong in the
> **return type**. Use `Result[T, str]`. Make the contract visible.

This is the foundation that all subsequent modules build on.
