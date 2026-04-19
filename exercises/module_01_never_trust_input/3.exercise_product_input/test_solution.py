from hypothesis import given, strategies as st
from returns.result import Failure, Success

from solution_product import parse_product_input


class TestParseProductName:
    def test_valid_name_is_accepted(self):
        result = parse_product_input(name="Widget Pro", price=29.99, stock=10, category="electronics")
        assert isinstance(result, Success)
        assert result.unwrap().name == "Widget Pro"

    def test_name_is_stripped(self):
        result = parse_product_input(name="  Widget  ", price=9.99, stock=5, category="food")
        assert isinstance(result, Success)
        assert result.unwrap().name == "Widget"

    def test_empty_name_returns_failure(self):
        result = parse_product_input(name="", price=9.99, stock=5, category="food")
        assert isinstance(result, Failure)
        assert "name" in result.failure().lower()

    def test_blank_name_returns_failure(self):
        result = parse_product_input(name="   ", price=9.99, stock=5, category="food")
        assert isinstance(result, Failure)
        assert "name" in result.failure().lower()

    def test_name_over_200_chars_returns_failure(self):
        result = parse_product_input(name="x" * 201, price=9.99, stock=5, category="food")
        assert isinstance(result, Failure)
        assert "name" in result.failure().lower()


class TestParseProductPrice:
    def test_valid_price_is_accepted(self):
        result = parse_product_input(name="Widget", price=29.99, stock=10, category="electronics")
        assert isinstance(result, Success)
        assert result.unwrap().price == 29.99

    def test_price_as_string_is_coerced(self):
        result = parse_product_input(name="Widget", price="29.99", stock=10, category="electronics")  # type: ignore[arg-type]
        assert isinstance(result, Success)
        assert result.unwrap().price == 29.99

    def test_zero_price_returns_failure(self):
        result = parse_product_input(name="Widget", price=0, stock=10, category="electronics")
        assert isinstance(result, Failure)
        assert "price" in result.failure().lower()

    def test_negative_price_returns_failure(self):
        result = parse_product_input(name="Widget", price=-1.0, stock=10, category="electronics")
        assert isinstance(result, Failure)
        assert "price" in result.failure().lower()

    @given(st.floats(min_value=0.01, max_value=1_000_000, allow_nan=False, allow_infinity=False))
    def test_property_positive_price_always_accepted(self, price: float):
        result = parse_product_input(name="Widget", price=price, stock=0, category="other")
        assert isinstance(result, Success)


class TestParseProductStock:
    def test_zero_stock_is_accepted(self):
        result = parse_product_input(name="Widget", price=9.99, stock=0, category="food")
        assert isinstance(result, Success)
        assert result.unwrap().stock == 0

    def test_positive_stock_is_accepted(self):
        result = parse_product_input(name="Widget", price=9.99, stock=100, category="food")
        assert isinstance(result, Success)

    def test_negative_stock_returns_failure(self):
        result = parse_product_input(name="Widget", price=9.99, stock=-3, category="food")
        assert isinstance(result, Failure)
        assert "stock" in result.failure().lower()

    @given(st.integers(min_value=0))
    def test_property_non_negative_stock_always_accepted(self, stock: int):
        result = parse_product_input(name="Widget", price=1.0, stock=stock, category="other")
        assert isinstance(result, Success)

    @given(st.integers(max_value=-1))
    def test_property_negative_stock_always_fails(self, stock: int):
        result = parse_product_input(name="Widget", price=1.0, stock=stock, category="other")
        assert isinstance(result, Failure)


class TestParseProductCategory:
    def test_valid_lowercase_category_is_accepted(self):
        result = parse_product_input(name="Widget", price=9.99, stock=5, category="electronics")
        assert isinstance(result, Success)
        assert result.unwrap().category == "electronics"

    def test_uppercase_category_is_normalised(self):
        result = parse_product_input(name="T-shirt", price=9.99, stock=5, category="CLOTHING")
        assert isinstance(result, Success)
        assert result.unwrap().category == "clothing"

    def test_mixed_case_category_is_normalised(self):
        result = parse_product_input(name="Bread", price=2.0, stock=10, category="Food")
        assert isinstance(result, Success)
        assert result.unwrap().category == "food"

    def test_invalid_category_returns_failure(self):
        result = parse_product_input(name="Widget", price=9.99, stock=5, category="superadmin")
        assert isinstance(result, Failure)
        assert "category" in result.failure().lower()

    @given(st.sampled_from(["electronics", "clothing", "food", "other",
                            "ELECTRONICS", "CLOTHING", "FOOD", "OTHER"]))
    def test_property_all_valid_categories_accepted(self, category: str):
        result = parse_product_input(name="Widget", price=1.0, stock=0, category=category)
        assert isinstance(result, Success)
        assert result.unwrap().category == category.lower()


class TestParseProductDescription:
    def test_valid_description_is_accepted(self):
        result = parse_product_input(name="Widget", price=9.99, stock=5,
                                     category="electronics", description="A great widget")
        assert isinstance(result, Success)
        assert result.unwrap().description == "A great widget"

    def test_description_is_stripped(self):
        result = parse_product_input(name="Widget", price=9.99, stock=5,
                                     category="electronics", description="  nice  ")
        assert isinstance(result, Success)
        assert result.unwrap().description == "nice"

    def test_blank_description_becomes_none(self):
        result = parse_product_input(name="Widget", price=9.99, stock=5,
                                     category="electronics", description="   ")
        assert isinstance(result, Success)
        assert result.unwrap().description is None

    def test_absent_description_is_none(self):
        result = parse_product_input(name="Widget", price=9.99, stock=5, category="electronics")
        assert isinstance(result, Success)
        assert result.unwrap().description is None
