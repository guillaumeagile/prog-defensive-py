# Module 02 — Part 5 Conclusion: Railway Oriented Programming

## What is ROP?

Railway Oriented Programming (coined by Scott Wlaschin for F#) models operations as two tracks:

```
get_user ──Ok──► get_account ──Ok──► get_balance ──Ok──► float
    │                │                  │
   Err              Err                Err
    │                │                  │
    └────────────────┴──────────────────┴──► error (routes itself)
```

- **Ok track**: Happy path, values flow forward through `bind`
- **Err track**: Errors bypass all downstream operations automatically

## The bind operation

```python
# Ok.bind(fn) calls fn with the value, continues the chain
# Err.bind(fn) returns self, short-circuiting the chain

def get_balance_railway(user_id: int) -> Result[float, object]:
    return (
        get_user(user_id)      # Result[User, UserNotFound]
        .bind(get_account)     # Result[Account, AccountNotFound | UserNotFound]
        .bind(get_balance)    # Result[float, AccountSuspended | ...]
    )  # Three lines, flat, no nesting
```

## Comparison

### Without Railway (nested checks):
```python
def process(user_id: int) -> Result[float, object]:
    user_result = get_user(user_id)
    if user_result.is_err():
        return user_result

    account_result = get_account(user_result.unwrap())
    if account_result.is_err():
        return account_result

    return get_balance(account_result.unwrap())
```

### With Railway:
```python
def process(user_id: int) -> Result[float, object]:
    return (
        get_user(user_id)
        .bind(get_account)
        .bind(get_balance)
    )
```

## Why ROP wins

| Aspect | Without ROP | With ROP |
|--------|-------------|----------|
| Lines of code | 8 | 4 |
| Indentation levels | 2 | 0 |
| Error handling | Explicit at each step | Automatic via bind |
| Readability | Happy path buried | Happy path is the code |

## Currying for multi-arg functions

Python doesn't auto-curry, so we use closures:

```python
def withdraw(amount: float) -> Callable[[float], Result[float, InsufficientFunds]]:
    def _withdraw(balance: float) -> Result[float, InsufficientFunds]:
        if balance < amount:
            return Err(InsufficientFunds(balance, amount))
        return Ok(balance - amount)
    return _withdraw

# Usage in chain
.bind(withdraw(50.0))  # returns a function expecting balance
```

## Pattern matching the result

```python
match process(42):
    case Ok(value=balance):              print(f"Balance: {balance}")
    case Err(error=UserNotFound()):      print("User not found")
    case Err(error=AccountNotFound()):   print("Account not found")
    case Err(error=AccountSuspended()):  print("Account suspended")
```

## Static checking

```bash
poetry run pyright --project pyright.railway.json
poetry run mypy --config-file mypy.railway.ini
```

## Next: Part 6

Part 6 replaces our hand-rolled `Result` with the production-grade `returns` library, adding:
- `@safe` decorator for exception-wrapping
- `flow()` and `pipe()` for cleaner chains
- `partial()` and `curry()` for ergonomics
