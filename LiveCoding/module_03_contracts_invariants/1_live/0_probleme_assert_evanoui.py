# Point de départ du live : une précondition écrite avec `assert`.
# L'interpréteur retire les `assert` avec `python -O`. La règle disparaît en production.
#
# Lancer :
#   python 0_probleme_assert_evanoui.py       -> AssertionError et sa stack, le script s'arrête
#   python -O 0_probleme_assert_evanoui.py    -> aucune erreur, des résultats absurdes (-40.0 puis -50.0)


def compute_discount(price: float, pct: float) -> float:
    assert price >= 0, "price must be >= 0"
    assert 0 <= pct <= 100, "pct must be between 0 and 100"
    return price * (1 - pct / 100)


if __name__ == "__main__":
    print("price=100 pct=20 ->", compute_discount(100.0, 20.0))
    # Sans -O : AssertionError avec sa stack, le script s'arrête ici.
    # Avec -O : l'assert a disparu, le prix négatif passe et on obtient -40.0.
    print("price=-50 pct=20 ->", compute_discount(-50.0, 20.0))
    print("price=100 pct=150 ->", compute_discount(100.0, 150.0))
