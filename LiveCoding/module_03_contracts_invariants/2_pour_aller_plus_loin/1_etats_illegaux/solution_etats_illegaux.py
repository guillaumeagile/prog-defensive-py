# Illegal states unrepresentable : le cycle de vie est encodé dans les types.
# Pas de drapeau `is_confirmed: bool`, pas d'état intermédiaire nullable.

from dataclasses import dataclass

from expression import Error, Ok, Result


@dataclass(frozen=True)
class DraftOrder:
    order_id: str
    lines: tuple[str, ...] = ()


@dataclass(frozen=True)
class ConfirmedOrder:
    order_id: str
    lines: tuple[str, ...]


def confirm(order: DraftOrder) -> Result[ConfirmedOrder, str]:
    if not order.lines:
        return Error("an order needs at least one line to be confirmed")
    return Ok(ConfirmedOrder(order.order_id, order.lines))


def ship(order: ConfirmedOrder) -> str:
    # Le type checker refuse `ship(DraftOrder(...))`.
    return f"order {order.order_id} shipped with {len(order.lines)} line(s)"


# L'immutabilité comme amplificateur de contrat : une fois créé, l'objet ne dérive plus.

@dataclass(frozen=True)
class Config:
    db_url: str
    max_retries: int
