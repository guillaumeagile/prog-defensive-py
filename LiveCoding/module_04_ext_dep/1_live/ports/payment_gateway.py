from __future__ import annotations

from typing import Protocol

from ..core.result import Err, Ok
from .dtos import (
    ChargeRequest,
    ChargeResult,
    PaymentDeclined,
    PaymentServiceError,
    RefundRequest,
    RefundResult,
)

ChargeOutcome = Ok[ChargeResult] | Err[PaymentDeclined | PaymentServiceError]
RefundOutcome = Ok[RefundResult] | Err[PaymentServiceError]


class PaymentGateway(Protocol):
    async def charge(self, request: ChargeRequest) -> ChargeOutcome: ...

    async def refund(self, request: RefundRequest) -> RefundOutcome: ...


class StripeApi(Protocol):
    async def create_payment_intent(self, request: ChargeRequest) -> object: ...

    async def create_refund(self, request: RefundRequest) -> object: ...
