from hypothesis import given, strategies as st

from solution_railway_oriented import (
    Ok,
    Err,
    UserNotFound,
    AccountNotFound,
    AccountSuspended,
    InsufficientFunds,
    get_balance_railway,
    process_withdrawal,
    withdraw,
)


class TestRailwayPBT:
    @given(st.integers(max_value=-1))
    def test_property_negative_user_id_fails_at_first_step(self, user_id: int):
        result = get_balance_railway(user_id)
        assert isinstance(result, Err)
        assert isinstance(result.error, UserNotFound)

    @given(st.integers(min_value=1000))
    def test_property_large_user_id_fails_at_first_step(self, user_id: int):
        result = get_balance_railway(user_id)
        assert isinstance(result, Err)
        assert isinstance(result.error, UserNotFound)

    @given(st.floats(min_value=0.0, max_value=1000.0, allow_nan=False, allow_infinity=False))
    def test_property_withdraw_zero_or_less_always_succeeds(self, amount: float):
        withdraw_fn = withdraw(0.0)
        result = withdraw_fn(amount)
        assert isinstance(result, Ok)
        assert result.unwrap() == amount

    @given(
        st.floats(min_value=100.01, max_value=10000.0, allow_nan=False, allow_infinity=False)
    )
    def test_property_withdraw_more_than_balance_fails(self, amount: float):
        result = process_withdrawal(1, amount)
        assert isinstance(result, Err)
        assert isinstance(result.error, InsufficientFunds)

    @given(st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False))
    def test_property_withdraw_within_balance_succeeds(self, amount: float):
        result = process_withdrawal(1, amount)
        assert isinstance(result, Ok)
        assert result.unwrap() == 100.0 - amount
