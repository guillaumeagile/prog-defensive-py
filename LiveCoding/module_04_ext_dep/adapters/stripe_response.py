from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StripeResponse:
    status_code: int
    body: dict[str, object]
