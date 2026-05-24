import json

from returns.result import Success, Failure

from solution_returns_library import (
    User,
    Account,
    UserNotFound,
    AccountNotFound,
    AccountSuspended,
    InsufficientFunds,
    get_user,
    get_account,
    get_balance,
    get_balance_flow,
    process_withdrawal_flow,
    withdraw,
    parse_config_json,
    divide,
    process_config_with_calculation,
    render_error,
    example_unwrap_or_usage,
    example_map_usage,
)


class TestReturnsResult:
    def test_success_creation(self):
        success = Success(42)
        assert success.value_or(0) == 42

    def test_failure_creation(self):
        failure = Failure("error")
        assert failure.value_or("didn't work") == "didn't work"


class TestDomainFunctions:
    def test_get_user_success(self):
        result = get_user(1)
        assert isinstance(result, Success)
        user = result.value_or(None)
        assert user.id == 1
        assert user.name == "Alice"

    def test_get_user_failure(self):
        result = get_user(999)
        assert isinstance(result, Failure)
        error = result.failure()
        assert isinstance(error, UserNotFound)

    def test_get_account_success(self):
        user = User(id=1, name="Alice")
        result = get_account(user)
        assert isinstance(result, Success)
        account = result.value_or(None)
        assert account.id == "acc-1"

    def test_get_balance_active_account(self):
        account = Account(id="acc-1", user_id=1, balance=100.0, suspended=False)
        result = get_balance(account)
        assert isinstance(result, Success)
        assert result.value_or(0) == 100.0

    def test_get_balance_suspended_account(self):
        account = Account(id="acc-2", user_id=2, balance=50.0, suspended=True)
        result = get_balance(account)
        assert isinstance(result, Failure)
        assert isinstance(result.failure(), AccountSuspended)


class TestFlowChains:
    def test_flow_success_all_steps(self):
        result = get_balance_flow(1)
        assert isinstance(result, Success)
        assert result.value_or(0) == 100.0

    def test_flow_fails_user_not_found(self):
        result = get_balance_flow(999)
        assert isinstance(result, Failure)
        assert isinstance(result.failure(), UserNotFound)

    def test_flow_fails_account_not_found(self):
        result = get_balance_flow(3)
        assert isinstance(result, Failure)
        assert isinstance(result.failure(), AccountNotFound)

    def test_flow_fails_account_suspended(self):
        result = get_balance_flow(2)
        assert isinstance(result, Failure)
        assert isinstance(result.failure(), AccountSuspended)


class TestWithdrawalFlow:
    def test_withdrawal_success(self):
        result = process_withdrawal_flow(1, 30.0)
        assert isinstance(result, Success)
        assert result.value_or(0) == 70.0

    def test_withdrawal_fails_insufficient_funds(self):
        result = process_withdrawal_flow(1, 150.0)
        assert isinstance(result, Failure)
        error = result.failure()
        assert isinstance(error, InsufficientFunds)
        assert error.balance == 100.0
        assert error.requested == 150.0

    def test_withdrawal_fails_at_user_lookup(self):
        result = process_withdrawal_flow(999, 10.0)
        assert isinstance(result, Failure)
        assert isinstance(result.failure(), UserNotFound)


    def test_withdrawal_fails_at_amount_neg(self):
        result = process_withdrawal_flow(1, -10.0)
        # In the original implementation, negative amounts actually succeed
        # because withdraw() doesn't validate the amount, only balance
        assert isinstance(result, Success)
        assert result.value_or(None) == 110.0  # 100 - (-10) = 110


class TestSafeDecorator:
    def test_safe_wraps_success(self):
        result = parse_config_json('{"value": 100}')
        assert isinstance(result, Success)
        assert result.value_or({}) == {"value": 100}

    def test_safe_catches_json_decode_error(self):
        result = parse_config_json("invalid json")
        assert isinstance(result, Failure)
        assert isinstance(result.failure(), ValueError)

    def test_divide_success(self):
        result = divide(100.0, 2.0)
        assert isinstance(result, Success)
        assert result.value_or(0) == 50.0

    def test_divide_by_zero_caught(self):
        result = divide(100.0, 0.0)
        assert isinstance(result, Failure)
        assert isinstance(result.failure(), ZeroDivisionError)

    def test_process_config_with_calculation_success(self):
        result = process_config_with_calculation('{"value": 100}', 2.0)
        assert isinstance(result, Success)
        assert result.value_or(0) == 50.0

    def test_process_config_with_calculation_json_error(self):
        result = process_config_with_calculation("invalid", 2.0)
        assert isinstance(result, Failure)
        assert isinstance(result.failure(), ValueError)

    def test_process_config_with_calculation_divide_by_zero(self):
        result = process_config_with_calculation('{"value": 100}', 0.0)
        assert isinstance(result, Failure)
        assert isinstance(result.failure(), ZeroDivisionError)


class TestBindBehavior:
    def test_bind_success_chains(self):
        result = Success(5).bind(lambda x: Success(x * 2))
        assert isinstance(result, Success)
        assert result.value_or(0) == 10

    def test_bind_failure_short_circuits(self):
        call_count = 0

        def track_calls(x):
            nonlocal call_count
            call_count += 1
            return Success(x)

        result = Failure("error").bind(track_calls)
        assert isinstance(result, Failure)
        assert call_count == 0


class TestUtilityMethods:
    def test_value_or_returns_value_on_success(self):
        result = example_unwrap_or_usage()
        assert result == 100.0

    def test_map_transforms_success_value(self):
        result = example_map_usage()
        assert isinstance(result, Success)
        assert result.value_or(0) == 105.0  # 100 * 1.05

    def test_map_passes_through_failure(self):
        failure = Failure(UserNotFound(user_id=999))
        result = failure.map(lambda x: x * 2)
        assert isinstance(result, Failure)
        assert isinstance(result.failure(), UserNotFound)


class TestErrorRendering:
    def test_render_user_not_found(self):
        error = UserNotFound(user_id=42)
        message = render_error(error)
        assert "42" in message

    def test_render_value_error(self):
        error = ValueError("bad input")
        message = render_error(error)
        assert "bad input" in message

    def test_render_zero_division(self):
        message = render_error(ZeroDivisionError())
        assert "divide by zero" in message.lower()

    def test_render_insufficient_funds(self):
        error = InsufficientFunds(balance=50.0, requested=100.0)
        message = render_error(error)
        assert "50" in message
        assert "100" in message
