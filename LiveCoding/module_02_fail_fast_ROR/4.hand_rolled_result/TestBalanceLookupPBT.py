from hypothesis import given, strategies as st

from solution_hand_rolled_result import (
    Ok,
    Err,
    UserNotFound,
    AccountNotFound,
    AccountSuspended,
    get_user,
    get_account,
    get_balance,
    User,
    Account,
)


class TestBalanceLookupPBT:
    @given(st.integers(max_value=-1))
    def test_property_negative_user_id_not_found(self, user_id: int):
        result = get_user(user_id)
        assert isinstance(result, Err)
        assert isinstance(result.error, UserNotFound)

    @given(st.integers(min_value=1000))
    def test_property_large_user_id_not_found(self, user_id: int):
        result = get_user(user_id)
        assert isinstance(result, Err)
        assert isinstance(result.error, UserNotFound)

    def test_property_account_suspension_always_fails(self):
        for suspended in [True, False]:
            account = Account(
                id="test-acc",
                user_id=1,
                balance=100.0,
                suspended=suspended
            )
            result = get_balance(account)
            if suspended:
                assert isinstance(result, Err)
                assert isinstance(result.error, AccountSuspended)
            else:
                assert isinstance(result, Ok)
                assert result.unwrap() == 100.0

    @given(st.floats(min_value=0.0, max_value=1_000_000.0))
    def test_property_active_account_balance_preserved(self, balance: float):
        account = Account(
            id="test-acc",
            user_id=1,
            balance=balance,
            suspended=False
        )
        result = get_balance(account)
        assert isinstance(result, Ok)
        assert result.unwrap() == balance
