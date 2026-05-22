from solution_railway_oriented import (
    Ok,
    Err,
    User,
    Account,
    UserNotFound,
    AccountNotFound,
    AccountSuspended,
    InsufficientFunds,
    get_user,
    get_account,
    get_balance,
    get_balance_without_railway,
    get_balance_railway,
    process_withdrawal,
    withdraw,
    render_error,
)


class TestRailwayChain:
    def test_railway_success_all_steps(self):
        result = get_balance_railway(1)
        assert isinstance(result, Ok)
        assert result.unwrap() == 100.0

    def test_railway_fails_at_first_step_user_not_found(self):
        result = get_balance_railway(999)
        assert isinstance(result, Err)
        assert isinstance(result.error, UserNotFound)

    def test_railway_fails_at_second_step_account_not_found(self):
        result = get_balance_railway(3)
        assert isinstance(result, Err)
        assert isinstance(result.error, AccountNotFound)

    def test_railway_fails_at_third_step_account_suspended(self):
        result = get_balance_railway(2)
        assert isinstance(result, Err)
        assert isinstance(result.error, AccountSuspended)

    def test_without_railway_same_results(self):
        for user_id in [1, 2, 3, 999]:
            without = get_balance_without_railway(user_id)
            with_railway = get_balance_railway(user_id)

            assert without.is_ok() == with_railway.is_ok()
            if without.is_err():
                assert type(without.error) == type(with_railway.error)


class TestExtendedPipeline:
    def test_withdrawal_success(self):
        result = process_withdrawal(1, 30.0)
        assert isinstance(result, Ok)
        assert result.unwrap() == 70.0

    def test_withdrawal_fails_insufficient_funds(self):
        result = process_withdrawal(1, 150.0)
        assert isinstance(result, Err)
        assert isinstance(result.error, InsufficientFunds)
        assert result.error.balance == 100.0
        assert result.error.requested == 150.0

    def test_withdrawal_fails_at_user_lookup(self):
        result = process_withdrawal(999, 10.0)
        assert isinstance(result, Err)
        assert isinstance(result.error, UserNotFound)

    def test_withdrawal_fails_at_account_suspended(self):
        result = process_withdrawal(2, 10.0)
        assert isinstance(result, Err)
        assert isinstance(result.error, AccountSuspended)


class TestWithdrawCurried:
    def test_withdraw_success(self):
        withdraw_30 = withdraw(30.0)
        result = withdraw_30(100.0)
        assert isinstance(result, Ok)
        assert result.unwrap() == 70.0

    def test_withdraw_failure(self):
        withdraw_150 = withdraw(150.0)
        result = withdraw_150(100.0)
        assert isinstance(result, Err)
        assert isinstance(result.error, InsufficientFunds)


class TestBindBehavior:
    def test_ok_bind_calls_function(self):
        ok = Ok(5)
        result = ok.bind(lambda x: Ok(x * 2))
        assert isinstance(result, Ok)
        assert result.unwrap() == 10

    def test_err_bind_short_circuits(self):
        err = Err("error")
        call_count = 0

        def track_calls(x):
            nonlocal call_count
            call_count += 1
            return Ok(x)

        result = err.bind(track_calls)
        assert isinstance(result, Err)
        assert result.error == "error"
        assert call_count == 0

    def test_err_in_chain_short_circuits_remaining(self):
        call_order = []

        def step1(x):
            call_order.append("step1")
            return Err("failed at step1")

        def step2(x):
            call_order.append("step2")
            return Ok(x)

        def step3(x):
            call_order.append("step3")
            return Ok(x)

        result = Ok("start").bind(step1).bind(step2).bind(step3)

        assert isinstance(result, Err)
        assert result.error == "failed at step1"
        assert call_order == ["step1"]  # step2 and step3 never called


class TestErrorRendering:
    def test_render_user_not_found(self):
        error = UserNotFound(user_id=42)
        message = render_error(error)
        assert "42" in message
        assert "not found" in message

    def test_render_insufficient_funds(self):
        error = InsufficientFunds(balance=50.0, requested=100.0)
        message = render_error(error)
        assert "50" in message
        assert "100" in message
        assert "less than" in message

    def test_render_unknown_error_fallback(self):
        class CustomError:
            pass

        message = render_error(CustomError())
        assert "Unknown error" in message
