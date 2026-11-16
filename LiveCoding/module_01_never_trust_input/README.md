# Module 01 — Never trust input

Point d'entrée de l'instructeur. Le plan détaillé (accroche, war story, timing, questions de la salle) se trouve dans [`module_01_never_trust_input.md`](module_01_never_trust_input.md). Les slides sont dans [`presentation.md`](presentation.md).

Source de pilotage : [`../../defensive_programming_live_coding_guide.md`](../../defensive_programming_live_coding_guide.md) (Module 01) et [`../../guideline.md`](../../guideline.md).

## Par où commencer

1. Lire `module_01_never_trust_input.md` (10 min de préparation).
2. Ouvrir `1_live/` : c'est le seul dossier à taper en direct.
3. Garder `presentation.md` ouvert dans Marp pour les diapositives.

## Déroulé live (~8 min)

| Min | Étape | Fichier | Message |
|---|---|---|---|
| 0–1 | ❌ Le code fait confiance à l'appelant | `1_live/etape_1_confiance_aveugle.py` | La donnée invalide entre sans résistance |
| 1–3 | ✅ Pythonic : Pydantic lève `ValidationError` | `1_live/etape_2_pydantic_exception.py` | La signature ne dit pas que l'appel peut échouer |
| 3–6 | ✅ FP : `parse_user -> Result[UserInput, str]` | `1_live/user_input.py` | Le type de retour dit toute la vérité |
| 6–7 | Tests : exemples + propriété `hypothesis` | `1_live/test_user_input.py` | Les tests fixent le contrat |
| 7–8 | Exercice : `ProductInput` | `../../exercises/module_01_never_trust_input/3.exercise_product_input/` | Appliquer la même boundary |

`1_live/testbook_user_input.ipynb` permet d'explorer `parse_user` et de lancer les tests depuis un notebook.

## Pour aller plus loin (hors live)

Dossier `2_pour_aller_plus_loin/`. Chaque sous-dossier contient une `synthese.md` en français.

| Dossier | Contenu |
|---|---|
| `1_exceptions_contre_exemple/` | Cascade d'exceptions dans un flux d'inscription, avec tests de fragilité |
| `2_dataclass_sans_pydantic/` | Même contrat avec `dataclass` + `__post_init__` |
| `3_erreurs_typees/` | `Result[T, ErrorADT]` : des variantes d'erreur au lieu de `str` |
| `4_composition_flow_bind/` | Un parser par champ, composés avec `flow` et `bind` |
| `5_chaines_registration/` | Chaîne d'inscription avec exceptions, puis avec `Result` |

Les dossiers 3 et 4 prolongent le Module 02 du guide (*Fail fast, fail loud*), qui traite déjà l'ADT d'erreurs et le ROP.

## Lancer les tests

Depuis la racine du dépôt :

```bash
pytest LiveCoding/module_01_never_trust_input/1_live            # tout est vert
pytest LiveCoding/module_01_never_trust_input                   # 4 échecs volontaires, voir ci-dessous
```

## Échecs volontaires

Ces tests échouent exprès. Ils servent à montrer les défauts d'un design classique ou à corriger en direct. Ne pas les « réparer ».

| Test | Raison |
|---|---|
| `1_exceptions_contre_exemple/test_DEMO_registration_fragility.py` : 3 tests de `TestUnanticipatedExceptionsLeakThrough` | Les `pytest.raises` sont commentés, l'exception remonte jusqu'au test |
| `4_composition_flow_bind/test_more_fp_style_pbt.py::test_property_success_name_is_always_trusted` | `parse_name` accepte un nom blanc (`" "`) et retourne `Name("")` |

Le fichier `3_erreurs_typees/TestParseUserInputPBT.py` garde son nom d'origine : pytest ne le collecte pas (il ne commence pas par `test_`). Le renommer ferait apparaître un échec supplémentaire.

## Vérification statique (optionnel)

```bash
poetry run pyright --project LiveCoding/module_01_never_trust_input/2_pour_aller_plus_loin/3_erreurs_typees/pyright.module01.json
poetry run mypy --config-file LiveCoding/module_01_never_trust_input/2_pour_aller_plus_loin/3_erreurs_typees/mypy.module01.ini
poetry run pyright --project LiveCoding/module_01_never_trust_input/2_pour_aller_plus_loin/4_composition_flow_bind/pyright.more_fp_style.json
```
