---
marp: true
theme: default
paginate: true
title: Module 02 — Fail fast, fail explicitly
---

<!--
Présentation du Module 02, au format Marp (une diapositive = un bloc entre `---`).
Affichage : extension VS Code « Marp for VS Code », ou `npx @marp-team/marp-cli presentation.md --html`.
Les notes de l'instructeur sont dans les commentaires HTML sous chaque diapositive.
Fichiers de code : dossier 1_live/ (voir README.md).
-->

# Fail fast, fail explicitly

## Module 02 — Defensive Programming from the Trenches

> « Soyez bruyants. Soyez clairs. Mais restez polis. Les exceptions sont impolies : elles interrompent tout et laissent l'appelant deviner. »

<!-- Accroche : 60 s. Fail fast, oui. Mais la façon de signaler l'échec compte. Puis votre war story (voir module_02_fail_fast_explicitly.md). -->

---

# Le problème : des exceptions pour des résultats attendus

```python
def get_user(user_id: int) -> User:
    user = USERS.get(user_id)
    if user is None:
        raise UserNotFoundError(user_id)   # « introuvable » est un cas normal
    return user
```

- Le type de retour dit `User`. Il omet le cas « introuvable ».
- Rien dans la signature ne prévient l'appelant.
- Chaque appelant doit redécouvrir les exceptions à gérer.

<!-- Fichier : 1_live/0_probleme_exceptions_invisibles.py. Le lancer : 4 utilisateurs, 4 messages. -->

---

# Ce que l'appelant doit savoir sans l'aide du type

```python
def process(user_id: int) -> str:
    try:
        user = get_user(user_id)
        account = get_account(user)
        balance = get_balance(account)
        return f"Solde : {balance}"
    except UserNotFoundError:     ...
    except AccountNotFoundError:  ...
    except AccountSuspendedError: ...
```

Trois exceptions, trois noms, trois moments où elles sont levées.
Cette connaissance vit hors du système de types, et chaque nouveau développeur doit la retrouver.

<!-- « Comptez ce que l'appelant devait savoir. C'est de la connaissance implicite, qu'on finit par oublier. » 90 s au total pour les deux slides. -->

---

# Deux niveaux d'explicite

| Niveau | Idée | Où |
|---|---|---|
| 1. Signatures honnêtes | Le type de retour annonce l'échec et son genre : `Result[T, E]` | **Aujourd'hui** |
| 2. États illégaux impossibles | Les types interdisent de construire un état invalide | Module 03 |

Aujourd'hui : rendre le chemin d'échec aussi visible que le chemin de succès.

<!-- 60 s, sans code. Le niveau 2 est annoncé pour le Module 03 (Contracts & invariants). -->

---

# Écriture 1 — `Result[T, E]` maison

```python
@dataclass(frozen=True)
class Ok(Generic[T]):
    value: T
    def bind(self, fn): return fn(self.value)   # succès : on continue

@dataclass(frozen=True)
class Err(Generic[E]):
    error: E
    def bind(self, fn): return self             # échec : on saute `fn`

Result = Ok[T] | Err[E]
```

30 lignes, aucune magie. `Err.bind` renvoie `self` : l'erreur saute toute la suite.

<!-- Fichier : 1_live/ecriture_1_result_maison.py. Taper lentement, c'est le cœur du module (60 s). -->

---

# Signatures honnêtes

```python
def get_user(user_id: int) -> Result[User, UserNotFound]:
    user = db.find_user(user_id)
    return Ok(user) if user else Err(UserNotFound(user_id))

def get_balance(account: Account) -> Result[float, AccountSuspended]:
    if account.suspended:
        return Err(AccountSuspended(account.id))
    return Ok(account.balance)
```

`Result[User, UserNotFound]` se lit comme une documentation :
succès avec un `User`, ou échec avec un `UserNotFound`.

<!-- Même fichier. Les erreurs sont des dataclasses frozen, pas des chaînes. Tests : 1_live/test_ecriture_1_result_maison.py -->

---

# Écriture 2 — Railway : `bind` enchaîne

```python
# Sans railway : un test à chaque étape
user_result = get_user(user_id)
if user_result.is_err():
    return user_result
account_result = get_account(user_result.unwrap())
...

# Avec railway
return get_user(user_id).bind(get_account).bind(get_balance)
```

Le chemin de succès reste plat. Les erreurs se routent seules.

<!-- Fichier : 1_live/ecriture_2_railway_bind.py (get_balance_without_railway puis get_balance_railway). 60 s. -->

---

# Le schéma des deux voies

```
get_user ──Ok──► get_account ──Ok──► get_balance ──Ok──► float
            │                   │                   │
           Err                 Err                 Err
            │                   │                   │
            └───────────────────┴───────────────────┴──► erreur (se route seule)
```

Railway Oriented Programming : Scott Wlaschin, pour F#. L'idée vaut dans tous les langages.

<!-- À dessiner au tableau (30 s). « Pas de try/except, pas de control flow caché. » -->

---

# Côté appelant : `match` exhaustif

```python
match process(42):
    case Ok(value=balance):              print(f"Solde : {balance}")
    case Err(error=UserNotFound()):      print("Utilisateur introuvable")
    case Err(error=AccountNotFound()):   print("Compte introuvable")
    case Err(error=AccountSuspended()):  print("Compte suspendu")
```

Chaque cas d'échec est nommé et typé. L'appelant lit le `match` comme la liste des issues possibles.

<!-- Fichier : render_error dans ecriture_1_result_maison.py et ecriture_2_railway_bind.py. -->

---

# Écriture 3 — la bibliothèque `returns`

```python
from returns.result import Result, Success, Failure
from returns.pipeline import flow
from returns.pointfree import bind

def get_balance_flow(user_id: int) -> Result[float, object]:
    return flow(user_id, get_user, bind(get_account), bind(get_balance))
```

Tout ce que nous avons écrit à la main existe en version prête pour la production :
`Success` / `Failure`, `flow`, `bind`, `map`, `value_or`.

<!-- Fichier : 1_live/ecriture_3_returns.py. Montrer que le code des écritures 1 et 2 se lit pareil. 60 s. -->

---

# `@safe` : le pont depuis le monde des exceptions

```python
from returns.result import safe

@safe
def parse_config_json(json_string: str) -> dict:
    return json.loads(json_string)   # lève ValueError si le JSON est invalide

parse_config_json('{"a": 1}')   # Success({'a': 1})
parse_config_json('pas du json') # Failure(JSONDecodeError(...))
```

Enveloppez une fois à la boundary (bibliothèques tierces, stdlib), parlez `Result` partout à l'intérieur.

<!-- Même fichier : parse_config_json, divide, process_config_with_calculation. -->

---

# Quand utiliser quoi

| Approche | À utiliser quand |
|---|---|
| Exceptions | Le vraiment exceptionnel : base de données HS, timeout réseau, bug |
| `NamedTuple` (user, error) | Marche intermédiaire, équipe pas prête pour le ROP |
| `Result` maison | Apprentissage, aucune dépendance autorisée |
| `returns` | Production, équipe convaincue, chaînes complexes |

<!-- Le NamedTuple se mentionne, il ne se démontre pas (voir « Sidebar » dans module_02_fail_fast_explicitly.md). -->

---

# Le spectre de l'explicite

```
Exceptions        Retours nommés     Result[T, E]       ADT complets
(invisibles,      (honnêtes,         (explicites,       (types scellés,
 non typées)       pas chaînables)    chaînables)        rien d'illégal)

 ◄──────────────────────────────────────────────────────────────►
 le plus courant                                     le plus explicite
 en Python aujourd'hui                               en Python aujourd'hui
```

Inutile d'aller tout à droite dès le premier jour. Connaître la direction suffit pour décider quoi sacrifier en restant à gauche.

<!-- 30 s. -->

---

# À retenir

1. Les exceptions servent à l'exceptionnel : infrastructure, bugs, imprévu.
2. Un échec attendu est une valeur de retour, visible dans la signature.
3. `bind` fait le routage : le chemin de succès reste plat, le premier `Err` gagne.
4. `@safe` ramène les exceptions de l'extérieur dans le pipeline.
5. Les états illégaux impossibles à construire : Module 03.

---

# Exercice (5 min)

Un pipeline de checkout en trois étapes, chacune peut échouer :

```python
def validate_cart(cart_id: str)             -> Result[Cart, ???]: ...
def apply_discount(cart: Cart, code: str)   -> Result[Cart, ???]: ...
def charge_card(cart: Cart, token: str)     -> Result[ChargeReceipt, ???]: ...
```

1. Définir une dataclass d'erreur par cas d'échec
2. Implémenter chaque fonction avec `Result`
3. Les chaîner avec `bind`
4. Traiter le résultat final avec `match`

<!-- Solution complète dans module_02_fail_fast_explicitly.md (section Exercice). Questions de discussion : lambda dans bind, couche service dans FastAPI/Django, que reste-t-il dans `except`. -->

---

# Pour aller plus loin

Dossier `2_pour_aller_plus_loin/`.

- `1_value_objects_gardiens/` : un `Amount` valide dès sa construction, combiné au ROP. Prépare le Module 03.

Références : *Railway Oriented Programming* (Scott Wlaschin), documentation de `returns` (returns.readthedocs.io), PEP 634 (pattern matching).
