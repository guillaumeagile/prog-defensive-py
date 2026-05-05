# Approach C — dataclass + __post_init__, no pydantic.
# The same Result-returning boundary pattern, built with stdlib only.
# Use this when you can't or won't add pydantic to a project.

import re
from dataclasses import dataclass

from returns.result import Failure, Result, Success


@dataclass(frozen=True)
class UserInput:
    name: str
    age: int
    email: str

    def __post_init__(self) -> None:
        # frozen=True means we cannot assign — use object.__setattr__ to normalise
        object.__setattr__(self, "name", self.name.strip())
        if not self.name:
            raise ValueError("name cannot be blank")
        if len(self.name) > 100:
            raise ValueError(f"name too long: {len(self.name)} chars (max 100)")
        if not (0 <= self.age <= 150):
            raise ValueError(f"age must be 0–150, got {self.age}")
        if "@" not in self.email:
            raise ValueError(f"invalid email: {self.email!r}")


def parse_user_input(name: str, age: int, email: str) -> Result[UserInput, str]:
    try:
        return Success(UserInput(name=name, age=age, email=email))
    except ValueError as e:
        return Failure(str(e))
