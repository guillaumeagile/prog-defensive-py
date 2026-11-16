# Module 01 — Synthèse : Result avec des types plus forts

## Place dans le Module 01

- **Étape :** hors live, approfondissement après les approches A, B et C
- **Approche couverte :** approche D
- **S'appuie sur :** `../../1_live/ecriture_2_parse_user_result.py`
- **Objectif :** remplacer `Result[UserInput, str]` par `Result[ParsedUserInput, ParseUserError]`
- **Prolonge :** le Module 02 du guide (`Result[ActiveUser, UserNotFound | UserInactive]`)

---

## Ce qui change

L'approche B rend le chemin d'erreur explicite avec `Result`, mais utilise `str` pour les échecs.
L'approche D garde le même flux et type les échecs.

```python
# Approche B
parse_user(...) -> Result[UserInput, str]

# Approche D
parse_user_input(...) -> Result[ParsedUserInput, ParseUserError]
```

Ce passage apporte l'aide du type checker et un pattern matching plus sûr chez les appelants.

---

## Pourquoi c'est plus FP

- Parse à la boundary une seule fois (`parse_raw_user_input` avec Pydantic)
- Parse les primitives du domaine en Value Objects (`Name`, `Age`, `Email`)
- Compose les étapes faillibles avec `flow(..., bind(...))`
- Représente chaque échec attendu par une variante, au lieu d'une chaîne libre
- Distingue précisément l'intention de l'erreur (`NameEmpty` vs `NameBlank`)

```python
match result:
    case Success(user):
        ...
    case Failure(NameBlank()):
        ...
    case Failure(AgeOutOfRange(raw_age=age)):
        ...
    case Failure(PayloadError(field=field, message=message)):
        ...
```

---

## Compromis

Les erreurs typées sont plus explicites et plus sûres, au prix d'un peu de cérémonie
(dataclasses + fonctions de mapping).

Utilisez ce style quand :

- la logique de gestion d'erreur compte (réponse UI/API différente selon le type d'erreur)
- vous voulez un meilleur support au refactoring
- un échec en `str` ne suffit plus

---

## Pourquoi un PBT dédié aide

Les tests unitaires classiques vérifient quelques chaînes représentatives (`""` ou `"Alice"`).
Ils peuvent manquer les cas d'espaces blancs seuls (`"   "`, `"\t\n"`, mélanges).

Ici, une classe PBT dédiée (`TestParseUserInputPBT.py`) parcourt cet espace d'entrées et vérifie que les noms
faits d'espaces blancs sont rejetés avec `NameBlank`, alors que `""` reste un cas distinct (`NameEmpty`).

---

## Vérification statique (optionnel)

L'approche D se prête bien aux vérifications statiques strictes, car les signatures sont explicites :

- `Result[ParsedUserInput, ParseUserError]` aux boundaries
- variantes d'erreur typées (`NameEmpty`, `NameBlank`, ...)
- `render_error` exhaustif via `assert_never`

Installer l'outillage avec Poetry (une fois) :

```bash
poetry add --group dev pydantic returns hypothesis pytest pyright mypy
```

Lancer depuis ce dossier (via Poetry) :

```bash
poetry run pyright --project pyright.module01.json
poetry run mypy --config-file mypy.module01.ini
```

---

## Règle pratique

Commencez avec `Result[T, str]` pour l'enseignement et les prototypes rapides.
Passez à `Result[T, ErrorADT]` quand le comportement dépend de *quel* échec s'est produit.
