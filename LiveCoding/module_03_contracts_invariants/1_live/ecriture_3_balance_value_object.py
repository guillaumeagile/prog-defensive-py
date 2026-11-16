# Écriture 3 — design FP presque pur : le solde devient un Value Object.
# BankAccount ne manipule plus aucun float et ne lit jamais l'intérieur d'un Value Object.

from dataclasses import dataclass, field

from returns.result import Failure, Result, Success


@dataclass(frozen=True)
class PositiveAmount:
    _value: float  # privé par convention : seul ce module le lit

    @classmethod
    def create(cls, value: float) -> Result[PositiveAmount, str]:
        if value <= 0:
            return Failure(f"amount must be positive, got {value}")
        return Success(cls(value))


@dataclass(frozen=True)
class InsufficientFunds:
    requested: PositiveAmount  # des Value Objects, plus de float
    available: Balance


@dataclass(frozen=True)
class Balance:
    _value: float = 0.0  # privé par convention : seul ce module le lit

    def has_enough_funds(self, amount: PositiveAmount) -> bool:
        return amount._value <= self._value

    def after_deposit(self, amount: PositiveAmount) -> Balance:
        return Balance(self._value + amount._value)  # total : un dépôt réussit toujours

    def after_withdraw(self, amount: PositiveAmount) -> Result[Balance, InsufficientFunds]:
        if not self.has_enough_funds(amount):
            return Failure(InsufficientFunds(requested=amount, available=self))
        return Success(Balance(self._value - amount._value))


@dataclass
class BankAccount:
    _balance: Balance = field(default_factory=Balance)

    def deposit(self, amount: PositiveAmount) -> None:
        self._balance = self._balance.after_deposit(amount)

    def withdraw(self, amount: PositiveAmount) -> Result[None, InsufficientFunds]:
        return self._balance.after_withdraw(amount).map(self._replace_balance)

    def _replace_balance(self, new_balance: Balance) -> None:
        self._balance = new_balance

    @property
    def balance(self) -> Balance:
        return self._balance


if __name__ == "__main__":
    account = BankAccount()
    PositiveAmount.create(100.0).map(account.deposit)
    PositiveAmount.create(30.0).bind(account.withdraw)
    print("solde :", account.balance)
    print("retrait de 500 :", PositiveAmount.create(500.0).bind(account.withdraw))
