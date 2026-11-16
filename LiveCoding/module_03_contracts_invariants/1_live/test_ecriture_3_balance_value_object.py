from returns.result import Failure, Success

from ecriture_3_balance_value_object import (
    Balance,
    BankAccount,
    InsufficientFunds,
    PositiveAmount,
)


def amount(value: float) -> PositiveAmount:
    return PositiveAmount.create(value).unwrap()


class TestBalance:
    def test_has_enough_funds(self):
        assert Balance(100.0).has_enough_funds(amount(100.0))
        assert not Balance(100.0).has_enough_funds(amount(100.1))

    def test_after_deposit_retourne_un_nouveau_solde(self):
        before = Balance(10.0)
        after = before.after_deposit(amount(5.0))
        assert after == Balance(15.0)
        assert before == Balance(10.0)

    def test_after_withdraw_succes(self):
        assert Balance(100.0).after_withdraw(amount(30.0)) == Success(Balance(70.0))

    def test_after_withdraw_refuse_ne_fabrique_jamais_de_solde_negatif(self):
        balance = Balance(10.0)
        assert balance.after_withdraw(amount(50.0)) == Failure(
            InsufficientFunds(requested=amount(50.0), available=balance)
        )

    def test_retraits_enchaines(self):
        result = (
            Balance(100.0)
            .after_withdraw(amount(30.0))
            .bind(lambda balance: balance.after_withdraw(amount(30.0)))
        )
        assert result == Success(Balance(40.0))

    def test_enchainement_s_arrete_au_premier_echec(self):
        result = (
            Balance(50.0)
            .after_withdraw(amount(60.0))
            .bind(lambda balance: balance.after_withdraw(amount(1.0)))
        )
        assert isinstance(result.failure(), InsufficientFunds)


class TestBankAccount:
    def test_depot_et_retrait(self):
        account = BankAccount()
        account.deposit(amount(100.0))
        assert account.withdraw(amount(30.0)) == Success(None)
        assert account.balance == Balance(70.0)

    def test_retrait_refuse_laisse_le_solde_intact(self):
        account = BankAccount()
        account.deposit(amount(10.0))
        result = account.withdraw(amount(50.0))
        assert isinstance(result.failure(), InsufficientFunds)
        assert account.balance == Balance(10.0)
