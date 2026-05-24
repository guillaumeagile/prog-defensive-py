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

    def bind(self, fn: Callable[[T], Result[U, E]]) -> Result[U, E]:
        return fn(self.value)

    def unwrap(self) -> T:
        return self.value

    def is_ok(self) -> bool:
        return True

    def is_err(self) -> bool:
        return False


@dataclass(frozen=True)
class Err(Generic[E]):
    error: E

    def map(self, fn: Callable[[T], U]) -> Err[E]:
        return self

    def bind(self, fn: Callable[[T], Result[U, E]]) -> Err[E]:
        return self

    def unwrap(self) -> T:
        raise RuntimeError(f"unwrap() on Err: {self.error}")

    def is_ok(self) -> bool:
        return False

    def is_err(self) -> bool:
        return True


Result = Ok[T] | Err[E]
