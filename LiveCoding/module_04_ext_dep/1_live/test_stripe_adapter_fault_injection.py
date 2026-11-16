"""
Part 10 — Testing the Adapter Against a Malfunctioning Provider.

These tests exercise StripePaymentGateway against MalfunctioningStripeApi,
a test double that simulates Stripe misbehaving.

The four principles being enforced:

  1. No exception must escape the adapter.
     Timeouts, transport errors, HTTP errors → Err(PaymentServiceError).
     Business logic never sees an asyncio.TimeoutError or TransportError.

  2. HTTP 200 is not success.
     A 200 with an error body → Err, not Ok.
     This is the trap that production incidents are made of.

  3. Schema violations are adapter failures.
     A garbled / renamed response shape → Err(PaymentServiceError).
     The caller never deals with KeyError or missing fields.

  4. The StripeApi protocol is the seam.
     No monkeypatching, no unittest.mock.patch.
     Inject a fault-configured double, assert on the Result.
"""

from __future__ import annotations

import asyncio

from .adapters.malfunctioning_stripe_api import MalfunctioningStripeApi
from .adapters.stripe_payment_gateway import StripePaymentGateway
from .core.result import Err
from .ports.dtos import ChargeRequest, PaymentServiceError, RefundRequest


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _run(coro):
    return asyncio.run(coro)


def _gateway(fault: str) -> StripePaymentGateway:
    return StripePaymentGateway(
        MalfunctioningStripeApi(fault),
        timeout_seconds=0.05,
        max_attempts=1,       # no retries — each test targets a single fault
        retry_delay_seconds=0.0,
    )


CHARGE = ChargeRequest(
    amount_cents=1000,
    currency="EUR",
    customer_id="cust_test",
    idempotency_key="idem_test",
)

REFUND = RefundRequest(
    charge_id="ch_test",
    amount_cents=500,
    idempotency_key="idem_refund_test",
)


# ─────────────────────────────────────────────────────────────────────────────
# Principle 1 — No exception escapes the adapter
# ─────────────────────────────────────────────────────────────────────────────

class TestNoExceptionEscapes:
    def test_timeout_returns_err_not_exception(self):
        # asyncio.TimeoutError must be caught inside the adapter
        result = _run(_gateway("timeout").charge(CHARGE))

        assert isinstance(result, Err)
        assert isinstance(result.error, PaymentServiceError)
        assert "timed out" in result.error.message

    def test_transport_error_returns_err_not_exception(self):
        # TransportError (TCP/DNS failure) must be caught inside the adapter
        result = _run(_gateway("transport_error").charge(CHARGE))

        assert isinstance(result, Err)
        assert isinstance(result.error, PaymentServiceError)

    def test_timeout_on_refund_returns_err_not_exception(self):
        result = _run(_gateway("timeout").refund(REFUND))

        assert isinstance(result, Err)
        assert isinstance(result.error, PaymentServiceError)
        assert "timed out" in result.error.message

    def test_transport_error_on_refund_returns_err_not_exception(self):
        result = _run(_gateway("transport_error").refund(REFUND))

        assert isinstance(result, Err)
        assert isinstance(result.error, PaymentServiceError)


# ─────────────────────────────────────────────────────────────────────────────
# Principle 2 — HTTP 200 is not success
# ─────────────────────────────────────────────────────────────────────────────

class TestHttp200IsNotSuccess:
    def test_200_with_error_body_charge_returns_err(self):
        # Stripe returns 200 but signals processing_error in the body.
        # The adapter must inspect the body, not trust the status code.
        result = _run(_gateway("200_with_error").charge(CHARGE))

        assert isinstance(result, Err)
        assert isinstance(result.error, PaymentServiceError)

    def test_200_with_error_body_refund_returns_err(self):
        result = _run(_gateway("200_with_error").refund(REFUND))

        assert isinstance(result, Err)
        assert isinstance(result.error, PaymentServiceError)


# ─────────────────────────────────────────────────────────────────────────────
# Principle 3 — Schema violations are adapter failures
# ─────────────────────────────────────────────────────────────────────────────

class TestSchemaViolationsAreAdapterFailures:
    def test_garbled_charge_response_returns_err(self):
        # Stripe renamed fields — "id" is now "charge_id", "amount" is "amt".
        # The adapter's _parse_charge_response detects missing fields
        # and returns Err(PaymentServiceError), never leaking a KeyError.
        result = _run(_gateway("garbled").charge(CHARGE))

        assert isinstance(result, Err)
        assert isinstance(result.error, PaymentServiceError)
        assert "missing" in result.error.message

    def test_garbled_refund_response_returns_err(self):
        result = _run(_gateway("garbled").refund(REFUND))

        assert isinstance(result, Err)
        assert isinstance(result.error, PaymentServiceError)
        assert "missing" in result.error.message


# ─────────────────────────────────────────────────────────────────────────────
# Principle 4 — HTTP 500 is also an adapter failure (not a crash)
# ─────────────────────────────────────────────────────────────────────────────

class TestServerErrorIsAdapterFailure:
    def test_500_charge_returns_err(self):
        result = _run(_gateway("server_error_500").charge(CHARGE))

        assert isinstance(result, Err)
        assert isinstance(result.error, PaymentServiceError)
        assert "500" in result.error.message

    def test_500_refund_returns_err(self):
        result = _run(_gateway("server_error_500").refund(REFUND))

        assert isinstance(result, Err)
        assert isinstance(result.error, PaymentServiceError)
        assert "500" in result.error.message
