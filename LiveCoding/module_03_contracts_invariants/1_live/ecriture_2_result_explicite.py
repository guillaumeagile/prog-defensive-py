# Écriture 2 — l'échec devient explicite au site d'appel.
# Le smart constructor et `withdraw` retournent un `Result` : la signature dit la vérité.

from dataclasses import dataclass

from returns.result import Failure, Result, Success


@dataclass(frozen=True)
class PositiveAmount:
    value: float  # privé par convention : créer via PositiveAmount.create()

    @classmethod
    def create(cls, value: float) -> Result[PositiveAmount, str]:
        if value <= 0:
            return Failure(f"amount must be positive, got {value}")
        return Success(cls(value=value))


@dataclass(frozen=True)
class InsufficientFunds:
    requested: float
    available: float


@dataclass
class BankAccount:
    _balance: float = 0.0

    def deposit(self, amount: PositiveAmount) -> None:
        self._balance += amount.value  # réussit toujours avec un PositiveAmount

    def withdraw(self, amount: PositiveAmount) -> Result[None, InsufficientFunds]:
        if amount.value > self._balance:
            return Failure(InsufficientFunds(requested=amount.value, available=self._balance))
        self._balance -= amount.value
        return Success(None)

    @property
    def balance(self) -> float:
        return self._balance


if __name__ == "__main__":
    account = BankAccount()
    match PositiveAmount.create(100.0):
        case Success(amount):
            account.deposit(amount)
        case Failure(error):
            print(error)
    match PositiveAmount.create(500.0):
        case Success(amount):
            match account.withdraw(amount):
                case Success(_):
                    print("retrait accepté")
                case Failure(InsufficientFunds(requested=requested, available=available)):
                    print(f"retrait refusé : {requested} demandé, {available} disponible")
        case Failure(error):
            print(error)
