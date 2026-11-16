# Module 02 — Fail fast, fail explicitly

Point d'entrée de l'instructeur. Le plan détaillé (accroche, war story, timing, exercice et solution) se trouve dans [`module_02_fail_fast_explicitly.md`](module_02_fail_fast_explicitly.md). Les slides sont dans [`presentation.md`](presentation.md).

Source de pilotage : [`../../defensive_programming_live_coding_guide.md`](../../defensive_programming_live_coding_guide.md) (Module 02) et [`../../guideline.md`](../../guideline.md).

## Par où commencer

1. Lire `module_02_fail_fast_explicitly.md` (10 min de préparation).
2. Ouvrir `1_live/` : c'est le seul dossier à taper en direct.
3. Garder `presentation.md` ouvert dans Marp pour les diapositives.

## Déroulé live (~9 min)

| Min | Étape | Fichier | Message |
|---|---|---|---|
| 0–3,5 | ❌ Exceptions pour des résultats attendus | `1_live/0_probleme_exceptions_invisibles.py` | La signature ment, l'appelant doit connaître 3 exceptions |
| 3,5–5,5 | ✅ Écriture 1 : `Result[T, E]` maison | `1_live/ecriture_1_result_maison.py` | 30 lignes, aucune magie |
| 5,5–7,5 | ✅ Écriture 2 : Railway avec `bind` | `1_live/ecriture_2_railway_bind.py` | Le chemin de succès reste plat |
| 7,5–8,5 | ✅ Écriture 3 : bibliothèque `returns` | `1_live/ecriture_3_returns.py` | `flow`, `bind`, `@safe` |
| 8,5–9 | Spectre de l'explicite | `presentation.md` | Connaître la direction |
| +5 | Exercice : pipeline de checkout | `module_02_fail_fast_explicitly.md` (section Exercice) | Appliquer `Result` + `bind` |

Chaque écriture a son fichier de tests : `test_ecriture_1_result_maison.py`, `test_ecriture_2_railway_bind.py`, `test_ecriture_3_returns.py`.

## Écart avec le guide

Le guide (Module 02) montre directement la version `returns` (`get_active_user`, `signup` avec Pydantic). Ce dossier suit la progression du plan : `Result` maison, Railway, puis `returns`. L'écriture 3 arrive au même code que le guide.

## Pour aller plus loin (hors live)

Dossier `2_pour_aller_plus_loin/`.

| Dossier | Contenu |
|---|---|
| `1_value_objects_gardiens/` | `Amount` : un value object qui garantit sa validité, combiné au ROP. Prépare le Module 03 (Contracts & invariants) |

## Lancer les tests

Depuis la racine du dépôt :

```bash
pytest LiveCoding/module_02_fail_fast_ROR            # tout est vert (72 tests)
```

Les fichiers `pbt_ecriture_*.py` (property-based testing, `hypothesis`) ne sont pas collectés par pytest, car leur nom ne commence pas par `test_`. Pour les lancer :

```bash
pytest LiveCoding/module_02_fail_fast_ROR/1_live/pbt_ecriture_1_result_maison.py
```

Le fichier de l'écriture 3 (`pbt_ecriture_3_returns.py`) contient 2 propriétés qui échouent, comme avant la restructuration. Ne pas les « réparer » sans accord de l'instructeur.

## Vérification statique (optionnel)

Configs dans `1_live/typage/`. Lancer depuis ce dossier :

```bash
cd LiveCoding/module_02_fail_fast_ROR/1_live/typage
poetry run pyright --project pyright.ecriture_1.json
poetry run mypy --config-file mypy.ecriture_1.ini
```

Remplacer `ecriture_1` par `ecriture_2` ou `ecriture_3` pour les autres étapes.

Le mode strict signale des erreurs dans ces fichiers (3, 19 et 11 en mypy pour les écritures 1, 2 et 3). Elles existaient avant la restructuration, le code n'a pas changé.
