from hypothesis import given, strategies as st

from returns.result import Success, Failure

from solution_returns_library import (
    UserNotFound,
    AccountNotFound,
    AccountSuspended,
    InsufficientFunds,
    get_balance_flow,
    process_withdrawal_flow,
    parse_config_json,
    divide,
)


class TestReturnsPBT:
    @given(st.integers(max_value=-1))
    def test_property_negative_user_id_fails_at_first_step(self, user_id: int):
        result = get_balance_flow(user_id)
        assert isinstance(result, Failure)
        assert isinstance(result.value_or(None), UserNotFound)


    @given(st.floats(min_value=100.01, max_value=10000.0, allow_nan=False, allow_infinity=False))
    def test_property_withdraw_more_than_balance_fails(self, amount: float):
        result = process_withdrawal_flow(1, amount)
        assert isinstance(result, Failure)
        assert isinstance(result.value_or(None), InsufficientFunds)

    @given(st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False))
    def test_property_withdraw_within_balance_succeeds(self, amount: float):
        result = process_withdrawal_flow(1, amount)
        assert isinstance(result, Success)
        expected = 100.0 - amount
        actual = result.value_or(None)
        assert abs(actual - expected) < 0.0001

    @given(st.text(min_size=1))
    def test_property_invalid_json_always_fails(self, text: str):
        # Filter out valid JSON by checking for missing structural chars
        if '"' not in text and '[' not in text and '{' not in text:
            result = parse_config_json(text)
            assert isinstance(result, Failure)

    @given(st.floats(), st.floats(min_value=0.0001, allow_nan=False, allow_infinity=False))
    def test_property_divide_by_non_zero_succeeds(self, a: float, b: float):
        result = divide(a, b)
        assert isinstance(result, Success)
        expected = a / b
        actual = result.value_or(None)
        if abs(expected) < 1e10 and abs(actual) < 1e10:
            assert abs(actual - expected) < 0.0001
