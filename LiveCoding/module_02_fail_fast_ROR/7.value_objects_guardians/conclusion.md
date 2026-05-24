# Part 7: Value Objects as Guardians

## Making Invalid States Unrepresentable

This part demonstrates how **value objects** can act as **guardians** by enforcing invariants at the type level. This is a powerful form of defensive programming that prevents invalid data from ever being created.

## The Guardian Pattern

### Traditional Approach (Problematic)
```python
def withdraw(account, amount):
    if amount < 0:
        raise ValueError("Amount cannot be negative")
    if amount > account.balance:
        raise ValueError("Insufficient funds")
    # ... business logic
```

**Issues:**
- Validation happens in business logic
- Invalid data can propagate through the system
- Same validation must be repeated everywhere
- Errors are discovered late in execution

### Guardian Approach (Value Objects)
```python
@dataclass(frozen=True)
class Amount:
    _value: float
    
    def __post_init__(self):
        if self._value < 0:
            raise AmountNegative(self._value)
        if self._value == 0:
            raise AmountZero()
```

**Benefits:**
- Validation happens at object creation
- Invalid states are unrepresentable
- Single source of truth for validation
- Errors are discovered immediately

## Key Concepts

### 1. **Value Objects as Guardians**
- Value objects encapsulate validation logic
- They enforce business invariants at the type level
- Once created, the object is guaranteed to be valid

### 2. **Fail Fast at Creation Time**
```python
# This fails immediately - the negative amount never enters the system
amount = Amount(-10.0)  # Raises AmountNegative

# vs traditional approach where -10.0 could propagate through business logic
# before being caught deep in some validation
```

### 3. **Immutable Guarantees**
- Frozen dataclasses prevent state mutation
- Once valid, always valid
- Thread-safe by design

### 4. **Composable Safety**
```python
def process_withdrawal(user_id: int, amount_value: float) -> Result[Amount, Exception]:
    # The guard against negative amounts is here - at the boundary
    amount = Amount.create(amount_value)._unwrap()
    
    # Business logic can assume amount is always valid
    account = find_user(user_id)
    account.withdraw(amount)  # No need to check amount >= 0 here
```

## Implementation Patterns

### Pattern 1: Constructor Guard (⚠️ Breaks Constructor Rules)

```python
@dataclass(frozen=True)
class Amount:
    _value: float
    
    def __post_init__(self):
        if self._value < 0:
            raise AmountNegative(self._value)
```

**⚠️ Problem:** This pattern breaks important constructor rules:
- **Constructors should not contain business logic** - Validation logic belongs elsewhere
- **Constructors should not crash** - Object creation should be safe and predictable
- **Makes object creation unsafe** - `Amount(-10.0)` will raise an exception
- **Violates fail-fast principles** - Errors happen during object construction, not at system boundaries

### Pattern 2: Factory Method with Result (✅ Recommended)

```python
@dataclass(frozen=True)
class Amount:
    _value: float
    
    @classmethod
    def create(cls, value: float) -> Result["Amount", AmountError]:
        """Factory method that returns Result instead of raising exceptions."""
        if value < 0:
            return Failure(AmountNegative(value))
        if value == 0:
            return Failure(AmountZero())
        return Success(cls(value))
```

**✅ Benefits:**
- **Constructor remains pure** - No validation logic in `__post_init__`
- **Safe object creation** - Never raises exceptions
- **Explicit error handling** - Returns Result type for composition
- **Follows fail-fast principles** - Validation at system boundary
- **Composable** - Works seamlessly with Railway Oriented Programming

### Pattern 3: Private Constructor + Factory (Most Robust)

```python
@dataclass(frozen=True)
class Amount:
    _value: float
    
    def __init__(self, value: float):
        # Private constructor - only called by factory methods
        object.__setattr__(self, '_value', value)
    
    @classmethod
    def create(cls, value: float) -> Result["Amount", AmountError]:
        """Public factory method with validation."""
        if value < 0:
            return Failure(AmountNegative(value))
        if value == 0:
            return Failure(AmountZero())
        return Success(cls(value))
    
    @classmethod
    def unsafe_create(cls, value: float) -> "Amount":
        """Unsafe constructor for internal use when value is pre-validated."""
        return cls(value)
```

**✅ Most Robust:**
- **Enforces factory usage** - Private constructor prevents direct instantiation
- **Clear separation** - Validation in factory, construction in constructor
- **Internal optimization** - `unsafe_create` for validated values
- **Type safety** - Impossible to create invalid Amount objects

### Pattern 3: Safe Arithmetic Operations
```python
def __add__(self, other: "Amount") -> "Amount":
    return Amount(self._value + other._value)  # Preserves invariant

def __sub__(self, other: "Amount") -> "Amount":
    result = self._value - other._value
    return Amount(result)  # Will raise if result is negative
```

## Benefits of Guardian Value Objects

### 1. **Elimination of Defensive Checks**
```python
# Before: Every function needs validation
def transfer(from_account, to_account, amount):
    if amount < 0:
        raise ValueError("Invalid amount")
    # ... more validation
    # ... business logic

# After: Validation is guaranteed by the type
def transfer(from_account, to_account, amount: Amount):
    # amount is guaranteed to be valid - no validation needed
    # ... business logic only
```

### 2. **Clear Error Location**
- When validation fails, it's immediately clear where
- No need to trace through business logic to find validation failures
- Errors are caught at the system boundary

### 3. **Consistent Enforcement**
- Same rules apply everywhere the value object is used
- No possibility of "forgetting" validation in some code path
- Single source of truth for business rules

### 4. **Self-Documenting Code**
```python
def process_payment(amount: Amount) -> Receipt:
    # Function signature clearly indicates validated amount
    # No need for additional validation comments
```

## When to Use Guardian Value Objects

### ✅ Good Candidates:
- **Numeric constraints** (positive numbers, ranges)
- **String formats** (emails, phone numbers, identifiers)
- **Business rules** (age limits, minimum amounts)
- **State machines** (status transitions)
- **Composite invariants** (start < end dates)

### ❌ Poor Candidates:
- Simple primitives without business rules
- Highly mutable data
- Performance-critical paths where object creation overhead matters
- Data that is inherently unvalidated (raw user input)

## Integration with Other Patterns

### With Railway Oriented Programming
```python
def process_withdrawal(user_id: int, amount_value: float) -> Result[Amount, Exception]:
    return (
        Amount.create(amount_value)
        .bind(lambda amount: find_user_result(user_id).bind(lambda user: 
            withdraw_from_account(user, amount)))
    )
```

### With Dependency Injection
```python
# Value objects can be injected as dependencies
class PaymentService:
    def __init__(self, minimum_payment: Amount):
        self.minimum_payment = minimum_payment
```

## Testing Guardian Value Objects

### Test the Invariants
```python
def test_negative_amount_raises_exception():
    with pytest.raises(AmountNegative):
        Amount(-10.0)

def test_zero_amount_raises_exception():
    with pytest.raises(AmountZero):
        Amount(0.0)
```

### Test the Factory Method
```python
def test_factory_returns_result():
    assert isinstance(Amount.create(10.0), Success)
    assert isinstance(Amount.create(-10.0), Failure)
```

### Test Business Logic Assumes Validity
```python
def test_business_logic_needs_no_validation():
    # Given a valid Amount, business logic should work without additional checks
    amount = Amount(50.0)
    account = Account(1, Amount(100.0))
    
    # No validation needed - amount is guaranteed valid
    account.withdraw(amount)
    assert account.balance.value == 50.0
```

## Comparison with Other Approaches

| Approach | Validation Location | Error Discovery | Code Duplication |
|----------|-------------------|-----------------|------------------|
| Manual Checks | Business Logic | Late | High |
| Decorators | Function Boundary | Early | Medium |
| Value Objects | Type Construction | Immediate | None |

## Conclusion

Value objects as guardians provide the strongest form of defensive programming:

1. **Make invalid states unrepresentable** - If it compiles, it's valid
2. **Fail immediately** - Problems caught at object creation
3. **Eliminate defensive code** - Business logic assumes validity
4. **Single source of truth** - Validation logic in one place
5. **Self-documenting** - Types communicate constraints

This approach represents the pinnacle of defensive programming: **preventing problems rather than detecting them**. By encoding business invariants into the type system, we create code that is safer, clearer, and more maintainable.

The guardian pattern is particularly powerful when combined with other defensive programming techniques like Railway Oriented Programming, creating a robust system where failures are handled explicitly and invalid states are impossible.
