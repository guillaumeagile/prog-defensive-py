from __future__ import annotations

import asyncio
from typing import Awaitable, Callable

from ..core.result import Err, Ok, Result
from ..ports.dtos import (
    ChargeRequest,
    ChargeResult,
    PaymentDeclined,
    PaymentServiceError,
    RefundRequest,
    RefundResult,
)
from ..ports.payment_gateway import ChargeOutcome, RefundOutcome, StripeApi
from .stripe_response import StripeResponse
from .transport_error import TransportError


class StripePaymentGateway:
    def __init__(
        self,
        api: StripeApi,
        *,
        timeout_seconds: float = 0.05,
        max_attempts: int = 3,
        retry_delay_seconds: float = 0.0,
    ) -> None:
        self._api = api
        self._timeout_seconds = timeout_seconds
        self._max_attempts = max_attempts
        self._retry_delay_seconds = retry_delay_seconds

    async def charge(self, request: ChargeRequest) -> ChargeOutcome:
        validation_error = _validate_charge_request(request)
        if validation_error is not None:
            return validation_error

        response_result = await self._call_with_retry(
            "Stripe charge",
            lambda: self._api.create_payment_intent(request),
        )
        if isinstance(response_result, Err):
            return response_result

        response = response_result.value
        if response.status_code == 402:
            return _decline_from_response(response)
        if response.status_code != 200:
            return Err(PaymentServiceError(f"Stripe returned {response.status_code}"))

        parsed = _parse_charge_response(response.body)
        if isinstance(parsed, Err):
            return parsed

        payload = parsed.value
        return Ok(
            ChargeResult(
                charge_id=payload["id"],
                amount_cents=payload["amount"],
                currency=payload["currency"],
                status=payload["status"],
            )
        )

    async def refund(self, request: RefundRequest) -> RefundOutcome:
        if request.amount_cents <= 0:
            return Err(PaymentServiceError("refund amount must be positive"))

        response_result = await self._call_with_retry(
            "Stripe refund",
            lambda: self._api.create_refund(request),
        )
        if isinstance(response_result, Err):
            return response_result

        response = response_result.value
        if response.status_code != 200:
            return Err(PaymentServiceError(f"Stripe returned {response.status_code}"))

        parsed = _parse_refund_response(response.body)
        if isinstance(parsed, Err):
            return parsed

        payload = parsed.value
        return Ok(
            RefundResult(
                refund_id=payload["id"],
                charge_id=payload["charge"],
                amount_cents=payload["amount"],
                status=payload["status"],
            )
        )

    async def _call_with_retry(
        self,
        label: str,
        operation: Callable[[], Awaitable[StripeResponse]],
    ) -> Result[StripeResponse, PaymentServiceError]:
        last_message = f"{label} failed"
        for attempt in range(1, self._max_attempts + 1):
            try:
                response = await asyncio.wait_for(operation(), timeout=self._timeout_seconds)
                return Ok(response)
            except asyncio.TimeoutError:
                last_message = f"{label} timed out"
            except TransportError as exc:
                last_message = f"{label} transport error: {exc}"

            if attempt < self._max_attempts:
                await asyncio.sleep(self._retry_delay_seconds)

        return Err(PaymentServiceError(last_message))


def _validate_charge_request(request: ChargeRequest) -> ChargeOutcome | None:
    if request.amount_cents <= 0:
        return Err(PaymentDeclined("amount must be positive"))
    if request.currency not in {"EUR", "USD", "GBP"}:
        return Err(PaymentDeclined(f"unsupported currency: {request.currency}"))
    if not request.customer_id:
        return Err(PaymentDeclined("customer_id must be provided"))
    return None


def _decline_from_response(response: StripeResponse) -> ChargeOutcome:
    error = response.body.get("error")
    if isinstance(error, dict):
        decline_code = error.get("decline_code")
        if isinstance(decline_code, str):
            return Err(PaymentDeclined(decline_code))
    return Err(PaymentServiceError("Stripe returned an invalid decline payload"))


def _parse_charge_response(body: dict[str, object]) -> Result[dict[str, str | int], PaymentServiceError]:
    charge_id = body.get("id")
    amount = body.get("amount")
    currency = body.get("currency")
    status = body.get("status")

    if not isinstance(charge_id, str):
        return Err(PaymentServiceError("Stripe charge payload is missing id"))
    if not isinstance(amount, int):
        return Err(PaymentServiceError("Stripe charge payload is missing amount"))
    if not isinstance(currency, str):
        return Err(PaymentServiceError("Stripe charge payload is missing currency"))
    if not isinstance(status, str):
        return Err(PaymentServiceError("Stripe charge payload is missing status"))

    return Ok({"id": charge_id, "amount": amount, "currency": currency, "status": status})


def _parse_refund_response(body: dict[str, object]) -> Result[dict[str, str | int], PaymentServiceError]:
    refund_id = body.get("id")
    charge_id = body.get("charge")
    amount = body.get("amount")
    status = body.get("status")

    if not isinstance(refund_id, str):
        return Err(PaymentServiceError("Stripe refund payload is missing id"))
    if not isinstance(charge_id, str):
        return Err(PaymentServiceError("Stripe refund payload is missing charge"))
    if not isinstance(amount, int):
        return Err(PaymentServiceError("Stripe refund payload is missing amount"))
    if not isinstance(status, str):
        return Err(PaymentServiceError("Stripe refund payload is missing status"))

    return Ok({"id": refund_id, "charge": charge_id, "amount": amount, "status": status})
