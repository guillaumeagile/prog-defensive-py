from __future__ import annotations

import uuid

from ..core.result import Err, Ok
from ..ports.dtos import (
    ChargeRequest,
    ChargeResult,
    PaymentDeclined,
    PaymentServiceError,
    RefundRequest,
    RefundResult,
)
from ..ports.payment_gateway import ChargeOutcome, RefundOutcome


class FakePaymentGateway:
    def __init__(self) -> None:
        self._charges_by_key: dict[str, ChargeResult] = {}
        self._charges_by_id: dict[str, ChargeResult] = {}
        self._refunds_by_key: dict[str, RefundResult] = {}
        self.decline_next = False
        self.decline_reason = "insufficient_funds"
        self.fail_next = False

    async def charge(self, request: ChargeRequest) -> ChargeOutcome:
        cached = self._charges_by_key.get(request.idempotency_key)
        if cached is not None:
            return Ok(cached)

        if self.fail_next:
            self.fail_next = False
            return Err(PaymentServiceError("gateway unavailable"))

        if self.decline_next:
            self.decline_next = False
            return Err(PaymentDeclined(self.decline_reason))

        validation_error = _validate_charge_request(request)
        if validation_error is not None:
            return validation_error

        result = ChargeResult(
            charge_id=f"fake_ch_{uuid.uuid4().hex[:8]}",
            amount_cents=request.amount_cents,
            currency=request.currency,
            status="succeeded",
        )
        self._charges_by_key[request.idempotency_key] = result
        self._charges_by_id[result.charge_id] = result
        return Ok(result)

    async def refund(self, request: RefundRequest) -> RefundOutcome:
        cached = self._refunds_by_key.get(request.idempotency_key)
        if cached is not None:
            return Ok(cached)

        if self.fail_next:
            self.fail_next = False
            return Err(PaymentServiceError("gateway unavailable"))

        if request.amount_cents <= 0:
            return Err(PaymentServiceError("refund amount must be positive"))

        charge = self._charges_by_id.get(request.charge_id)
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
        self._refunds_by_key[request.idempotency_key] = result
        return Ok(result)


def _validate_charge_request(request: ChargeRequest) -> ChargeOutcome | None:
    if request.amount_cents <= 0:
        return Err(PaymentDeclined("amount must be positive"))
    if request.currency not in {"EUR", "USD", "GBP"}:
        return Err(PaymentDeclined(f"unsupported currency: {request.currency}"))
    if not request.customer_id:
        return Err(PaymentDeclined("customer_id must be provided"))
    return None
