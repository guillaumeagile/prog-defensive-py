from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

T = TypeVar("T")
E = TypeVar("E")
U = TypeVar("U")


@dataclass(frozen=True)
class Ok(Generic[T]):
    value: T

    def map(self, fn: Callable[[T], U]) -> Ok[U]:
        return Ok(fn(self.value))

    def unwrap(self) -> T:
        return self.value

    def is_ok(self) -> bool:
        return True


@dataclass(frozen=True)
class Err(Generic[E]):
    error: E

    def map(self, fn) -> Err[E]:
        return self

    def unwrap(self):
        raise RuntimeError(f"unwrap() on Err: {self.error}")

    def is_ok(self) -> bool:
        return False


Result = Ok[T] | Err[E]
