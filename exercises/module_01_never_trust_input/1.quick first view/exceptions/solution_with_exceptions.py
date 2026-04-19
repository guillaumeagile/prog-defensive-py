# Approach A — Pydantic raises exceptions on invalid input.
# Callers must wrap calls in try/except to handle validation failures.
# The error path is implicit: nothing in the signature tells you it can fail.

from pydantic import BaseModel, Field, field_validator


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
    def email_must_contain_at(cls, v: str) -> str:
        if "@" not in v:
            raise ValueError("email must contain '@'")
        return v


# Caller code — the error path is invisible in the signature:
#
#   from pydantic import ValidationError
#
#   try:
#       user = UserInput(name="", age=30, email="alice@example.com")
#   except ValidationError as e:
#       print(e)  # only way to know it failed
