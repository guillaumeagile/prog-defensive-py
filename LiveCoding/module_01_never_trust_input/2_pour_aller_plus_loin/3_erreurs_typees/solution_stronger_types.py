# Approach D — Result with stronger domain and error types.
# Keep Pydantic at the boundary, then parse into value objects.
# Failures are explicit typed values, not string messages.

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ValidationError
from returns.result import Failure, Result, Success


@dataclass(frozen=True)
class Name:
    value: str


@dataclass(frozen=True)
class Age:
    value: int


@dataclass(frozen=True)
class Email:
    value: str


@dataclass(frozen=True)
class ParsedUserInput:
    name: Name
    age: Age
    email: Email


@dataclass(frozen=True)
class PayloadError:
    field: str
    message: str


@dataclass(frozen=True)
class NameEmpty:
    pass


@dataclass(frozen=True)
class NameBlank:
    raw_name: str


@dataclass(frozen=True)
class NameTooLong:
    length: int
    max_length: int


@dataclass(frozen=True)
class AgeOutOfRange:
    raw_age: int


@dataclass(frozen=True)
class EmailMissingAt:
    raw_email: str


ParseUserError = PayloadError | NameEmpty | NameBlank | NameTooLong | AgeOutOfRange | EmailMissingAt


class _RawUserSchema(BaseModel):
    name: str
    age: int
    email: str


@dataclass(frozen=True)
class _RawUserInput:
    name: str
    age: int
    email: str


def parse_raw_user_input(raw_payload: dict[str, Any]) -> Result[_RawUserInput, ParseUserError]:
    try:
        parsed = _RawUserSchema.model_validate(raw_payload)
        return Success(_RawUserInput(name=parsed.name, age=parsed.age, email=parsed.email))
    except ValidationError as error:
        first = error.errors()[0]
        loc = first["loc"]
        field = str(loc[0]) if loc else "payload"
        message = str(first["msg"])
        return Failure(PayloadError(field=field, message=message))


def parse_name(raw_name: str) -> Result[Name, ParseUserError]:
    if raw_name == "":
        return Failure(NameEmpty())
    stripped = raw_name.strip()
    if len(stripped) > 100:
        return Failure(NameTooLong(length=len(stripped), max_length=100))
    return Success(Name(value=stripped))



def parse_age(raw_age: int) -> Result[Age, ParseUserError]:
    if not (0 <= raw_age <= 150):
        return Failure(AgeOutOfRange(raw_age=raw_age))
    return Success(Age(value=raw_age))


def parse_email(raw_email: str) -> Result[Email, ParseUserError]:
    if "@" not in raw_email:
        return Failure(EmailMissingAt(raw_email=raw_email))
    return Success(Email(value=raw_email))


def parse_user_input(name: str, age: int, email: str) -> Result[ParsedUserInput, ParseUserError]:
    parsed_name_result = parse_name(name)
    if isinstance(parsed_name_result, Failure):
        return Failure(parsed_name_result.failure())
    parsed_name = parsed_name_result.unwrap()

    parsed_age_result = parse_age(age)
    if isinstance(parsed_age_result, Failure):
        return Failure(parsed_age_result.failure())
    parsed_age = parsed_age_result.unwrap()

    parsed_email_result = parse_email(email)
    if isinstance(parsed_email_result, Failure):
        return Failure(parsed_email_result.failure())
    parsed_email = parsed_email_result.unwrap()

    return Success(ParsedUserInput(name=parsed_name, age=parsed_age, email=parsed_email))


def parse_user_payload(raw_payload: dict[str, Any]) -> Result[ParsedUserInput, ParseUserError]:
    parsed_raw_result = parse_raw_user_input(raw_payload)
    if isinstance(parsed_raw_result, Failure):
        return Failure(parsed_raw_result.failure())

    raw = parsed_raw_result.unwrap()
    return parse_user_input(raw.name, raw.age, raw.email)


def render_error(error: ParseUserError) -> str:
    match error:
        case PayloadError(field=field, message=message):
            return f"{field}: {message}"
        case NameEmpty():
            return "name cannot be empty"
        case NameBlank():
            return "name cannot be blank"
        case NameTooLong(length=length, max_length=max_length):
            return f"name too long: {length} chars (max {max_length})"
        case AgeOutOfRange(raw_age=raw_age):
            return f"age must be 0-150, got {raw_age}"
        case EmailMissingAt(raw_email=raw_email):
            return f"email must contain '@': {raw_email!r}"
