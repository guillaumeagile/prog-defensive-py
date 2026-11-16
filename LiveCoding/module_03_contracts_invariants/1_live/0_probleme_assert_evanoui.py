# Point de départ du live : une précondition écrite avec `assert`.
# L'interpréteur retire les `assert` avec `python -O`. La règle disparaît en production.
#
# Lancer :
#   python 0_probleme_assert_evanoui.py       -> la précondition protège
#   python -O 0_probleme_assert_evanoui.py    -> la précondition n'existe plus


def compute_discount(price: float, pct: float) -> float:
    assert price >= 0, "price must be >= 0"
    assert 0 <= pct <= 100, "pct must be between 0 and 100"
    return price * (1 - pct / 100)


if __name__ == "__main__":
    for price, pct in [(100.0, 20.0), (-50.0, 20.0), (100.0, 150.0)]:
        try:
            print(f"price={price} pct={pct} ->", compute_discount(price, pct))
        except AssertionError as error:
            print(f"price={price} pct={pct} -> refusé : {error}")
