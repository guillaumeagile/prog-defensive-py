import pytest
from returns.result import Failure, Success

from ecriture_2_result_explicite import BankAccount, InsufficientFunds, PositiveAmount


class TestSmartConstructor:
    def test_montant_positif(self):
        assert PositiveAmount.create(10.0) == Success(PositiveAmount(10.0))

    @pytest.mark.parametrize("value", [0.0, -5.0])
    def test_montant_non_positif_retourne_failure(self, value):
        assert PositiveAmount.create(value) == Failure(f"amount must be positive, got {value}")


class TestRetraitExplicite:
    def test_retrait_accepte(self):
        account = BankAccount()
        account.deposit(PositiveAmount(100.0))
        assert account.withdraw(PositiveAmount(30.0)) == Success(None)
        assert account.balance == 70.0

    def test_retrait_refuse_decrit_l_echec_et_ne_modifie_rien(self):
        account = BankAccount()
        account.deposit(PositiveAmount(10.0))
        result = account.withdraw(PositiveAmount(50.0))
        assert result == Failure(InsufficientFunds(requested=50.0, available=10.0))
        assert account.balance == 10.0

    def test_montant_invalide_n_atteint_jamais_le_retrait(self):
        account = BankAccount()
        account.deposit(PositiveAmount(10.0))
        assert PositiveAmount.create(-1.0) == Failure("amount must be positive, got -1.0")
        assert account.balance == 10.0
