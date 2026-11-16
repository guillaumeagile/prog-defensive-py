# Écriture 2 — l'échec devient explicite au site d'appel.
# Le smart constructor et `withdraw` retournent un `Result` : la signature dit la vérité.

from dataclasses import dataclass

from expression import Error, Ok, Result


@dataclass(frozen=True)
class PositiveAmount:
    value: float  # privé par convention : créer via PositiveAmount.create()

    @classmethod
    def create(cls, value: float) -> Result[PositiveAmount, str]:
        if value <= 0:
            return Error(f"amount must be positive, got {value}")
        return Ok(cls(value=value))


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
            return Error(InsufficientFunds(requested=amount.value, available=self._balance))
        self._balance -= amount.value
        return Ok(None)

    @property
    def balance(self) -> float:
        return self._balance


if __name__ == "__main__":
    account = BankAccount()
    PositiveAmount.create(100.0).map(account.deposit)
    # bind enchaîne deux erreurs de types différents : str (montant) puis InsufficientFunds (solde)
    match PositiveAmount.create(500.0).bind(account.withdraw):
        case Ok():
            print("retrait accepté")
        case Error(error=InsufficientFunds(requested=requested, available=available)):
            print(f"retrait refusé : {requested} demandé, {available} disponible")
        case Error(error=message):
            print(message)
