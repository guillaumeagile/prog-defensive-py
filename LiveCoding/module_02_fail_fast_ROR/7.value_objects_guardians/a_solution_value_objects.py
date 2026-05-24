"""
Value Objects as Guardians - Making Invalid States Unrepresentable

This demonstrates how value objects can act as guardians by enforcing invariants
at the type level, preventing invalid data from ever being created.
"""

from dataclasses import dataclass
from typing import Union
from returns.result import Result, Failure, Success


class AmountError(Exception):
    """Base class for amount-related errors."""
    pass


class AmountNegative(AmountError):
    """Raised when attempting to create a negative amount."""
    def __init__(self, value: float):
        self.value = value
        super().__init__(f"Amount cannot be negative: {value}")


class AmountZero(AmountError):
    """Raised when attempting to create a zero amount."""
    def __init__(self):
        super().__init__("Amount cannot be zero")


@dataclass(frozen=True)
class Amount:
    """
    Value object that represents a positive monetary amount.
    
    This value object acts as a guardian by ensuring that:
    1. Amount can never be negative
    2. Amount can never be zero (for withdrawal operations)
    3. The value is immutable once created
    
    This uses Pattern 2: Factory Method with Result to avoid putting
    validation logic in the constructor (constructors shouldn't crash).
    """
    _value: float
    
    @property
    def value(self) -> float:
        """Safe access to the underlying value."""
        return self._value
    
    @classmethod
    def create(cls, value: float) -> Result["Amount", AmountError]:
        """
        Factory method that returns a Result instead of raising exceptions.
        This allows for composition with other Result-based operations.
        
        This is Pattern 2: Factory Method with Result (recommended approach).
        It keeps the constructor pure and safe - no validation logic in __post_init__.
        """
        if value < 0:
            return Failure(AmountNegative(value))
        if value == 0:
            return Failure(AmountZero())
        return Success(cls(value))
    
    @classmethod
    def unsafe_create(cls, value: float) -> "Amount":
        """
        Unsafe constructor for internal use when value is pre-validated.
        This is used internally when we know the value is already valid.
        """
        return cls(value)
    
    def __str__(self) -> str:
        return f"${self._value:.2f}"
    
    def __repr__(self) -> str:
        return f"Amount({self._value})"
    
    def __add__(self, other: "Amount") -> "Amount":
        """Amount addition preserves the invariant."""
        # Addition of positive amounts is always positive, so we can use unsafe_create
        return Amount.unsafe_create(self._value + other._value)
    
    def __sub__(self, other: "Amount") -> Result["Amount", AmountError]:
        """Amount subtraction returns Result since it might fail."""
        result = self._value - other._value
        return Amount.create(result)  # Returns Failure if result is negative or zero


# Domain errors
class InsufficientFunds(Exception):
    def __init__(self, requested: Amount, available: Amount):
        self.requested = requested
        self.available = available
        super().__init__(f"Insufficient funds: requested {requested}, available {available}")


class UserNotFound(Exception):
    def __init__(self, user_id: int):
        self.user_id = user_id
        super().__init__(f"User {user_id} not found")


@dataclass
class Account:
    user_id: int
    balance: Amount
    
    def withdraw(self, amount: Amount) -> Result[Amount, AmountError]:
        """
        Withdrawal now works with Amount value objects.
        The negative amount invariant is already guaranteed by Amount.
        Returns Result since subtraction might fail.
        """
        if amount.value > self.balance.value:
            raise InsufficientFunds(amount, self.balance)
        
        # Create new balance through Amount arithmetic
        new_balance_result = self.balance - amount
        return new_balance_result.bind(lambda new_balance: 
            setattr(self, 'balance', new_balance) or Success(new_balance))


# Repository
accounts = {
    1: Account(user_id=1, balance=Amount.unsafe_create(100.0)),
    2: Account(user_id=2, balance=Amount.unsafe_create(50.0)),
}


def find_user(user_id: int) -> Account:
    if user_id not in accounts:
        raise UserNotFound(user_id)
    return accounts[user_id]


def process_withdrawal_flow(user_id: int, amount_value: float) -> Result[Amount, Exception]:
    """
    Withdrawal flow that uses Amount value objects.
    The guard against negative amounts is now handled by the Amount type.
    Uses Pattern 2: Factory Method with Result throughout.
    """
    # Create Amount using factory method - this is where the negative amount guard lives
    amount_result = Amount.create(amount_value)
    if isinstance(amount_result, Failure):
        return amount_result
    
    amount = amount_result.value_or(None)
    
    try:
        # Find user
        account = find_user(user_id)
        
        # Process withdrawal - now returns Result
        withdraw_result = account.withdraw(amount)
        if isinstance(withdraw_result, Failure):
            return withdraw_result
        
        return Success(amount)
        
    except (UserNotFound, InsufficientFunds) as e:
        return Failure(e)


if __name__ == "__main__":
    # Demonstration of the guardian pattern using Pattern 2: Factory Method with Result
    
    print("=== Value Objects as Guardians (Pattern 2: Factory Method) ===")
    
    # Using the factory method with Result - this is the recommended approach
    print("\n=== Factory Method with Result ===")
    
    result_valid = Amount.create(25.0)
    print(f"Valid amount result: {result_valid}")
    
    result_negative = Amount.create(-5.0)
    print(f"Negative amount result: {result_negative}")
    
    result_zero = Amount.create(0.0)
    print(f"Zero amount result: {result_zero}")
    
    # Demonstrate that constructor is now safe (no validation logic)
    print("\n=== Safe Constructor (No Validation Logic) ===")
    
    # Constructor is now safe - it never crashes
    # But we should use factory methods for public API
    print("✅ Constructor is now safe - no validation logic")
    print("✅ Use Amount.create() for public API with validation")
    print("✅ Use Amount.unsafe_create() only for internal validated values")
    
    # Withdrawal flow demonstration
    print("\n=== Withdrawal Flow ===")
    
    # Successful withdrawal
    success = process_withdrawal_flow(1, 30.0)
    print(f"Successful withdrawal: {success}")
    
    # Negative amount - blocked by Amount guardian at factory
    negative_result = process_withdrawal_flow(1, -10.0)
    print(f"Negative amount withdrawal: {negative_result}")
    
    # Zero amount - blocked by Amount guardian at factory
    zero_result = process_withdrawal_flow(1, 0.0)
    print(f"Zero amount withdrawal: {zero_result}")
    
    # User not found
    user_not_found = process_withdrawal_flow(999, 10.0)
    print(f"User not found: {user_not_found}")
    
    # Insufficient funds
    insufficient = process_withdrawal_flow(1, 200.0)
    print(f"Insufficient funds: {insufficient}")
    
    print("\n=== Pattern 2 Benefits ===")
    print("✅ Constructor never crashes - follows best practices")
    print("✅ Validation logic is in factory methods")
    print("✅ Safe object creation with Result type")
    print("✅ Composable with Railway Oriented Programming")
    print("✅ Clear separation of concerns")
