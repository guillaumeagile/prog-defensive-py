# Defensive Programming from the Trenches
## Live Coding Session — Facilitator Guide

> **Format**: ~50 min · 6 modules · Python examples · Language-agnostic principles  
> **Audience**: Developers  
> **Goal**: Walk away writing defensive code by reflex, not deliberation

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

**✅ Better — validate at the boundary**
```python
from pydantic import BaseModel, Field, validator

class UserInput(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    age:  int  = Field(..., ge=0, le=150)

    @validator("name")
    def no_empty_name(cls, v):
        if not v.strip():
            raise ValueError("name cannot be blank")
        return v.strip()

def create_user(data: dict):
    user = UserInput(**data)   # raises ValidationError early, not later
    db.insert(name=user.name, age=user.age)
```

**Demo moment**: call `create_user({"name": "", "age": -5})` — show the error is clear and early.

### Key points to say out loud
- Whitelist what's valid, don't blacklist what's bad
- Type hints document intent; pydantic/dataclasses *enforce* it at runtime
- Falsehoods programmers believe: names with spaces, ages as strings, "valid" email formats

### ⚔ War story slot
> *Your story here — e.g. a None slipping through unvalidated input that corrupted a record three hops later*

### Exercise (1 min)
> Add a `email` field to `UserInput` that rejects addresses without an `@` symbol.

---

## Module 02 — Fail fast, fail loud `~8 min`

> *"If a failure is expected, encode it in the type. If a state is impossible, make it unconstructable."*

### Concept (2 min)
Silent failures are the most expensive bugs. Returning `None` and continuing with invalid state delays the explosion — and corrupts data along the way.

In this course, **fail loud** means:

1. Expected failures are explicit values (`Result`), not hidden control flow.
2. Illegal states are unrepresentable (functions only accept already-valid domain types).

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

### Illegal states unrepresentable — quick pattern
```python
@dataclass(frozen=True)
class DraftOrder:
    order_id: str


@dataclass(frozen=True)
class ConfirmedOrder:
    order_id: str


def confirm(order: DraftOrder) -> Result[ConfirmedOrder, str]:
    ...

# No "is_confirmed: bool" flags, no nullable half-state.
# You cannot call shipped(order) with a DraftOrder by mistake.
```

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

> *"What must always be true? Write it down. Then enforce it."*

### Concept (2 min)
An **invariant** is a condition that must hold throughout an object's lifetime. A **precondition** is what must be true before a function runs. Write them down — they become free regression tests.

### Live code (5 min)

**Guard clauses over nested conditionals**
```python
# ❌ Arrow anti-pattern
def process(order):
    if order:
        if order.items:
            if order.user:
                if order.user.is_active:
                    # actual logic buried here
                    pass

# ✅ Guard clauses — fail early, happy path is flat
def process(order):
    if not order:
        raise ValueError("order is required")
    if not order.items:
        raise ValueError("order has no items")
    if not order.user:
        raise ValueError("order has no user")
    if not order.user.is_active:
        raise ValueError(f"user {order.user.id} is inactive")

    # actual logic here — flat and readable
```

**Immutability as defence**
```python
from dataclasses import dataclass

# ❌ Mutable — anyone can mutate shared config
@dataclass
class Config:
    db_url: str
    max_retries: int

# ✅ Frozen — immutable after construction
@dataclass(frozen=True)
class Config:
    db_url: str
    max_retries: int
```

**Class invariant pattern**
```python
@dataclass
class BankAccount:
    _balance: float = 0.0

    def deposit(self, amount: float):
        assert amount > 0, "deposit amount must be positive"
        self._balance += amount
        assert self._balance >= 0, "invariant: balance cannot be negative"

    def withdraw(self, amount: float):
        if amount > self._balance:
            raise ValueError("insufficient funds")
        self._balance -= amount
        assert self._balance >= 0, "invariant: balance cannot be negative"
```

### Exercise (1 min)
> Add a precondition to this function:
> ```python
> def compute_discount(price: float, pct: float) -> float:
>     return price * (1 - pct / 100)
> ```

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

# ✅ Ask forgiveness, not permission
try:
    with open(path) as f:
        data = f.read()
except FileNotFoundError:
    data = None
```

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
  [ ] Custom exceptions with context, not generic RuntimeError

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

### Closing 1-liner to leave on screen
> *"Defensive code isn't pessimism. It's respect for the system's actual operating conditions."*

---

## Appendix — Further reading

- *A Philosophy of Software Design* — John Ousterhout (Chapter 10: Define Errors Out Of Existence)
- *Designing Distributed Systems* — Brendan Burns (idempotency, circuit breakers)
- Python `tenacity` library — production-grade retry decorator
- Python `pydantic` v2 docs — validation at the boundary
- Falsehoods Programmers Believe About Names — kalzumeus.com

---

*Guide version 1.0 — expand war stories before the session*
