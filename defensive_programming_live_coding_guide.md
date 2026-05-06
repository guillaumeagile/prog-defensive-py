# Defensive Programming from the Trenches
## Live Coding Session — Facilitator Guide

> **Format**: ~50 min · 6 modules · Python examples · Language-agnostic principles  
> **Audience**: Developers  
> **Goal**: Walk away writing defensive code by reflex, not deliberation

---

## A tale of two worldviews

This guide deliberately shows both the **Pythonic idiom** and the **FP-consistent idiom** side by side, because you will encounter both in the wild and you need to be able to reason about the trade-offs.

| | Pythonic Python | FP-consistent Python |
|---|---|---|
| Expected failure | `raise ValueError` / return `None` | `return Failure(...)` |
| Constructor validation | `__post_init__` raises | smart constructor returns `Result` |
| Control flow | `try / except` at each call site | `bind` chains, one handler at the top |
| Signature honesty | `def f(x) -> User` (lies — can raise) | `def f(x) -> Result[User, E]` (whole truth) |

Neither is universally right. The Pythonic way is shorter and familiar to every Python dev. The FP way is more honest, more composable, and scales better when error paths get complex. Knowing *why* they diverge is what this guide is really teaching.

The rule used throughout:
- **Domain / expected failures** (user error, missing record, age < 18) → `Result`
- **Programming errors / true invariant violations** (corrupted DB row, unreachable branch) → `raise`

---

## Before you start

- Open a Python REPL or notebook alongside this guide
- Have a "bad" snippet ready for the Module 06 audit exercise (see end of this doc)
- Each module has a **❌ Bad code** → **✅ Better code** pair — type them live, don't paste
- War stories marked **⚔** are your own to fill in; placeholders are provided

---

## Module 01 — Never trust input `~8 min`

> *"The world is full of liars. Your function's callers are no exception."*

### Concept (2 min)
Validation belongs at the **boundary** — the moment data enters your system (API endpoint, CLI arg, file read, queue message). Not three layers deep when something breaks silently.

### Live code (5 min)

**❌ Bad — trusting the caller**
```python
def create_user(data: dict):
    name = data["name"]
    age  = data["age"]
    db.insert(name=name, age=age)
```

**✅ Pythonic — validate at the boundary with Pydantic**
```python
from pydantic import BaseModel, Field, field_validator

class UserInput(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    age:  int  = Field(..., ge=0, le=150)

    @field_validator("name")
    @classmethod
    def no_empty_name(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("name cannot be blank")
        return v.strip()

def create_user(data: dict) -> None:
    user = UserInput(**data)   # raises ValidationError early, not later
    db.insert(name=user.name, age=user.age)
```

**Demo moment**: call `create_user({"name": "", "age": -5})` — show the error is clear and early.

---

> ### FP perspective: why `raise` in a constructor is a lie
>
> **How `@field_validator` actually works**: when you call `UserInput(**data)`, Pydantic
> generates an `__init__` that runs all validators in sequence. Your `@field_validator("name")`
> is injected into that `__init__`. The `raise ValueError(...)` inside the validator is caught
> by Pydantic and re-raised as a `ValidationError` — so from outside, the constructor either
> returns a `UserInput` or blows up.
>
> This connects to a broader principle — *constructors should be logic-free*:
>
> | Tradition | How they say it |
> |---|---|
> | Misko Hevery (Google / Angular) | "Constructors do no work" |
> | FP / type theory | "Constructors are total; parsing is separate" |
> | Parse don't validate (Alexis King) | "Convert unstructured data into structured data exactly once, at the boundary" |
> | DDD | "Use factory methods, not constructors, for domain object creation" |
>
> They all say the same thing: **construction and validation are two different operations**.
> Conflating them into `__init__` creates a partial function — one defined only on valid inputs,
> yet whose signature claims to work on all inputs.
>
> The FP person looking at `UserInput(**data)` asks: *"What is the return type of this call?"*
> The answer is `UserInput` — but that is only true if the input is valid.
> If the input is invalid it raises. So the real type is `UserInput | raises ValidationError`.
> Python's type system cannot express `| raises`, which means the signature **lies by omission**.
>
> The FP-consistent fix is a **smart constructor** — a plain function, not a class constructor,
> that makes the failure explicit in its return type:
>
> ```python
> from pydantic import BaseModel, Field, ValidationError, field_validator
> from returns.result import Result, Success, Failure
>
>
> class UserInput(BaseModel):
>     name: str = Field(..., min_length=1, max_length=100)
>     age:  int  = Field(..., ge=0, le=150)
>
>     @field_validator("name")
>     @classmethod
>     def no_empty_name(cls, v: str) -> str:
>         if not v.strip():
>             raise ValueError("name cannot be blank")
>         return v.strip()
>
>
> def parse_user(data: dict) -> Result[UserInput, str]:
>     """Smart constructor: the only way to get a UserInput."""
>     try:
>         return Success(UserInput(**data))
>     except ValidationError as e:
>         first = e.errors()[0]
>         return Failure(f"{first['loc'][0]}: {first['msg']}")
>
>
> def create_user(data: dict) -> Result[None, str]:
>     return parse_user(data).map(
>         lambda user: db.insert(name=user.name, age=user.age)
>     )
> ```
>
> Now the signature of `parse_user` tells the whole truth: it either succeeds with a `UserInput`
> or fails with a string message. No caller needs a `try/except`.
>
> **Which to choose?**
> The raising version is fine when `create_user` is a web endpoint and your framework already
> catches `ValidationError` and turns it into a 422. The `Result` version is better when you
> compose multiple parsing steps or when the failure needs to propagate through several layers
> without sprinkling `try/except` everywhere.

---

### Key points to say out loud
- Whitelist what's valid, don't blacklist what's bad
- Type hints document intent; Pydantic *enforces* it at runtime
- Falsehoods programmers believe: names with spaces, ages as strings, "valid" email formats
- If your framework handles `ValidationError` for you, the Pythonic version is perfectly fine — the smart constructor shines when you own the error path

### ⚔ War story slot
> *Your story here — e.g. a None slipping through unvalidated input that corrupted a record three hops later*

### Exercise (1 min)
> Add an `email` field to `UserInput` that rejects addresses without an `@` symbol.
> Then write a `parse_user` smart constructor that returns `Result[UserInput, str]`.

---

## Module 02 — Fail fast, fail loud `~8 min`

> *"If a failure is expected, encode it in the type."*

### Concept (2 min)
Silent failures are the most expensive bugs. Returning `None` and continuing with invalid state delays the explosion — and corrupts data along the way.

In this course, **fail loud** means:

1. Expected failures are explicit values (`Result`), not hidden control flow.
2. The error path is visible in signatures and impossible to ignore by accident.

### Live code (5 min)

**❌ Bad — silent failure**
```python
def get_user(user_id: int):
    result = db.query(user_id)
    if not result:
        return None          # caller might not check this

def process_order(user_id: int):
    user = get_user(user_id)
    send_email(user.email)   # AttributeError: NoneType has no attribute 'email'
```

**✅ Better — explicit failures + unrepresentable invalid state**
```python
from dataclasses import dataclass

from returns.result import Failure, Result, Success


@dataclass(frozen=True)
class ActiveUser:
    user_id: int
    email: str


@dataclass(frozen=True)
class UserNotFound:
    user_id: int


@dataclass(frozen=True)
class UserInactive:
    user_id: int


GetUserError = UserNotFound | UserInactive


def get_active_user(user_id: int) -> Result[ActiveUser, GetUserError]:
    row = db.query(user_id)
    if row is None:
        return Failure(UserNotFound(user_id))
    if not row.is_active:
        return Failure(UserInactive(user_id))
    return Success(ActiveUser(user_id=row.id, email=row.email))


def process_order_for_active_user(user: ActiveUser) -> None:
    send_email(user.email)


def process_order(user_id: int) -> Result[None, GetUserError]:
    return get_active_user(user_id).map(process_order_for_active_user)
```

**Demo moment**: call `process_order(999)` and `process_order(inactive_id)`.
Show `Failure(UserNotFound(...))` / `Failure(UserInactive(...))` — explicit, typed, and impossible to ignore.

---

> ### FP perspective: why the error ADT matters more than the Result wrapper
>
> The Pythonic alternative would be a custom exception hierarchy:
> ```python
> class UserNotFoundError(Exception): ...
> class UserInactiveError(Exception): ...
> ```
> Both approaches name the failure cases. The difference is **where the compiler helps you**.
>
> With exceptions, a caller that forgets to handle `UserInactiveError` compiles and runs fine —
> the error silently propagates up the stack until something catches `Exception`.
> With `Result[ActiveUser, UserNotFound | UserInactive]`, a type checker (pyright/mypy) forces
> the caller to inspect the result before using the value. You cannot accidentally treat a
> `Failure(UserInactive(...))` as an `ActiveUser`.
>
> The FP term is **making illegal states unrepresentable at the call site**, not just at
> the construction site.

---

### ROP fail-fast (Python + Pydantic)
```python
from pydantic import BaseModel, ValidationError
from returns.pipeline import flow
from returns.pointfree import bind
from returns.result import Failure, Result, Success


class SignupSchema(BaseModel):
    email: str
    age: int


def parse_signup(raw: dict[str, object]) -> Result[SignupSchema, str]:
    try:
        parsed = SignupSchema.model_validate(raw)  # boundary parsing
        return Success(parsed)
    except ValidationError as error:
        first = error.errors()[0]
        field = str(first["loc"][0])
        msg = str(first["msg"])
        return Failure(f"{field}: {msg}")


def ensure_adult(data: SignupSchema) -> Result[SignupSchema, str]:
    if data.age < 18:
        return Failure("adult only")
    return Success(data)


def create_account(data: SignupSchema) -> Result[str, str]:
    return Success(f"created:{data.email}")


def signup(raw: dict[str, object]) -> Result[str, str]:
    return flow(
        parse_signup(raw),
        bind(ensure_adult),
        bind(create_account),
    )
```

First `Failure` wins: later steps are skipped automatically, so the pipeline fails fast without hidden exceptions.

### Loud failure rule — quick rule
```python
# Expected domain failures: return Result
def reserve_stock(sku: str, qty: int) -> Result[None, OutOfStock]:
    ...

# Unexpected technical failures (bugs/corruption): raise
raise RuntimeError("unreachable branch hit")
```

### Bridge to Module 03
In Module 03, we turn invariants into explicit contracts and then push them further with
**illegal states unrepresentable** (type-level contracts).

### ⚔ War story slot
> *Your story here — e.g. a None that propagated silently into a financial calculation*

### Exercise (1 min)
> Refactor this to return `Result[Config, ConfigError]` (no `None`, no exception for expected missing file):
> ```python
> def parse_config(path: str):
>     if not os.path.exists(path):
>         return None
> ```

---

## Module 03 — Contracts & invariants `~8 min`

> *"A contract says who guarantees what. Invariants are one part of that contract."*

### Aim (1 min)
By the end of this module, the audience should be able to distinguish and enforce:

- Function contracts (**preconditions + postconditions**)
- Class invariants (**must always hold after construction and after each mutation**)
- Type-level contracts (**illegal states unrepresentable**)

### Concept (2 min)
A **contract** has three parts:

1. **Preconditions** — what the caller must provide.
2. **Postconditions** — what the function promises to return/guarantee.
3. **Invariants** — what must always stay true for valid objects.

`Illegal states unrepresentable` is the strongest contract form: invalid combinations cannot be constructed.

Rule of thumb for teaching and design:

1. If a rule is about **one value**, encode it as a **Value Object**.
2. If a rule is about **relationships between fields**, enforce a **class invariant**.
3. If a rule is about **lifecycle/states**, encode it in **types/state variants**.

### Live code (5 min)

**Function contract = guard clauses + explicit postcondition**
```python
from returns.result import Failure, Result, Success


def compute_discount(price: float, pct: float) -> Result[float, str]:
    if price < 0:
        return Failure("price must be >= 0")
    if not (0 <= pct <= 100):
        return Failure("pct must be between 0 and 100")
    return Success(price * (1 - pct / 100))
```

- Preconditions: `price >= 0`, `0 <= pct <= 100`
- Postcondition: caller always gets a `Result` (no hidden `None`)

---

**Value Object — two styles**

The Pythonic style uses `__post_init__` to raise:

```python
# Pythonic: raises on bad input
@dataclass(frozen=True)
class PositiveAmount:
    value: float

    def __post_init__(self) -> None:
        if self.value <= 0:
            raise ValueError("amount must be positive")
```

> **FP perspective — why `__post_init__` raising is a partial function**
>
> `PositiveAmount(value=-1)` looks like a normal constructor call.
> Its apparent return type is `PositiveAmount`. But for negative input it raises instead.
> That makes it a **partial function**: defined only on a subset of its input domain,
> yet the signature claims to be total.
>
> A total constructor either succeeds or returns an explicit failure — never raises for
> domain validation. The FP-consistent version uses a smart constructor:
>
> ```python
> # FP-consistent: smart constructor, total function
> @dataclass(frozen=True)
> class PositiveAmount:
>     value: float  # private by convention — only create via PositiveAmount.create()
>
>     @classmethod
>     def create(cls, value: float) -> Result["PositiveAmount", str]:
>         if value <= 0:
>             return Failure(f"amount must be positive, got {value}")
>         return Success(cls(value=value))
> ```
>
> Now every caller is forced by the type system to handle the failure case before touching
> the `PositiveAmount`. No `try/except` needed anywhere — the failure is just a `Failure`.
>
> **Which to choose?**
> If `PositiveAmount` is only ever constructed from already-validated data (e.g., from your DB
> schema), the raising version is fine — it guards against programming errors, not user errors.
> Use the smart constructor when the value comes from user input or external data.

---

**Class invariant pattern (for cross-field / state rules)**

```python
# Pythonic: mutable object, invariant checked after each transition
@dataclass
class BankAccount:
    _balance: float = 0.0

    def __post_init__(self) -> None:
        self._ensure_invariant()

    def _ensure_invariant(self) -> None:
        if self._balance < 0:
            raise ValueError("invariant: balance cannot be negative")

    def deposit(self, amount: PositiveAmount) -> None:
        self._balance += amount.value
        self._ensure_invariant()

    def withdraw(self, amount: PositiveAmount) -> None:
        if amount.value > self._balance:
            raise ValueError("insufficient funds")
        self._balance -= amount.value
        self._ensure_invariant()
```

> **FP perspective — make the failure explicit at the call site**
>
> `withdraw` raises for an expected domain event (insufficient funds).
> The FP-consistent version returns `Result` so the caller sees the failure in the type:
>
> ```python
> @dataclass(frozen=True)
> class InsufficientFunds:
>     requested: float
>     available: float
>
>
> @dataclass
> class BankAccount:
>     _balance: float = 0.0
>
>     def deposit(self, amount: PositiveAmount) -> None:
>         self._balance += amount.value  # always succeeds given PositiveAmount
>
>     def withdraw(self, amount: PositiveAmount) -> Result[None, InsufficientFunds]:
>         if amount.value > self._balance:
>             return Failure(InsufficientFunds(
>                 requested=amount.value, available=self._balance
>             ))
>         self._balance -= amount.value
>         return Success(None)
> ```
>
> The invariant `_balance >= 0` now holds **by construction** — `withdraw` simply refuses
> to go below zero and tells the caller why, rather than raising after the fact.
> No external `_ensure_invariant()` call needed because the mutation only happens on the
> `Success` branch.

---

Pattern to say out loud:
1. Check invariant after construction.
2. Push single-value preconditions into Value Objects (`PositiveAmount`).
3. Re-check invariant after each state transition.
4. For **domain failures** (expected, recoverable), prefer `Result` over `raise`.
5. Reserve `raise` for **programming errors** — conditions that should never happen if the code is correct.

**Illegal states unrepresentable (type-level contract)**
```python
from dataclasses import dataclass


@dataclass(frozen=True)
class DraftOrder:
    order_id: str


@dataclass(frozen=True)
class ConfirmedOrder:
    order_id: str


def confirm(order: DraftOrder) -> Result[ConfirmedOrder, str]:
    ...

# No "is_confirmed: bool" flags, no nullable half-state.
# `ship(order: ConfirmedOrder)` cannot be called with DraftOrder.
```

**Immutability as contract amplifier**
```python
@dataclass(frozen=True)
class Config:
    db_url: str
    max_retries: int
```

Once created, `Config` cannot drift into an invalid state through accidental mutation.

### Exercise (1 min)
> Pick one function in your codebase and write down:
> 1) one precondition,
> 2) one postcondition,
> 3) one invariant.
>
> Then enforce each one explicitly in code — and decide for each: `raise` or `Result`?

---

## Module 04 — Handling external dependencies `~10 min`

> *"Everything outside your process is hostile: APIs, DBs, the filesystem, time."*

### Concept (2 min)
External calls will: time out, return unexpected shapes, return 200 with an error inside, succeed on the first call and fail on retry, and run twice due to your retry logic. Design for all of this.

### Live code (6 min)

**Always timeout**
```python
import httpx

# ❌ No timeout — hangs forever
response = httpx.get("https://api.example.com/data")

# ✅ Explicit timeout on connect AND read
response = httpx.get(
    "https://api.example.com/data",
    timeout=httpx.Timeout(connect=2.0, read=5.0)
)
```

**Retry with exponential backoff + jitter**
```python
import time, random

def with_retry(fn, max_attempts=3, base_delay=0.5):
    for attempt in range(max_attempts):
        try:
            return fn()
        except (httpx.TimeoutException, httpx.NetworkError) as e:
            if attempt == max_attempts - 1:
                raise
            delay = base_delay * (2 ** attempt) + random.uniform(0, 0.3)
            time.sleep(delay)
```

**Circuit breaker (minimal, 20 lines)**
```python
from datetime import datetime, timedelta

class CircuitBreaker:
    def __init__(self, threshold=5, timeout=30):
        self.failures   = 0
        self.threshold  = threshold
        self.timeout    = timedelta(seconds=timeout)
        self.opened_at  = None

    def call(self, fn):
        if self.opened_at:
            if datetime.now() - self.opened_at < self.timeout:
                raise RuntimeError("circuit open — service unavailable")
            self.opened_at = None   # half-open: allow one probe

        try:
            result = fn()
            self.failures = 0       # success — reset
            return result
        except Exception:
            self.failures += 1
            if self.failures >= self.threshold:
                self.opened_at = datetime.now()
            raise
```

**Never trust the shape — validate the response too**
```python
# ❌ Assumes API behaves
data = response.json()
user_id = data["user"]["id"]

# ✅ Defensive parsing
data = response.json()
user = data.get("user") or {}
user_id = user.get("id")
if not user_id:
    raise ExternalServiceError(f"unexpected response shape: {data}")
```

### ⚔ War story slot
> *Your story here — e.g. the third-party API that returned HTTP 200 with `{"status": "error"}` in the body*

### Exercise (1 min)
> Add a timeout and a single retry to this call:
> ```python
> def fetch_exchange_rate(currency: str) -> float:
>     return httpx.get(f"https://api.rates.io/{currency}").json()["rate"]
> ```

---

## Module 05 — Concurrency traps `~8 min`

> *"Concurrent code doesn't crash in tests. It crashes in production, at 2am."*

### Concept (2 min)
Python's GIL protects against some race conditions in CPython — but not all, not in asyncio, and not across processes. The safest bet: design operations to be **idempotent** from the start.

### Live code (4 min)

**TOCTOU — time-of-check to time-of-use**
```python
import os

# ❌ Race: file could be deleted between check and open
if os.path.exists(path):
    with open(path) as f:    # FileNotFoundError possible here
        data = f.read()
```

**Pythonic fix — ask forgiveness, not permission**
```python
# Pythonic: exception used for control flow
try:
    with open(path) as f:
        data = f.read()
except FileNotFoundError:
    data = None
```

> **FP perspective — the Pythonic fix still hides the failure**
>
> The `try/except` solves the race but introduces a new problem: `data` is now
> `str | None`, and a caller that forgets to check for `None` crashes later with an
> `AttributeError` — the exact silent-failure pattern Module 02 warns against.
>
> The FP-consistent fix keeps the "ask forgiveness" idea but makes the absence explicit
> in the return type:
>
> ```python
> from returns.result import Result, Success, Failure
>
>
> def read_file(path: str) -> Result[str, FileNotFoundError]:
>     try:
>         with open(path) as f:
>             return Success(f.read())
>     except FileNotFoundError as e:
>         return Failure(e)
> ```
>
> Now the caller *cannot* use the content without first handling the missing-file case.
> The `try/except` is still there — Python still needs it to detect the race —
> but the failure is surfaced in the type rather than silently replaced with `None`.
>
> **Which to choose?**
> If `data = None` flows into a single `if data:` branch right below, the Pythonic version
> is fine — it's readable and the scope is tiny. Use `Result` when the content will travel
> through multiple layers before being consumed.

---

**asyncio: the silent fire-and-forget trap**
```python
import asyncio

# ❌ Task is scheduled but exceptions are silently swallowed
asyncio.create_task(send_email(user))

# ✅ Keep a reference, handle exceptions
async def safe_task(coro):
    try:
        await coro
    except Exception as e:
        logger.error("background task failed", exc_info=e)

task = asyncio.create_task(safe_task(send_email(user)))
```

**Idempotency key pattern**
```python
def process_payment(order_id: str, amount: float, idempotency_key: str):
    if db.payment_exists(idempotency_key):
        return db.get_payment(idempotency_key)   # safe to retry
    
    result = payment_gateway.charge(amount)
    db.save_payment(idempotency_key, result)
    return result
```

### ⚔ War story slot
> *Your story here — e.g. a double-charge caused by a network retry without idempotency keys*

### Quick mental model to share
> *"If this function ran twice simultaneously with the same input, what breaks?"*  
> If the answer is "nothing" — it's idempotent. Aim for that everywhere it matters.

### Quiz (1 min)
> What's wrong with this asyncio code?
> ```python
> async def handler(request):
>     asyncio.create_task(log_request(request))
>     return Response(200)
> ```

---

## Module 06 — Review & reflex `~8 min`

> *"The goal: defensive patterns that feel automatic, not deliberate."*

### Code review checklist (print this / share as a gist)

```
INPUTS
  [ ] All external inputs validated at the boundary
  [ ] No implicit trust of dict keys without .get() or a schema
  [ ] File paths, env vars, and config values checked before use

FAILURES
  [ ] No bare `except:` or `except Exception: pass`
  [ ] Functions return meaningful types — no None-as-error
  [ ] Expected domain failures use Result, not raise
  [ ] Custom exceptions reserved for programming errors / infrastructure failures

EXTERNAL CALLS
  [ ] Every HTTP/DB call has a timeout
  [ ] Retries are bounded and use backoff
  [ ] Response shape is validated, not assumed

CONCURRENCY
  [ ] Shared mutable state accessed only under a lock
  [ ] asyncio tasks are awaited or tracked
  [ ] State-changing operations are idempotent where possible

INVARIANTS
  [ ] Preconditions documented and enforced
  [ ] Guard clauses at the top, happy path flat
  [ ] Mutable shared objects replaced with frozen ones where feasible
  [ ] Smart constructors used when invalid construction is a domain failure
```

### Live audit exercise (5 min)

**Paste this snippet — ask the audience to find the bugs**
```python
def transfer_funds(from_id, to_id, amount):
    sender   = db.get_user(from_id)
    receiver = db.get_user(to_id)

    if sender.balance >= amount:
        sender.balance   -= amount
        receiver.balance += amount
        db.save(sender)
        db.save(receiver)
        notify_service.send(f"Transfer of {amount} complete")

    return True
```

**Bugs to surface (let the audience find them first)**
- `db.get_user()` might return `None` — no guard
- No validation on `amount` (negative? zero? float precision?)
- Race condition: balance check and debit are not atomic
- `db.save(sender)` could succeed and `db.save(receiver)` could fail — no transaction
- `notify_service.send()` is a fire-and-forget external call with no timeout/retry
- Always returns `True` — even if nothing happened

**FP bonus question**: what would the signature of a correct `transfer_funds` look like?
```python
@dataclass(frozen=True)
class TransferFailed:
    reason: str

def transfer_funds(
    from_id: int,
    to_id: int,
    amount: PositiveAmount,
) -> Result[None, TransferFailed]:
    ...
```
The `PositiveAmount` type eliminates the negative/zero amount bug before the function body even runs.
The `Result` return makes it impossible for callers to ignore a failed transfer.

### Closing 1-liner to leave on screen
> *"Defensive code isn't pessimism. It's respect for the system's actual operating conditions."*

---

## Appendix — Further reading

- *A Philosophy of Software Design* — John Ousterhout (Chapter 10: Define Errors Out Of Existence)
- *Designing Distributed Systems* — Brendan Burns (idempotency, circuit breakers)
- *Domain Modelling Made Functional* — Scott Wlaschin (the canonical reference for illegal states unrepresentable, smart constructors, and Result-based pipelines)
- Python `returns` library — `Result`, `bind`, `flow` for Python
- Python `tenacity` library — production-grade retry decorator
- Python `pydantic` v2 docs — validation at the boundary
- Falsehoods Programmers Believe About Names — kalzumeus.com

---

*Guide version 1.1 — expand war stories before the session*
