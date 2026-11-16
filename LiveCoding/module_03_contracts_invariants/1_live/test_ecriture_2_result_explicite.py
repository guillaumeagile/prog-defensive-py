import pytest
from expression import Error, Ok

from ecriture_2_result_explicite import BankAccount, InsufficientFunds, PositiveAmount


class TestSmartConstructor:
    def test_montant_positif(self):
        assert PositiveAmount.create(10.0) == Ok(PositiveAmount(10.0))

    @pytest.mark.parametrize("value", [0.0, -5.0])
    def test_montant_non_positif_retourne_failure(self, value):
        assert PositiveAmount.create(value) == Error(f"amount must be positive, got {value}")


class TestRetraitExplicite:
    def test_retrait_accepte(self):
        account = BankAccount()
        account.deposit(PositiveAmount(100.0))
        assert account.withdraw(PositiveAmount(30.0)) == Ok(None)
        assert account.balance == 70.0

    def test_retrait_refuse_decrit_l_echec_et_ne_modifie_rien(self):
        account = BankAccount()
        account.deposit(PositiveAmount(10.0))
        result = account.withdraw(PositiveAmount(50.0))
        assert result == Error(InsufficientFunds(requested=50.0, available=10.0))
        assert account.balance == 10.0

    def test_composition_par_bind_avec_deux_types_d_erreur(self):
        account = BankAccount()
        account.deposit(PositiveAmount(10.0))
        assert PositiveAmount.create(50.0).bind(account.withdraw) == Error(
            InsufficientFunds(requested=50.0, available=10.0)
        )
        assert PositiveAmount.create(-1.0).bind(account.withdraw) == Error(
            "amount must be positive, got -1.0"
        )
        assert account.balance == 10.0
