"""Larger Approach A example: exception-based processing chain.

This file is intentionally exception-heavy to demonstrate the style many teams
start with: each layer raises, wraps, and propagates exceptions upward.
"""

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field, ValidationError, field_validator


class DuplicateEmailError(Exception):
    pass


class NotificationError(Exception):
    pass


class ApiError(Exception):
    status_code = 500


class BadRequestError(ApiError):
    status_code = 400


class ConflictError(ApiError):
    status_code = 409


class ServiceUnavailableError(ApiError):
    status_code = 503


class RegistrationPayload(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    age: int = Field(..., ge=0, le=150)
    email: str = Field(..., min_length=1)

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("name cannot be blank")
        return stripped

    @field_validator("email")
    @classmethod
    def email_must_contain_at(cls, value: str) -> str:
        if "@" not in value:
            raise ValueError("email must contain '@'")
        return value


@dataclass(frozen=True)
class RegisteredUser:
    user_id: str
    name: str
    age: int
    email: str


class UserRepository:
    def __init__(self) -> None:
        self._users_by_email: dict[str, RegisteredUser] = {}

    def save(self, user: RegisteredUser) -> RegisteredUser:
        if user.email in self._users_by_email:
            raise DuplicateEmailError(f"email already exists: {user.email}")
        self._users_by_email[user.email] = user
        return user


class NotificationGateway:
    def __init__(self, flaky_domain: str = "example.fail") -> None:
        self._flaky_domain = flaky_domain

    def send_welcome_email(self, email: str) -> None:
        if email.endswith(f"@{self._flaky_domain}"):
            raise NotificationError(
                f"notification provider timeout for domain {self._flaky_domain}"
            )


class UserRegistrationService:
    def __init__(self, repository: UserRepository, notifications: NotificationGateway) -> None:
        self._repository = repository
        self._notifications = notifications
        self._next_id = 1

    def register_user(self, raw_payload: dict[str, Any]) -> RegisteredUser:
        payload = RegistrationPayload(**raw_payload)

        if payload.email.endswith("@banned.local"):
            raise ValueError("email domain is blocked by policy")

        user = RegisteredUser(
            user_id=self._allocate_user_id(),
            name=payload.name,
            age=payload.age,
            email=payload.email,
        )

        saved = self._repository.save(user)
        self._notifications.send_welcome_email(saved.email)
        return saved

    def _allocate_user_id(self) -> str:
        user_id = f"user-{self._next_id:04d}"
        self._next_id += 1
        return user_id


def create_user_http_endpoint(
    raw_json: dict[str, Any],
    service: UserRegistrationService,
) -> dict[str, Any]:
    try:
        user = service.register_user(raw_json)
        return {
            "status": 201,
            "body": {
                "user_id": user.user_id,
                "email": user.email,
            },
        }
    except ValidationError as exc:
        raise BadRequestError("invalid request payload") from exc
    except ValueError as exc:
        raise BadRequestError(str(exc)) from exc
    except DuplicateEmailError as exc:
        raise ConflictError(str(exc)) from exc
    except NotificationError as exc:
        raise ServiceUnavailableError("notification provider unavailable") from exc


def handle_signup_message(
    message: dict[str, Any],
    service: UserRegistrationService,
) -> dict[str, Any]:
    try:
        payload = message["payload"]
    except KeyError as exc:
        raise BadRequestError("message is missing 'payload'") from exc

    try:
        return create_user_http_endpoint(payload, service)
    except ApiError as exc:
        request_id = str(message.get("request_id", "unknown"))
        raise RuntimeError(f"signup processing failed for request_id={request_id}") from exc
