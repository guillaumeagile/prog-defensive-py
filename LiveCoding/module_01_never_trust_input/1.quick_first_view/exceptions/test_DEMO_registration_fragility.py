"""
Tests that EXPOSE the fragility of exception-based defensive programming.

Reading guide
─────────────
The tests are grouped into three sections:

  1. Green tests  — the happy-path and the errors the team anticipated.
                    These all pass.  They give a false sense of safety.

  2. Red tests    — the errors the team did NOT anticipate (new exceptions
                    added later by the DB team).  These demonstrate that
                    register_endpoint() crashes instead of returning an
                    HttpResponse.  The tests are written to DOCUMENT the
                    broken behaviour with pytest.raises(), so the suite
                    stays green — but the ⚠️  comments explain what a
                    production caller would actually experience.

  3. Noise tests  — show how much boilerplate is needed just to exercise
                    every layer of the exception cascade.
"""

import pytest

from DEMO_registration_with_exceptions import (
    BannedDomainError,
    DatabaseConnectionError,
    DatabaseTimeoutError,
    DuplicateEmailError,
    FlakyDbUserRepository,
    InMemoryUserRepository,
    NotificationGateway,
    UserRegistrationService,
    register_endpoint,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def make_service(
    *,
    repo=None,
    flaky_domain: str = "flaky.io",
) -> UserRegistrationService:
    return UserRegistrationService(
        repository=repo or InMemoryUserRepository(),
        notifications=NotificationGateway(flaky_domain=flaky_domain),
    )


VALID = {"name": "Alice", "age": 30, "email": "alice@example.com"}


# ─────────────────────────────────────────────────────────────────────────────
# Section 1 — Green tests (anticipated errors, all pass)
# ─────────────────────────────────────────────────────────────────────────────

class TestAnticipatedErrors:
    """Everything the team knew about when they wrote the code."""

    def test_happy_path_returns_201(self):
        resp = register_endpoint(VALID, make_service())
        assert resp.status == 201
        assert resp.body["email"] == "alice@example.com"

    def test_missing_at_sign_returns_400(self):
        resp = register_endpoint(
            {"name": "Bob", "age": 25, "email": "notanemail"},
            make_service(),
        )
        assert resp.status == 400

    def test_blank_name_returns_400(self):
        resp = register_endpoint(
            {"name": "   ", "age": 25, "email": "bob@example.com"},
            make_service(),
        )
        assert resp.status == 400

    def test_negative_age_returns_400(self):
        resp = register_endpoint(
            {"name": "Bob", "age": -1, "email": "bob@example.com"},
            make_service(),
        )
        assert resp.status == 400

    def test_banned_domain_returns_403(self):
        resp = register_endpoint(
            {"name": "Eve", "age": 22, "email": "eve@banned.local"},
            make_service(),
        )
        assert resp.status == 403

    def test_duplicate_email_returns_409(self):
        svc = make_service()
        register_endpoint(VALID, svc)
        resp = register_endpoint(VALID, svc)
        assert resp.status == 409

    def test_notification_failure_is_swallowed_and_returns_201(self):
        # The service swallows NotificationError — user is registered anyway.
        svc = make_service(flaky_domain="example.com")  # alice@example.com will fail
        resp = register_endpoint(VALID, svc)
        # ⚠️  Swallowing a network error silently is itself a design smell,
        #     but at least it doesn't crash.
        assert resp.status == 201


# ─────────────────────────────────────────────────────────────────────────────
# Section 2 — Red tests (unanticipated DB exceptions leak through)
#
# These tests DOCUMENT the crash.  They use pytest.raises() so the CI suite
# stays green, but read the comments — in production there is no pytest.raises
# wrapper, so the process crashes or the framework returns a raw 500.
# ─────────────────────────────────────────────────────────────────────────────

class TestUnanticipatedExceptionsLeakThrough:
    """
    The DB team added DatabaseConnectionError and DatabaseTimeoutError AFTER
    the service and endpoint were written.  Nobody updated the except clauses.
    """

    def test_db_connection_error_is_NOT_caught_by_endpoint(self):
        """
        register_endpoint() has no except clause for DatabaseConnectionError.
        Instead of returning HttpResponse(503, ...) it raises straight through.

        ⚠️  In production: unhandled exception → framework 500 or process crash.
        """
        svc = make_service(repo=FlakyDbUserRepository(fail_with=DatabaseConnectionError))

        with pytest.raises(DatabaseConnectionError):
            # A production caller expects an HttpResponse.
            # It gets a crash instead.
            register_endpoint(VALID, svc)

    def test_db_timeout_error_is_NOT_caught_by_endpoint(self):
        """
        DatabaseTimeoutError is a *subclass* of DatabaseConnectionError.
        Even if someone later adds 'except DatabaseConnectionError' in the
        wrong place, a more specific subclass can still slip through.

        ⚠️  Same crash in production.
        """
        svc = make_service(repo=FlakyDbUserRepository(fail_with=DatabaseTimeoutError))

        #with pytest.raises(DatabaseTimeoutError):
        register_endpoint(VALID, svc)

    def test_db_connection_error_also_bypasses_the_service_layer(self):
        """
        The service's try/except block only lists DuplicateEmailError.
        DatabaseConnectionError is not re-wrapped or translated — it
        propagates raw through service AND endpoint.
        """
        svc = make_service(repo=FlakyDbUserRepository(fail_with=DatabaseConnectionError))

        # with pytest.raises(DatabaseConnectionError):
        svc.register(VALID)

    def test_any_unknown_future_exception_will_also_leak(self):
        """
        The pattern generalises: any exception type not explicitly listed in
        every except clause on every layer will leak.  This test uses a
        brand-new ad-hoc exception to prove the point.
        """
        class FutureRepoError(Exception):
            """Imaginary exception added next quarter."""

        svc = make_service(repo=FlakyDbUserRepository(fail_with=FutureRepoError))

        #with pytest.raises(FutureRepoError):
        register_endpoint(VALID, svc)


# ─────────────────────────────────────────────────────────────────────────────
# Section 3 — Noise: the boilerplate cost of exception-based testing
#
# Count the lines in this class vs. what it actually tests.
# Every single failure path needs its own pytest.raises() + knowledge of
# which exact exception type each layer raises.
# ─────────────────────────────────────────────────────────────────────────────

class TestExceptionBoilerplateNoise:
    """
    To test the service directly (bypassing the endpoint) every caller must
    know the internal exception vocabulary of every dependency.
    """

    def test_service_raises_ValueError_for_bad_input(self):
        # Must know: pydantic's ValidationError is re-wrapped as ValueError here
        with pytest.raises(ValueError):
            make_service().register({"name": "", "age": 30, "email": "a@b.com"})

    def test_service_raises_BannedDomainError_for_banned_email(self):
        # Must know: BannedDomainError, not ValueError, not ValidationError
        with pytest.raises(BannedDomainError):
            make_service().register({"name": "X", "age": 20, "email": "x@banned.local"})

    def test_service_raises_DuplicateEmailError_on_second_save(self):
        # Must know: DuplicateEmailError comes from the repo and is re-raised
        svc = make_service()
        svc.register(VALID)
        with pytest.raises(DuplicateEmailError):
            svc.register(VALID)

    def test_service_does_NOT_raise_for_notification_failure(self):
        # Must know: NotificationError is swallowed — no exception is raised
        # But this is invisible: the caller gets a 201 and has no idea the
        # welcome email was never sent.
        svc = make_service(flaky_domain="example.com")
        result = svc.register(VALID)   # should not raise
        assert result.email == "alice@example.com"

