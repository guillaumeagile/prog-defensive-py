import pytest
from returns.result import Failure, Success

from ecriture_1_invariant_classique import BankAccount, PositiveAmount, compute_discount


class TestContratDeFonction:
    def test_remise_valide(self):
        assert compute_discount(100.0, 20.0) == Success(80.0)

    def test_prix_negatif_refuse(self):
        assert compute_discount(-1.0, 20.0) == Failure("price must be >= 0")

    @pytest.mark.parametrize("pct", [-1.0, 100.1])
    def test_pourcentage_hors_bornes_refuse(self, pct):
        assert compute_discount(100.0, pct) == Failure("pct must be between 0 and 100")


class TestValueObject:
    @pytest.mark.parametrize("value", [0.0, -5.0])
    def test_montant_non_positif_leve(self, value):
        with pytest.raises(ValueError):
            PositiveAmount(value)


class TestInvariantDeClasse:
    def test_depot_puis_retrait(self):
        account = BankAccount()
        account.deposit(PositiveAmount(100.0))
        account.withdraw(PositiveAmount(30.0))
        assert account.balance == 70.0

    def test_retrait_superieur_au_solde_leve(self):
        account = BankAccount()
        account.deposit(PositiveAmount(10.0))
        with pytest.raises(ValueError, match="insufficient funds"):
            account.withdraw(PositiveAmount(50.0))
        assert account.balance == 10.0

    def test_construction_avec_solde_negatif_leve(self):
        with pytest.raises(ValueError, match="invariant"):
            BankAccount(_balance=-1.0)
