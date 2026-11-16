"""
HttpStripeApi — the real adapter that talks to Stripe over HTTP.

This is the layer Seam B tests: real httpx machinery runs,
only the TCP transport is replaced by a controllable fake.

Kept minimal on purpose — only charge, no retry logic,
so the tests stay focused on transport-level fault handling.
"""

from __future__ import annotations

import httpx

from .result import Err, Ok
from .dtos import ChargeRequest, ChargeResult, PaymentServiceError

ChargeOutcome = Ok[ChargeResult] | Err[PaymentServiceError]


class HttpStripeApi:
    """
    Calls the real Stripe /v1/payment_intents endpoint.
    Accepts an injected httpx.AsyncClient so the transport can be swapped
    in tests without touching any business logic.
    """

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def charge(self, request: ChargeRequest) -> ChargeOutcome:
        try:
            response = await self._client.post(
                "/v1/payment_intents",
                data={
                    "amount": str(request.amount_cents),
                    "currency": request.currency.lower(),
                    "customer": request.customer_id,
                    "confirm": "true",
                    "payment_method": "pm_card_visa",
                },
                headers={"Idempotency-Key": request.idempotency_key},
            )
        except httpx.TimeoutException:
            return Err(PaymentServiceError("Stripe charge timed out"))
        except httpx.TransportError as exc:
            return Err(PaymentServiceError(f"Stripe transport error: {exc}"))

        if response.status_code == 500:
            return Err(PaymentServiceError("Stripe returned 500"))

        try:
            body = response.json()
        except Exception:
            return Err(PaymentServiceError("Stripe returned non-JSON response"))

        # HTTP 200 is not success — inspect the body
        if response.status_code != 200:
            msg = body.get("error", {}).get("message", f"status {response.status_code}")
            return Err(PaymentServiceError(str(msg)))

        charge_id = body.get("id")
        amount = body.get("amount")
        currency = body.get("currency")
        status = body.get("status")

        if not isinstance(charge_id, str):
            return Err(PaymentServiceError("Stripe response missing id"))
        if not isinstance(amount, int):
            return Err(PaymentServiceError("Stripe response missing amount"))
        if not isinstance(currency, str):
            return Err(PaymentServiceError("Stripe response missing currency"))
        if not isinstance(status, str):
            return Err(PaymentServiceError("Stripe response missing status"))

        return Ok(ChargeResult(
            charge_id=charge_id,
            amount_cents=amount,
            currency=currency,
            status=status,
        ))
