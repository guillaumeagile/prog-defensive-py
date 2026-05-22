from solution_hand_rolled_result import (
    Ok,
    Err,
    User,
    Account,
    UserNotFound,
    AccountNotFound,
    AccountSuspended,
    get_user,
    get_account,
    get_balance,
    render_error,
)


class TestHandRolledResult:
    def test_ok_creation_and_unwrap(self):
        ok = Ok(42)
        assert ok.unwrap() == 42
        assert ok.is_ok()
        assert not ok.is_err()

    def test_err_creation(self):
        err = Err("error")
        assert err.is_err()
        assert not err.is_ok()

    def test_ok_map_transforms_value(self):
        ok = Ok(5)
        result = ok.map(lambda x: x * 2)
        assert isinstance(result, Ok)
        assert result.unwrap() == 10

    def test_err_map_passes_through(self):
        err = Err("error")
        result = err.map(lambda x: x * 2)
        assert isinstance(result, Err)
        assert result.error == "error"


class TestDomainFunctions:
    def test_get_user_returns_ok_for_existing_user(self):
        result = get_user(1)
        assert isinstance(result, Ok)
        user = result.unwrap()
        assert user.id == 1
        assert user.name == "Alice"

    def test_get_user_returns_err_for_missing_user(self):
        result = get_user(999)
        assert isinstance(result, Err)
        error = result.error
        assert isinstance(error, UserNotFound)
        assert error.user_id == 999

    def test_get_account_returns_ok_for_existing_account(self):
        user = User(id=1, name="Alice")
        result = get_account(user)
        assert isinstance(result, Ok)
        account = result.unwrap()
        assert account.id == "acc-1"

    def test_get_account_returns_err_for_missing_account(self):
        user = User(id=999, name="Ghost")
        result = get_account(user)
        assert isinstance(result, Err)
        assert isinstance(result.error, AccountNotFound)

    def test_get_balance_returns_ok_for_active_account(self):
        account = Account(id="acc-1", user_id=1, balance=100.0, suspended=False)
        result = get_balance(account)
        assert isinstance(result, Ok)
        assert result.unwrap() == 100.0

    def test_get_balance_returns_err_for_suspended_account(self):
        account = Account(id="acc-2", user_id=2, balance=50.0, suspended=True)
        result = get_balance(account)
        assert isinstance(result, Err)
        error = result.error
        assert isinstance(error, AccountSuspended)
        assert error.account_id == "acc-2"


class TestErrorRendering:
    def test_render_user_not_found(self):
        error = UserNotFound(user_id=42)
        assert "42" in render_error(error)
        assert "not found" in render_error(error)

    def test_render_account_not_found(self):
        error = AccountNotFound(user_id=99)
        message = render_error(error)
        assert "99" in message
        assert "No account" in message

    def test_render_account_suspended(self):
        error = AccountSuspended(account_id="acc-xyz")
        message = render_error(error)
        assert "acc-xyz" in message
        assert "suspended" in message
