from hypothesis import given, strategies as st
from returns.result import Failure, Success

from solution_stronger_types import (
    AgeOutOfRange,
    EmailMissingAt,
    NameBlank,
    ParsedUserInput,
    parse_user_input,
)


class TestParseUserInputPBT:
    @given(st.text(min_size=1, max_size=100).filter(lambda s: s.strip()))
    def test_property_valid_non_blank_name_succeeds(self, name: str):
        result = parse_user_input(name=name, age=25, email="a@b.com")
        assert isinstance(result, Success)
        parsed_user = result.unwrap()
        assert isinstance(parsed_user, ParsedUserInput)
        assert parsed_user.name.value == name.strip()

    @given(st.integers().filter(lambda x: x < 0 or x > 150))
    def test_property_out_of_range_age_returns_typed_failure(self, age: int):
        result = parse_user_input(name="Alice", age=age, email="a@b.com")
        assert isinstance(result, Failure)
        assert isinstance(result.failure(), AgeOutOfRange)

    @given(st.text().filter(lambda s: "@" not in s and len(s) > 0))
    def test_property_email_without_at_returns_typed_failure(self, email: str):
        result = parse_user_input(name="Alice", age=25, email=email)
        assert isinstance(result, Failure)
        assert isinstance(result.failure(), EmailMissingAt)

    @given(st.text(max_size=150))
    def test_property_success_name_is_always_trusted(self, name: str):
        result = parse_user_input(name=name, age=25, email="a@b.com")
        if isinstance(result, Success):
            parsed_name = result.unwrap().name.value
            assert parsed_name == parsed_name.strip()
            assert parsed_name != ""

    # @given(
    #     st.text(alphabet=" \t\n\r\f\v", min_size=1, max_size=30)
    #     .filter(lambda s: s != "")
    # )
    # def test_property_whitespace_only_name_is_rejected_as_blank(self, name: str):
    #     result = parse_user_input(name=name, age=25, email="a@b.com")
    #     assert isinstance(result, Failure)
    #     assert isinstance(result.failure(), NameBlank)