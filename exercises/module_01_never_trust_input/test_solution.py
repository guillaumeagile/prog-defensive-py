import pytest
from hypothesis import given, strategies as st
from pydantic import ValidationError

from solution import UserInput  # noqa: does not exist yet — tests fail first


class TestUserInputName:
    def test_valid_name_is_accepted(self):
        user = UserInput(name="Alice", age=30, email="alice@example.com")
        assert user.name == "Alice"

    def test_empty_name_raises(self):
        with pytest.raises(ValidationError):
            UserInput(name="", age=30, email="alice@example.com")

    def test_blank_name_raises(self):
        with pytest.raises(ValidationError):
            UserInput(name="   ", age=30, email="alice@example.com")

    def test_name_is_stripped(self):
        user = UserInput(name="  Bob  ", age=30, email="bob@example.com")
        assert user.name == "Bob"

    def test_name_over_100_chars_raises(self):
        with pytest.raises(ValidationError):
            UserInput(name="x" * 101, age=30, email="x@example.com")

    @given(st.text(min_size=1, max_size=100).filter(lambda s: s.strip()))
    def test_property_any_non_blank_name_is_accepted(self, name: str):
        user = UserInput(name=name, age=25, email="a@b.com")
        assert user.name == name.strip()


class TestUserInputAge:
    def test_valid_age_is_accepted(self):
        user = UserInput(name="Alice", age=25, email="alice@example.com")
        assert user.age == 25

    def test_zero_age_is_accepted(self):
        user = UserInput(name="Alice", age=0, email="alice@example.com")
        assert user.age == 0

    def test_age_150_is_accepted(self):
        user = UserInput(name="Alice", age=150, email="alice@example.com")
        assert user.age == 150

    def test_negative_age_raises(self):
        with pytest.raises(ValidationError):
            UserInput(name="Alice", age=-1, email="alice@example.com")

    def test_age_over_150_raises(self):
        with pytest.raises(ValidationError):
            UserInput(name="Alice", age=151, email="alice@example.com")

    @given(st.integers(min_value=0, max_value=150))
    def test_property_valid_age_range_always_accepted(self, age: int):
        user = UserInput(name="Alice", age=age, email="a@b.com")
        assert user.age == age

    @given(st.integers().filter(lambda x: x < 0 or x > 150))
    def test_property_invalid_age_always_raises(self, age: int):
        with pytest.raises(ValidationError):
            UserInput(name="Alice", age=age, email="a@b.com")


class TestUserInputEmail:
    def test_valid_email_is_accepted(self):
        user = UserInput(name="Alice", age=30, email="alice@example.com")
        assert user.email == "alice@example.com"

    def test_email_without_at_raises(self):
        with pytest.raises(ValidationError):
            UserInput(name="Alice", age=30, email="notanemail")

    def test_empty_email_raises(self):
        with pytest.raises(ValidationError):
            UserInput(name="Alice", age=30, email="")

    @given(st.emails())
    def test_property_valid_emails_always_accepted(self, email: str):
        user = UserInput(name="Alice", age=25, email=email)
        assert "@" in user.email

    @given(st.text().filter(lambda s: "@" not in s and len(s) > 0))
    def test_property_emails_without_at_always_raise(self, email: str):
        with pytest.raises(ValidationError):
            UserInput(name="Alice", age=25, email=email)
