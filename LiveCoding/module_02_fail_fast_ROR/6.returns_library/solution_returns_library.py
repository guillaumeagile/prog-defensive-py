# Part 6 — The `returns` Library
# Production-grade ROP with Success/Failure, flow(), and @safe decorator.
# https://returns.readthedocs.io

from dataclasses import dataclass
from typing import Callable
import json

from returns.result import Result, Success, Failure, safe
from returns.pipeline import flow
from returns.pointfree import bind


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


@dataclass(frozen=True)
class InsufficientFunds:
    balance: float
    requested: float


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


# Functions with honest signatures using returns.Result

def get_user(user_id: int) -> Result[User, UserNotFound]:
    user = db.find_user(user_id)
    return Success(user) if user else Failure(UserNotFound(user_id))


def get_account(user: User) -> Result[Account, AccountNotFound]:
    account = db.get_account_for_user(user.id)
    return Success(account) if account else Failure(AccountNotFound(user.id))


def get_balance(account: Account) -> Result[float, AccountSuspended]:
    if account.suspended:
        return Failure(AccountSuspended(account.id))
    return Success(account.balance)


def withdraw(amount: float) -> Callable[[float], Result[float, InsufficientFunds]]:
    def _withdraw(balance: float) -> Result[float, InsufficientFunds]:
        if balance < amount:
            return Failure(InsufficientFunds(balance=balance, requested=amount))
        return Success(balance - amount)
    return _withdraw


# flow() — the Railway chain without explicit .bind() calls

def get_balance_flow(user_id: int) -> Result[float, object]:
    return flow(
        user_id,
        get_user,
        bind(get_account),
        bind(get_balance),
    )


def process_withdrawal_flow(user_id: int, amount: float) -> Result[float, object]:
    return flow(
        user_id,
        get_user,
        bind(get_account),
        bind(get_balance),
        bind(withdraw(amount)),
    )


# @safe decorator — bridge from exception world to Result world

@safe
def parse_config_json(json_string: str) -> dict:
    """Raises ValueError on invalid JSON — @safe catches it."""
    return json.loads(json_string)


@safe
def divide(a: float, b: float) -> float:
    """Raises ZeroDivisionError — @safe catches it."""
    return a / b


# Combining @safe with flow

def process_config_with_calculation(json_string: str, divisor: float) -> Result[float, Exception]:
    return flow(
        json_string,
        parse_config_json,
        bind(lambda d: Success(d.get("value", 0.0))),
        bind(lambda v: divide(v, divisor)),
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
        case ValueError() as e:
            return f"Invalid input: {e}"
        case ZeroDivisionError():
            return "Cannot divide by zero"
        case _:
            return f"Unknown error: {error}"


# Example usage patterns

def example_match_usage():
    result = get_balance_flow(1)

    match result:
        case Success(success_value=balance):
            print(f"Balance: {balance}")
        case Failure(failure_value=UserNotFound()):
            print("User not found")
        case Failure(failure_value=AccountNotFound()):
            print("Account not found")
        case Failure(failure_value=AccountSuspended()):
            print("Account suspended")


def example_unwrap_or_usage():
    balance = get_balance_flow(1).value_or(0.0)
    return balance


def example_map_usage():
    # Transform success value without leaving Result context
    result = get_balance_flow(1).map(lambda b: b * 1.05)  # Add 5% fee
    return result
