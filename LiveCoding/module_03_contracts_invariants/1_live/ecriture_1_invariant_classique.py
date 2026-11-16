# Écriture 1 — invariant de classe traditionnel.
# Objet mutable, `raise` pour toute violation. C'est la forme que l'audience connaît.

from dataclasses import dataclass

from returns.result import Failure, Result, Success


# Contrat de fonction : guard clauses + postcondition explicite

def compute_discount(price: float, pct: float) -> Result[float, str]:
    if price < 0:
        return Failure("price must be >= 0")
    if not (0 <= pct <= 100):
        return Failure("pct must be between 0 and 100")
    return Success(price * (1 - pct / 100))


# Value Object : la règle d'une seule valeur vit dans le constructeur

@dataclass(frozen=True)
class PositiveAmount:
    value: float

    def __post_init__(self) -> None:
        if self.value <= 0:
            raise ValueError("amount must be positive")


# Invariant de classe : vérifié après la construction et après chaque mutation

@dataclass
class BankAccount:
    _balance: float = 0.0

    def __post_init__(self) -> None:
        self._ensure_invariant()

    def _ensure_invariant(self) -> None:
        if self._balance < 0:
            raise ValueError("invariant: balance cannot be negative")

    def deposit(self, amount: PositiveAmount) -> None:
        self._balance += amount.value
        self._ensure_invariant()

    def withdraw(self, amount: PositiveAmount) -> None:
        if amount.value > self._balance:
            raise ValueError("insufficient funds")
        self._balance -= amount.value
        self._ensure_invariant()

    @property
    def balance(self) -> float:
        return self._balance


if __name__ == "__main__":
    account = BankAccount()
    account.deposit(PositiveAmount(100.0))
    account.withdraw(PositiveAmount(30.0))
    print("solde :", account.balance)
    try:
        account.withdraw(PositiveAmount(500.0))
    except ValueError as error:
        print("retrait refusé :", error)
