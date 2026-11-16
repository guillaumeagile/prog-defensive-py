from __future__ import annotations

from ..ports.dtos import ChargeRequest, RefundRequest
from .stripe_response import StripeResponse
from .transport_error import TransportError


class MalfunctioningStripeApi:
    """
    A test double that simulates Stripe misbehaving at the protocol level.

    Each instance is configured with a single fault mode, applied to every
    call. This keeps tests explicit: one fault per test, no shared mutable
    state between scenarios.

    Fault modes
    ───────────
    "timeout"           asyncio.TimeoutError — provider never responds
    "transport_error"   TransportError — TCP connection refused / DNS failure
    "server_error_500"  HTTP 500 — Stripe internal error
    "200_with_error"    HTTP 200, body contains {"status": "error"} — the trap
    "garbled"           HTTP 200, body has wrong shape — renamed/missing fields
    """

    def __init__(self, fault: str) -> None:
        _valid = {"timeout", "transport_error", "server_error_500", "200_with_error", "garbled"}
        if fault not in _valid:
            raise ValueError(f"unknown fault {fault!r}, choose from {_valid}")
        self._fault = fault

    async def create_payment_intent(self, request: ChargeRequest) -> StripeResponse:
        return await self._respond()

    async def create_refund(self, request: RefundRequest) -> StripeResponse:
        return await self._respond()

    async def _respond(self) -> StripeResponse:
        match self._fault:
            case "timeout":
                import asyncio
                raise asyncio.TimeoutError()
            case "transport_error":
                raise TransportError("connection refused")
            case "server_error_500":
                return StripeResponse(
                    status_code=500,
                    body={"error": {"message": "internal server error"}},
                )
            case "200_with_error":
                # HTTP 200 but Stripe signals a processing failure in the body
                return StripeResponse(
                    status_code=200,
                    body={"status": "error", "code": "processing_error"},
                )
            case "garbled":
                # Wrong shape — fields renamed, required keys absent
                return StripeResponse(
                    status_code=200,
                    body={"charge_id": "ch_123", "amt": 1000},  # not the expected shape
                )
            case _:
                raise AssertionError(f"unhandled fault: {self._fault}")
