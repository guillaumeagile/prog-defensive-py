# Module 03 — Contrats et invariants
## Plan détaillé · ~8 minutes live · Defensive Programming from the Trenches

> *« Un contrat dit qui garantit quoi. Les invariants en sont une partie. »*

Point d'entrée : [`README.md`](README.md). Source de pilotage : le Module 03 de `defensive_programming_live_coding_guide.md`.

---

## Fichiers du live

Tout ce que vous tapez ou montrez en direct se trouve dans `1_live/`.

| Fichier | Contenu |
|---|---|
| `1_live/0_probleme_assert_evanoui.py` | ❌ Précondition écrite avec `assert` |
| `1_live/ecriture_1_invariant_classique.py` | ✅ Contrat de fonction, Value Object qui lève, invariant de classe |
| `1_live/ecriture_2_result_explicite.py` | ✅ Smart constructor et `withdraw` qui retournent un `Result` |
| `1_live/ecriture_3_balance_value_object.py` | ✅ `Balance` : le solde porte sa propre règle |
| `1_live/test_ecriture_*.py` | Tests de chaque écriture |

Les approfondissements hors live sont dans `2_pour_aller_plus_loin/`.

---

## Vue d'ensemble

| | |
|---|---|
| **Durée** | 8 minutes (live) + 1 min d'exercice |
| **Principe central** | Une règle vit dans l'objet qui la possède. Plus on la rapproche du type, moins il reste de discipline de relecture. |
| **Focus Python** | `assert` et `-O` → invariant de classe → `Result` → Value Object `Balance` |
| **Ce que le public retient** | Je sais où poser préconditions, postconditions et invariants, et choisir entre `raise` et `Result` |

---

## Objectifs d'apprentissage

1. Distinguer précondition, postcondition et invariant
2. Savoir pourquoi `assert` ne protège pas la production
3. Pousser une règle sur une seule valeur dans un Value Object
4. Faire évoluer un invariant de classe vers un état Value Object qui porte sa règle

Règle pratique à poser dès le début :

1. Une règle sur **une seule valeur** va dans un Value Object.
2. Une règle sur **les relations entre champs** devient un invariant de classe.
3. Une règle sur **le cycle de vie** s'encode dans des types distincts.

---

## Timing de l'instructeur

```
00:00 — 01:30   Concept : contrat = préconditions + postconditions + invariants (90 s)
01:30 — 03:00   Le problème : assert disparaît avec python -O (90 s)
03:00 — 04:30   Live : écriture 1, invariant de classe traditionnel (90 s)
04:30 — 06:00   Live : écriture 2, l'échec devient explicite (90 s)
06:00 — 08:00   Live : écriture 3, Balance est un Value Object (2 min)
08:00 — 09:00   Exercice : pré, post, invariant (1 min)
```

---

## Déroulé

### 0. Le problème : `assert` (`0_probleme_assert_evanoui.py`)

Lancer le fichier normalement, puis avec `python -O`. Avec `-O`, `compute_discount(-50, 20)` retourne `-40.0`.

À dire : une précondition de domaine doit exister dans tous les modes d'exécution. On garde `assert` pour documenter une hypothèse du programmeur, jamais pour valider une entrée.

### 1. Écriture 1 : invariant de classe (`ecriture_1_invariant_classique.py`)

- `compute_discount` : guard clauses et postcondition explicite (un `Result`, jamais de `None`).
- `PositiveAmount` : la règle d'une seule valeur dans `__post_init__`.
- `BankAccount` : invariant `_balance >= 0` vérifié après la construction et après chaque mutation.

À dire : c'est la forme que tout le monde connaît. Elle protège, mais `withdraw` lève pour un événement de domaine attendu (fonds insuffisants).

### 2. Écriture 2 : l'échec devient explicite (`ecriture_2_result_explicite.py`)

- `PositiveAmount.create` retourne un `Result` : le constructeur est une fonction totale.
- `withdraw` retourne `Result[None, InsufficientFunds]` et ne mute que sur la branche `Success`.
- `_ensure_invariant()` disparaît : l'invariant tient par construction.

À dire : `__post_init__` qui lève est une **partial function**, définie sur une partie seulement de son domaine. Le smart constructor convient aux entrées utilisateur. Un constructeur qui lève convient aux données déjà validées.

Point à nommer : `BankAccount` écrit toujours `amount.value > self._balance`. La règle reste dans la classe, protégée par la relecture.

### 3. Écriture 3 : `Balance` est un Value Object (`ecriture_3_balance_value_object.py`)

Deux règles pour `BankAccount` : aucun `float`, et jamais de lecture de l'intérieur d'un Value Object.

- `Balance.has_enough_funds(amount)` répond à « assez de fonds ? ».
- `Balance.after_deposit(amount)` et `Balance.after_withdraw(amount)` produisent le nouveau solde.
- `BankAccount` orchestre : elle demande un nouveau `Balance` et le range si l'opération réussit.

Ce que l'audience doit voir :

- Aucun chemin ne fabrique un solde négatif.
- Les opérations se composent : `solde.after_withdraw(a).bind(lambda s: s.after_withdraw(b))`.
- Critère de qualité : réécrire `Balance` avec des `Decimal` ou des centimes entiers ne change pas une ligne de `BankAccount`.

Principes qui nomment ce défaut (à citer, sans y passer plus de 30 secondes) :

- **Tell, Don't Ask** et **loi de Déméter** : `BankAccount` demande `amount.value` puis décide à la place de l'objet.
- **Object Calisthenics, règle 5**, [un seul point par ligne](https://williamdurand.fr/2013/06/03/object-calisthenics/#5-one-dot-per-line).

Note Python : `BankAccount` reste mutable (elle remplace son `Balance`). Seules les valeurs sont immuables. Une version entièrement pure retournerait un nouveau `BankAccount` à chaque opération.

---

## Pattern à dire à voix haute

1. Vérifier l'invariant après la construction.
2. Pousser les préconditions sur une seule valeur dans des Value Objects.
3. Revérifier l'invariant après chaque transition d'état.
4. Pour un **échec de domaine** (attendu, récupérable), préférer `Result` à `raise`.
5. Réserver `raise` aux **erreurs de programmation**.
6. Quand le code extrait la valeur d'un Value Object pour raisonner dessus, déplacer ce raisonnement dans le Value Object.

---

## Exercice (1 min)

Choisir une fonction de votre codebase et noter :

1. une précondition,
2. une postcondition,
3. un invariant.

Les imposer explicitement dans le code, puis décider pour chacun : `raise` ou `Result` ?

---

## Pour aller plus loin

`2_pour_aller_plus_loin/1_etats_illegaux/` : `DraftOrder` et `ConfirmedOrder` rendent un état illégal impossible à construire (`ship` n'accepte que `ConfirmedOrder`). `Config` en `frozen=True` montre l'immutabilité comme amplificateur de contrat.
