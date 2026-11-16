from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ChargeRequest:
    amount_cents: int
    currency: str
    customer_id: str
    idempotency_key: str


@dataclass(frozen=True)
class ChargeResult:
    charge_id: str
    amount_cents: int
    currency: str
    status: str


@dataclass(frozen=True)
class RefundRequest:
    charge_id: str
    amount_cents: int
    idempotency_key: str


@dataclass(frozen=True)
class RefundResult:
    refund_id: str
    charge_id: str
    amount_cents: int
    status: str


@dataclass(frozen=True)
class PaymentDeclined:
    reason: str


@dataclass(frozen=True)
class PaymentServiceError:
    message: str
