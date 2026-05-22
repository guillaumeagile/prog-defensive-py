# Module 02 — Fail Fast, Fail Explicitly
## Detailed Lesson Plan · ~9 minutes live · Defensive Programming from the Trenches

> *Be loud. Be clear. But don't be rude. Exceptions are rude — they interrupt everything, bypass the call stack, and leave the caller guessing. Explicit outcomes speak calmly and carry all the information.*

---

## Overview

| | |
|---|---|
| **Duration** | 9 minutes (live) + 5 min exercise if async |
| **Core principle** | Fail fast — but speak in types, not interruptions. Expected failures are return values, not exceptions. |
| **Python focus** | `Result[T, E]` hand-rolled → Railway Oriented Programming → `returns` library |
| **Theory depth** | Medium — name the concepts, show the code, let mypy demonstrate |
| **Audience takeaway** | I can encode failure in the type system — explicit, composable, impossible to ignore |

---

## Learning Objectives

1. Articulate why exceptions are the wrong tool for expected failure paths
2. Build and read a minimal `Result[T, E]` type
3. Chain operations Railway-style — no nested try/except pyramids
4. Know when to reach for the `returns` library vs hand-rolling

---

## Facilitator Timing

```
00:00 — 01:00   Hook: exceptions are rude (60 sec)
01:00 — 02:00   Concept: two levels of explicitness, name them (60 sec)
02:00 — 03:30   The problem: exceptions as flow control (90 sec)
03:30 — 05:30   Live code: hand-roll Result[T, E] (2 min)
05:30 — 07:30   Live code: Railway — bind chain + diagram (2 min)
07:30 — 08:30   Show: returns library + @safe (60 sec)
08:30 — 09:00   Wrap: spectrum bar + direction of travel (30 sec)
```

---

## Part 1 — Hook (60 sec)

**Open with this:**

> "We want to fail fast. Absolutely. Detect problems early, surface them immediately, never let bad state propagate. But *how* we surface them matters."

**Pause. Then:**

> "Exceptions are rude. They don't return a value — they *interrupt*. They bypass your entire call stack, unwind the stack frame, and force every caller upstream to either wrap everything in try/except or silently ignore the problem. And they're *invisible* in the function signature — there is no way to know `get_user()` can fail without reading its source or its docs. That's not explicit. That's a trap."

**The reframe:**

> "Fail fast, yes. But fail *explicitly* — speak in types. An expected failure is a perfectly valid return value. It should be as visible in the signature as the success case. If 'user not found' is a normal outcome of a user lookup, it belongs in the return type, not in an exception."

**Plant the seed:**

> "There's a programming style that makes this concrete — Railway Oriented Programming. We'll get there. Let's build up to it."

### ⚔ War story slot

> *Your story here. Suggested angle: a swallowed exception or bare `except: pass` that converted a real error into a silent wrong branch — not a crash, a wrong decision taken confidently. A charge processed twice. A record updated with stale data. The expensive failures are never the crashes — they're the quiet ones.*

---

## Part 2 — Concept: Two Levels of Explicit (60 sec)

**Say — no code here, just orient the audience:**

> "There are two levels to this idea, and they're complementary."

**Level 1 — Honest signatures:** the function return type tells you it can fail, and exactly what kind of failure. The caller *cannot* ignore it — it's in the type. This is `Result[T, E]`, and it's what we're building today.

**Level 2 — Illegal states unrepresentable:** restructure your types so the wrong state *can't be constructed* at all. Not detected — impossible. That's sum types and sealed class hierarchies. We're covering that in Module 03.

> "Today: Level 1. How to make failure paths as visible as the happy path."

---

## Part 3 — The Problem: Exceptions as Flow Control (90 sec)

> **Facilitator note**: type this live. The point lands when the audience sees how much *hidden knowledge* the caller is carrying.

```python
# ❌ Exceptions for expected outcomes — rude and invisible
def get_user(user_id: int) -> User:
    user = db.find(user_id)
    if not user:
        raise UserNotFoundError(user_id)
        # "User not found" is a perfectly normal outcome.
        # Nothing in the signature warns the caller.
        # The return type says "User" — it lies.

def get_account(user: User) -> Account:
    account = db.get_account(user.id)
    if not account:
        raise AccountNotFoundError(user.id)   # same lie

def get_balance(account: Account) -> float:
    if account.suspended:
        raise AccountSuspendedError()         # same lie

# The caller pays the price for all three lies
def process(user_id: int):
    try:
        user    = get_user(user_id)
        account = get_account(user)
        balance = get_balance(account)
        return balance
    except UserNotFoundError: ...
    except AccountNotFoundError: ...
    except AccountSuspendedError: ...
    # Every except clause = knowledge the type system didn't give you.
    # Knowledge that has to be re-discovered by every caller, forever.
```

**Say:** "Count what the caller had to *know* without the type system telling them — three exception types, their names, when they're raised. That's implicit knowledge spread across the codebase, waiting to be forgotten by the next developer, or by you in six months."

**Then:** "Now let's fix the signatures."

---

## Part 4 — Live Code: Result[T, E] (2 min)

> **Facilitator note**: this is the heart of the module. Type it slowly. The goal is demystification — show that this is 30 lines, not magic.

### The type (60 sec)

```python
from dataclasses import dataclass
from typing import TypeVar, Generic, Callable

T = TypeVar("T")
E = TypeVar("E")
U = TypeVar("U")

@dataclass(frozen=True)
class Ok(Generic[T]):
    value: T

    def map(self, fn: Callable[[T], U]) -> "Ok[U]":
        return Ok(fn(self.value))

    def bind(self, fn: Callable[[T], "Result[U, E]"]) -> "Result[U, E]":
        return fn(self.value)        # success: keep going

    def unwrap(self) -> T:
        return self.value

@dataclass(frozen=True)
class Err(Generic[E]):
    error: E

    def map(self, fn):   return self   # error: pass through, skip fn
    def bind(self, fn):  return self   # error: pass through, skip fn

    def unwrap(self):
        raise RuntimeError(f"unwrap() on Err: {self.error}")

Result = Ok[T] | Err[E]
```

**Say:** "That's it. `Ok` holds a success value. `Err` holds a failure value. Both are plain values — no interruption, no stack unwinding. And notice `bind` on `Err` — it just returns `self`. That's the key. Errors skip everything downstream automatically."

### Honest signatures (60 sec)

```python
@dataclass(frozen=True)
class UserNotFound:
    user_id: int

@dataclass(frozen=True)
class AccountNotFound:
    user_id: int

@dataclass(frozen=True)
class AccountSuspended:
    account_id: str

# The signature is now honest — it tells you everything
def get_user(user_id: int) -> Result[User, UserNotFound]:
    user = db.find(user_id)
    return Ok(user) if user else Err(UserNotFound(user_id))

def get_account(user: User) -> Result[Account, AccountNotFound]:
    account = db.get_account(user.id)
    return Ok(account) if account else Err(AccountNotFound(user.id))

def get_balance(account: Account) -> Result[float, AccountSuspended]:
    if account.suspended:
        return Err(AccountSuspended(account.id))
    return Ok(account.balance)
```

**Say:** "No docs needed. No source-reading. The return type is the documentation. A new developer reads `Result[User, UserNotFound]` and knows immediately: this can succeed with a User, or fail with a UserNotFound. That's explicit."

---

## Part 5 — Live Code: Railway (2 min)

### Without Railway — still verbose (30 sec)

```python
# ✅ Explicit, but tedious — checking at each step
def process(user_id: int) -> Result[float, object]:
    user_result = get_user(user_id)
    if user_result.is_err():
        return user_result

    account_result = get_account(user_result.unwrap())
    if account_result.is_err():
        return account_result

    return get_balance(account_result.unwrap())
```

**Say:** "Better than exceptions — but noisy. Every step is a check. The happy path is buried."

### With Railway — bind chains it (60 sec)

```python
# ✅✅ Railway — bind handles the routing
def process(user_id: int) -> Result[float, object]:
    return (
        get_user(user_id)
        .bind(get_account)
        .bind(get_balance)
    )

# Usage — exhaustive match, no surprises
match process(42):
    case Ok(value=balance):              print(f"Balance: {balance}")
    case Err(error=UserNotFound()):      print("User not found")
    case Err(error=AccountNotFound()):   print("Account not found")
    case Err(error=AccountSuspended()):  print("Account suspended")
```

### Draw this on the board (30 sec)

```
get_user ──Ok──► get_account ──Ok──► get_balance ──Ok──► float
            │                   │                   │
           Err                 Err                 Err
            │                   │                   │
            └───────────────────┴───────────────────┴──► error (routes itself, politely)
```

**Say:** "Two tracks. The Ok track is your happy path — three words, flat, readable. The Err track is errors routing themselves around everything downstream without being told to. No try/except. No hidden control flow. That's Railway Oriented Programming — Scott Wlaschin coined it for F#, but the idea is universal."

---

## Part 6 — The `returns` Library (60 sec)

> *"Everything we hand-rolled exists in production-grade form in `returns` by dry-python."*

```bash
pip install returns
```

```python
from returns.result import Result, Success, Failure
from returns.pipeline import flow
from returns.pointfree import bind

def get_user(user_id: int) -> Result[User, UserNotFound]:
    user = db.find(user_id)
    return Success(user) if user else Failure(UserNotFound(user_id))

# flow() is the Railway chain — no .bind() calls needed
pipeline = flow(
    get_user,
    bind(get_account),
    bind(get_balance),
)

result = pipeline(42)
```

**The killer feature — `@safe`:**

```python
from returns.result import safe

# Wraps any exception-raising function into Result automatically
@safe
def parse_config(path: str) -> dict:
    return json.loads(open(path).read())   # raises on bad JSON or missing file

parse_config("config.json")    # → Success({...})
parse_config("missing.json")   # → Failure(FileNotFoundError(...))
```

**Say:** "`@safe` is your bridge between the exception-throwing world — third-party libraries, stdlib — and your Railway pipeline. Wrap it once at the boundary, speak Result everywhere inside."

---

## Sidebar: The Pythonic Middle Ground (facilitator note, don't demo live)

> *For teams where Result feels like too big a cultural step — a named tuple return is still better than exceptions as flow control:*

```python
from typing import NamedTuple

class UserResult(NamedTuple):
    user:  User | None
    error: str | None

def get_user(user_id: int) -> UserResult:
    user = db.find(user_id)
    return UserResult(user=user, error=None) if user \
        else UserResult(user=None, error=f"user {user_id} not found")
```

> *Honest signature, explicit error — just not chainable. Mention it as the stepping stone, not the destination.*

---

## Exercise (solo or pair, 5 min)

### Task

A checkout pipeline. Three steps, each can fail explicitly.

```python
# Given these stubs — make them speak Result

@dataclass(frozen=True)
class Cart:
    id:    str
    total: float

@dataclass(frozen=True)
class ChargeReceipt:
    charge_id: str
    amount:    float

# 1. Define typed error dataclasses for each failure case
# 2. Implement each function returning Result
# 3. Chain them with .bind()
# 4. Handle the final result with match

def validate_cart(cart_id: str) -> Result[Cart, ???]: ...
def apply_discount(cart: Cart, code: str) -> Result[Cart, ???]: ...
def charge_card(cart: Cart, token: str) -> Result[ChargeReceipt, ???]: ...
```

### Solution

```python
@dataclass(frozen=True)
class CartNotFound:    cart_id: str
@dataclass(frozen=True)
class CartEmpty:       cart_id: str
@dataclass(frozen=True)
class DiscountExpired: code: str
@dataclass(frozen=True)
class CardDeclined:    reason: str

def validate_cart(cart_id: str) -> Result[Cart, CartNotFound | CartEmpty]:
    if cart_id == "missing": return Err(CartNotFound(cart_id))
    if cart_id == "empty":   return Err(CartEmpty(cart_id))
    return Ok(Cart(id=cart_id, total=99.99))

def apply_discount(cart: Cart, code: str) -> Result[Cart, DiscountExpired]:
    if code == "EXPIRED": return Err(DiscountExpired(code))
    return Ok(Cart(id=cart.id, total=cart.total * 0.9))

def charge_card(cart: Cart, token: str) -> Result[ChargeReceipt, CardDeclined]:
    if token == "declined": return Err(CardDeclined("insufficient funds"))
    return Ok(ChargeReceipt(charge_id="CH-001", amount=cart.total))

def checkout(cart_id: str, code: str, token: str) -> Result[ChargeReceipt, object]:
    return (
        validate_cart(cart_id)
        .bind(lambda cart: apply_discount(cart, code))
        .bind(lambda cart: charge_card(cart, token))
    )

match checkout("cart-123", "SAVE10", "tok_visa"):
    case Ok(value=receipt):              print(f"Charged {receipt.amount}")
    case Err(error=CartNotFound()):      print("Cart not found")
    case Err(error=CartEmpty()):         print("Cart is empty")
    case Err(error=DiscountExpired()):   print("Discount expired")
    case Err(error=CardDeclined(r)):     print(f"Card declined: {r}")
```

**Discussion points:**
- The lambda in `.bind(lambda cart: apply_discount(cart, code))` — Python's main ergonomic rough edge vs F#. `returns` has `partial` helpers for this.
- Where does this pipeline live in FastAPI/Django? Service layer. The view translates `Ok` → 200, `Err` → 4xx.
- What goes in `except` now? Only genuinely exceptional things: DB connection failure, network timeout, unexpected `None` from a library bug.

---

## Key Takeaways

1. **Exceptions are for exceptional things** — infrastructure failures, bugs, the truly unexpected. Not expected business outcomes.
2. **Honest signatures.** `Result[User, UserNotFound]` tells you everything before you run the code.
3. **Railway Oriented Programming** — two tracks, `bind` does the routing. Happy path stays flat.
4. **`@safe`** bridges the exception-throwing world into your Railway pipeline.
5. **Illegal states** — that's Module 03.

---

## The Spectrum

```
Exceptions          Named returns       Result[T, E]        Full ADTs
(rude —             (honest but         (explicit,          (sealed types,
 invisible,          not chainable)      chainable,           nothing illegal)
 untyped)                               type-checked)

   ◄──────────────────────────────────────────────────────────────►
   most common                                           most explicit
   in Python today                                      in Python today
```

> *"You don't have to go all the way to the right on day one. But know the direction of travel — and understand what you're trading away when you stay on the left."*

---

## Notes for slide deck (Phase 2)

Key visuals for this module:
- The two-track Railway diagram (Ok lane / Err lane)
- Side-by-side: exceptions pyramid of try/except vs three-line `.bind()` chain
- The spectrum bar
- `@safe` as the bridge illustration (exception world → Result world)

---

## References

- *Railway Oriented Programming* — Scott Wlaschin, fsharpforfun.com
- `returns` library — https://returns.readthedocs.io
- PEP 634 — Structural Pattern Matching (Python 3.10+)
- *Domain Modeling Made Functional* — Scott Wlaschin (F# — ideas transfer directly)

---

*Module 02 of 6 · Defensive Programming from the Trenches*
