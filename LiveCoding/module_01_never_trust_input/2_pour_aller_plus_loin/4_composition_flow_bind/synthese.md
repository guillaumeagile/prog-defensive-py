# Module 01 — Synthèse : un style FP plus poussé

## Place dans le Module 01

- **Étape :** hors live, approfondissement de l'approche FP
- **Approche couverte :** approche E
- **S'appuie sur :** `../3_erreurs_typees/` (approche D, `Result[T, ErrorADT]`)
- **Objectif :** parser chaque champ dans son propre Value Object (`Name`, `Age`, `Email`) et composer les étapes avec `flow` + `bind`
- **Prolonge :** le ROP du Module 02 du guide (`flow` + `bind`)

---

## Ce qui change par rapport à l'approche D

L'approche D enveloppait tout le modèle validé dans un `Result` avec des erreurs typées.
L'approche E découpe la validation en une fonction par champ, chacune retournant un `Result`, puis les compose.

```python
# Approche D — une grosse fonction de parse
parse_user_input(...) -> Result[ParsedUserInput, ParseUserError]

# Approche E — trois petits parsers composés avec flow/bind
parse_name(raw_name)   -> Result[Name, ParseUserError]
parse_age(raw_age)     -> Result[Age, ParseUserError]
parse_email(raw_email) -> Result[Email, ParseUserError]

parse_user_input(name, age, email) -> Result[ParsedUserInput, ParseUserError]:
    return flow(
        parse_name(name),
        bind(_bind_parse_age(age)),
        bind(_bind_parse_email(email)),
    )
```

Chaque concept du domaine devient un type distinct. `ParsedUserInput` contient `Name`, `Age`, `Email`, et plus de chaînes brutes.
Une fonction qui accepte un `Name` ne peut donc jamais recevoir par accident une chaîne non validée.

---

## Pourquoi les Value Objects comptent

```python
# Sans Value Objects — bug silencieux possible
def greet(name: str) -> str:
    return f"Hello, {name}"

greet(user.email)   # compile et s'exécute — mauvaise donnée, aucune erreur

# Avec Value Objects — attrapé par le type checker
def greet(name: Name) -> str:
    return f"Hello, {name.value}"

greet(user.email)   # TypeError au point d'appel
```

Le système de types impose ce que la donnée *signifie*, au-delà de ce qu'elle *est*.

---

## Le pattern de composition

`flow` et `bind` (de la bibliothèque `returns`) font passer un `Result` à travers un pipeline.
Si une étape retourne un `Failure`, le reste du pipeline est court-circuité : ni exception, ni `if` imbriqués.

```python
parse_user_input("Alice", 30, "alice@example.com")
# → Success(ParsedUserInput(Name("Alice"), Age(30), Email("alice@example.com")))

parse_user_input("", 30, "alice@example.com")
# → Failure(NameEmpty())   — pipeline arrêté à l'étape 1
```

---

## Comparaison des cinq approches

| | A (exceptions) | B (Result + str) | C (dataclass + Result) | D (Result + ADT) | E (Value Objects + flow) |
|---|---|---|---|---|---|
| Où la voir | `1_live/etape_2_pydantic_exception.py` | `1_live/user_input.py` | `2_dataclass_sans_pydantic/` | `3_erreurs_typees/` | `4_composition_flow_bind/` |
| Fichier clé | `etape_2_pydantic_exception.py` | `user_input.py` | `solution_dataclass.py` | `solution_stronger_types.py` | `solution_more_fp_style.py` |
| Chemin d'erreur dans la signature | Non | Oui | Oui | Oui | Oui |
| Type d'erreur | implicite | `str` | `str` | ADT typé | ADT typé |
| Types du domaine | chaînes brutes | chaînes brutes | chaînes brutes | chaînes brutes | Value Objects |
| Pipeline composable | Non | Partiellement | Partiellement | Partiellement | Oui (`flow`/`bind`) |
| Usage des champs sûr au niveau des types | Non | Non | Non | Non | Oui |
| Boilerplate | Faible | Faible | Moyen | Moyen | Plus élevé |

---

## Quand utiliser ce style

Utilisez l'approche E quand :

- le même concept du domaine (name, email, age) apparaît dans beaucoup de fonctions : les Value Objects évitent les mélanges
- vous voulez construire de grands pipelines à partir de petites briques validées
- l'équipe est à l'aise avec la composition fonctionnelle (`flow`, `bind`, `map`)

Pour la plupart des services CRUD, l'approche D offre un bon équilibre.
L'approche E brille dans les modèles riches en domaine, où l'identité des champs compte.

---

## Règle pratique

> Parsez l'entrée brute à la boundary, une seule fois.
> Chaque champ reçoit son propre type : une chaîne invalide n'entre jamais dans le domaine.
> Composez de petits parsers de confiance plutôt qu'un grand validator.
>
> `parse_name`, `parse_age`, `parse_email` font chacun une chose.
> `parse_user_input` se contente de les relier.
> Aucune couche n'a besoin de `try/except`.
