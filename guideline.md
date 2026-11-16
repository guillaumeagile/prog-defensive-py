# Defensive & Pragmatic Python — Guideline pour Claude Code

> **Objet** : référence de la session de live coding pour un Python propre, sûr côté types
> et orienté fonctionnel. Tout code de production est piloté par les tests. Ce document est le
> contrat que Claude Code suit pendant toute la session.

---

## 0. Philosophie

Trois principes gouvernent chaque décision de conception de cette session :

| Principe | Ce que cela signifie en pratique |
|---|---|
| **Parse, don't validate** | Transformer les données non fiables en types riches à la boundary. Ne jamais passer de strings/dicts bruts dans la logique du domaine. |
| **Make illegal states unrepresentable** | Modéliser le domaine pour que les combinaisons invalides ne puissent pas être construites, au lieu de les attraper à l'exécution. |
| **Value Objects** | Envelopper les primitives dans des types nommés qui portent leurs propres invariants. `UserId` n'est pas un `int`. |

Le runtime de Python n'impose rien de tout cela. L'outillage s'en charge.

---

## 1. Toolchain (non négociable)

### Type checking — `pyright` en mode strict

Chaque projet doit avoir un `pyrightconfig.json` à la racine :

```json
{
  "typeCheckingMode": "strict",
  "pythonVersion": "3.12",
  "reportMissingImports": true,
  "reportUnusedVariable": "warning"
}
```

À lancer avant chaque commit. Une erreur de type équivaut à un échec de build.

### Tests — `pytest` + `hypothesis`

```toml
# pyproject.toml
[tool.pytest.ini_options]
addopts = "--tb=short -q"

[tool.hypothesis]
max_examples = 200
```

Deux sortes de tests coexistent toujours :

- **Example-based** (`pytest`) : cas précis, cas limites, happy path, échecs connus.
- **Property-based** (`hypothesis`) : invariants qui doivent tenir pour *toute* entrée valide.

### Bibliothèques

```bash
pip install pydantic returns expression pyright pytest hypothesis
```

| Bibliothèque | Rôle |
|---|---|
| `pydantic` | Parsing et validation aux boundaries du système (HTTP, fichiers, env) |
| `returns` | `Result`, `Maybe`, railway-oriented programming dans la logique du domaine |
| `expression` | Utilitaires FP : `pipe`, `Option`, tagged unions, collections immuables |
| `pyright` | Vérification statique des types |

---

## 2. Règles TDD

### Le seul workflow autorisé

```
Install deps → Tests collect & run → Watch them fail (right reason) → Write minimum code to pass → Refactor
```

Aucun code de production sans test préalable. Aucune exception.

### Prérequis : les tests doivent s'exécuter avant tout le reste

Avant d'écrire du code de solution, vérifier :

1. **Les dépendances sont installées** : `pytest`, `hypothesis`, `pydantic`, `returns`, `expression` doivent toutes s'importer. Lancer `pip install` si besoin.
2. **Les tests se collectent sans erreur d'import** : `pytest --collect-only` doit réussir.
3. **Les tests échouent pour la bonne raison** : l'échec doit être `ModuleNotFoundError: No module named 'solution'` (ou équivalent), et non une erreur d'outillage ou d'environnement.

Ce n'est qu'une fois l'étape 3 confirmée qu'il est permis d'écrire `solution.py`.

### Structure des fichiers de test

```
exercises/
  exercise_01_value_objects/
    README.md          ← quoi implémenter et pourquoi
    test_solution.py   ← tests écrits d'abord, import de la solution commenté
    solution.py        ← écrit une fois les tests passés
  exercise_02_parse_dont_validate/
    ...
```

Chaque exercice est autonome. Les tests importent depuis `solution.py` dans le même dossier.

### Convention de nommage

```python
# Example-based
def test_<unit>_<scenario>_<expected_outcome>():
    ...

# Property-based
@given(...)
def test_<unit>_property_<invariant_name>(...):
    ...
```

---

## 3. Concepts FP (expliqués pour des audiences mixtes)

### 3.1 Value Objects

> Un **Value Object** est un objet dont l'identité est définie par sa valeur, pas par son
> adresse mémoire. Deux instances `Email("a@b.com")` sont égales. Il est immuable.
> Il se valide lui-même à la construction, ou refuse d'être construit.

```python
from dataclasses import dataclass
from returns.result import Result, Success, Failure


@dataclass(frozen=True)  # frozen = immutable after creation
class Email:
    value: str

    def __post_init__(self) -> None:
        if "@" not in self.value:
            raise ValueError(f"Invalid email: {self.value!r}")

    @classmethod
    def parse(cls, raw: str) -> Result["Email", str]:
        """Parse, don't validate: return a Result instead of raising."""
        if "@" not in raw:
            return Failure(f"Invalid email: {raw!r}")
        return Success(cls(raw))
```

Point clé : `Email.parse()` retourne un `Result`, donc l'appelant est **forcé** de traiter
le cas d'échec. Aucun `None` silencieux, aucune exception non attrapée.

### 3.2 Parse, don't validate

> **Validate** : prendre une valeur, retourner `True/False`. La valeur reste non typée ensuite.
> **Parse** : prendre une valeur, retourner un *type plus riche* ou un échec explicite. Après le parsing,
> le type lui-même est la preuve de validité.

```python
# ❌ Validate — caller can ignore the check
def is_valid_age(n: int) -> bool:
    return 0 <= n <= 150

age = int(input())
# nothing stops you from using `age` without calling is_valid_age first

# ✅ Parse — the type carries the proof
@dataclass(frozen=True)
class Age:
    value: int

    @classmethod
    def parse(cls, n: int) -> Result["Age", str]:
        if not (0 <= n <= 150):
            return Failure(f"Age must be 0–150, got {n}")
        return Success(cls(n))
```

### 3.3 Make illegal states unrepresentable

> Si votre système de types permet de construire une valeur qui n'a aucun sens dans votre
> domaine, vous avez un bug latent qui attend ses conditions de déclenchement.

```python
# ❌ Allows nonsense: is_loading=True AND data=something
@dataclass
class FetchState:
    is_loading: bool
    data: str | None
    error: str | None

# ✅ Only valid combinations can exist
from typing import Literal
from expression import tagged_union, case, tag

@tagged_union
class FetchState:
    tag: Literal["loading", "success", "error"] = tag()
    loading: None = case()
    success: str = case()
    error: str = case()
```

Faire du pattern matching dessus : pyright signale une branche manquante.

### 3.4 Result & Railway-Oriented Programming

> **Railway-oriented programming** (ROP) : imaginer deux voies, une voie de succès et une voie
> d'échec. Une fois qu'un calcul déraille sur la voie d'échec, les étapes suivantes
> sont sautées. On compose des fonctions faillibles sans `try/except` imbriqués.

```python
from returns.result import Result, Success, Failure
from returns.pipeline import flow
from returns.pointfree import bind


def parse_email(raw: str) -> Result[Email, str]:
    ...

def check_not_banned(email: Email) -> Result[Email, str]:
    ...

def create_user(email: Email) -> Result[User, str]:
    ...

# Functions compose on the success track; failures short-circuit
register = flow(
    parse_email,
    bind(check_not_banned),
    bind(create_user),
)

result = register("user@example.com")

match result:
    case Success(user):
        print(f"Created: {user}")
    case Failure(error):
        print(f"Failed: {error}")
```

### 3.5 Option / Maybe

> Utiliser `Maybe` quand une valeur peut légitimement être absente, sans que ce soit une erreur : simplement
> « rien ici ». Remplace les retours `None` par un type explicite qu'il faut déballer.

```python
from returns.maybe import Maybe, Some, Nothing


def find_user(user_id: int) -> Maybe[User]:
    user = db.get(user_id)
    return Some(user) if user else Nothing

# Force the caller to handle absence
match find_user(42):
    case Some(user):
        print(user.name)
    case Nothing:
        print("Not found")
```

### 3.6 Pipe

> `pipe` fait passer une valeur à travers une séquence de fonctions, de gauche à droite.
> Il remplace `f(g(h(x)))` par quelque chose de lisible.

```python
from expression import pipe
from expression.collections import seq


result = pipe(
    [1, 2, 3, 4, 5],
    seq.map(lambda x: x * 2),
    seq.filter(lambda x: x > 4),
    list,
)
# result = [6, 8, 10]
```

---

## 4. Structure des exercices

Chaque exercice suit ce schéma :

```
README.md        — concept expliqué, quoi implémenter
test_solution.py — tests écrits AVANT l'existence de solution.py
solution.py      — écrit pendant la session, piloté par le TDD
```

### Liste des exercices

| # | Concept | Outil clé |
|---|---|---|
| 01 | Value Objects — envelopper une primitive, imposer des invariants | `dataclass(frozen=True)` |
| 02 | Parse, don't validate — `Result` à la boundary | `returns` |
| 03 | Illegal states — modéliser une state machine | `expression @tagged_union` |
| 04 | Railway — composer des fonctions faillibles | `returns flow + bind` |
| 05 | Pydantic à la boundary — parser du JSON externe | `pydantic BaseModel` |
| 06 | Property-based tests — trouver les violations d'invariants | `hypothesis` |
| 07 | Tout assembler — un petit domaine de bout en bout | tout ce qui précède |

---

## 5. Templates d'exercices

### Exercice 01 — Value Objects

**`test_solution.py`**

```python
import pytest
from hypothesis import given, strategies as st
from solution import Email, Age  # noqa: these don't exist yet — tests fail first


class TestEmail:
    def test_valid_email_is_created(self):
        email = Email("user@example.com")
        assert email.value == "user@example.com"

    def test_email_without_at_sign_raises(self):
        with pytest.raises(ValueError):
            Email("notanemail")

    def test_emails_with_same_value_are_equal(self):
        assert Email("a@b.com") == Email("a@b.com")

    def test_email_is_immutable(self):
        email = Email("a@b.com")
        with pytest.raises(Exception):  # frozen dataclass raises FrozenInstanceError
            email.value = "other@b.com"  # type: ignore

    @given(st.emails())
    def test_property_valid_email_always_parses(self, raw: str):
        email = Email(raw)
        assert "@" in email.value


class TestAge:
    def test_valid_age_is_created(self):
        assert Age(25).value == 25

    def test_negative_age_raises(self):
        with pytest.raises(ValueError):
            Age(-1)

    def test_age_over_150_raises(self):
        with pytest.raises(ValueError):
            Age(151)

    @given(st.integers(min_value=0, max_value=150))
    def test_property_any_valid_age_constructs(self, n: int):
        assert Age(n).value == n

    @given(st.integers().filter(lambda x: x < 0 or x > 150))
    def test_property_invalid_age_always_raises(self, n: int):
        with pytest.raises(ValueError):
            Age(n)
```

---

### Exercice 02 — Parse, don't validate

**`test_solution.py`**

```python
from returns.result import Success, Failure
from hypothesis import given, strategies as st
from solution import Email, Age


class TestEmailParse:
    def test_parse_valid_email_returns_success(self):
        result = Email.parse("user@example.com")
        assert isinstance(result, Success)

    def test_parse_invalid_email_returns_failure(self):
        result = Email.parse("notanemail")
        assert isinstance(result, Failure)

    def test_parse_empty_string_returns_failure(self):
        result = Email.parse("")
        assert isinstance(result, Failure)

    @given(st.emails())
    def test_property_valid_emails_always_succeed(self, raw: str):
        assert isinstance(Email.parse(raw), Success)

    @given(st.text().filter(lambda s: "@" not in s))
    def test_property_strings_without_at_always_fail(self, raw: str):
        assert isinstance(Email.parse(raw), Failure)


class TestAgeParse:
    def test_parse_valid_age_returns_success(self):
        assert isinstance(Age.parse(30), Success)

    def test_parse_negative_returns_failure(self):
        assert isinstance(Age.parse(-1), Failure)

    @given(st.integers(min_value=0, max_value=150))
    def test_property_valid_range_always_succeeds(self, n: int):
        assert isinstance(Age.parse(n), Success)
```

---

### Exercice 03 — Illegal States

**`test_solution.py`**

```python
import pytest
from solution import Order, OrderStatus


class TestOrderStateMachine:
    def test_new_order_is_pending(self):
        order = Order.new(item="Book", quantity=1)
        assert order.status == OrderStatus.PENDING

    def test_pending_order_can_be_confirmed(self):
        order = Order.new("Book", 1)
        confirmed = order.confirm()
        assert confirmed.status == OrderStatus.CONFIRMED

    def test_confirmed_order_can_be_shipped(self):
        order = Order.new("Book", 1).confirm()
        shipped = order.ship()
        assert shipped.status == OrderStatus.SHIPPED

    def test_pending_order_cannot_be_shipped_directly(self):
        order = Order.new("Book", 1)
        with pytest.raises(Exception):
            order.ship()

    def test_shipped_order_cannot_be_cancelled(self):
        order = Order.new("Book", 1).confirm().ship()
        with pytest.raises(Exception):
            order.cancel()

    def test_cancelled_order_cannot_be_confirmed(self):
        order = Order.new("Book", 1).cancel()
        with pytest.raises(Exception):
            order.confirm()
```

---

### Exercice 04 — Railway-Oriented Programming

**`test_solution.py`**

```python
from returns.result import Success, Failure
from solution import register_user


class TestRegisterUser:
    def test_valid_registration_succeeds(self):
        result = register_user(email="user@example.com", age=25)
        assert isinstance(result, Success)

    def test_invalid_email_fails_early(self):
        result = register_user(email="notanemail", age=25)
        assert isinstance(result, Failure)
        assert "email" in result.failure().lower()

    def test_invalid_age_fails(self):
        result = register_user(email="user@example.com", age=-5)
        assert isinstance(result, Failure)
        assert "age" in result.failure().lower()

    def test_banned_email_fails(self):
        result = register_user(email="banned@blacklist.com", age=25)
        assert isinstance(result, Failure)
        assert "banned" in result.failure().lower()

    def test_failure_is_descriptive(self):
        result = register_user(email="", age=25)
        assert isinstance(result, Failure)
        assert len(result.failure()) > 0
```

---

### Exercice 05 — Pydantic à la boundary

**`test_solution.py`**

```python
import pytest
from pydantic import ValidationError
from solution import UserPayload, parse_user_payload


class TestUserPayload:
    def test_valid_payload_parses(self):
        raw = {"email": "user@example.com", "age": 30, "name": "Alice"}
        user = UserPayload.model_validate(raw)
        assert user.email == "user@example.com"

    def test_missing_field_raises(self):
        with pytest.raises(ValidationError):
            UserPayload.model_validate({"email": "user@example.com"})  # no age

    def test_wrong_type_raises(self):
        with pytest.raises(ValidationError):
            UserPayload.model_validate({"email": "user@example.com", "age": "old", "name": "Alice"})

    def test_invalid_email_raises(self):
        with pytest.raises(ValidationError):
            UserPayload.model_validate({"email": "notanemail", "age": 30, "name": "Alice"})

    def test_parse_returns_domain_object(self):
        raw = {"email": "user@example.com", "age": 30, "name": "Alice"}
        result = parse_user_payload(raw)
        # result should be a domain User, not a raw dict
        assert hasattr(result, "email")
```

---

### Exercice 06 — Property-Based Testing

**`test_solution.py`**

```python
from hypothesis import given, strategies as st, assume
from solution import Email, Age, merge_user_data


class TestProperties:
    @given(st.emails())
    def test_email_roundtrip(self, raw: str):
        """Parsing a valid email and reading back its value is lossless."""
        email = Email(raw)
        assert email.value == raw

    @given(st.integers(min_value=0, max_value=150))
    def test_age_value_preserved(self, n: int):
        """Age value is stored exactly as provided."""
        assert Age(n).value == n

    @given(st.dictionaries(st.text(), st.text()),
           st.dictionaries(st.text(), st.text()))
    def test_merge_is_associative_on_non_overlapping_keys(self, a: dict, b: dict):
        """Merging two dicts with no shared keys: order doesn't matter."""
        assume(not set(a.keys()) & set(b.keys()))
        assert merge_user_data(a, b) == merge_user_data(b, a)

    @given(st.text(min_size=1))
    def test_email_parse_failure_message_is_never_empty(self, raw: str):
        """A failed parse always produces a descriptive error message."""
        from returns.result import Failure
        assume("@" not in raw)
        result = Email.parse(raw)
        assert isinstance(result, Failure)
        assert len(result.failure()) > 0
```

---

### Exercice 07 — Domaine de bout en bout

**`README.md` (à écrire pendant la session)**

Concevoir et développer en TDD un `OrderService` minimal qui :

- Accepte du JSON brut en entrée (parsé avec `pydantic`)
- Crée des Value Objects `Order` (parse, don't validate)
- Passe par une state machine (illegal states unrepresentable)
- Retourne `Result[Order, str]` à chaque étape (railway)
- Possède des tests example-based et property-based

C'est l'exercice d'intégration : aucun nouveau concept, uniquement de la composition.

---

## 6. Règles de style de code pour Claude Code

Ces règles s'appliquent à **tout code généré** pendant cette session.

```
1. Toute fonction publique a une annotation de type de retour.
2. Aucun `except:` nu — toujours attraper des types précis.
3. Aucun `Optional[X]` — utiliser `X | None` (syntaxe Python 3.10+).
4. Aucun argument par défaut mutable.
5. Aucun `dict` ni `list` comme types de domaine — les envelopper dans des types nommés.
6. `dataclass(frozen=True)` pour tous les value objects.
7. `Result` pour les opérations qui peuvent échouer. Ne jamais retourner `None` comme signal d'erreur.
8. `Maybe/Option` pour la présence optionnelle. Ne jamais retourner `None` pour « non trouvé ».
9. Les modèles Pydantic vivent uniquement à la boundary — ils ne sont jamais passés dans la logique du domaine.
10. Les tests utilisent `assert` directement — pas de `assertEqual`, pas de style unittest.
11. Aucune exception comme control flow — les appelants ne doivent pas avoir besoin de try/except
    pour gérer les échecs attendus. Encapsuler la ValidationError de Pydantic en interne et
    exposer les échecs en `Result[T, str]`. Les exceptions sont réservées aux erreurs vraiment
    inattendues. But : un code lisible et maintenable où le happy path et le chemin d'erreur
    sont tous deux explicites dans le type de retour.
```

---

## 7. Mise en place du projet

```bash
# Bootstrap a session exercise directory
mkdir python_fp_session && cd python_fp_session
python -m venv .venv && source .venv/bin/activate

pip install pydantic "returns[compatible-mypy]" expression pytest hypothesis

# pyright
pip install pyright
cat > pyrightconfig.json << 'EOF'
{
  "typeCheckingMode": "strict",
  "pythonVersion": "3.12"
}
EOF

# Run all tests
pytest exercises/ -v

# Type check
pyright exercises/
```

---

## 8. Aide-mémoire

```
CONCEPT                  TOOL                    PATTERN
─────────────────────────────────────────────────────────────────
Value Object             dataclass(frozen=True)  Wrap + validate in __post_init__
Parse boundary           pydantic BaseModel      model_validate(raw_dict)
Parse domain             returns Result          @classmethod parse() → Result[Self, str]
Absent value             returns Maybe           Some(x) | Nothing
Composing failures       returns flow + bind     flow(parse, bind(validate), bind(save))
Illegal states           expression tagged_union match on tag, pyright checks exhaustion
Pipelines                expression pipe         pipe(value, fn1, fn2, fn3)
Immutable collections    expression Block/Map    Block([1,2,3])
Example tests            pytest                  def test_<unit>_<scenario>_<outcome>
Property tests           hypothesis @given       @given(st.text()) def test_invariant(...)
Type checking            pyright strict          pyrightconfig.json typeCheckingMode=strict
```
