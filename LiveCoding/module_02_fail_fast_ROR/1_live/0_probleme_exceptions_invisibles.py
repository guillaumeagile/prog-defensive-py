# Point de départ du live : des exceptions pour des résultats attendus.
# Les signatures disent « User », « Account », « float ». Elles mentent par omission.
#
# Lancer : python 0_probleme_exceptions_invisibles.py
# Le script plante sur la première exception, avec sa stack : c'est voulu.

from dataclasses import dataclass


@dataclass(frozen=True)
class User:
    id: int
    name: str


@dataclass(frozen=True)
class Account:
    id: str
    user_id: int
    balance: float
    suspended: bool = False


class UserNotFoundError(Exception):
    pass


class AccountNotFoundError(Exception):
    pass


class AccountSuspendedError(Exception):
    pass


USERS = {1: User(1, "Alice"), 2: User(2, "Bob"), 3: User(3, "Charlie")}
ACCOUNTS = {
    1: Account("acc-1", user_id=1, balance=100.0),
    2: Account("acc-2", user_id=2, balance=50.0, suspended=True),
}


def get_user(user_id: int) -> User:
    user = USERS.get(user_id)
    if user is None:
        raise UserNotFoundError(user_id)  # « utilisateur absent » est un résultat normal
    return user


def get_account(user: User) -> Account:
    account = ACCOUNTS.get(user.id)
    if account is None:
        raise AccountNotFoundError(user.id)
    return account


def get_balance(account: Account) -> float:
    if account.suspended:
        raise AccountSuspendedError(account.id)
    return account.balance


def process(user_id: int) -> str:
    # Rien dans la signature ne prévient l'appelant : trois exceptions peuvent sortir.
    user = get_user(user_id)
    account = get_account(user)
    balance = get_balance(account)
    return f"Solde : {balance}"


if __name__ == "__main__":
    print(1, "->", process(1))
    # UserNotFoundError : le script s'arrête ici, avec sa stack.
    # Autres sorties possibles : 2 -> AccountSuspendedError, 3 -> AccountNotFoundError.
    print(999, "->", process(999))
