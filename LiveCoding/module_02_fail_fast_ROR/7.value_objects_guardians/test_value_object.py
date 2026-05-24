"""
Tests for Railway Oriented Programming + Value Object Guardians integration.

These tests demonstrate how RoR patterns work seamlessly with Amount value objects
as guardians, providing both type safety and composable error handling.
"""

import pytest

from returns.result import Success, Failure

from solution_ror_with_amount import (
    Amount,
    AmountError,
    AmountNegative,
    AmountZero,
    User,
    Account,
    InsufficientFunds,
    UserNotFound,
    AccountNotFound,
    AccountSuspended,
    get_user,
    get_account,
    get_balance,
    withdraw,
    get_balance_flow,
    process_withdrawal_flow,
    process_withdrawal_flow_from_float,
)


class TestAmountGuardianWithROR:
    """Test Amount value object guardian pattern in RoR context."""
    
    def test_amount_factory_with_result_type(self):
        """Amount.create() returns Result type for RoR composition."""
        # Valid amount
        result = Amount.create(100.0)
        assert isinstance(result, Success)
        assert result.value_or(None).value == 100.0
        
        # Negative amount fails at guardian boundary
        result = Amount.create(-10.0)
        assert isinstance(result, Failure)
        assert isinstance(result.failure(), AmountNegative)
        
        # Zero amount fails at guardian boundary
        result = Amount.create(0.0)
        assert isinstance(result, Failure)
        assert isinstance(result.failure(), AmountZero)
    
    def test_amount_arithmetic_with_result_types(self):
        """Amount arithmetic works with RoR Result types."""
        amount1 = Amount.create(50.0).unwrap()
        amount2 = Amount.create(30.0).unwrap()
        
        # Addition returns Amount directly (always safe)
        sum_amount = amount1 + amount2
        assert sum_amount.value == 80.0
        
        # Subtraction returns Result (might fail)
        result = amount1 - amount2
        assert isinstance(result, Success)
        assert result.value_or(None).value == 20.0
        
        # Subtraction that would fail
        result = amount2 - amount1
        assert isinstance(result, Failure)
        assert isinstance(result.failure(), AmountNegative)


class TestRORFunctionsWithAmount:
    """Test RoR functions integrated with Amount value objects."""
    
    def test_get_balance_returns_amount(self):
        """get_balance now returns Amount instead of float."""
        user = User(id=1, name="Alice")
        account = Account(id="acc-1", user_id=1, balance=Amount.create(100.0).unwrap())
        
        result = get_balance(account)
        assert isinstance(result, Success)
        balance = result.value_or(None)
        assert isinstance(balance, Amount)
        assert balance.value == 100.0
    
    def test_withdraw_with_amount_objects(self):
        """withdraw function works with Amount value objects."""
        withdrawal_amount = Amount.create(30.0).unwrap()
        withdraw_fn = withdraw(withdrawal_amount)
        
        # Successful withdrawal
        balance = Amount.create(100.0).unwrap()
        result = withdraw_fn(balance)
        assert isinstance(result, Success)
        new_balance = result.value_or(None)
        assert new_balance.value == 70.0
        
        # Insufficient funds
        small_balance = Amount.create(20.0).unwrap()
        result = withdraw_fn(small_balance)
        assert isinstance(result, Failure)
        error = result.failure()
        assert isinstance(error, InsufficientFunds)
        assert error.requested.value == 30.0
        assert error.balance.value == 20.0


class TestIntegratedFlows:
    """Test the complete integrated flows."""
    
    def test_get_balance_flow_with_amount(self):
        """get_balance_flow returns Amount objects."""
        result = get_balance_flow(1)
        assert isinstance(result, Success)
        balance = result.value_or(None)
        assert isinstance(balance, Amount)
        assert balance.value == 100.0
    
    def test_process_withdrawal_flow_success(self):
        """Complete withdrawal flow succeeds with valid Amount input."""
        amount = Amount.create(30.0).unwrap()
        result = process_withdrawal_flow(1, amount)
        assert isinstance(result, Success)
        remaining_balance = result.value_or(None)
        assert isinstance(remaining_balance, Amount)
        assert remaining_balance.value == 70.0  # 100 - 30 = 70
    
    def test_process_withdrawal_flow_user_not_found(self):
        """Flow handles user not found (business logic error)."""
        amount = Amount.create(10.0).unwrap()
        result = process_withdrawal_flow(999, amount)
        assert isinstance(result, Failure)
        assert isinstance(result.failure(), UserNotFound)
    
    def test_process_withdrawal_flow_insufficient_funds(self):
        """Flow handles insufficient funds (business logic error)."""
        amount = Amount.create(200.0).unwrap()
        result = process_withdrawal_flow(1, amount)
        assert isinstance(result, Failure)
        assert isinstance(result.failure(), InsufficientFunds)
        error = result.failure()
        assert isinstance(error.requested, Amount)
        assert isinstance(error.balance, Amount)


class TestFullRailwayFromFloat:
    """Test the full chain from float amount to Amount and then into the railway."""

    def test_valid_float_amount_enters_the_railway(self):
        """A valid float is converted to Amount and the railway continues."""
        result = process_withdrawal_flow_from_float(1, 30.0)

        assert isinstance(result, Success)
        remaining_balance = result.value_or(None)
        assert isinstance(remaining_balance, Amount)
        assert remaining_balance.value == 70.0

    def test_negative_float_amount_exits_the_railway_early(self):
        """An invalid float never reaches the rest of the railway."""
        result = process_withdrawal_flow_from_float(1, -10.0)

        assert isinstance(result, Failure)
        assert isinstance(result.failure(), AmountNegative)

    def test_zero_float_amount_exits_the_railway_early(self):
        """Zero is also rejected before any downstream bind happens."""
        result = process_withdrawal_flow_from_float(1, 0.0)

        assert isinstance(result, Failure)
        assert isinstance(result.failure(), AmountZero)





class TestIntegrationBenefits:
    """Test scenarios that demonstrate the benefits of integration."""
    
    def test_type_safety_throughout_flow(self):
        """Amount type safety is maintained throughout the RoR flow."""
        amount = Amount.create(30.0).unwrap()
        result = process_withdrawal_flow(1, amount)
        
        # Every step in the chain works with Amount objects
        assert isinstance(result, Success)
        remaining_balance = result.value_or(None)
        assert isinstance(remaining_balance, Amount)
        assert remaining_balance.value == 70.0  # 100 - 30 = 70
    
    def test_caller_must_handle_validation(self):
        """Caller must handle validation before calling process_withdrawal_flow."""
        # This demonstrates making illegal states unrepresentable
        
        # Caller must handle validation
        def safe_withdrawal(user_id: int, amount_value: float):
            amount_result = Amount.create(amount_value)
            if isinstance(amount_result, Failure):
                return amount_result  # Validation error
            
            # Now we can safely call the flow
            return process_withdrawal_flow(user_id, amount_result.value_or(None))
        
        # Valid amount works
        result = safe_withdrawal(1, 30.0)
        assert isinstance(result, Success)
        
        # Invalid amounts caught at caller level
        negative_result = safe_withdrawal(1, -10.0)
        assert isinstance(negative_result, Failure)
        assert isinstance(negative_result.failure(), AmountNegative)
        
        zero_result = safe_withdrawal(1, 0.0)
        assert isinstance(zero_result, Failure)
        assert isinstance(zero_result.failure(), AmountZero)
    
    def test_business_logic_separation(self):
        """Business logic errors are separate from type validation errors."""
        # Type validation handled by caller
        amount = Amount.create(200.0).unwrap()  # Valid amount for type system
        
        # Business logic error
        insufficient_result = process_withdrawal_flow(1, amount)
        assert isinstance(insufficient_result.failure(), InsufficientFunds)
        
        # Clear separation between type validation and business rules
    
    def test_composable_error_handling(self):
        """RoR composition works seamlessly with Amount guardians."""
        # Can chain operations that might fail at different levels
        amount_result = Amount.create(50.0)
        if isinstance(amount_result, Success):
            amount = amount_result.value_or(None)
            # Continue with RoR flow
            flow_result = get_balance_flow(1)
            assert isinstance(flow_result, Success)
            
            # Can combine Amount objects in RoR context
            balance = flow_result.value_or(None)
            combined = balance + amount
            assert combined.value == 150.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
