from __future__ import annotations

import asyncio
import uuid

from ..ports.dtos import ChargeRequest, RefundRequest
from .stripe_response import StripeResponse
from .transport_error import TransportError


class FakeStripeApi:
    def __init__(self) -> None:
        self.decline_next = False
        self.decline_reason = "insufficient_funds"
        self.transport_error_next = False
        self.malformed_next = False
        self.delay_seconds_each_call: float | None = None
        self._charges_by_key: dict[str, StripeResponse] = {}
        self._refunds_by_key: dict[str, StripeResponse] = {}
        self.payment_intent_calls = 0
        self.refund_calls = 0

    async def create_payment_intent(self, request: ChargeRequest) -> StripeResponse:
        self.payment_intent_calls += 1
        await self._maybe_delay()

        if self.transport_error_next:
            self.transport_error_next = False
            raise TransportError("stripe api unavailable")

        cached = self._charges_by_key.get(request.idempotency_key)
        if cached is not None:
            return cached

        if self.decline_next:
            self.decline_next = False
            response = StripeResponse(
                status_code=402,
                body={"error": {"decline_code": self.decline_reason}},
            )
            self._charges_by_key[request.idempotency_key] = response
            return response

        if self.malformed_next:
            self.malformed_next = False
            response = StripeResponse(status_code=200, body={"unexpected": "shape"})
            self._charges_by_key[request.idempotency_key] = response
            return response

        response = StripeResponse(
            status_code=200,
            body={
                "id": f"ch_{uuid.uuid4().hex[:10]}",
                "amount": request.amount_cents,
                "currency": request.currency,
                "status": "succeeded",
            },
        )
        self._charges_by_key[request.idempotency_key] = response
        return response

    async def create_refund(self, request: RefundRequest) -> StripeResponse:
        self.refund_calls += 1
        await self._maybe_delay()

        if self.transport_error_next:
            self.transport_error_next = False
            raise TransportError("stripe api unavailable")

        cached = self._refunds_by_key.get(request.idempotency_key)
        if cached is not None:
            return cached

        if self.malformed_next:
            self.malformed_next = False
            response = StripeResponse(status_code=200, body={"refund": "broken"})
            self._refunds_by_key[request.idempotency_key] = response
            return response

        if request.amount_cents <= 0:
            response = StripeResponse(
                status_code=400,
                body={"error": {"message": "refund amount must be positive"}},
            )
            self._refunds_by_key[request.idempotency_key] = response
            return response

        response = StripeResponse(
            status_code=200,
            body={
                "id": f"re_{uuid.uuid4().hex[:10]}",
                "charge": request.charge_id,
                "amount": request.amount_cents,
                "status": "succeeded",
            },
        )
        self._refunds_by_key[request.idempotency_key] = response
        return response

    async def _maybe_delay(self) -> None:
        if self.delay_seconds_each_call is not None:
            await asyncio.sleep(self.delay_seconds_each_call)
