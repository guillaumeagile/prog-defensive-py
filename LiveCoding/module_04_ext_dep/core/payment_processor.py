from __future__ import annotations

import logging
from dataclasses import dataclass

from .result import Err, Ok, Result
from ..ports.dtos import ChargeRequest, ChargeResult, PaymentDeclined, PaymentServiceError
from ..ports.payment_gateway import PaymentGateway, ChargeOutcome

# Non-generic logger (specifically configured for this module domain)
logger = logging.getLogger(__name__)

DAILY_RISK_LIMIT_CENTS = 500000  # 5000.00 EUR/USD/GBP


@dataclass(frozen=True)
class RiskLimitExceeded:
    amount_cents: int
    limit_cents: int


class PaymentProcessor:
    """
    Domain service / use case inside Hexagonal Core.
    Coordinates business rules and interacts with outbound ports.
    """

    def __init__(self, gateway: PaymentGateway) -> None:
        self._gateway = gateway

    async def process_checkout(
        self,
        customer_id: str,
        amount_cents: int,
        currency: str,
        idempotency_key: str,
    ) -> Result[ChargeResult, RiskLimitExceeded | PaymentDeclined | PaymentServiceError]:
        # Domain validation (invariant checking): Never allow transactions exceeding risk limits
        if amount_cents > DAILY_RISK_LIMIT_CENTS:
            logger.warning(
                "Transaction blocked: risk limit exceeded for customer %s. Amount: %d, Limit: %d",
                customer_id,
                amount_cents,
                DAILY_RISK_LIMIT_CENTS,
            )
            return Err(
                RiskLimitExceeded(
                    amount_cents=amount_cents,
                    limit_cents=DAILY_RISK_LIMIT_CENTS,
                )
            )

        logger.info(
            "Processing checkout charge for customer %s of %d %s",
            customer_id,
            amount_cents,
            currency,
        )

        # Call outbound port
        outcome = await self._gateway.charge(
            ChargeRequest(
                amount_cents=amount_cents,
                currency=currency,
                customer_id=customer_id,
                idempotency_key=idempotency_key,
            )
        )

        # Return domain-translated outcomes using pattern matching / Result monad
        match outcome:
            case Ok(value=charge):
                logger.info("Checkout charge successful: %s", charge.charge_id)
                return Ok(charge)
            case Err(error=err):
                logger.error("Checkout charge failed: %s", err)
                return Err(err)
