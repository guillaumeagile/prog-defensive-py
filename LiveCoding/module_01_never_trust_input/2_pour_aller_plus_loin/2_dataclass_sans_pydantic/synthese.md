# Module 01 — Synthèse : dataclass + `__post_init__`

## Place dans le Module 01

- **Étape :** hors live, chemin de repli quand Pydantic n'est pas disponible
- **Approche couverte :** approche C
- **Se compare à :** l'approche B (`../../1_live/user_input.py`, recommandée), sans dépendance à Pydantic
- **Concepts renforcés :** Value Objects, contrat parse-don't-validate, échecs explicites via `Result`
- **Extension possible :** `../3_erreurs_typees/` (approche D) pour des ADT d'erreurs typées

---

## Ce que montre cette approche

L'approche B (Pydantic + Result) est le chemin recommandé. Elle demande une dépendance externe.
Cette étape répond à la question : **que faire si l'on ne peut pas, ou ne veut pas, utiliser Pydantic ?**

La réponse : le même pattern, avec la stdlib seule.

---

## Fonctionnement

```python
@dataclass(frozen=True)
class UserInput:
    name: str
    age: int
    email: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", self.name.strip())
        if not self.name:
            raise ValueError("name cannot be blank")
        if not (0 <= self.age <= 150):
            raise ValueError(f"age must be 0–150, got {self.age}")
        if "@" not in self.email:
            raise ValueError(f"invalid email: {self.email!r}")


def parse_user_input(name: str, age: int, email: str) -> Result[UserInput, str]:
    try:
        return Success(UserInput(name=name, age=age, email=email))
    except ValueError as e:
        return Failure(str(e))
```

`__post_init__` s'exécute automatiquement après `__init__`. C'est le point d'accroche naturel pour
imposer des invariants dans une dataclass. Le `ValueError` qu'il lève est aussitôt attrapé par `parse_user_input`
et converti en `Failure` : il n'atteint jamais l'appelant.

**Une subtilité :** `frozen=True` rend la dataclass immuable après construction. Une affectation
normale (`self.name = ...`) lève `FrozenInstanceError`. Pour normaliser un champ (retirer les espaces),
il faut utiliser `object.__setattr__(self, "name", ...)`. C'est une particularité de la stdlib à connaître.

---

## Comparaison des trois approches

| | Approche A (Pydantic + exceptions) | Approche B (Pydantic + Result) | Approche C (dataclass + Result) |
|---|---|---|---|
| Dépendance externe | `pydantic` | `pydantic`, `returns` | `returns` seul |
| Coercion (string → int) | Oui, automatique | Oui, automatique | Manuelle |
| Règles de validation | Déclaratives (`Field`, validators) | Déclaratives | Impératives (`if`) |
| Chemin d'erreur dans la signature | Non | Oui | Oui |
| Boilerplate | Faible | Faible | Moyen |

## Quand l'utiliser

- Projets legacy où ajouter Pydantic est impossible
- Petits utilitaires ou CLI où une bibliothèque de validation complète est disproportionnée
- Enseigner le principe sans le cacher derrière un framework

Pour les services de production avec des entrées externes (HTTP, queues, fichiers), préférez l'approche B.
Le style déclaratif de Pydantic passe mieux à l'échelle quand le nombre de champs augmente.

---

## L'invariant reste identique

Quel que soit l'outil, Pydantic ou `dataclass`, le contrat est le même :

> `parse_user_input(...) -> Result[UserInput, str]`

`UserInput` reste un Value Object immuable, et l'appelant n'a jamais besoin de `try/except`.
Le chemin d'erreur est dans le type.
