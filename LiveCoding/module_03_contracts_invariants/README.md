# Module 03 — Contrats et invariants

Point d'entrée de l'instructeur. Le plan détaillé (accroche, timing, points à dire, exercice) se trouve dans [`module_03_contracts_invariants.md`](module_03_contracts_invariants.md).

Source de pilotage : [`../../defensive_programming_live_coding_guide.md`](../../defensive_programming_live_coding_guide.md) (Module 03) et [`../../guideline.md`](../../guideline.md).

## Par où commencer

1. Lire `module_03_contracts_invariants.md` (10 min de préparation).
2. Ouvrir `1_live/` : c'est le seul dossier à taper en direct.

## Déroulé live (~8 min)

| Min | Étape | Fichier | Message |
|---|---|---|---|
| 0–1,5 | ❌ `assert` comme précondition | `1_live/0_probleme_assert_evanoui.py` | `python -O` retire la règle en production |
| 1,5–3 | ✅ Écriture 1 : invariant de classe | `1_live/ecriture_1_invariant_classique.py` | La forme classique : objet mutable, `raise` |
| 3–5 | ✅ Écriture 2 : l'échec devient explicite | `1_live/ecriture_2_result_explicite.py` | Smart constructor et `withdraw` retournent un `Result` |
| 5–7,5 | ✅ Écriture 3 : `Balance` est un Value Object | `1_live/ecriture_3_balance_value_object.py` | `BankAccount` n'a plus de règle ni de `float` |
| 7,5–8 | Ce que l'audience retient | `module_03_contracts_invariants.md` | La règle vit chez l'objet qui la possède |
| +1 | Exercice : pré, post, invariant | `module_03_contracts_invariants.md` (section Exercice) | `raise` ou `Result` ? |

Chaque écriture a son fichier de tests : `test_ecriture_1_invariant_classique.py`, `test_ecriture_2_result_explicite.py`, `test_ecriture_3_balance_value_object.py`.

## Écart avec le guide

Le guide (Module 03) présente les trois étapes sous forme de blocs de code et de perspectives FP. Ce dossier les rend exécutables et ajoute le point de départ `assert`. Le code utilise les annotations sans guillemets de Python 3.14 (PEP 649).

## Pour aller plus loin (hors live)

Dossier `2_pour_aller_plus_loin/`.

| Dossier | Contenu |
|---|---|
| `1_etats_illegaux/` | `DraftOrder` / `ConfirmedOrder` : le cycle de vie encodé dans les types, et l'immutabilité avec `Config` |

## Lancer les tests

Depuis la racine du dépôt, dans l'environnement Poetry :

```bash
poetry run pytest LiveCoding/module_03_contracts_invariants    # 26 tests
```

Lancer le point de départ avec et sans optimisation :

```bash
python LiveCoding/module_03_contracts_invariants/1_live/0_probleme_assert_evanoui.py
python -O LiveCoding/module_03_contracts_invariants/1_live/0_probleme_assert_evanoui.py
```
