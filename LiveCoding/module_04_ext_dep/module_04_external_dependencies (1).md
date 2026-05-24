# Module 04 — Handling External Dependencies
## Detailed Lesson Plan · ~10 minutes live · Defensive Programming from the Trenches

> *"Everything outside your process is hostile: APIs, queues, the filesystem, time itself.*
> *Not malicious — hostile. It will be slow, unavailable, wrong-shaped, and it will succeed on the first call then fail on the retry."*

---

## Overview

| | |
|---|---|
| **Duration** | 10 minutes live |
| **Core principle** | The outside world is untrusted input at scale — apply M01's boundary thinking and M02's explicit failures to every process crossing |
| **Python focus** | `typing.Protocol`, adapter pattern, `httpx` async, `stamina` retry, fake over mock, pytest DI |
| **Builds on** | M01 (validate at the boundary), M02 (explicit failures as `Result` types) |
| **Audience takeaway** | Design the interface first, fake it for tests, plug in the real thing via DI — the test suite runs both |

---

## Learning Objectives

1. Design an adapter interface using `typing.Protocol` as the seam between your code and the outside world
2. Build a self-made fake that fully implements the interface — no mock library
3. Write tests against the fake that cover all behavior cases — happy and unhappy paths
4. Apply the same test suite to the production implementation via pytest fixture parametrization
5. Apply timeouts, bounded retry, and response validation inside the adapter
6. Explain why fakes are superior to mocks for contract testing

---

## Facilitator Timing

```
00:00 — 00:45   Hook: the hostile outside world (45s)
00:45 — 01:30   Concept: M01 + M02 at the boundary (45s)
01:30 — 02:30   The adapter pattern: design the seam first (60s)
02:30 — 03:30   Protocol as interface (60s)
03:30 — 05:00   The fake implementation (90s)
05:00 — 06:00   Tests against the fake — all behavior cases (60s)
06:00 — 07:00   The real Stripe adapter (60s)
07:00 — 08:00   DI in tests: same suite, two implementations (60s)
08:00 — 09:00   Timeout + retry inside the adapter (60s)
09:00 — 09:30   Circuit breaker + idempotency (30s)
09:30 — 10:00   Wrap (30s)
```

---

## Part 1 — Hook (45s)

**Open with this:**

> "Everything we've covered so far — validate at the boundary, fail explicitly, encode failures in the type — assumes *you* wrote the other side. You control the data model. You control what goes in and comes out."

**Pause.**

> "External dependencies break that assumption completely. An HTTP API can return 200 with an error in the body. It can hang for 30 seconds then timeout. It can succeed on your first call and fail on the retry — because your retry triggered a duplicate charge."

**The frame:**

> "The outside world is not malicious. It's just indifferent to your correctness. Your job is to build a defensive perimeter at every point your code crosses a process boundary — and to design that perimeter so you can test it without hitting the real thing."

### ⚔ War story slot

> *Your story here. High-value options:*
> - *A retry without idempotency that charged a customer twice*
> - *A call with no timeout that held a connection pool thread for 40 minutes*
> - *A third-party deploy that changed a field name — silent `None` propagation downstream*
> - *A mock that passed tests but didn't match what the real API actually returned*

---

## Part 2 — Concept: M01 + M02 at the Boundary (45s)

**Bridge from M01 and M02:**

```
M01 — validate at boundary:    API response = untrusted input. Validate the shape.
M02 — explicit failures:       Network errors = Result[T, E]. Not exceptions.
M04 — both, under pressure:    Slow, wrong-shaped, lying, and you retry it.
```

**The three rules:**

> 1. Every external call gets a timeout. Always.
> 2. Every response gets validated. Never trust the shape.
> 3. Every state-changing operation is designed to be safe to retry.

**And one more, today's addition:**

> 4. Design the interface first. The real implementation is a plugin.

---

## Part 3 — The Adapter Pattern: Design the Seam First (60s)

The core idea: **your business logic should never know it's talking to Stripe**.

It talks to a `PaymentGateway` abstraction (Outbound Port), and your production adapter (Driven Adapter) plugged into it is a separate implementation.

```
[ core/ (Hexagonal Core) ]   ──────►   [ ports/ (Abstractions) ]
- payment_processor.py                 - payment_gateway.py (Protocol)
- result.py                            - dtos.py (Data contracts)
                                                     ▲
                                                     │
                                       [ adapters/ (Plugins) ]
                                       - fake_payment_gateway.py
                                       - stripe_payment_gateway.py
```

**Why this matters:**

- Your core domain logic (`core/`) is entirely pure — it doesn't import or depend on network clients, frameworks, or Stripe.
- Switching payment providers means writing a new adapter in `adapters/`, not touching business logic in `core/`.
- The interface and its contracts (`ports/`) define the strict boundaries of what enters or leaves your system.
- The test suite that runs against the fake *also* runs against Stripe — same contract, different adapter.

**Say:** "The interface is not boilerplate. It's the most important design decision you'll make about this dependency. Get the interface right and everything else is a detail."

---

## Part 4 — Protocol as Interface (60s)

Python gives us two ways to define an interface. Start with `Protocol`.

### `typing.Protocol` — structural subtyping

```python
from typing import Protocol
from dataclasses import dataclass

# Value types — what flows across the interface
@dataclass(frozen=True)
class ChargeRequest:
    amount_cents:    int      # always work in cents — floats and money don't mix
    currency:        str      # "EUR", "USD", "GBP"
    customer_id:     str
    idempotency_key: str      # caller's responsibility to generate

@dataclass(frozen=True)
class ChargeResult:
    charge_id:   str
    amount_cents: int
    currency:     str
    status:       str         # "succeeded", "pending"

@dataclass(frozen=True)
class RefundRequest:
    charge_id:       str
    amount_cents:    int      # partial refund supported
    idempotency_key: str

@dataclass(frozen=True)
class RefundResult:
    refund_id:    str
    charge_id:    str
    amount_cents: int
    status:       str

# Error types
@dataclass(frozen=True)
class PaymentDeclined:
    reason: str

@dataclass(frozen=True)
class PaymentServiceError:
    message: str

ChargeOutcome = Ok[ChargeResult] | Err[PaymentDeclined | PaymentServiceError]
RefundOutcome = Ok[RefundResult] | Err[PaymentServiceError]

# The interface — structural, no inheritance required
class PaymentGateway(Protocol):
    async def charge(self, request: ChargeRequest) -> ChargeOutcome: ...
    async def refund(self, request: RefundRequest) -> RefundOutcome: ...
```

**Say:** "Protocol is structural subtyping — duck typing with type checking. Any class that implements `charge` and `refund` with the right signatures *is* a `PaymentGateway`, without inheriting from it. mypy enforces this. No registration, no base class noise."

### ABC — the alternative (mention briefly)

```python
from abc import ABC, abstractmethod

class PaymentGateway(ABC):
    @abstractmethod
    async def charge(self, request: ChargeRequest) -> ChargeOutcome: ...
    @abstractmethod
    async def refund(self, request: RefundRequest) -> RefundOutcome: ...

# Difference: explicit inheritance required, enforced at instantiation time
# Use ABC when you want runtime enforcement even without mypy
# Use Protocol when you want structural typing and maximum flexibility
```

**Say:** "ABC enforces the contract at instantiation — you'll get a `TypeError` if you forget to implement a method, even without a type checker. Protocol enforces it at type-check time. In a well-typed codebase, Protocol is cleaner. In a mixed or legacy codebase, ABC gives you a safety net at runtime."

---

## Part 5 — The Fake Implementation (90s)

> *"A fake is a real implementation — lightweight, in-memory, no network. Not a mock. A mock replaces calls with assertions. A fake replaces the system with a simpler one that behaves correctly."*

```python
import uuid

class FakePaymentGateway:
    """
    In-memory payment gateway for tests and local development.
    Implements the full PaymentGateway Protocol.
    No network. No external state. Fully controllable.
    """

    def __init__(self):
        self._charges: dict[str, ChargeResult] = {}
        self._refunds:  dict[str, RefundResult] = {}
        # Test control points — configure failure modes from the test
        self.decline_next:   bool = False
        self.decline_reason: str  = "insufficient_funds"
        self.fail_next:      bool = False

    async def charge(self, request: ChargeRequest) -> ChargeOutcome:
        # Idempotency — same key, same result
        if request.idempotency_key in self._charges:
            return Ok(self._charges[request.idempotency_key])

        # Configurable failure modes — tests set these
        if self.fail_next:
            self.fail_next = False
            return Err(PaymentServiceError("gateway unavailable"))

        if self.decline_next:
            self.decline_next = False
            return Err(PaymentDeclined(self.decline_reason))

        # Preconditions — the fake enforces the same contract as the real thing
        if request.amount_cents <= 0:
            return Err(PaymentDeclined("amount must be positive"))
        if request.currency not in {"EUR", "USD", "GBP"}:
            return Err(PaymentDeclined(f"unsupported currency: {request.currency}"))

        result = ChargeResult(
            charge_id=f"fake_ch_{uuid.uuid4().hex[:8]}",
            amount_cents=request.amount_cents,
            currency=request.currency,
            status="succeeded",
        )
        self._charges[request.idempotency_key] = result
        return Ok(result)

    async def refund(self, request: RefundRequest) -> RefundOutcome:
        # Idempotency
        if request.idempotency_key in self._refunds:
            return Ok(self._refunds[request.idempotency_key])

        if self.fail_next:
            self.fail_next = False
            return Err(PaymentServiceError("gateway unavailable"))

        # Find the original charge
        charge = next(
            (c for c in self._charges.values() if c.charge_id == request.charge_id),
            None,
        )
        if charge is None:
            return Err(PaymentServiceError(f"charge {request.charge_id!r} not found"))
        if request.amount_cents > charge.amount_cents:
            return Err(PaymentServiceError("refund exceeds original charge amount"))

        result = RefundResult(
            refund_id=f"fake_re_{uuid.uuid4().hex[:8]}",
            charge_id=request.charge_id,
            amount_cents=request.amount_cents,
            status="succeeded",
        )
        self._refunds[request.idempotency_key] = result
        return Ok(result)
```

**Key points to say:**

- `decline_next` and `fail_next` are **test control points** — the test flips a flag, the next call behaves accordingly. No mock library, no patch, no magic.
- Idempotency is implemented in the fake — same key, same result. The test verifies this behavior, which the real Stripe also guarantees.
- The fake enforces the same preconditions as the real thing — `amount_cents > 0`, supported currencies. If your fake is too permissive, your tests won't catch contract violations.

---

## Part 6 — Tests Against the Fake: All Behavior Cases (60s)

```python
import pytest
import uuid

def make_key() -> str:
    return str(uuid.uuid4())

@pytest.fixture
def gateway() -> FakePaymentGateway:
    return FakePaymentGateway()

# Happy path
async def test_charge_succeeds(gateway):
    result = await gateway.charge(ChargeRequest(
        amount_cents=1000, currency="EUR",
        customer_id="cust_1", idempotency_key=make_key(),
    ))
    assert isinstance(result, Ok)
    assert result.value.amount_cents == 1000
    assert result.value.status == "succeeded"

# Unhappy path — card declined
async def test_charge_declined(gateway):
    gateway.decline_next = True
    gateway.decline_reason = "insufficient_funds"
    result = await gateway.charge(ChargeRequest(
        amount_cents=1000, currency="EUR",
        customer_id="cust_1", idempotency_key=make_key(),
    ))
    assert isinstance(result, Err)
    assert isinstance(result.error, PaymentDeclined)
    assert result.error.reason == "insufficient_funds"

# Unhappy path — gateway down
async def test_charge_service_error(gateway):
    gateway.fail_next = True
    result = await gateway.charge(ChargeRequest(
        amount_cents=1000, currency="EUR",
        customer_id="cust_1", idempotency_key=make_key(),
    ))
    assert isinstance(result, Err)
    assert isinstance(result.error, PaymentServiceError)

# Idempotency — same key, same result, called twice
async def test_charge_idempotent(gateway):
    key = make_key()
    request = ChargeRequest(amount_cents=500, currency="USD",
                            customer_id="cust_2", idempotency_key=key)
    first  = await gateway.charge(request)
    second = await gateway.charge(request)
    assert isinstance(first, Ok)
    assert isinstance(second, Ok)
    assert first.value.charge_id == second.value.charge_id  # same result

# Refund happy path
async def test_refund_succeeds(gateway):
    key = make_key()
    charge = await gateway.charge(ChargeRequest(
        amount_cents=2000, currency="EUR",
        customer_id="cust_3", idempotency_key=key,
    ))
    assert isinstance(charge, Ok)

    refund = await gateway.refund(RefundRequest(
        charge_id=charge.value.charge_id,
        amount_cents=500,                   # partial refund
        idempotency_key=make_key(),
    ))
    assert isinstance(refund, Ok)
    assert refund.value.amount_cents == 500

# Refund exceeds original — contract violation
async def test_refund_exceeds_charge(gateway):
    key = make_key()
    charge = await gateway.charge(ChargeRequest(
        amount_cents=1000, currency="EUR",
        customer_id="cust_4", idempotency_key=key,
    ))
    assert isinstance(charge, Ok)

    refund = await gateway.refund(RefundRequest(
        charge_id=charge.value.charge_id,
        amount_cents=9999,                  # more than charged
        idempotency_key=make_key(),
    ))
    assert isinstance(refund, Err)
    assert isinstance(refund.error, PaymentServiceError)
```

**Say:** "These tests cover the full behavioral contract of the interface — not Stripe's implementation, not HTTP calls. They run in milliseconds, no network, no credentials. And in a moment, the same tests will run against real Stripe."

---

## Part 7 — The Real Stripe Adapter (60s)

```python
import httpx
import stamina
from pydantic import BaseModel

# Pydantic models for Stripe's actual response shapes
class StripeCharge(BaseModel):
    id:       str
    amount:   int
    currency: str
    status:   str

class StripeRefund(BaseModel):
    id:       str
    charge:   str
    amount:   int
    status:   str

class StripePaymentGateway:
    """Production adapter — wraps Stripe's API behind the PaymentGateway Protocol."""

    def __init__(self, api_key: str):
        self._client = httpx.AsyncClient(
            base_url="https://api.stripe.com/v1",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=httpx.Timeout(connect=2.0, read=10.0),
        )

    @stamina.retry(on=(httpx.TimeoutException, httpx.TransportError), attempts=3, wait_initial=0.5, wait_jitter=0.2)
    async def charge(self, request: ChargeRequest) -> ChargeOutcome:
        try:
            response = await self._client.post(
                "/payment_intents",
                data={
                    "amount":   request.amount_cents,
                    "currency": request.currency.lower(),
                    "customer": request.customer_id,
                    "confirm":  "true",
                },
                headers={"Idempotency-Key": request.idempotency_key},
            )

            if response.status_code == 402:           # card declined
                body = response.json()
                return Err(PaymentDeclined(
                    body.get("error", {}).get("decline_code", "unknown")
                ))

            response.raise_for_status()
            stripe_charge = StripeCharge.model_validate(response.json())

            return Ok(ChargeResult(
                charge_id=stripe_charge.id,
                amount_cents=stripe_charge.amount,
                currency=stripe_charge.currency.upper(),
                status=stripe_charge.status,
            ))

        except httpx.HTTPStatusError as e:
            return Err(PaymentServiceError(f"Stripe error {e.response.status_code}"))
        except httpx.TimeoutException:
            return Err(PaymentServiceError("Stripe request timed out"))

    @stamina.retry(on=(httpx.TimeoutException, httpx.TransportError), attempts=3, wait_initial=0.5, wait_jitter=0.2)
    async def refund(self, request: RefundRequest) -> RefundOutcome:
        try:
            response = await self._client.post(
                "/refunds",
                data={
                    "charge": request.charge_id,
                    "amount": request.amount_cents,
                },
                headers={"Idempotency-Key": request.idempotency_key},
            )
            response.raise_for_status()
            stripe_refund = StripeRefund.model_validate(response.json())

            return Ok(RefundResult(
                refund_id=stripe_refund.id,
                charge_id=stripe_refund.charge,
                amount_cents=stripe_refund.amount,
                status=stripe_refund.status,
            ))

        except httpx.HTTPStatusError as e:
            return Err(PaymentServiceError(f"Stripe refund error {e.response.status_code}"))
        except httpx.TimeoutException:
            return Err(PaymentServiceError("Stripe refund timed out"))

    async def aclose(self):
        await self._client.aclose()
```

**Say:** "Notice what's inside the adapter: timeouts, retry, response validation with pydantic, explicit `Result` types. Everything defensive stays here. The business logic never sees an httpx call. It just calls `charge()` and gets back a `ChargeOutcome`."

---

## Part 8 — DI in Tests: Same Suite, Two Implementations (60s)

```python
# conftest.py

import asyncio
import pytest
import os

def pytest_addoption(parser):
    parser.addoption(
        "--gateway",
        default="fake",
        choices=["fake", "stripe"],
        help="Payment gateway implementation to test against",
    )

@pytest.fixture
def gateway(request) -> PaymentGateway:
    mode = request.config.getoption("--gateway")

    if mode == "stripe":
        api_key = os.environ["STRIPE_TEST_API_KEY"]
        gw = StripePaymentGateway(api_key=api_key)
        yield gw
        # cleanup: cancel any test payment intents
        asyncio.run(gw.aclose())
    else:
        yield FakePaymentGateway()
```

```bash
# Run against the fake — fast, no credentials, runs in CI always
pytest tests/payment/

# Run against real Stripe test environment — slow, needs credentials, run on demand
pytest tests/payment/ --gateway=stripe
```

**Say:** "The test file doesn't change. The fixture changes. The gateway flag decides which implementation flows in. Every test that passes against the fake is a claim about the contract — and running the same suite against Stripe verifies that the real adapter honors that contract."

**The insight to land:**

> "The fake is not a shortcut for testing. It *is* the test of the interface design. If the fake is hard to write, your interface is too wide. If the fake needs to know about HTTP, your abstraction is leaking. The fake is feedback."

---

## Part 9 — Timeout, Retry, Idempotency: Where They Live (30s)

**The answer is: inside the adapter. Always.**

```
[ Business Logic ]   charge(request)          Result[ChargeResult, ...]
        │            ──────────────────────►   ◄──────────────────────
        │
[ StripePaymentGateway ]
    - connect timeout: 2s        ← here
    - read timeout: 10s          ← here
    - retry on transient: 3x     ← here
    - idempotency key: forwarded ← caller generates, adapter passes through
    - response validation        ← here
    - Result wrapping            ← here
```

**Say:** "The business logic generates the idempotency key — it owns the operation identity. The adapter handles all transport concerns. This is the clean separation the adapter pattern gives you."

---

## Circuit Breaker — One Line (15s)

> "For high-volume dependencies, add a circuit breaker around the adapter. `stamina` supports it. When Stripe is down, fail fast — don't retry 3 times × every request in your queue. Give the service room to recover."

---

## Wrap (15s)

> "Design the interface. Fake it. Test the contract. Plug in the real thing. Run the same tests. That's the full loop — and it applies to every external dependency you'll ever write."

---

## Key Takeaways

1. **Design the interface first** — your business logic should never know it's talking to Stripe.
2. **`typing.Protocol`** is structural subtyping — any class that matches the shape *is* the interface.
3. **Fakes over mocks** — a fake is a real implementation, lightweight and controllable. A mock tests the call, not the contract.
4. **The fake is design feedback** — hard to write means the interface is too wide or leaking.
5. **Same tests, two implementations** — pytest fixture DI runs the contract suite against fake and real.
6. **All defensive machinery lives inside the adapter** — timeout, retry, validation, Result wrapping.
7. **Caller generates the idempotency key** — adapter passes it through. Retry is safe.

---

## Notes for Slide Deck (Phase 2)

Key visuals for this module:
- The adapter seam diagram: Business Logic → Protocol → [Fake | Stripe]
- The test DI flow: same test file, `--gateway` flag, two fixture paths
- Fake control points: `decline_next`, `fail_next` — show as a simple state toggle
- Where defensive machinery lives: annotated adapter class diagram

---

## References

- `typing.Protocol` — PEP 544, Python 3.8+
- `httpx` async docs — https://www.python-httpx.org
- `stamina` library — https://stamina.hynek.me
- Stripe test mode docs — https://stripe.com/docs/testing
- *Growing Object-Oriented Software, Guided by Tests* — Freeman & Pryce (the fake vs mock argument, definitively)
- *Working Effectively with Legacy Code* — Feathers (seam theory)

---

*Module 04 of 6 · Defensive Programming from the Trenches*
