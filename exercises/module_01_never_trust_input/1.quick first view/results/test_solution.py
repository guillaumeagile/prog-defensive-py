from hypothesis import given, strategies as st
from returns.result import Failure, Success

from solution import parse_user_input


class TestParseUserInputName:
    def test_valid_name_is_accepted(self):
        result = parse_user_input(name="Alice", age=30, email="alice@example.com")
        assert isinstance(result, Success)
        assert result.unwrap().name == "Alice"

    def test_empty_name_returns_failure(self):
        result = parse_user_input(name="", age=30, email="alice@example.com")
        assert isinstance(result, Failure)
        assert "name" in result.failure().lower()

    def test_blank_name_returns_failure(self):
        result = parse_user_input(name="   ", age=30, email="alice@example.com")
        assert isinstance(result, Failure)
        assert "name" in result.failure().lower()

    def test_name_is_stripped(self):
        result = parse_user_input(name="  Bob  ", age=30, email="bob@example.com")
        assert isinstance(result, Success)
        assert result.unwrap().name == "Bob"

    def test_name_over_100_chars_returns_failure(self):
        result = parse_user_input(name="x" * 101, age=30, email="x@example.com")
        assert isinstance(result, Failure)
        assert "name" in result.failure().lower()

    @given(st.text(min_size=1, max_size=100).filter(lambda s: s.strip()))
    def test_property_any_non_blank_name_is_accepted(self, name: str):
        result = parse_user_input(name=name, age=25, email="a@b.com")
        assert isinstance(result, Success)
        assert result.unwrap().name == name.strip()


class TestParseUserInputAge:
    def test_valid_age_is_accepted(self):
        result = parse_user_input(name="Alice", age=25, email="alice@example.com")
        assert isinstance(result, Success)
        assert result.unwrap().age == 25

    def test_zero_age_is_accepted(self):
        result = parse_user_input(name="Alice", age=0, email="alice@example.com")
        assert isinstance(result, Success)

    def test_age_150_is_accepted(self):
        result = parse_user_input(name="Alice", age=150, email="alice@example.com")
        assert isinstance(result, Success)

    def test_negative_age_returns_failure(self):
        result = parse_user_input(name="Alice", age=-1, email="alice@example.com")
        assert isinstance(result, Failure)
        assert "age" in result.failure().lower()

    def test_age_over_150_returns_failure(self):
        result = parse_user_input(name="Alice", age=151, email="alice@example.com")
        assert isinstance(result, Failure)
        assert "age" in result.failure().lower()

    @given(st.integers(min_value=0, max_value=150))
    def test_property_valid_age_range_always_accepted(self, age: int):
        result = parse_user_input(name="Alice", age=age, email="a@b.com")
        assert isinstance(result, Success)
        assert result.unwrap().age == age

    @given(st.integers().filter(lambda x: x < 0 or x > 150))
    def test_property_invalid_age_always_fails(self, age: int):
        result = parse_user_input(name="Alice", age=age, email="a@b.com")
        assert isinstance(result, Failure)


class TestParseUserInputEmail:
    def test_valid_email_is_accepted(self):
        result = parse_user_input(name="Alice", age=30, email="alice@example.com")
        assert isinstance(result, Success)
        assert result.unwrap().email == "alice@example.com"

    def test_email_without_at_returns_failure(self):
        result = parse_user_input(name="Alice", age=30, email="notanemail")
        assert isinstance(result, Failure)
        assert "email" in result.failure().lower()

    def test_empty_email_returns_failure(self):
        result = parse_user_input(name="Alice", age=30, email="")
        assert isinstance(result, Failure)
        assert "email" in result.failure().lower()

    @given(st.emails())
    def test_property_valid_emails_always_accepted(self, email: str):
        result = parse_user_input(name="Alice", age=25, email=email)
        assert isinstance(result, Success)
        assert "@" in result.unwrap().email

    @given(st.text().filter(lambda s: "@" not in s and len(s) > 0))
    def test_property_emails_without_at_always_fail(self, email: str):
        result = parse_user_input(name="Alice", age=25, email=email)
        assert isinstance(result, Failure)
