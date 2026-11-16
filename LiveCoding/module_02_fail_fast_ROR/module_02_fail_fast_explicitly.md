# Module 02 — Fail Fast, Fail Explicitly
## Plan détaillé · ~9 minutes live · Defensive Programming from the Trenches

> *Soyez bruyants. Soyez clairs. Mais restez polis. Les exceptions sont impolies : elles interrompent tout, contournent la pile d'appels et laissent l'appelant deviner. Les résultats explicites parlent calmement et portent toute l'information.*

Point d'entrée : [`README.md`](README.md). Slides : [`presentation.md`](presentation.md). Source de pilotage : le Module 02 de `defensive_programming_live_coding_guide.md`.

---

## Fichiers du live

Tout ce que vous tapez ou montrez en direct se trouve dans `1_live/`.

| Fichier | Slide | Contenu |
|---|---|---|
| `1_live/0_probleme_exceptions_invisibles.py` | « Le problème » | ❌ Exceptions pour des résultats attendus |
| `1_live/ecriture_1_result_maison.py` | Écriture 1 | ✅ `Ok` / `Err` écrits à la main |
| `1_live/ecriture_2_railway_bind.py` | Écriture 2 | ✅ Railway : `bind` enchaîne les étapes |
| `1_live/ecriture_3_returns.py` | Écriture 3 | ✅ `returns` : `flow`, `bind`, `@safe` |
| `1_live/test_ecriture_*.py` | | Tests de chaque écriture |

Les approfondissements hors live sont dans `2_pour_aller_plus_loin/`.

---

## Vue d'ensemble

| | |
|---|---|
| **Durée** | 9 minutes (live) + 5 min d'exercice si asynchrone |
| **Principe central** | Fail fast, mais en types, sans interruption. Un échec attendu est une valeur de retour, pas une exception. |
| **Focus Python** | `Result[T, E]` maison → Railway Oriented Programming → bibliothèque `returns` |
| **Profondeur théorique** | Moyenne : nommer les concepts, montrer le code, laisser mypy démontrer |
| **Ce que le public retient** | Je sais encoder l'échec dans le système de types : explicite, composable, impossible à ignorer |

---

## Objectifs d'apprentissage

1. Expliquer pourquoi les exceptions sont le mauvais outil pour les échecs attendus
2. Construire et lire un type `Result[T, E]` minimal
3. Enchaîner les opérations façon Railway, sans pyramide de try/except
4. Savoir quand utiliser la bibliothèque `returns` et quand écrire son propre `Result`

---

## Timing de l'instructeur

```
00:00 — 01:00   Accroche : les exceptions sont impolies (60 s)
01:00 — 02:00   Concept : deux niveaux d'explicite, les nommer (60 s)
02:00 — 03:30   Le problème : exceptions comme control flow (90 s)
03:30 — 05:30   Live : écrire Result[T, E] à la main (2 min)
05:30 — 07:30   Live : Railway, chaîne de bind + schéma (2 min)
07:30 — 08:30   Montrer : bibliothèque returns + @safe (60 s)
08:30 — 09:00   Conclusion : spectre + direction à suivre (30 s)
```

---

## Partie 1 — Accroche (60 s)

**Ouvrir avec :**

> « Nous voulons échouer vite. Absolument. Détecter les problèmes tôt, les faire remonter immédiatement, ne jamais laisser un mauvais état se propager. Mais *la façon* de les signaler compte. »

**Pause. Puis :**

> « Les exceptions sont impolies. Elles ne retournent pas de valeur : elles *interrompent*. Elles contournent toute votre pile d'appels, déroulent les frames, et obligent chaque appelant en amont à tout envelopper dans un try/except ou à ignorer le problème en silence. Et elles sont *invisibles* dans la signature : impossible de savoir que `get_user()` peut échouer sans lire son code ou sa doc. C'est un piège, pas de l'explicite. »

**Le recadrage :**

> « Fail fast, oui. Mais fail *explicitly* : parlez en types. Un échec attendu est une valeur de retour parfaitement valide. Il doit être aussi visible dans la signature que le cas de succès. Si "utilisateur introuvable" est une issue normale d'une recherche d'utilisateur, il appartient au type de retour, pas à une exception. »

**Planter la graine :**

> « Il existe un style de programmation qui rend cela concret : le Railway Oriented Programming. Nous y arrivons. Construisons pas à pas. »

### ⚔ Emplacement de la war story

> *Votre histoire ici. Angle suggéré : une exception avalée ou un `except: pass` qui a transformé une vraie erreur en mauvaise branche silencieuse. Pas un crash, une décision erronée prise avec assurance. Un paiement traité deux fois. Un enregistrement mis à jour avec des données périmées. Les échecs coûteux ne sont jamais les crashs, ce sont les silencieux.*

---

## Partie 2 — Concept : deux niveaux d'explicite (60 s)

**Dire, sans code, juste pour orienter le public :**

> « Cette idée a deux niveaux, complémentaires. »

**Niveau 1 — Signatures honnêtes :** le type de retour dit que la fonction peut échouer, et quel genre d'échec. L'appelant *ne peut pas* l'ignorer, c'est dans le type. C'est `Result[T, E]`, ce que nous construisons aujourd'hui.

**Niveau 2 — États illégaux impossibles :** restructurer les types pour que l'état invalide *ne puisse pas être construit*. Il n'est pas détecté, il est impossible. Ce sont les sum types et les hiérarchies de classes scellées. Nous les couvrons au Module 03.

> « Aujourd'hui : le niveau 1. Rendre les chemins d'échec aussi visibles que le chemin de succès. »

---

## Partie 3 — Le problème : exceptions comme control flow (90 s)

> **Note instructeur** : fichier `1_live/0_probleme_exceptions_invisibles.py`. À taper ou à montrer en direct. Le point porte quand le public voit la quantité de *connaissance cachée* que l'appelant transporte. Lancer le fichier : 4 utilisateurs, 4 messages.

```python
# ❌ Exceptions pour des résultats attendus : impolies et invisibles
def get_user(user_id: int) -> User:
    user = db.find(user_id)
    if not user:
        raise UserNotFoundError(user_id)
        # « Utilisateur introuvable » est une issue parfaitement normale.
        # Rien dans la signature ne prévient l'appelant.
        # Le type de retour dit "User" : il ment.

def get_account(user: User) -> Account:
    account = db.get_account(user.id)
    if not account:
        raise AccountNotFoundError(user.id)   # même mensonge

def get_balance(account: Account) -> float:
    if account.suspended:
        raise AccountSuspendedError()         # même mensonge

# L'appelant paie le prix de trois mensonges
def process(user_id: int):
    try:
        user    = get_user(user_id)
        account = get_account(user)
        balance = get_balance(account)
        return balance
    except UserNotFoundError: ...
    except AccountNotFoundError: ...
    except AccountSuspendedError: ...
    # Chaque clause except = une connaissance que le système de types n'a pas donnée.
    # Une connaissance que chaque appelant doit redécouvrir, pour toujours.
```

**Dire :** « Comptez ce que l'appelant devait *savoir* sans que le système de types le lui dise : trois types d'exception, leurs noms, les moments où elles sont levées. C'est de la connaissance implicite dispersée dans le code, que le prochain développeur oubliera, ou vous-même dans six mois. »

**Puis :** « Corrigeons les signatures. »

---

## Partie 4 — Live : Result[T, E] (2 min)

> **Note instructeur** : c'est le cœur du module. Fichier `1_live/ecriture_1_result_maison.py`. Taper lentement. Le but est de démystifier : montrer que ce sont 30 lignes, pas de la magie.

### Le type (60 s)

```python
from dataclasses import dataclass
from typing import TypeVar, Generic, Callable

T = TypeVar("T")
E = TypeVar("E")
U = TypeVar("U")

@dataclass(frozen=True)
class Ok(Generic[T]):
    value: T

    def map(self, fn: Callable[[T], U]) -> "Ok[U]":
        return Ok(fn(self.value))

    def bind(self, fn: Callable[[T], "Result[U, E]"]) -> "Result[U, E]":
        return fn(self.value)        # succès : on continue

    def unwrap(self) -> T:
        return self.value

@dataclass(frozen=True)
class Err(Generic[E]):
    error: E

    def map(self, fn):   return self   # erreur : on passe, on saute fn
    def bind(self, fn):  return self   # erreur : on passe, on saute fn

    def unwrap(self):
        raise RuntimeError(f"unwrap() on Err: {self.error}")

Result = Ok[T] | Err[E]
```

**Dire :** « Voilà tout. `Ok` porte une valeur de succès. `Err` porte une valeur d'échec. Les deux sont des valeurs simples : pas d'interruption, pas de déroulement de pile. Et regardez `bind` sur `Err` : il renvoie `self`. C'est la clé. Les erreurs sautent automatiquement tout ce qui suit. »

### Signatures honnêtes (60 s)

```python
@dataclass(frozen=True)
class UserNotFound:
    user_id: int

@dataclass(frozen=True)
class AccountNotFound:
    user_id: int

@dataclass(frozen=True)
class AccountSuspended:
    account_id: str

# La signature est maintenant honnête : elle dit tout
def get_user(user_id: int) -> Result[User, UserNotFound]:
    user = db.find(user_id)
    return Ok(user) if user else Err(UserNotFound(user_id))

def get_account(user: User) -> Result[Account, AccountNotFound]:
    account = db.get_account(user.id)
    return Ok(account) if account else Err(AccountNotFound(user.id))

def get_balance(account: Account) -> Result[float, AccountSuspended]:
    if account.suspended:
        return Err(AccountSuspended(account.id))
    return Ok(account.balance)
```

**Dire :** « Pas de doc à lire, pas de code source à fouiller. Le type de retour est la documentation. Un nouveau développeur lit `Result[User, UserNotFound]` et sait aussitôt : cela peut réussir avec un User, ou échouer avec un UserNotFound. C'est de l'explicite. »

---

## Partie 5 — Live : Railway (2 min)

> **Note instructeur** : fichier `1_live/ecriture_2_railway_bind.py`. Les fonctions `get_balance_without_railway` puis `get_balance_railway` montrent l'avant et l'après.

### Sans Railway : encore verbeux (30 s)

```python
# ✅ Explicite, mais fastidieux : un test à chaque étape
def process(user_id: int) -> Result[float, object]:
    user_result = get_user(user_id)
    if user_result.is_err():
        return user_result

    account_result = get_account(user_result.unwrap())
    if account_result.is_err():
        return account_result

    return get_balance(account_result.unwrap())
```

**Dire :** « Mieux que les exceptions, mais bruyant. Chaque étape est un test. Le chemin de succès est enfoui. »

### Avec Railway : bind enchaîne (60 s)

```python
# ✅✅ Railway : bind s'occupe du routage
def process(user_id: int) -> Result[float, object]:
    return (
        get_user(user_id)
        .bind(get_account)
        .bind(get_balance)
    )

# Usage : match exhaustif, aucune surprise
match process(42):
    case Ok(value=balance):              print(f"Balance: {balance}")
    case Err(error=UserNotFound()):      print("User not found")
    case Err(error=AccountNotFound()):   print("Account not found")
    case Err(error=AccountSuspended()):  print("Account suspended")
```

### Dessiner au tableau (30 s)

```
get_user ──Ok──► get_account ──Ok──► get_balance ──Ok──► float
            │                   │                   │
           Err                 Err                 Err
            │                   │                   │
            └───────────────────┴───────────────────┴──► erreur (se route seule, poliment)
```

**Dire :** « Deux voies. La voie Ok est votre chemin de succès : trois mots, plat, lisible. La voie Err : les erreurs se routent seules autour de tout ce qui suit, sans qu'on leur dise. Pas de try/except. Pas de control flow caché. C'est le Railway Oriented Programming. Scott Wlaschin l'a inventé pour F#, mais l'idée est universelle. »

---

## Partie 6 — La bibliothèque `returns` (60 s)

> **Note instructeur** : fichier `1_live/ecriture_3_returns.py`.

> *« Tout ce que nous avons écrit à la main existe en version production dans `returns`, de dry-python. »*

```bash
pip install returns
```

```python
from returns.result import Result, Success, Failure
from returns.pipeline import flow
from returns.pointfree import bind

def get_user(user_id: int) -> Result[User, UserNotFound]:
    user = db.find(user_id)
    return Success(user) if user else Failure(UserNotFound(user_id))

# flow() est la chaîne Railway : plus besoin d'appels .bind()
pipeline = flow(
    get_user,
    bind(get_account),
    bind(get_balance),
)

result = pipeline(42)
```

**La fonctionnalité phare, `@safe` :**

```python
from returns.result import safe

# Enveloppe toute fonction qui lève une exception en Result, automatiquement
@safe
def parse_config(path: str) -> dict:
    return json.loads(open(path).read())   # lève sur JSON invalide ou fichier absent

parse_config("config.json")    # → Success({...})
parse_config("missing.json")   # → Failure(FileNotFoundError(...))
```

**Dire :** « `@safe` est votre pont entre le monde qui lève des exceptions (bibliothèques tierces, stdlib) et votre pipeline Railway. Enveloppez une fois à la boundary, parlez Result partout à l'intérieur. »

---

## Sidebar : le compromis Pythonic (note instructeur, à ne pas démontrer en live)

> *Pour les équipes où Result représente un trop grand pas culturel, un retour en `NamedTuple` reste meilleur que des exceptions comme control flow :*

```python
from typing import NamedTuple

class UserResult(NamedTuple):
    user:  User | None
    error: str | None

def get_user(user_id: int) -> UserResult:
    user = db.find(user_id)
    return UserResult(user=user, error=None) if user \
        else UserResult(user=None, error=f"user {user_id} not found")
```

> *Signature honnête, erreur explicite, mais pas chaînable. À présenter comme une marche intermédiaire, pas comme la destination.*

---

## Exercice (seul ou en binôme, 5 min)

### Énoncé

Un pipeline de checkout. Trois étapes, chacune peut échouer explicitement.

```python
# Avec ces stubs, faites-les parler Result

@dataclass(frozen=True)
class Cart:
    id:    str
    total: float

@dataclass(frozen=True)
class ChargeReceipt:
    charge_id: str
    amount:    float

# 1. Définir une dataclass d'erreur typée pour chaque cas d'échec
# 2. Implémenter chaque fonction avec un retour Result
# 3. Les chaîner avec .bind()
# 4. Traiter le résultat final avec match

def validate_cart(cart_id: str) -> Result[Cart, ???]: ...
def apply_discount(cart: Cart, code: str) -> Result[Cart, ???]: ...
def charge_card(cart: Cart, token: str) -> Result[ChargeReceipt, ???]: ...
```

### Solution

```python
@dataclass(frozen=True)
class CartNotFound:    cart_id: str
@dataclass(frozen=True)
class CartEmpty:       cart_id: str
@dataclass(frozen=True)
class DiscountExpired: code: str
@dataclass(frozen=True)
class CardDeclined:    reason: str

def validate_cart(cart_id: str) -> Result[Cart, CartNotFound | CartEmpty]:
    if cart_id == "missing": return Err(CartNotFound(cart_id))
    if cart_id == "empty":   return Err(CartEmpty(cart_id))
    return Ok(Cart(id=cart_id, total=99.99))

def apply_discount(cart: Cart, code: str) -> Result[Cart, DiscountExpired]:
    if code == "EXPIRED": return Err(DiscountExpired(code))
    return Ok(Cart(id=cart.id, total=cart.total * 0.9))

def charge_card(cart: Cart, token: str) -> Result[ChargeReceipt, CardDeclined]:
    if token == "declined": return Err(CardDeclined("insufficient funds"))
    return Ok(ChargeReceipt(charge_id="CH-001", amount=cart.total))

def checkout(cart_id: str, code: str, token: str) -> Result[ChargeReceipt, object]:
    return (
        validate_cart(cart_id)
        .bind(lambda cart: apply_discount(cart, code))
        .bind(lambda cart: charge_card(cart, token))
    )

match checkout("cart-123", "SAVE10", "tok_visa"):
    case Ok(value=receipt):              print(f"Charged {receipt.amount}")
    case Err(error=CartNotFound()):      print("Cart not found")
    case Err(error=CartEmpty()):         print("Cart is empty")
    case Err(error=DiscountExpired()):   print("Discount expired")
    case Err(error=CardDeclined(r)):     print(f"Card declined: {r}")
```

**Points de discussion :**
- Le lambda dans `.bind(lambda cart: apply_discount(cart, code))` est l'aspérité ergonomique principale de Python face à F#. `returns` propose des helpers `partial` pour cela.
- Où vit ce pipeline dans FastAPI/Django ? Dans la couche service. La vue traduit `Ok` → 200, `Err` → 4xx.
- Que met-on dans `except` maintenant ? Seulement le vraiment exceptionnel : panne de connexion à la base, timeout réseau, `None` inattendu venant d'un bug de bibliothèque.

---

## Points clés

1. **Les exceptions servent à l'exceptionnel** : pannes d'infrastructure, bugs, imprévu. Les issues métier attendues n'en font pas partie.
2. **Signatures honnêtes.** `Result[User, UserNotFound]` dit tout avant d'exécuter le code.
3. **Railway Oriented Programming** : deux voies, `bind` fait le routage. Le chemin de succès reste plat.
4. **`@safe`** ramène le monde des exceptions dans votre pipeline Railway.
5. **États illégaux** : c'est le Module 03.

---

## Le spectre

```
Exceptions          Retours nommés      Result[T, E]        ADT complets
(impolies :         (honnêtes,          (explicite,         (types scellés,
 invisibles,         pas chaînables)     chaînable,          rien d'illégal)
 non typées)                             vérifié par types)

   ◄──────────────────────────────────────────────────────────────►
   le plus courant                                     le plus explicite
   en Python aujourd'hui                              en Python aujourd'hui
```

> *« Inutile d'aller tout à droite dès le premier jour. Mais connaissez la direction, et comprenez ce que vous sacrifiez en restant à gauche. »*

---

## Pour aller plus loin (hors live)

`2_pour_aller_plus_loin/1_value_objects_gardiens/` : un `Amount` qui garantit sa validité dès la construction, combiné au ROP. Prépare le Module 03.

---

## Références

- *Railway Oriented Programming*, Scott Wlaschin, fsharpforfun.com
- Bibliothèque `returns` : https://returns.readthedocs.io
- PEP 634, Structural Pattern Matching (Python 3.10+)
- *Domain Modeling Made Functional*, Scott Wlaschin (F#, les idées se transposent directement)

---

*Module 02 sur 6 · Defensive Programming from the Trenches*
