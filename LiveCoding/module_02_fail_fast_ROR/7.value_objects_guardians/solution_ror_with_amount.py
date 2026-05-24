# Part 7 — Railway Oriented Programming + Value Object Guardians
# Production-grade ROP with Success/Failure, flow(), and @safe decorator
# Integrated with Amount value objects as guardians
# https://returns.readthedocs.io

from dataclasses import dataclass
from typing import Callable
import json

from returns.result import Result, Success, Failure, safe
from returns.pipeline import flow
from returns.pointfree import bind

from a_solution_value_objects import Amount, AmountError, AmountNegative, AmountZero


# Domain model

@dataclass(frozen=True)
class User:
    id: int
    name: str


@dataclass(frozen=True)
class Account:
    id: str
    user_id: int
    balance: Amount  # Now using Amount value object instead of float
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
    balance: Amount
    requested: Amount


# Simulated database

class FakeDB:
    def __init__(self):
        self._users: dict[int, User] = {
            1: User(id=1, name="Alice"),
            2: User(id=2, name="Bob"),
            3: User(id=3, name="Charlie"),
        }
        # Initialize database with validated amounts
        balance1 = Amount.create(100.0).unwrap()  # We know this is valid
        balance2 = Amount.create(50.0).unwrap()   # We know this is valid
        self._accounts: dict[str, Account] = {
            "acc-1": Account(id="acc-1", user_id=1, balance=balance1),
            "acc-2": Account(id="acc-2", user_id=2, balance=balance2, suspended=True),
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


def get_balance(account: Account) -> Result[Amount, AccountSuspended]:
    """Now returns Amount instead of float."""
    if account.suspended:
        return Failure(AccountSuspended(account.id))
    return Success(account.balance)


def withdraw(amount: Amount) -> Callable[[Amount], Result[Amount, InsufficientFunds]]:
    """
    Withdrawal function now works with Amount value objects.
    The negative amount invariant is already guaranteed by the Amount type.
    """
    def _withdraw(balance: Amount) -> Result[Amount, InsufficientFunds]:
        # Compare Amount values
        if balance.value < amount.value:
            return Failure(InsufficientFunds(balance=balance, requested=amount))
        
        # Use Amount arithmetic which preserves invariants
        new_balance = balance - amount
        return new_balance
    return _withdraw


# flow() — the Railway chain with Amount value objects

def get_balance_flow(user_id: int) -> Result[Amount, object]:
    """Now returns Amount instead of float."""
    return flow(
        user_id,
        get_user,
        bind(get_account),
        bind(get_balance),
    )


def process_withdrawal_flow(user_id: int, amount: Amount) -> Result[Amount, object]:
    """
    Withdrawal flow that uses Amount value objects as guardians.
    
    By requiring Amount as parameter, this method forces the caller to handle
    the validation of negative amounts before calling this method.
    This is the essence of making illegal states unrepresentable.
    """
    # No validation needed here - Amount guarantees it's valid
    return flow(
        user_id,
        get_user,
        bind(get_account),
        bind(get_balance),
        bind(withdraw(amount)),
    )


def process_withdrawal_flow_from_float(user_id: int, amount_value: float) -> Result[Amount, object]:
    """
    Full railway flow that starts from a primitive float and turns it into an Amount
    before continuing with the rest of the pipeline.

    If the float cannot become a valid Amount, the railway exits immediately.
    """
    return flow(
        amount_value,
        Amount.create,
        bind(lambda amount: process_withdrawal_flow(user_id, amount)),
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




def example_unwrap_or_usage():
    zero_amount = Amount.create(0.0).unwrap()  # We know 0.0 would fail, so use fallback
    balance = get_balance_flow(1).value_or(Amount(0.1))  # Small positive fallback
    return balance


def example_map_usage():
    # Transform success value without leaving Result context
    five_dollars = Amount.create(5.0).unwrap()  # We know this is valid
    result = get_balance_flow(1).map(lambda b: b + five_dollars)  # Add $5.00
    return result


# Demonstration of the integrated pattern

if __name__ == "__main__":
    print("=== Railway Oriented Programming + Value Object Guardians ===")
    print("Making illegal states unrepresentable through type signatures")
    
    # Successful operations
    print("\n--- Successful Operations ---")
    
    balance_result = get_balance_flow(1)
    print(f"Get balance: {balance_result}")
    
    # Caller must handle validation before calling process_withdrawal_flow
    print("\n--- Caller Handles Validation ---")
    
    # Example: Proper usage - caller handles validation
    def safe_withdrawal(user_id: int, amount_value: float) -> Result[Amount, object]:
        """Example of how caller must handle validation."""
        amount_result = Amount.create(amount_value)
        if isinstance(amount_result, Failure):
            return amount_result  # Validation error
        
        # Now we know amount is valid, can safely call the flow
        return process_withdrawal_flow(user_id, amount_result.unwrap())
    
    # Valid amount - works
    withdrawal_result = safe_withdrawal(1, 30.0)
    print(f"Successful withdrawal: {withdrawal_result}")
    
    # Invalid amounts - caught at caller level
    negative_result = safe_withdrawal(1, -10.0)
    print(f"Negative amount blocked: {negative_result}")
    
    zero_result = safe_withdrawal(1, 0.0)
    print(f"Zero amount blocked: {zero_result}")
    
    # Business logic errors still work (these are different from validation errors)
    print("\n--- Business Logic Errors (Different from Validation) ---")
    
    insufficient_result = safe_withdrawal(1, 200.0)
    print(f"Insufficient funds: {insufficient_result}")
    
    user_not_found = safe_withdrawal(999, 10.0)
    print(f"User not found: {user_not_found}")
    
        
    print("\n=== Benefits of Making Illegal States Unrepresentable ===")
    print("✅ Type safety: Amount prevents invalid values at creation")
    print("✅ API clarity: process_withdrawal_flow signature forces valid input")
    print("✅ Caller responsibility: Validation handled at system boundary")
    print("✅ Business clarity: Domain logic separate from validation")
    print("✅ Fail fast: Problems caught immediately at call site")
    print("✅ Compiler helps: Invalid states cannot be compiled through")
