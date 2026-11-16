"""Étape 1 du live : le code fait confiance à l'appelant.

Reprend le « ❌ Bad » du guide (Module 01). À lancer tel quel :

    python 0_probleme_confiance_aveugle.py

Rien ne valide l'entrée : la donnée invalide entre dans le système
et le problème apparaît plus loin, ou jamais.
"""

from typing import Any


class FakeDb:
    """Base de données minimale pour la démo."""

    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []

    def insert(self, *, name: str, age: int) -> None:
        self.rows.append({"name": name, "age": age})


db = FakeDb()


def create_user(data: dict[str, Any]) -> None:
    name = data["name"]
    age = data["age"]
    db.insert(name=name, age=age)


if __name__ == "__main__":
    # Entrée absurde : elle est acceptée sans broncher.
    create_user({"name": "", "age": -5})
    print("Ligne enregistrée :", db.rows[-1])

    # Entrée incomplète : l'erreur est un KeyError technique, sans message métier.

    create_user({"name": "Bob"})
