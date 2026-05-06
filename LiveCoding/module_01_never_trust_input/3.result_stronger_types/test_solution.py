
from returns.result import Failure, Success

from solution_stronger_types import (
    AgeOutOfRange,
    EmailMissingAt,
    NameEmpty,
    NameTooLong,
    PayloadError,
    ParsedUserInput,
    parse_user_input,
    parse_user_payload,
    render_error,
)


class TestParseUserPayload:
    def test_valid_payload_returns_success(self):
        result = parse_user_payload(
            {
                "name": "  Alice  ",
                "age": "30",
                "email": "alice@example.com",
            }
        )
        assert isinstance(result, Success)
        user = result.unwrap()

        assert isinstance(user, ParsedUserInput)

        assert user.name.value == "Alice"
        assert user.age.value == 30
        assert user.email.value == "alice@example.com"

    def test_missing_field_returns_payload_error(self):
        result = parse_user_payload({"name": "Alice", "age": 30})
        assert isinstance(result, Failure)
        error = result.failure()
        assert isinstance(error, PayloadError)
        assert error.field == "email"

    def test_non_int_age_returns_payload_error(self):
        result = parse_user_payload(
            {
                "name": "Alice",
                "age": "thirty",
                "email": "alice@example.com",
            }
        )
        assert isinstance(result, Failure)
        error = result.failure()
        assert isinstance(error, PayloadError)
        assert error.field == "age"


class TestParseUserInputDomainRules:
    def test_empty_name_returns_name_empty(self):
        result = parse_user_input(name="", age=30, email="alice@example.com")
        assert isinstance(result, Failure)
        assert isinstance(result.failure(), NameEmpty)

    def test_name_over_100_returns_name_too_long(self):
        result = parse_user_input(name="x" * 101, age=30, email="alice@example.com")
        assert isinstance(result, Failure)
        error = result.failure()
        assert isinstance(error, NameTooLong)
        assert error.length == 101

    def test_negative_age_returns_age_out_of_range(self):
        result = parse_user_input(name="Alice", age=-1, email="alice@example.com")
        assert isinstance(result, Failure)
        assert isinstance(result.failure(), AgeOutOfRange)

    def test_email_without_at_returns_email_missing_at(self):
        result = parse_user_input(name="Alice", age=30, email="not-an-email")
        assert isinstance(result, Failure)
        assert isinstance(result.failure(), EmailMissingAt)

    def test_render_error_formats_typed_error(self):
        result = parse_user_input(name="Alice", age=-1, email="alice@example.com")
        assert isinstance(result, Failure)
        message = render_error(result.failure())
        assert "age must be 0-150" in message


