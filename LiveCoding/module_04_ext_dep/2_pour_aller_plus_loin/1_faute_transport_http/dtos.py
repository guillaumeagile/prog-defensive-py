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
class PaymentServiceError:
    message: str
