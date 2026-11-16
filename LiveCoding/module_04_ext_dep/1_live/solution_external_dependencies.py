from core.result import Err, Ok, Result
from core.payment_processor import PaymentProcessor, RiskLimitExceeded
from ports.payment_gateway import PaymentGateway, StripeApi, ChargeOutcome, RefundOutcome
from ports.dtos import (
    ChargeRequest,
    ChargeResult,
    RefundRequest,
    RefundResult,
    PaymentDeclined,
    PaymentServiceError,
)
from adapters.fake_payment_gateway import FakePaymentGateway
from adapters.fake_stripe_api import FakeStripeApi
from adapters.stripe_payment_gateway import StripePaymentGateway
from adapters.stripe_response import StripeResponse
from adapters.transport_error import TransportError

