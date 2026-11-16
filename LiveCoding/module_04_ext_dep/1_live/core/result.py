from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Generic, NoReturn, TypeVar

# Covariants : un `Err[PaymentServiceError]` est aussi un `Err[PaymentDeclined | PaymentServiceError]`.
# La syntaxe `class Err[E]` donne un paramètre invariant pour une dataclass avec pyright 1.1.414.
T_co = TypeVar("T_co", covariant=True)
E_co = TypeVar("E_co", covariant=True)


@dataclass(frozen=True)
class Ok(Generic[T_co]):
    value: T_co

    def map[U](self, fn: Callable[[T_co], U]) -> Ok[U]:
        return Ok(fn(self.value))

    def bind[U, E](self, fn: Callable[[T_co], Result[U, E]]) -> Result[U, E]:
        return fn(self.value)

    def unwrap(self) -> T_co:
        return self.value

    def is_ok(self) -> bool:
        return True

    def is_err(self) -> bool:
        return False


@dataclass(frozen=True)
class Err(Generic[E_co]):
    error: E_co

    def map[T, U](self, fn: Callable[[T], U]) -> Err[E_co]:
        return self

    def bind[T, U, F](self, fn: Callable[[T], Result[U, F]]) -> Err[E_co]:
        return self

    def unwrap(self) -> NoReturn:
        raise RuntimeError(f"unwrap() on Err: {self.error}")

    def is_ok(self) -> bool:
        return False

    def is_err(self) -> bool:
        return True


type Result[T, E] = Ok[T] | Err[E]
