# Defensive Programming from the Trenches
## Session de live coding — Guide de l'animateur

> **Format** : ~50 min · 6 modules · exemples Python · principes indépendants du langage  
> **Audience** : développeurs  
> **Objectif** : repartir en écrivant du code défensif par réflexe, sans délibération

---

## A tale of two worldviews

Ce guide montre volontairement côte à côte l'**idiome Pythonic** et l'**idiome FP-consistent**, car vous croiserez les deux dans la nature et vous devez savoir raisonner sur leurs compromis.

| | Pythonic Python | FP-consistent Python |
|---|---|---|
| Échec attendu | `raise ValueError` / retourner `None` | `return Failure(...)` |
| Validation au constructeur | `__post_init__` lève une exception | smart constructor qui retourne un `Result` |
| Control flow | `try / except` à chaque site d'appel | chaînes de `bind`, un seul handler en haut |
| Honnêteté de la signature | `def f(x) -> User` (ment : peut lever) | `def f(x) -> Result[User, E]` (toute la vérité) |

Aucune des deux ne s'impose partout. La voie Pythonic est plus courte et familière à tout développeur Python. La voie FP est plus honnête, plus composable, et passe mieux à l'échelle quand les chemins d'erreur se complexifient. Comprendre *pourquoi* elles divergent est ce que ce guide enseigne vraiment.

La règle utilisée tout au long :
- **Échecs du domaine / attendus** (erreur utilisateur, enregistrement manquant, âge < 18) → `Result`
- **Erreurs de programmation / violations d'invariant réelles** (ligne de base corrompue, branche inatteignable) → `raise`

---

## Avant de commencer

- Ouvrir un REPL Python ou un notebook à côté de ce guide
- Préparer un extrait « bad » pour l'exercice d'audit du Module 06 (voir la fin du document)
- Chaque module contient une paire **❌ Bad code** → **✅ Better code** : la taper en direct, sans la coller
- Les war stories marquées **⚔** sont à remplir avec vos propres histoires ; des emplacements sont prévus
- Le code de démo du Module 01 se trouve dans `LiveCoding/module_01_never_trust_input/` (point d'entrée : `README.md`)
- Le code de démo du Module 02 se trouve dans `LiveCoding/module_02_fail_fast_ROR/` (point d'entrée : `README.md`)
---

## Module 01 — Never trust input `~8 min`

> *« Le monde est plein de menteurs. Les appelants de votre fonction n'y font pas exception. »*

### Concept (2 min)
La validation appartient à la **boundary** : le moment où la donnée entre dans votre système (endpoint d'API, argument CLI, lecture de fichier, message de queue). Elle se fait là, et non trois couches plus bas quand quelque chose casse en silence.

### Live code (5 min)

**❌ Bad — faire confiance à l'appelant**
```python
def create_user(data: dict):
    name = data["name"]
    age  = data["age"]
    db.insert(name=name, age=age)
```

**✅ Pythonic — valider à la boundary avec Pydantic**
```python
from pydantic import BaseModel, Field, field_validator

class UserInput(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    age:  int  = Field(..., ge=0, le=150)

    @field_validator("name")
    @classmethod
    def no_empty_name(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("name cannot be blank")
        return v.strip()

def create_user(data: dict) -> None:
    user = UserInput(**data)   # raises ValidationError early, not later
    db.insert(name=user.name, age=user.age)
```

**Moment de démo** : appeler `create_user({"name": "", "age": -5})` et montrer que l'erreur est claire et précoce.

---

### Perspective FP : pourquoi un `raise` dans un constructeur est un mensonge

**Comment `@field_validator` fonctionne réellement** : quand vous appelez `UserInput(**data)`, Pydantic
génère un `__init__` qui exécute tous les validators en séquence. Votre `@field_validator("name")`
est injecté dans cet `__init__`. Le `raise ValueError(...)` du validator est attrapé
par Pydantic et relevé en `ValidationError` : vu de l'extérieur, le constructeur retourne un `UserInput`
ou explose.

Cela rejoint un principe plus large : *les constructeurs doivent rester sans logique* :

| Tradition | Comment ils le disent |
|---|---|
| Misko Hevery (Google / Angular) | « Constructors do no work » |
| FP / théorie des types | « Constructors are total; parsing is separate » |
| Parse don't validate (Alexis King) | « Convert unstructured data into structured data exactly once, at the boundary » |
| DDD | « Use factory methods, not constructors, for domain object creation » |

Toutes disent la même chose : **construction et validation sont deux opérations différentes**.
Les fusionner dans `__init__` crée une partial function, définie seulement sur les entrées valides,
alors que sa signature prétend fonctionner sur toutes les entrées.

Face à `UserInput(**data)`, la personne FP demande : *« Quel est le type de retour de cet appel ? »*
La réponse est `UserInput`, mais seulement si l'entrée est valide.
Si l'entrée est invalide, l'appel lève. Le vrai type est donc `UserInput | raises ValidationError`.
Le système de types de Python ne sait pas exprimer `| raises`, donc la signature **ment par omission**.

La correction FP-consistent est un **smart constructor** : une fonction simple, sans constructeur de classe,
qui rend l'échec explicite dans son type de retour :

```python
from pydantic import BaseModel, Field, ValidationError, field_validator
from returns.result import Result, Success, Failure


class UserInput(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    age:  int  = Field(..., ge=0, le=150)

    @field_validator("name")
    @classmethod
    def no_empty_name(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("name cannot be blank")
        return v.strip()


def parse_user(data: dict) -> Result[UserInput, str]:
    """Smart constructor: the only way to get a UserInput."""
    try:
        return Success(UserInput(**data))
    except ValidationError as e:
        first = e.errors()[0]
        return Failure(f"{first['loc'][0]}: {first['msg']}")


def create_user(data: dict) -> Result[None, str]:
    return parse_user(data).map(
        lambda user: db.insert(name=user.name, age=user.age)
    )
```

La signature de `parse_user` dit maintenant toute la vérité : elle réussit avec un `UserInput`
ou échoue avec un message. Aucun appelant n'a besoin de `try/except`.

**Laquelle choisir ?**
La version qui lève convient quand `create_user` est un endpoint web et que votre framework
attrape déjà `ValidationError` pour en faire un 422. La version `Result` est meilleure quand vous
composez plusieurs étapes de parsing, ou quand l'échec doit traverser plusieurs couches
sans semer des `try/except` partout.

---

### Points clés à dire à voix haute
- Whitelist ce qui est valide, ne blacklistez pas ce qui est mauvais
- Les type hints documentent l'intention ; Pydantic l'*impose* à l'exécution
- Falsehoods que croient les programmeurs : noms avec espaces, âges en chaînes, formats d'email « valides »
- Si votre framework gère `ValidationError` pour vous, la version Pythonic convient parfaitement ; le smart constructor brille quand vous possédez le chemin d'erreur

### ⚔ Emplacement de la war story
> *Votre histoire ici — par exemple un None passé à travers une entrée non validée et qui a corrompu un enregistrement trois sauts plus loin*

### Exercice (1 min)
> Ajouter à `UserInput` un champ `email` qui rejette les adresses sans symbole `@`.
> Écrire ensuite un smart constructor `parse_user` qui retourne `Result[UserInput, str]`.

---

## Module 02 — Fail fast, fail loud `~8 min`

> *« Si un échec est attendu, encodez-le dans le type. »*

### Concept (2 min)
Les échecs silencieux sont les bugs les plus coûteux. Retourner `None` et continuer avec un état invalide retarde l'explosion et corrompt des données en chemin.

Dans ce cours, **fail loud** signifie :

1. Les échecs attendus sont des valeurs explicites (`Result`), sans control flow caché.
2. Le chemin d'erreur est visible dans les signatures et impossible à ignorer par accident.

### Live code (5 min)

**❌ Bad — échec silencieux**
```python
def get_user(user_id: int):
    result = db.query(user_id)
    if not result:
        return None          # caller might not check this

def process_order(user_id: int):
    user = get_user(user_id)
    send_email(user.email)   # AttributeError: NoneType has no attribute 'email'
```

**✅ Better — échecs explicites + état invalide non représentable**
```python
from dataclasses import dataclass

from returns.result import Failure, Result, Success


@dataclass(frozen=True)
class ActiveUser:
    user_id: int
    email: str


@dataclass(frozen=True)
class UserNotFound:
    user_id: int


@dataclass(frozen=True)
class UserInactive:
    user_id: int


GetUserError = UserNotFound | UserInactive


def get_active_user(user_id: int) -> Result[ActiveUser, GetUserError]:
    row = db.query(user_id)
    if row is None:
        return Failure(UserNotFound(user_id))
    if not row.is_active:
        return Failure(UserInactive(user_id))
    return Success(ActiveUser(user_id=row.id, email=row.email))


def process_order_for_active_user(user: ActiveUser) -> None:
    send_email(user.email)


def process_order(user_id: int) -> Result[None, GetUserError]:
    return get_active_user(user_id).map(process_order_for_active_user)
```

**Moment de démo** : appeler `process_order(999)` et `process_order(inactive_id)`.
Montrer `Failure(UserNotFound(...))` / `Failure(UserInactive(...))` : explicites, typés, impossibles à ignorer.

---

> ### Perspective FP : pourquoi l'ADT d'erreurs compte plus que le wrapper Result
>
> L'alternative Pythonic serait une hiérarchie d'exceptions personnalisées :
> ```python
> class UserNotFoundError(Exception): ...
> class UserInactiveError(Exception): ...
> ```
> Les deux approches nomment les cas d'échec. La différence tient à **l'endroit où le compilateur vous aide**.
>
> Avec des exceptions, un appelant qui oublie de gérer `UserInactiveError` compile et s'exécute sans problème :
> l'erreur remonte en silence dans la pile jusqu'à ce que quelque chose attrape `Exception`.
> Avec `Result[ActiveUser, UserNotFound | UserInactive]`, un type checker (pyright/mypy) oblige
> l'appelant à inspecter le résultat avant d'utiliser la valeur. Vous ne pouvez pas traiter par accident
> un `Failure(UserInactive(...))` comme un `ActiveUser`.
>
> Le terme FP est **making illegal states unrepresentable au site d'appel**, et pas seulement
> au site de construction.

---

### ROP fail-fast (Python + Pydantic)
```python
from pydantic import BaseModel, ValidationError
from returns.pipeline import flow
from returns.pointfree import bind
from returns.result import Failure, Result, Success


class SignupSchema(BaseModel):
    email: str
    age: int


def parse_signup(raw: dict[str, object]) -> Result[SignupSchema, str]:
    try:
        parsed = SignupSchema.model_validate(raw)  # boundary parsing
        return Success(parsed)
    except ValidationError as error:
        first = error.errors()[0]
        field = str(first["loc"][0])
        msg = str(first["msg"])
        return Failure(f"{field}: {msg}")


def ensure_adult(data: SignupSchema) -> Result[SignupSchema, str]:
    if data.age < 18:
        return Failure("adult only")
    return Success(data)


def create_account(data: SignupSchema) -> Result[str, str]:
    return Success(f"created:{data.email}")


def signup(raw: dict[str, object]) -> Result[str, str]:
    return flow(
        parse_signup(raw),
        bind(ensure_adult),
        bind(create_account),
    )
```

Le premier `Failure` l'emporte : les étapes suivantes sont sautées automatiquement, donc le pipeline échoue vite sans exception cachée.

### Règle du loud failure — version courte
```python
# Expected domain failures: return Result
def reserve_stock(sku: str, qty: int) -> Result[None, OutOfStock]:
    ...

# Unexpected technical failures (bugs/corruption): raise
raise RuntimeError("unreachable branch hit")
```

### Pont vers le Module 03
Au Module 03, nous transformons les invariants en contrats explicites, puis nous allons plus loin avec
**illegal states unrepresentable** (contrats au niveau des types).

### ⚔ Emplacement de la war story
> *Votre histoire ici — par exemple un None propagé en silence dans un calcul financier*

### Exercice (1 min)
> Refactorer ceci pour retourner `Result[Config, ConfigError]` (ni `None`, ni exception pour un fichier manquant attendu) :
> ```python
> def parse_config(path: str):
>     if not os.path.exists(path):
>         return None
> ```

---

## Module 03 — Contracts & invariants `~8 min`

> *« Un contrat dit qui garantit quoi. Les invariants en sont une partie. »*

### Objectif (1 min)
À la fin de ce module, l'audience doit savoir distinguer et appliquer :

- Les contrats de fonction (**preconditions + postconditions**)
- Les invariants de classe (**doivent toujours tenir après la construction et après chaque mutation**)
- Les contrats au niveau des types (**illegal states unrepresentable**)

### Concept (2 min)
Un **contrat** comporte trois parties :

1. **Preconditions** : ce que l'appelant doit fournir.
2. **Postconditions** : ce que la fonction promet de retourner ou de garantir.
3. **Invariants** : ce qui doit toujours rester vrai pour des objets valides.

`Illegal states unrepresentable` est la forme de contrat la plus forte : les combinaisons invalides ne peuvent pas être construites.

Règle pratique pour l'enseignement et la conception :

1. Si une règle porte sur **une seule valeur**, l'encoder dans un **Value Object**.
2. Si une règle porte sur **les relations entre champs**, imposer un **invariant de classe**.
3. Si une règle porte sur **le cycle de vie / les états**, l'encoder dans des **types / variantes d'états**.

### Live code (5 min)

**Contrat de fonction = guard clauses + postcondition explicite**
```python
from returns.result import Failure, Result, Success


def compute_discount(price: float, pct: float) -> Result[float, str]:
    if price < 0:
        return Failure("price must be >= 0")
    if not (0 <= pct <= 100):
        return Failure("pct must be between 0 and 100")
    return Success(price * (1 - pct / 100))
```

- Preconditions : `price >= 0`, `0 <= pct <= 100`
- Postcondition : l'appelant reçoit toujours un `Result` (aucun `None` caché)

> **Le réflexe Pythonic : `assert`**
>
> Un développeur Python met naturellement des `assert price >= 0` en tête de fonction.
> C'est lisible, mais l'interpréteur ignore les `assert` avec `python -O`. La précondition disparaît alors en production.
> Une précondition de domaine doit exister dans tous les modes d'exécution : on la déplace dans le
> constructeur d'un type (voir plus bas) ou dans une garde qui retourne un `Result`.
> Gardons `assert` pour documenter une hypothèse du programmeur, jamais pour valider une entrée.

---

**Value Object — deux styles**

Le style Pythonic utilise `__post_init__` pour lever :

```python
# Pythonic: raises on bad input
@dataclass(frozen=True)
class PositiveAmount:
    value: float

    def __post_init__(self) -> None:
        if self.value <= 0:
            raise ValueError("amount must be positive")
```

> **Perspective FP — pourquoi un `__post_init__` qui lève est une partial function**
>
> `PositiveAmount(value=-1)` ressemble à un appel de constructeur normal.
> Son type de retour apparent est `PositiveAmount`. Pour une entrée négative, l'appel lève pourtant.
> C'est une **partial function** : définie sur une partie seulement de son domaine d'entrée,
> alors que la signature se prétend totale.
>
> Un constructeur total réussit ou retourne un échec explicite, sans jamais lever pour de la validation
> de domaine. La version FP-consistent utilise un smart constructor :
>
> ```python
> # FP-consistent: smart constructor, total function
> @dataclass(frozen=True)
> class PositiveAmount:
>     value: float  # private by convention — only create via PositiveAmount.create()
>
>     @classmethod
>     def create(cls, value: float) -> Result["PositiveAmount", str]:
>         if value <= 0:
>             return Failure(f"amount must be positive, got {value}")
>         return Success(cls(value=value))
> ```
>
> Chaque appelant est maintenant forcé par le système de types de traiter le cas d'échec avant de toucher
> au `PositiveAmount`. Aucun `try/except` nulle part : l'échec est simplement un `Failure`.
>
> **Laquelle choisir ?**
> Si `PositiveAmount` n'est jamais construit qu'à partir de données déjà validées (par exemple le schéma
> de votre base), la version qui lève convient : elle protège contre les erreurs de programmation, pas contre
> les erreurs utilisateur. Utilisez le smart constructor quand la valeur vient d'une entrée utilisateur ou de
> données externes.

---

**Pattern d'invariant de classe (pour les règles entre champs / d'état)**

Un Value Object suffit tant que la règle porte sur un seul état (`PositiveAmount`).
Dès que la règle relie une valeur à un état qui évolue (« un retrait ne peut pas dépasser le solde »),
le réflexe courant est de passer à un objet mutable avec un invariant de classe.
On part de cette forme traditionnelle, que l'audience connaît, puis on la fait évoluer en trois étapes :

1. **Étape 1 : invariant de classe traditionnel** (ci-dessous). Objet mutable, `raise`.
2. **Étape 2 : l'échec devient explicite au site d'appel** (`Result`).
3. **Étape 3 : design FP presque pur**. L'état lui-même devient un Value Object qui porte sa règle.

```python
# Pythonic: mutable object, invariant checked after each transition
@dataclass
class BankAccount:
    _balance: float = 0.0

    def __post_init__(self) -> None:
        self._ensure_invariant()

    def _ensure_invariant(self) -> None:
        if self._balance < 0:
            raise ValueError("invariant: balance cannot be negative")

    def deposit(self, amount: PositiveAmount) -> None:
        self._balance += amount.value
        self._ensure_invariant()

    def withdraw(self, amount: PositiveAmount) -> None:
        if amount.value > self._balance:
            raise ValueError("insufficient funds")
        self._balance -= amount.value
        self._ensure_invariant()
```

> **À pointer pendant le live : `amount.value`**
>
> Regardez `deposit` et `withdraw`. `BankAccount` ouvre `PositiveAmount`, extrait le `float`,
> puis refait l'arithmétique et la comparaison elle-même. Le code ne fait donc pas confiance au Value Object.
> Il s'en sert comme d'une boîte à `float`, parce que `PositiveAmount` ne sait rien faire de métier :
> il garantit seulement `> 0`. La logique « assez de fonds ? » et « nouveau solde » vit ailleurs, dans
> la classe, et `_balance` reste un `float` nu que l'invariant doit surveiller après chaque mutation.
> Chaque `.value` signale une règle métier qui n'a pas encore trouvé son type.

> **Perspective FP — rendre l'échec explicite au site d'appel**
>
> `withdraw` lève pour un événement de domaine attendu (fonds insuffisants).
> La version FP-consistent retourne un `Result`, pour que l'appelant voie l'échec dans le type :
>
> ```python
> @dataclass(frozen=True)
> class InsufficientFunds:
>     requested: float
>     available: float
>
>
> @dataclass
> class BankAccount:
>     _balance: float = 0.0
>
>     def deposit(self, amount: PositiveAmount) -> None:
>         self._balance += amount.value  # always succeeds given PositiveAmount
>
>     def withdraw(self, amount: PositiveAmount) -> Result[None, InsufficientFunds]:
>         if amount.value > self._balance:
>             return Failure(InsufficientFunds(
>                 requested=amount.value, available=self._balance
>             ))
>         self._balance -= amount.value
>         return Success(None)
> ```
>
> L'invariant `_balance >= 0` tient maintenant **par construction** : `withdraw` refuse simplement
> de descendre sous zéro et dit pourquoi à l'appelant, au lieu de lever après coup.
> Plus besoin d'un appel externe à `_ensure_invariant()`, car la mutation n'a lieu que sur la
> branche `Success`.
>
> C'est un premier pas. `BankAccount` manipule toujours des `float` et compare `amount.value > self._balance`
> elle-même : la règle reste dans la classe, protégée par une discipline de relecture.

> **Perspective FP — design presque pur : le solde devient un Value Object**
>
> On applique deux règles à `BankAccount` :
>
> - elle ne manipule plus aucun `float` ;
> - elle ne lit jamais l'intérieur d'un Value Object (`.value`, `._value`).
>
> Toute question et toute arithmétique passent par des opérations sur les types `Balance` et `PositiveAmount`.
> Les `float` ne sont touchés que dans le module qui définit ces Value Objects, le seul endroit
> où la règle « jamais négatif » existe.
>
> ```python
> @dataclass(frozen=True)
> class InsufficientFunds:
>     requested: PositiveAmount   # des VO, plus de float
>     available: "Balance"
>
>
> @dataclass(frozen=True)
> class Balance:
>     _value: float = 0.0  # privé par convention : seul ce module le lit
>
>     def has_enough_funds(self, amount: PositiveAmount) -> bool:
>         return amount._value <= self._value
>
>     def after_deposit(self, amount: PositiveAmount) -> "Balance":
>         return Balance(self._value + amount._value)  # total : un dépôt réussit toujours
>
>     def after_withdraw(self, amount: PositiveAmount) -> Result["Balance", InsufficientFunds]:
>         if not self.has_enough_funds(amount):
>             return Failure(InsufficientFunds(requested=amount, available=self))
>         return Success(Balance(self._value - amount._value))
>
>
> @dataclass
> class BankAccount:
>     _balance: Balance = field(default_factory=Balance)
>
>     def deposit(self, amount: PositiveAmount) -> None:
>         self._balance = self._balance.after_deposit(amount)
>
>     def withdraw(self, amount: PositiveAmount) -> Result[None, InsufficientFunds]:
>         return self._balance.after_withdraw(amount).map(self._replace_balance)
>
>     def _replace_balance(self, new_balance: Balance) -> None:
>         self._balance = new_balance
> ```
>
> Ce que l'audience doit voir :
>
> - `Balance` **porte sa propre précondition**. Il n'existe aucun chemin pour fabriquer un solde négatif,
>   donc `_ensure_invariant()` disparaît.
> - `BankAccount` ne contient plus aucune règle. Elle orchestre : elle demande un nouveau `Balance`
>   et le range si l'opération réussit.
> - Les opérations se **composent** par les types : `after_withdraw` retourne un `Result`, qu'on enchaîne
>   avec `.map` / `.bind` (`solde.after_withdraw(a).bind(lambda s: s.after_withdraw(b))`).
>   C'est une monade en devenir : on compose des opérations qui peuvent échouer
>   sans jamais ouvrir la valeur.
> - Le critère de qualité : si on réécrit `Balance` avec des `Decimal` ou des centimes entiers,
>   `BankAccount` ne change pas d'une ligne.
>
> Note Python : les noms des méthodes sont en `snake_case` (`has_enough_funds`, `after_withdraw`).
> L'objet `BankAccount` reste mutable (il remplace son `Balance`) ; seules les valeurs sont immuables.
> Une version entièrement pure retournerait un nouveau `BankAccount` à chaque opération.

---

Pattern à dire à voix haute :
1. Vérifier l'invariant après la construction.
2. Pousser les preconditions sur une seule valeur dans des Value Objects (`PositiveAmount`).
3. Revérifier l'invariant après chaque transition d'état.
4. Pour les **échecs de domaine** (attendus, récupérables), préférer `Result` à `raise`.
5. Réserver `raise` aux **erreurs de programmation** : les conditions qui ne devraient jamais se produire si le code est correct.
6. Quand le code extrait la valeur d'un Value Object (`.value`) pour raisonner dessus, déplacer ce raisonnement
   dans le Value Object : `has_enough_funds`, `after_withdraw`. L'objet qui possède la règle l'applique.

**Illegal states unrepresentable (contrat au niveau des types)**
```python
from dataclasses import dataclass


@dataclass(frozen=True)
class DraftOrder:
    order_id: str


@dataclass(frozen=True)
class ConfirmedOrder:
    order_id: str


def confirm(order: DraftOrder) -> Result[ConfirmedOrder, str]:
    ...

# No "is_confirmed: bool" flags, no nullable half-state.
# `ship(order: ConfirmedOrder)` cannot be called with DraftOrder.
```

**L'immutabilité comme amplificateur de contrat**
```python
@dataclass(frozen=True)
class Config:
    db_url: str
    max_retries: int
```

Une fois créé, `Config` ne peut pas dériver vers un état invalide par mutation accidentelle.

### Exercice (1 min)
> Choisir une fonction de votre codebase et noter :
> 1) une precondition,
> 2) une postcondition,
> 3) un invariant.
>
> Puis les imposer explicitement dans le code, et décider pour chacun : `raise` ou `Result` ?

---

## Module 04 — Handling external dependencies `~10 min`

> *« Tout ce qui est hors de votre process est hostile : APIs, bases, filesystem, temps. »*

### Concept (2 min)
Les appels externes vont : expirer (timeout), retourner des formes inattendues, retourner 200 avec une erreur dans le corps, réussir au premier appel et échouer au retry, et s'exécuter deux fois à cause de votre logique de retry. Concevez en tenant compte de tout cela.

### Live code (6 min)

**Toujours un timeout**
```python
import httpx

# ❌ No timeout — hangs forever
response = httpx.get("https://api.example.com/data")

# ✅ Explicit timeout on connect AND read
response = httpx.get(
    "https://api.example.com/data",
    timeout=httpx.Timeout(connect=2.0, read=5.0)
)
```

**Retry avec exponential backoff + jitter**
```python
import time, random

def with_retry(fn, max_attempts=3, base_delay=0.5):
    for attempt in range(max_attempts):
        try:
            return fn()
        except (httpx.TimeoutException, httpx.NetworkError) as e:
            if attempt == max_attempts - 1:
                raise
            delay = base_delay * (2 ** attempt) + random.uniform(0, 0.3)
            time.sleep(delay)
```

**Circuit breaker (minimal, 20 lignes)**
```python
from datetime import datetime, timedelta

class CircuitBreaker:
    def __init__(self, threshold=5, timeout=30):
        self.failures   = 0
        self.threshold  = threshold
        self.timeout    = timedelta(seconds=timeout)
        self.opened_at  = None

    def call(self, fn):
        if self.opened_at:
            if datetime.now() - self.opened_at < self.timeout:
                raise RuntimeError("circuit open — service unavailable")
            self.opened_at = None   # half-open: allow one probe

        try:
            result = fn()
            self.failures = 0       # success — reset
            return result
        except Exception:
            self.failures += 1
            if self.failures >= self.threshold:
                self.opened_at = datetime.now()
            raise
```

**Ne jamais faire confiance à la forme — valider aussi la réponse**
```python
# ❌ Assumes API behaves
data = response.json()
user_id = data["user"]["id"]

# ✅ Defensive parsing
data = response.json()
user = data.get("user") or {}
user_id = user.get("id")
if not user_id:
    raise ExternalServiceError(f"unexpected response shape: {data}")
```

### ⚔ Emplacement de la war story
> *Votre histoire ici — par exemple l'API tierce qui retournait HTTP 200 avec `{"status": "error"}` dans le corps*

### Exercice (1 min)
> Ajouter un timeout et un seul retry à cet appel :
> ```python
> def fetch_exchange_rate(currency: str) -> float:
>     return httpx.get(f"https://api.rates.io/{currency}").json()["rate"]
> ```

---

## Module 05 — Concurrency traps `~8 min`

> *« Le code concurrent ne plante pas dans les tests. Il plante en production, à 2 h du matin. »*

### Concept (2 min)
Le GIL de Python protège de certaines race conditions en CPython, mais pas de toutes, ni dans asyncio, ni entre processus. Le pari le plus sûr : concevoir dès le départ des opérations **idempotent**.

### Live code (4 min)

**TOCTOU — time-of-check to time-of-use**
```python
import os

# ❌ Race: file could be deleted between check and open
if os.path.exists(path):
    with open(path) as f:    # FileNotFoundError possible here
        data = f.read()
```

**Correction Pythonic — demander pardon, pas la permission**
```python
# Pythonic: exception used for control flow
try:
    with open(path) as f:
        data = f.read()
except FileNotFoundError:
    data = None
```

> **Perspective FP — la correction Pythonic cache encore l'échec**
>
> Le `try/except` règle la race mais introduit un nouveau problème : `data` vaut maintenant
> `str | None`, et un appelant qui oublie de tester `None` plante plus tard avec un
> `AttributeError`, exactement le pattern d'échec silencieux que le Module 02 déconseille.
>
> La correction FP-consistent garde l'idée de « demander pardon » mais rend l'absence explicite
> dans le type de retour :
>
> ```python
> from returns.result import Result, Success, Failure
>
>
> def read_file(path: str) -> Result[str, FileNotFoundError]:
>     try:
>         with open(path) as f:
>             return Success(f.read())
>     except FileNotFoundError as e:
>         return Failure(e)
> ```
>
> L'appelant *ne peut pas* utiliser le contenu sans avoir traité le cas du fichier manquant.
> Le `try/except` reste là (Python en a besoin pour détecter la race), mais l'échec apparaît
> dans le type au lieu d'être remplacé en silence par `None`.
>
> **Laquelle choisir ?**
> Si `data = None` aboutit dans un seul `if data:` juste en dessous, la version Pythonic
> convient : elle est lisible et le scope est minuscule. Utilisez `Result` quand le contenu
> traverse plusieurs couches avant d'être consommé.

---

**asyncio : le piège du fire-and-forget silencieux**
```python
import asyncio

# ❌ Task is scheduled but exceptions are silently swallowed
asyncio.create_task(send_email(user))

# ✅ Keep a reference, handle exceptions
async def safe_task(coro):
    try:
        await coro
    except Exception as e:
        logger.error("background task failed", exc_info=e)

task = asyncio.create_task(safe_task(send_email(user)))
```

**Pattern de l'idempotency key**
```python
def process_payment(order_id: str, amount: float, idempotency_key: str):
    if db.payment_exists(idempotency_key):
        return db.get_payment(idempotency_key)   # safe to retry
    
    result = payment_gateway.charge(amount)
    db.save_payment(idempotency_key, result)
    return result
```

### ⚔ Emplacement de la war story
> *Votre histoire ici — par exemple un double débit causé par un retry réseau sans idempotency key*

### Modèle mental rapide à partager
> *« Si cette fonction s'exécutait deux fois simultanément avec la même entrée, qu'est-ce qui casserait ? »*  
> Si la réponse est « rien », elle est idempotent. Visez cela partout où cela compte.

### Quiz (1 min)
> Qu'est-ce qui cloche dans ce code asyncio ?
> ```python
> async def handler(request):
>     asyncio.create_task(log_request(request))
>     return Response(200)
> ```

---

## Module 06 — Review & reflex `~8 min`

> *« Le but : des patterns défensifs qui deviennent automatiques, sans délibération. »*

### Checklist de code review (à imprimer / partager en gist)

```
INPUTS
  [ ] All external inputs validated at the boundary
  [ ] No implicit trust of dict keys without .get() or a schema
  [ ] File paths, env vars, and config values checked before use

FAILURES
  [ ] No bare `except:` or `except Exception: pass`
  [ ] Functions return meaningful types — no None-as-error
  [ ] Expected domain failures use Result, not raise
  [ ] Custom exceptions reserved for programming errors / infrastructure failures

EXTERNAL CALLS
  [ ] Every HTTP/DB call has a timeout
  [ ] Retries are bounded and use backoff
  [ ] Response shape is validated, not assumed

CONCURRENCY
  [ ] Shared mutable state accessed only under a lock
  [ ] asyncio tasks are awaited or tracked
  [ ] State-changing operations are idempotent where possible

INVARIANTS
  [ ] Preconditions documented and enforced
  [ ] Guard clauses at the top, happy path flat
  [ ] Mutable shared objects replaced with frozen ones where feasible
  [ ] Smart constructors used when invalid construction is a domain failure
```

### Exercice d'audit en live (5 min)

**Coller cet extrait et demander à l'audience de trouver les bugs**
```python
def transfer_funds(from_id, to_id, amount):
    sender   = db.get_user(from_id)
    receiver = db.get_user(to_id)

    if sender.balance >= amount:
        sender.balance   -= amount
        receiver.balance += amount
        db.save(sender)
        db.save(receiver)
        notify_service.send(f"Transfer of {amount} complete")

    return True
```

**Bugs à faire émerger (laisser l'audience les trouver d'abord)**
- `db.get_user()` peut retourner `None`, sans guard
- Aucune validation sur `amount` (négatif ? zéro ? précision des floats ?)
- Race condition : la vérification du solde et le débit ne sont pas atomiques
- `db.save(sender)` peut réussir et `db.save(receiver)` échouer : pas de transaction
- `notify_service.send()` est un appel externe fire-and-forget sans timeout ni retry
- Retourne toujours `True`, même si rien ne s'est passé

**Question bonus FP** : à quoi ressemblerait la signature d'un `transfer_funds` correct ?
```python
@dataclass(frozen=True)
class TransferFailed:
    reason: str

def transfer_funds(
    from_id: int,
    to_id: int,
    amount: PositiveAmount,
) -> Result[None, TransferFailed]:
    ...
```
Le type `PositiveAmount` élimine le bug du montant négatif ou nul avant même l'exécution du corps de la fonction.
Le retour `Result` rend impossible, pour les appelants, d'ignorer un transfert raté.

### Phrase de clôture à laisser à l'écran
> *« Le code défensif traduit du respect pour les conditions réelles d'exploitation du système, sans une once de pessimisme. »*

---

## Annexe — Pour aller plus loin

- *A Philosophy of Software Design* — John Ousterhout (chapitre 10 : Define Errors Out Of Existence)
- *Designing Distributed Systems* — Brendan Burns (idempotency, circuit breakers)
- *Domain Modelling Made Functional* — Scott Wlaschin (la référence pour illegal states unrepresentable, smart constructors et pipelines basés sur Result)
- Bibliothèque Python `returns` — `Result`, `bind`, `flow` pour Python
- Bibliothèque Python `tenacity` — décorateur de retry de niveau production
- Documentation Python `pydantic` v2 — validation à la boundary
- Falsehoods Programmers Believe About Names — kalzumeus.com

---

*Guide version 1.2 — enrichir les war stories avant la session*
