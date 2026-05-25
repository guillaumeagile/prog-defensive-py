"""
DIRTY EXAMPLE — Exception cascade in a registration flow.

Purpose: illustrate WHY exception-based defensive programming is noisy.
  1. Every layer must know which exception types live below it.
  2. Adding a new exception in a low-level class silently breaks any caller
     that does not update its except clause.
  3. Tests are full of pytest.raises() boilerplate.
  4. A fake repository that throws an unexpected exception exposes how
     fragile the whole thing is — one missed except and the crash bubbles
     to the top.

Run the demos at the bottom with:
    python dirty_registration_with_exceptions.py
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field, ValidationError, field_validator

# ---------------------------------------------------------------------------
# Domain exceptions — one per bad thing that can happen
# (already getting noisy before we wrote a single line of business logic)
# ---------------------------------------------------------------------------

class DuplicateEmailError(Exception):
    """Raised by the repository when the e-mail already exists."""

class BannedDomainError(Exception):
    """Raised by the service when the e-mail domain is blacklisted."""

class NotificationError(Exception):
    """Raised by the notification gateway when the provider is down."""

class DatabaseConnectionError(Exception):
    """Raised by the repository when the DB is unreachable."""
    # ⚠️  ADDED LATER by the DB team — every existing caller forgets to catch this

class DatabaseTimeoutError(DatabaseConnectionError):
    """Raised when a query exceeds its timeout budget."""
    # ⚠️  Another late addition — subclass callers also miss

# ---------------------------------------------------------------------------
# Input validation model
# ---------------------------------------------------------------------------

class UserInput(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    age: int = Field(..., ge=0, le=150)
    email: str = Field(..., min_length=1)

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("name cannot be blank")
        return stripped

    @field_validator("email")
    @classmethod
    def email_has_at(cls, v: str) -> str:
        if "@" not in v:
            raise ValueError("email must contain '@'")
        return v


@dataclass(frozen=True)
class RegisteredUser:
    user_id: str
    name: str
    age: int
    email: str


# ---------------------------------------------------------------------------
# Repository — two flavours: well-behaved and FLAKY
# ---------------------------------------------------------------------------

class InMemoryUserRepository:
    """Works fine in unit tests, never touches the network."""

    def __init__(self) -> None:
        self._store: dict[str, RegisteredUser] = {}

    def save(self, user: RegisteredUser) -> RegisteredUser:
        if user.email in self._store:
            raise DuplicateEmailError(f"already registered: {user.email}")
        self._store[user.email] = user
        return user


class FlakyDbUserRepository:
    """
    Simulates a real database driver.
    It raises DatabaseConnectionError and DatabaseTimeoutError —
    exceptions the service layer never anticipated when it was first written.
    """

    def __init__(self, *, fail_with: type[Exception] | None = None) -> None:
        self._fail_with = fail_with
        self._store: dict[str, RegisteredUser] = {}

    def save(self, user: RegisteredUser) -> RegisteredUser:
        if self._fail_with is not None:
            raise self._fail_with("db says no")
        if user.email in self._store:
            raise DuplicateEmailError(f"already registered: {user.email}")
        self._store[user.email] = user
        return user


# ---------------------------------------------------------------------------
# Notification gateway
# ---------------------------------------------------------------------------

class NotificationGateway:
    def __init__(self, *, flaky_domain: str = "flaky.io") -> None:
        self._flaky_domain = flaky_domain

    def send_welcome(self, email: str) -> None:
        if email.endswith(f"@{self._flaky_domain}"):
            raise NotificationError(f"provider timeout for {self._flaky_domain}")


# ---------------------------------------------------------------------------
# Service — the layer that must catch EVERYTHING below it
# Notice how the except list grows every time a new exception is introduced
# ---------------------------------------------------------------------------

class UserRegistrationService:
    def __init__(
        self,
        repository: InMemoryUserRepository | FlakyDbUserRepository,
        notifications: NotificationGateway,
    ) -> None:
        self._repo = repository
        self._notif = notifications

    def register(self, raw: dict[str, Any]) -> RegisteredUser:
        # Layer 1 — input validation (ValidationError from pydantic)
        try:
            payload = UserInput(**raw)
        except ValidationError as exc:
            raise ValueError(f"invalid input: {exc}") from exc

        # Layer 2 — business rule (raises plain ValueError)
        if payload.email.endswith("@banned.local"):
            raise BannedDomainError("email domain is banned")

        user = RegisteredUser(
            user_id=str(uuid.uuid4())[:8],
            name=payload.name,
            age=payload.age,
            email=payload.email,
        )

        # Layer 3 — persistence
        # ⚠️  We catch DuplicateEmailError but NOT DatabaseConnectionError /
        #     DatabaseTimeoutError — because those were added after this code
        #     was written and no one updated this except clause.
        try:
            saved = self._repo.save(user)
        except DuplicateEmailError:
            raise  # let it propagate — the API layer will translate it

        # Layer 4 — notification (NotificationError)
        try:
            self._notif.send_welcome(saved.email)
        except NotificationError as exc:
            # We decide to swallow notification errors here — but only here.
            # Other callers might not make the same decision.
            print(f"[WARN] welcome email failed, continuing anyway: {exc}")

        return saved


# ---------------------------------------------------------------------------
# HTTP endpoint — must translate ALL domain exceptions to HTTP status codes
# Every new exception = one more except clause here too
# ---------------------------------------------------------------------------

class HttpResponse:
    def __init__(self, status: int, body: dict[str, Any]) -> None:
        self.status = status
        self.body = body

    def __repr__(self) -> str:
        return f"HTTP {self.status} — {self.body}"


def register_endpoint(
    raw_json: dict[str, Any],
    service: UserRegistrationService,
) -> HttpResponse:
    try:
        user = service.register(raw_json)
        return HttpResponse(201, {"user_id": user.user_id, "email": user.email})

    except ValidationError as exc:          # pydantic — direct from service
        return HttpResponse(400, {"error": str(exc)})

    except ValueError as exc:               # re-raised validation OR business rule
        return HttpResponse(400, {"error": str(exc)})

    except BannedDomainError as exc:        # business rule
        return HttpResponse(403, {"error": str(exc)})

    except DuplicateEmailError as exc:      # repository
        return HttpResponse(409, {"error": str(exc)})

    except NotificationError as exc:        # gateway — already swallowed above,
        return HttpResponse(503, {"error": str(exc)})  # but left here "just in case"

    # ⚠️  DatabaseConnectionError / DatabaseTimeoutError are NOT listed here.
    #     They will crash the process with an unhandled exception.


# ---------------------------------------------------------------------------
# Demo — run directly to see the cascade in action
# ---------------------------------------------------------------------------

def _separator(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)


if __name__ == "__main__":
    gateway = NotificationGateway()

    # ── Demo 1: happy path ──────────────────────────────────────────────────
    _separator("Demo 1 — happy path")
    svc = UserRegistrationService(InMemoryUserRepository(), gateway)
    resp = register_endpoint({"name": "Alice", "age": 30, "email": "alice@example.com"}, svc)
    print(resp)

    # ── Demo 2: bad input (ValidationError cascade) ─────────────────────────
    _separator("Demo 2 — bad input: no @ in email")
    resp = register_endpoint({"name": "Bob", "age": 25, "email": "notanemail"}, svc)
    print(resp)

    # ── Demo 3: banned domain (BannedDomainError) ───────────────────────────
    _separator("Demo 3 — banned domain")
    resp = register_endpoint({"name": "Eve", "age": 22, "email": "eve@banned.local"}, svc)
    print(resp)

    # ── Demo 4: duplicate email (DuplicateEmailError) ───────────────────────
    _separator("Demo 4 — duplicate email")
    register_endpoint({"name": "Alice2", "age": 31, "email": "alice@example.com"}, svc)
    resp = register_endpoint({"name": "Alice3", "age": 32, "email": "alice@example.com"}, svc)
    print(resp)

    # ── Demo 5: flaky notification (swallowed, continues) ───────────────────
    _separator("Demo 5 — flaky notification domain (swallowed)")
    resp = register_endpoint({"name": "Frank", "age": 40, "email": "frank@flaky.io"}, svc)
    print(resp)

    # ── Demo 6: DatabaseConnectionError — NOBODY catches this ───────────────
    _separator("Demo 6 — DatabaseConnectionError leaks through (CRASH)")
    flaky_repo = FlakyDbUserRepository(fail_with=DatabaseConnectionError)
    svc_flaky = UserRegistrationService(flaky_repo, gateway)
    try:
        resp = register_endpoint({"name": "Carol", "age": 28, "email": "carol@example.com"}, svc_flaky)
        print(resp)
    except DatabaseConnectionError as exc:
        print(f"[UNHANDLED in endpoint] {type(exc).__name__}: {exc}")
        print("  → The endpoint has no except clause for this. In production this would be a 500 / process crash.")

    # ── Demo 7: DatabaseTimeoutError (subclass) — same problem ──────────────
    _separator("Demo 7 — DatabaseTimeoutError (subclass) also leaks")
    flaky_repo2 = FlakyDbUserRepository(fail_with=DatabaseTimeoutError)
    svc_flaky2 = UserRegistrationService(flaky_repo2, gateway)
    try:
        resp = register_endpoint({"name": "Dave", "age": 35, "email": "dave@example.com"}, svc_flaky2)
        print(resp)
    except DatabaseTimeoutError as exc:
        print(f"[UNHANDLED in endpoint] {type(exc).__name__}: {exc}")
        print("  → Even a subclass of a known exception slips through if you didn't think of it.")

    print("\n[POINT] Every new exception forces updates in EVERY layer above it.")
    print("[POINT] Forgetting one except clause = silent crash in production.")
    print("[POINT] The test suite only proves what you already knew to test for.")