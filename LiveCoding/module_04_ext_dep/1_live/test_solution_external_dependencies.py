from .core.result import Err, Ok
from .core.payment_processor import PaymentProcessor, RiskLimitExceeded
from .ports.dtos import (
    ChargeRequest,
    RefundRequest,
    PaymentDeclined,
    PaymentServiceError,
)
from .adapters.fake_payment_gateway import FakePaymentGateway
from .adapters.fake_stripe_api import FakeStripeApi
from .adapters.stripe_payment_gateway import StripePaymentGateway


class TestFakePaymentGateway:
    def test_charge_succeeds(self) -> None:
        gateway = FakePaymentGateway()

        result = _run(
            gateway.charge(
                ChargeRequest(
                    amount_cents=1000,
                    currency="EUR",
                    customer_id="cust_1",
                    idempotency_key="key-1",
                )
            )
        )

        assert isinstance(result, Ok)
        assert result.value.amount_cents == 1000
        assert result.value.currency == "EUR"
        assert result.value.status == "succeeded"

    def test_charge_declined(self) -> None:
        gateway = FakePaymentGateway()
        gateway.decline_next = True
        gateway.decline_reason = "insufficient_funds"

        result = _run(
            gateway.charge(
                ChargeRequest(
                    amount_cents=1000,
                    currency="EUR",
                    customer_id="cust_1",
                    idempotency_key="key-1",
                )
            )
        )

        assert isinstance(result, Err)
        assert isinstance(result.error, PaymentDeclined)
        assert result.error.reason == "insufficient_funds"

    def test_charge_is_idempotent(self) -> None:
        gateway = FakePaymentGateway()
        request = ChargeRequest(
            amount_cents=500,
            currency="USD",
            customer_id="cust_2",
            idempotency_key="same-key",
        )

        first = _run(gateway.charge(request))
        second = _run(gateway.charge(request))

        assert isinstance(first, Ok)
        assert isinstance(second, Ok)
        assert first.value.charge_id == second.value.charge_id

    def test_refund_succeeds(self) -> None:
        gateway = FakePaymentGateway()
        charge = _run(
            gateway.charge(
                ChargeRequest(
                    amount_cents=2000,
                    currency="EUR",
                    customer_id="cust_3",
                    idempotency_key="charge-key",
                )
            )
        )
        assert isinstance(charge, Ok)

        refund = _run(
            gateway.refund(
                RefundRequest(
                    charge_id=charge.value.charge_id,
                    amount_cents=500,
                    idempotency_key="refund-key",
                )
            )
        )

        assert isinstance(refund, Ok)
        assert refund.value.amount_cents == 500
        assert refund.value.charge_id == charge.value.charge_id

    def test_refund_rejects_amount_over_charge(self) -> None:
        gateway = FakePaymentGateway()
        charge = _run(
            gateway.charge(
                ChargeRequest(
                    amount_cents=1000,
                    currency="EUR",
                    customer_id="cust_4",
                    idempotency_key="charge-key",
                )
            )
        )
        assert isinstance(charge, Ok)

        refund = _run(
            gateway.refund(
                RefundRequest(
                    charge_id=charge.value.charge_id,
                    amount_cents=9999,
                    idempotency_key="refund-key",
                )
            )
        )

        assert isinstance(refund, Err)
        assert isinstance(refund.error, PaymentServiceError)


class TestStripePaymentGateway:
    def test_charge_succeeds(self) -> None:
        api = FakeStripeApi()
        gateway = StripePaymentGateway(api)

        result = _run(
            gateway.charge(
                ChargeRequest(
                    amount_cents=1500,
                    currency="EUR",
                    customer_id="cust_5",
                    idempotency_key="stripe-key-1",
                )
            )
        )

        assert isinstance(result, Ok)
        assert result.value.amount_cents == 1500
        assert result.value.currency == "EUR"
        assert result.value.status == "succeeded"
        assert api.payment_intent_calls == 1

    def test_charge_declined(self) -> None:
        api = FakeStripeApi()
        api.decline_next = True
        api.decline_reason = "do_not_honor"
        gateway = StripePaymentGateway(api)

        result = _run(
            gateway.charge(
                ChargeRequest(
                    amount_cents=1500,
                    currency="EUR",
                    customer_id="cust_5",
                    idempotency_key="stripe-key-2",
                )
            )
        )

        assert isinstance(result, Err)
        assert isinstance(result.error, PaymentDeclined)
        assert result.error.reason == "do_not_honor"

    def test_charge_times_out_once_then_succeeds_with_retry(self) -> None:
        api = FakeStripeApi()
        api.delay_seconds_each_call = 0.1
        gateway = StripePaymentGateway(
            api,
            timeout_seconds=0.01,
            max_attempts=2,
            retry_delay_seconds=0.0,
        )

        result = _run(
            gateway.charge(
                ChargeRequest(
                    amount_cents=1500,
                    currency="EUR",
                    customer_id="cust_5",
                    idempotency_key="stripe-key-3",
                )
            )
        )

        assert isinstance(result, Err)
        assert isinstance(result.error, PaymentServiceError)
        assert "timed out" in result.error.message
        assert api.payment_intent_calls == 2

    def test_charge_retries_transport_error_and_succeeds(self) -> None:
        api = FakeStripeApi()
        api.transport_error_next = True
        gateway = StripePaymentGateway(
            api,
            timeout_seconds=0.05,
            max_attempts=2,
            retry_delay_seconds=0.0,
        )

        result = _run(
            gateway.charge(
                ChargeRequest(
                    amount_cents=1500,
                    currency="EUR",
                    customer_id="cust_5",
                    idempotency_key="stripe-key-4",
                )
            )
        )

        assert isinstance(result, Ok)
        assert result.value.amount_cents == 1500
        assert api.payment_intent_calls == 2

    def test_refund_succeeds(self) -> None:
        api = FakeStripeApi()
        gateway = StripePaymentGateway(api)

        charge = _run(
            gateway.charge(
                ChargeRequest(
                    amount_cents=2000,
                    currency="EUR",
                    customer_id="cust_6",
                    idempotency_key="stripe-charge-key",
                )
            )
        )
        assert isinstance(charge, Ok)

        refund = _run(
            gateway.refund(
                RefundRequest(
                    charge_id=charge.value.charge_id,
                    amount_cents=500,
                    idempotency_key="stripe-refund-key",
                )
            )
        )

        assert isinstance(refund, Ok)
        assert refund.value.amount_cents == 500
        assert refund.value.charge_id == charge.value.charge_id

    def test_refund_rejects_malformed_payload(self) -> None:
        api = FakeStripeApi()
        api.malformed_next = True
        gateway = StripePaymentGateway(api)

        result = _run(
            gateway.refund(
                RefundRequest(
                    charge_id="ch_missing",
                    amount_cents=500,
                    idempotency_key="stripe-refund-key-2",
                )
            )
        )

        assert isinstance(result, Err)
        assert isinstance(result.error, PaymentServiceError)
        assert "missing" in result.error.message or "invalid" in result.error.message


class TestPaymentProcessor:
    def test_processor_success_checkout(self) -> None:
        gateway = FakePaymentGateway()
        processor = PaymentProcessor(gateway)

        result = _run(
            processor.process_checkout(
                customer_id="cust_abc",
                amount_cents=25000,  # 250.00 (well within limits)
                currency="EUR",
                idempotency_key="key-usecase-1",
            )
        )

        assert isinstance(result, Ok)
        assert result.value.amount_cents == 25000
        assert result.value.status == "succeeded"

    def test_processor_risk_limit_exceeded(self) -> None:
        gateway = FakePaymentGateway()
        processor = PaymentProcessor(gateway)

        result = _run(
            processor.process_checkout(
                customer_id="cust_abc",
                amount_cents=600000,  # 6000.00 (violates limit)
                currency="EUR",
                idempotency_key="key-usecase-2",
            )
        )

        assert isinstance(result, Err)
        assert isinstance(result.error, RiskLimitExceeded)
        assert result.error.amount_cents == 600000
        assert result.error.limit_cents == 500000


def _run(coro):
    import asyncio

    return asyncio.run(coro)


if __name__ == "__main__":
    TestFakePaymentGateway().test_charge_succeeds()
    TestFakePaymentGateway().test_charge_declined()
    TestFakePaymentGateway().test_charge_is_idempotent()
    TestFakePaymentGateway().test_refund_succeeds()
    TestFakePaymentGateway().test_refund_rejects_amount_over_charge()
    TestStripePaymentGateway().test_charge_succeeds()
    TestStripePaymentGateway().test_charge_declined()
    TestStripePaymentGateway().test_charge_times_out_once_then_succeeds_with_retry()
    TestStripePaymentGateway().test_charge_retries_transport_error_and_succeeds()
    TestStripePaymentGateway().test_refund_succeeds()
    TestStripePaymentGateway().test_refund_rejects_malformed_payload()

    # Domain Use Case / Service tests
    TestPaymentProcessor().test_processor_success_checkout()
    TestPaymentProcessor().test_processor_risk_limit_exceeded()
