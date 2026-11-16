---
marp: true
theme: default
paginate: true
title: Module 03 — Contrats et invariants
---

<!--
Présentation du Module 03, au format Marp (une diapositive = un bloc entre `---`).
Affichage : extension VS Code « Marp for VS Code », ou `npx @marp-team/marp-cli presentation.md --html`.
Les notes de l'instructeur sont dans les commentaires HTML sous chaque diapositive.
Fichiers de code : dossier 1_live/ (voir README.md).
-->

# Contrats et invariants

## Module 03 — Defensive Programming from the Trenches

> « Un contrat dit qui garantit quoi. Les invariants en sont une partie. »

<!-- Accroche : 30 s. Puis votre war story (voir module_03_contracts_invariants.md). -->

---

# Un contrat a trois parties

| Partie | Question | Exemple |
|---|---|---|
| **Précondition** | Que doit fournir l'appelant ? | `price >= 0` |
| **Postcondition** | Que promet la fonction ? | un `Result`, jamais un `None` caché |
| **Invariant** | Qu'est-ce qui reste toujours vrai ? | `balance >= 0` |

Les trois se vérifient dans tous les modes d'exécution, sinon ils ne protègent personne.

<!-- 60 s. Annoncer le fil rouge : un compte bancaire. -->

---

# Où poser la règle ?

1. Une règle sur **une seule valeur** va dans un **Value Object**.
2. Une règle sur **les relations entre champs** devient un **invariant de classe**.
3. Une règle sur **le cycle de vie** s'encode dans **des types distincts**.

<!-- 30 s. On parcourt les trois dans l'ordre pendant le live. -->

---

# Le problème : `assert` comme précondition

```python
def compute_discount(price: float, pct: float) -> float:
    assert price >= 0, "price must be >= 0"
    assert 0 <= pct <= 100, "pct must be between 0 and 100"
    return price * (1 - pct / 100)
```

```text
$ python -O 0_probleme_assert_evanoui.py
price=-50.0 pct=20.0 -> -40.0
```

`python -O` retire les `assert`. La précondition disparaît en production.

<!-- Fichier : 1_live/0_probleme_assert_evanoui.py. Le lancer deux fois, avec puis sans -O. 90 s.
« assert documente une hypothèse du programmeur. Il ne valide jamais une entrée. » -->

---

# Écriture 1 : l'invariant de classe

```python
@dataclass
class BankAccount:
    _balance: float = 0.0

    def __post_init__(self) -> None:
        self._ensure_invariant()

    def _ensure_invariant(self) -> None:
        if self._balance < 0:
            raise ValueError("invariant: balance cannot be negative")

    def withdraw(self, amount: PositiveAmount) -> None:
        if amount.value > self._balance:
            raise ValueError("insufficient funds")
        self._balance -= amount.value
        self._ensure_invariant()
```

L'invariant est vérifié après la construction et après chaque mutation.

<!-- Fichier : 1_live/ecriture_1_invariant_classique.py. Montrer aussi compute_discount (guard clauses + Result)
et PositiveAmount (règle d'une seule valeur dans __post_init__). 90 s. -->

---

# Une fonction qui lève est une fonction partielle

```python
PositiveAmount(value=-1)   # ressemble à un appel normal, lève pourtant
```

- La signature annonce `PositiveAmount`. Elle est définie sur une partie seulement de son domaine.
- `withdraw` lève pour un événement de domaine **attendu** (fonds insuffisants).
- L'appelant découvre l'échec à l'exécution.

<!-- 30 s. Transition vers l'écriture 2. -->

---

# Écriture 2 : l'échec devient explicite

```python
@classmethod
def create(cls, value: float) -> Result[PositiveAmount, str]:
    if value <= 0:
        return Failure(f"amount must be positive, got {value}")
    return Success(cls(value=value))

def withdraw(self, amount: PositiveAmount) -> Result[None, InsufficientFunds]:
    if amount.value > self._balance:
        return Failure(InsufficientFunds(amount.value, self._balance))
    self._balance -= amount.value
    return Success(None)
```

L'invariant tient **par construction** : la mutation n'a lieu que sur la branche `Success`.

<!-- Fichier : 1_live/ecriture_2_result_explicite.py. 90 s.
Choix : smart constructor pour les entrées utilisateur, constructeur qui lève pour des données déjà validées.
Point à nommer : `amount.value > self._balance` reste écrit dans BankAccount. -->

---

# Un signal : chaque `.value`

```python
if amount.value > self._balance:      # BankAccount ouvre PositiveAmount...
    ...
self._balance -= amount.value         # ...et refait l'arithmétique elle-même
```

`BankAccount` connaît la représentation interne de `PositiveAmount`.
Chaque `.value` signale une règle métier qui n'a pas encore trouvé son type.

- **Tell, Don't Ask** : dire à l'objet quoi faire, au lieu de lui demander son état.
- **Loi de Déméter** : ne parler qu'à ses amis directs.
- **Object Calisthenics, règle 5** : [un seul point par ligne](https://williamdurand.fr/2013/06/03/object-calisthenics/#5-one-dot-per-line).

<!-- 30 s. Ne pas s'attarder : les trois principes décrivent le même symptôme. -->

---

# Écriture 3 : le solde devient un Value Object

```python
@dataclass(frozen=True)
class Balance:
    _value: float = 0.0

    def has_enough_funds(self, amount: PositiveAmount) -> bool: ...
    def after_deposit(self, amount: PositiveAmount) -> Balance: ...
    def after_withdraw(self, amount: PositiveAmount) -> Result[Balance, InsufficientFunds]: ...

@dataclass
class BankAccount:
    _balance: Balance = field(default_factory=Balance)

    def withdraw(self, amount: PositiveAmount) -> Result[None, InsufficientFunds]:
        return self._balance.after_withdraw(amount).map(self._replace_balance)
```

<!-- Fichier : 1_live/ecriture_3_balance_value_object.py. 2 min.
Deux règles : BankAccount ne manipule plus aucun float, et ne lit jamais l'intérieur d'un Value Object. -->

---

# Ce que l'audience doit voir

- `Balance` **porte sa propre précondition** : aucun chemin ne fabrique un solde négatif.
- `BankAccount` **orchestre** : elle demande un nouveau `Balance` et le range si l'opération réussit.
- Les opérations **se composent** : `solde.after_withdraw(a).bind(lambda s: s.after_withdraw(b))`.
- Critère de qualité : réécrire `Balance` avec des `Decimal` ne change **aucune ligne** de `BankAccount`.

<!-- 60 s. Python 3.14 : annotations sans guillemets (PEP 649), `available: Balance` avant la définition de Balance. -->

---

# Pour aller plus loin : états illégaux

```python
@dataclass(frozen=True)
class DraftOrder:     order_id: str
@dataclass(frozen=True)
class ConfirmedOrder: order_id: str

def confirm(order: DraftOrder) -> Result[ConfirmedOrder, str]: ...
def ship(order: ConfirmedOrder) -> str: ...      # ship(DraftOrder(...)) est refusé par le type checker
```

Pas de drapeau `is_confirmed`, pas d'état intermédiaire nullable. `frozen=True` empêche la dérive par mutation.

<!-- Hors live : 2_pour_aller_plus_loin/1_etats_illegaux/. -->

---

# À retenir

1. Vérifier l'invariant après la construction et après chaque transition.
2. Une règle sur une seule valeur va dans un Value Object.
3. Échec de domaine : `Result`. Erreur de programmation : `raise`.
4. Quand le code extrait `.value` pour raisonner, déplacer le raisonnement dans le Value Object.

---

# Exercice (1 min)

Choisir une fonction de votre codebase et noter :

1. une **précondition**,
2. une **postcondition**,
3. un **invariant**.

Les imposer dans le code, puis décider pour chacun : `raise` ou `Result` ?
