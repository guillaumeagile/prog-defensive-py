# Part 5 — Railway Oriented Programming (ROP)
# Chain operations with bind — no nested if/else, no try/except pyramids.
# Two tracks: Ok flows forward, Err bypasses everything downstream.

from dataclasses import dataclass
from typing import TypeVar, Generic, Callable

T = TypeVar("T")
E = TypeVar("E")
U = TypeVar("U")


@dataclass(frozen=True)
class Ok(Generic[T]):
    value: T

    def map(self, fn: Callable[[T], U]) -> "Ok[U]":
        return Ok(fn(self.value))

    def bind(self, fn: Callable[[T], "Result[U, E]"]) -> "Result[U, E]":
        return fn(self.value)

    def unwrap(self) -> T:
        return self.value

    def is_ok(self) -> bool:
        return True

    def is_err(self) -> bool:
        return False


@dataclass(frozen=True)
class Err(Generic[E]):
    error: E

    def map(self, fn: Callable[[T], U]) -> "Err[E]":
        return self

    def bind(self, fn: Callable[[T], "Result[U, E]"]) -> "Err[E]":
        return self

    def unwrap(self) -> T:
        raise RuntimeError(f"unwrap() on Err: {self.error}")

    def is_ok(self) -> bool:
        return False

    def is_err(self) -> bool:
        return True


Result = Ok[T] | Err[E]


# Domain model

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


# Typed error dataclasses

@dataclass(frozen=True)
class UserNotFound:
    user_id: int


@dataclass(frozen=True)
class AccountNotFound:
    user_id: int


@dataclass(frozen=True)
class AccountSuspended:
    account_id: str


# Simulated database

class FakeDB:
    def __init__(self):
        self._users: dict[int, User] = {
            1: User(id=1, name="Alice"),
            2: User(id=2, name="Bob"),
            3: User(id=3, name="Charlie"),
        }
        self._accounts: dict[str, Account] = {
            "acc-1": Account(id="acc-1", user_id=1, balance=100.0),
            "acc-2": Account(id="acc-2", user_id=2, balance=50.0, suspended=True),
        }

    def find_user(self, user_id: int) -> User | None:
        return self._users.get(user_id)

    def get_account_for_user(self, user_id: int) -> Account | None:
        for acc in self._accounts.values():
            if acc.user_id == user_id:
                return acc
        return None


db = FakeDB()


# Functions with honest signatures

def get_user(user_id: int) -> Result[User, UserNotFound]:
    user = db.find_user(user_id)
    return Ok(user) if user else Err(UserNotFound(user_id))


def get_account(user: User) -> Result[Account, AccountNotFound]:
    account = db.get_account_for_user(user.id)
    return Ok(account) if account else Err(AccountNotFound(user.id))


def get_balance(account: Account) -> Result[float, AccountSuspended]:
    if account.suspended:
        return Err(AccountSuspended(account.id))
    return Ok(account.balance)


# Railway chains

# WITHOUT Railway — verbose, checks at every step
def get_balance_without_railway(user_id: int) -> Result[float, object]:
    user_result = get_user(user_id)
    if user_result.is_err():
        return user_result

    account_result = get_account(user_result.unwrap())
    if account_result.is_err():
        return account_result

    return get_balance(account_result.unwrap())


# WITH Railway — bind handles the routing
def get_balance_railway(user_id: int) -> Result[float, object]:
    return (
        get_user(user_id)
        .bind(get_account)
        .bind(get_balance)
    )


# Extended pipeline with more steps

@dataclass(frozen=True)
class InsufficientFunds:
    balance: float
    requested: float


def withdraw(amount: float) -> Callable[[float], Result[float, InsufficientFunds]]:
    def _withdraw(balance: float) -> Result[float, InsufficientFunds]:
        if balance < amount:
            return Err(InsufficientFunds(balance=balance, requested=amount))
        return Ok(balance - amount)
    return _withdraw


def process_withdrawal(user_id: int, amount: float) -> Result[float, object]:
    return (
        get_user(user_id)
        .bind(get_account)
        .bind(get_balance)
        .bind(withdraw(amount))
    )


# Error rendering

def render_error(error: object) -> str:
    match error:
        case UserNotFound(user_id=user_id):
            return f"User {user_id} not found"
        case AccountNotFound(user_id=user_id):
            return f"No account for user {user_id}"
        case AccountSuspended(account_id=account_id):
            return f"Account {account_id} is suspended"
        case InsufficientFunds(balance=balance, requested=requested):
            return f"Balance {balance} is less than requested {requested}"
        case _:
            return f"Unknown error: {error}"


# Railway diagram (visualized in code comments):
#
# get_user ──Ok──► get_account ──Ok──► get_balance ──Ok──► withdraw ──Ok──► new_balance
#     │                │                  │                  │
#    Err              Err                Err                Err
#     │                │                  │                  │
#     └────────────────┴──────────────────┴──────────────────┴────────────► error (routes itself)
