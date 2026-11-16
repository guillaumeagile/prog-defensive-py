"""Larger Approach B example: Result-based processing chain.

Same workflow as the exception-heavy chain, but all expected failures are
modeled in the return type and composed explicitly.
"""

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field, ValidationError, field_validator
from returns.pipeline import flow
from returns.pointfree import bind
from returns.result import Failure, Result, Success


@dataclass(frozen=True)
class AppError:
    code: str
    message: str
    status_code: int


def bad_request(message: str) -> AppError:
    return AppError(code="bad_request", message=message, status_code=400)


def conflict(message: str) -> AppError:
    return AppError(code="conflict", message=message, status_code=409)


def service_unavailable(message: str) -> AppError:
    return AppError(code="service_unavailable", message=message, status_code=503)


class RegistrationPayload(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    age: int = Field(..., ge=0, le=150)
    email: str = Field(..., min_length=1)



@dataclass(frozen=True)
class RegisteredUser:
    user_id: str
    name: str
    age: int
    email: str


def parse_registration_payload(raw_payload: dict[str, Any]) -> Result[RegistrationPayload, AppError]:
    try:
        return Success(RegistrationPayload(**raw_payload))
    except ValidationError as error:
        first = error.errors()[0]
        field = str(first["loc"][0])
        message = str(first["msg"])
        return Failure(bad_request(f"{field}: {message}"))


def ensure_allowed_domain(payload: RegistrationPayload) -> Result[RegistrationPayload, AppError]:
    if payload.email.endswith("@banned.local"):
        return Failure(bad_request("email domain is blocked by policy"))
    return Success(payload)


class UserRepository:
    def __init__(self) -> None:
        self._users_by_email: dict[str, RegisteredUser] = {}

    def save(self, user: RegisteredUser) -> Result[RegisteredUser, AppError]:
        if user.email in self._users_by_email:
            return Failure(conflict(f"email already exists: {user.email}"))
        self._users_by_email[user.email] = user
        return Success(user)


class NotificationGateway:
    def __init__(self, flaky_domain: str = "example.fail") -> None:
        self._flaky_domain = flaky_domain

    def send_welcome_email(self, email: str) -> Result[None, AppError]:
        if email.endswith(f"@{self._flaky_domain}"):
            return Failure(
                service_unavailable(
                    f"notification provider timeout for domain {self._flaky_domain}"
                )
            )
        return Success(None)


class UserRegistrationService:
    def __init__(self, repository: UserRepository, notifications: NotificationGateway) -> None:
        self._repository = repository
        self._notifications = notifications
        self._next_id = 1

    def register_user(self, raw_payload: dict[str, Any]) -> Result[RegisteredUser, AppError]:
        return flow(
            parse_registration_payload(raw_payload),
            bind(ensure_allowed_domain),
            bind(self._build_and_save_user),
            bind(self._send_welcome_and_return_user),
        )

    def _build_and_save_user(self, payload: RegistrationPayload) -> Result[RegisteredUser, AppError]:
        user = RegisteredUser(
            user_id=self._allocate_user_id(),
            name=payload.name,
            age=payload.age,
            email=payload.email,
        )
        return self._repository.save(user)

    def _send_welcome_and_return_user(self, user: RegisteredUser) -> Result[RegisteredUser, AppError]:
        return self._notifications.send_welcome_email(user.email).map(lambda _: user)

    def _allocate_user_id(self) -> str:
        user_id = f"user-{self._next_id:04d}"
        self._next_id += 1
        return user_id


def extract_payload_from_message(message: dict[str, Any]) -> Result[dict[str, Any], AppError]:
    payload = message.get("payload")
    if not isinstance(payload, dict):
        return Failure(bad_request("message is missing 'payload'"))
    return Success(payload)


def to_http_response(
    result: Result[RegisteredUser, AppError],
    request_id: str | None = None,
) -> dict[str, Any]:
    match result:
        case Success(user):
            status = 201
            body: dict[str, Any] = {
                "user_id": user.user_id,
                "email": user.email,
            }
        case Failure(error):
            status = error.status_code
            body = {
                "error": error.message,
                "code": error.code,
            }

    if request_id is not None:
        body["request_id"] = request_id

    return {
        "status": status,
        "body": body,
    }


def create_user_http_endpoint(
    raw_json: dict[str, Any],
    service: UserRegistrationService,
) -> dict[str, Any]:
    return to_http_response(service.register_user(raw_json))


def handle_signup_message(
    message: dict[str, Any],
    service: UserRegistrationService,
) -> dict[str, Any]:
    request_id = str(message.get("request_id", "unknown"))
    result = flow(
        extract_payload_from_message(message),
        bind(service.register_user),
    )
    return to_http_response(result, request_id=request_id)
