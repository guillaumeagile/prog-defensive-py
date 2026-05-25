"""
Seam B fault injection — transport level.

Real httpx runs. Only the TCP socket is replaced by FaultyStripeTransport.
This proves HttpStripeApi handles every wire-level failure correctly,
including failures that only surface when real HTTP parsing code runs.
"""

from __future__ import annotations

import asyncio

import httpx
import pytest
from .faulty_stripe_transport import FaultyStripeTransport
from .http_stripe_api import HttpStripeApi
from .result import Err, Ok
from .dtos import ChargeRequest, ChargeResult, PaymentServiceError


def _run(coro):
    return asyncio.run(coro)


def _api(fault: str) -> HttpStripeApi:
    transport = FaultyStripeTransport(fault)
    client = httpx.AsyncClient(
        base_url="https://api.stripe.com",
        transport=transport,
        timeout=httpx.Timeout(0.1),
    )
    return HttpStripeApi(client)


CHARGE = ChargeRequest(
    amount_cents=1000,
    currency="EUR",
    customer_id="cust_test",
    idempotency_key="idem_test",
)


# ─────────────────────────────────────────────────────────────────────────────
# Principle 1 — No httpx exception escapes the adapter
# ─────────────────────────────────────────────────────────────────────────────

class TestNoHttpxExceptionEscapes:
    def test_read_timeout_returns_err(self):
        # httpx.ReadTimeout must be caught inside the adapter
        result = _run(_api("timeout").charge(CHARGE))

        assert isinstance(result, Err)
        assert isinstance(result.error, PaymentServiceError)
        assert "timed out" in result.error.message

    def test_connect_error_returns_err(self):
        # httpx.ConnectError (TCP refused, DNS failure) must also be caught
        result = _run(_api("connection").charge(CHARGE))

        assert isinstance(result, Err)
        assert isinstance(result.error, PaymentServiceError)
        assert "transport error" in result.error.message


# ─────────────────────────────────────────────────────────────────────────────
# Principle 2 — HTTP 200 is not success
# ─────────────────────────────────────────────────────────────────────────────

class TestHttp200IsNotSuccess:
    def test_200_with_error_body_returns_err(self):
        # Stripe sends 200 but the body signals a processing failure.
        # The adapter must read the body, not trust the status code.
        result = _run(_api("200_error_body").charge(CHARGE))

        assert isinstance(result, Err)
        assert isinstance(result.error, PaymentServiceError)


# ─────────────────────────────────────────────────────────────────────────────
# Principle 3 — Schema violations are adapter failures
# ─────────────────────────────────────────────────────────────────────────────

class TestSchemaViolationsAreAdapterFailures:
    def test_garbled_json_returns_err(self):
        # Stripe renamed fields — real httpx parses the JSON fine,
        # but the adapter's field checks catch the wrong shape.
        result = _run(_api("garbled").charge(CHARGE))

        assert isinstance(result, Err)
        assert isinstance(result.error, PaymentServiceError)
        assert "missing" in result.error.message

    def test_non_json_body_returns_err(self):
        # Stripe returns an HTML error page (e.g. from a load balancer).
        # response.json() raises — the adapter must catch that too.
        result = _run(_api("non_json").charge(CHARGE))

        assert isinstance(result, Err)
        assert isinstance(result.error, PaymentServiceError)
        assert "non-JSON" in result.error.message


# ─────────────────────────────────────────────────────────────────────────────
# Principle 4 — HTTP 500 is an adapter failure
# ─────────────────────────────────────────────────────────────────────────────

class TestServerErrorIsAdapterFailure:
    def test_500_returns_err(self):
        result = _run(_api("server_500").charge(CHARGE))

        assert isinstance(result, Err)
        assert isinstance(result.error, PaymentServiceError)
        assert "500" in result.error.message


# ─────────────────────────────────────────────────────────────────────────────
# INTENTIONALLY FAILING TESTS — production bugs reproduced in a controlled env
#
# These two tests are marked xfail so the suite stays green,
# but the failure reason is printed so the reader sees exactly what goes wrong.
# Remove the @pytest.mark.xfail to watch them fail in red.
# ─────────────────────────────────────────────────────────────────────────────

class NaiveHttpStripeApi:
    """
    A broken adapter that trusts HTTP 200 = success and never inspects the body.
    Simulates the most common real production mistake.
    """
    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def charge(self, request: ChargeRequest) -> Ok[ChargeResult] | Err[PaymentServiceError]:
        response = await self._client.post(
            "/v1/payment_intents",
            data={"amount": str(request.amount_cents), "currency": request.currency.lower()},
        )
        # BUG: trusts status_code, never checks the body for error signals
        if response.status_code == 200:
            body = response.json()
            return Ok(ChargeResult(
                charge_id=body.get("id", ""),
                amount_cents=body.get("amount", 0),
                currency=body.get("currency", ""),
                status=body.get("status", ""),
            ))
        return Err(PaymentServiceError(f"unexpected status {response.status_code}"))


class LeakyHttpStripeApi:
    """
    A broken adapter that catches TimeoutException but forgets ConnectError.
    Simulates incomplete exception handling — one clause missing.
    """
    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def charge(self, request: ChargeRequest) -> Ok[ChargeResult] | Err[PaymentServiceError]:
        try:
            response = await self._client.post(
                "/v1/payment_intents",
                data={"amount": str(request.amount_cents), "currency": request.currency.lower()},
            )
        except httpx.TimeoutException:
            return Err(PaymentServiceError("timed out"))
        # BUG: httpx.ConnectError is a TransportError, not a TimeoutException —
        #      it is NOT caught here and will propagate as an unhandled exception

        body = response.json()
        return Ok(ChargeResult(
            charge_id=body.get("id", ""),
            amount_cents=body.get("amount", 0),
            currency=body.get("currency", ""),
            status=body.get("status", ""),
        ))


def _naive_api(fault: str) -> NaiveHttpStripeApi:
    client = httpx.AsyncClient(
        base_url="https://api.stripe.com",
        transport=FaultyStripeTransport(fault),
        timeout=httpx.Timeout(0.1),
    )
    return NaiveHttpStripeApi(client)


def _leaky_api(fault: str) -> LeakyHttpStripeApi:
    client = httpx.AsyncClient(
        base_url="https://api.stripe.com",
        transport=FaultyStripeTransport(fault),
        timeout=httpx.Timeout(0.1),
    )
    return LeakyHttpStripeApi(client)

"""
@pytest.mark.xfail(strict=True, reason=(
    "NaiveHttpStripeApi trusts HTTP 200 = success. "
    "Stripe sends 200 with an error body — the adapter returns Ok instead of Err. "
    "In production: the charge is silently accepted, money never moves."
))"""
def test_FAILS_naive_adapter_trusts_200_as_success():
    result = _run(_naive_api("200_error_body").charge(CHARGE))

    # We expect Err — the naive adapter returns Ok(ChargeResult(...)) instead
    assert isinstance(result, Err), (
        f"Got Ok({result.value!r}) — adapter blindly trusted HTTP 200. "  # type: ignore[union-attr]
        "Stripe said 'error' in the body. This charge will never settle."
    )



def test_FAILS_leaky_adapter_lets_connect_error_escape():
    # This does not return Err — it raises httpx.ConnectError straight through.
    # The caller gets a crash, not a Result.
    result = _run(_leaky_api("connection").charge(CHARGE))

    assert isinstance(result, Err), (
        "Expected Err(PaymentServiceError) — got an unhandled httpx.ConnectError instead. "
        "The exception escaped the adapter boundary."
    )
