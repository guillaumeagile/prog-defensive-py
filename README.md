# Defensive Programming from the Trenches

Support d'une session de live coding en français sur la programmation défensive en Python. Chaque module part d'un code fragile (exceptions invisibles, `assert` désactivé, entrées non vérifiées), puis le réécrit en plusieurs étapes jusqu'à un code où les états illégaux ne se représentent plus. Les principes valent pour d'autres langages ; les exemples sont en Python 3.14 avec `pytest`, `pyright`, `mypy`, `Pydantic`, `returns` et `Expression`.

## Structure du dépôt

```text
.
├── README.md                                   ce fichier
├── defensive_programming_live_coding_guide.md  guide de l'animateur (déroulé complet, slides)
├── guideline.md                                règles suivies par Claude Code pendant la session
├── python_et_style_fonctionnel.md              Python, style fonctionnel, mypy contre pyright
├── pyproject.toml / poetry.lock                dépendances (Python >=3.14,<3.15)
├── conftest.py                                 ajoute le dossier de chaque test à sys.path
├── LiveCoding/
│   ├── module_01_never_trust_input/
│   ├── module_02_fail_fast_ROR/
│   ├── module_03_contracts_invariants/
│   └── module_04_ext_dep/
│       ├── README.md                           point d'entrée du module
│       ├── module_0X_*.md                      plan détaillé (accroche, timing, questions)
│       ├── presentation.md                     slides Marp (modules 01 à 03)
│       ├── 1_live/                             code écrit en direct : problème, écritures 1..n, tests
│       │   └── typage/                         configs pyright et mypy par écriture (modules 02, 03)
│       └── 2_pour_aller_plus_loin/             exemples et solutions complémentaires
├── exercises/                                  exercices pour les participants
└── MCP/                                        instructions pour les agents (AGENTS, CLAUDE, GEMINI)
```

## Documents

| Document | Contenu |
|---|---|
| [`defensive_programming_live_coding_guide.md`](defensive_programming_live_coding_guide.md) | Déroulé de la session, module par module |
| [`guideline.md`](guideline.md) | Règles de code et de tests de la session |
| [`python_et_style_fonctionnel.md`](python_et_style_fonctionnel.md) | Ce que Python offre pour le style fonctionnel, comparaison des bibliothèques, `mypy` et `pyright` |
| [`LiveCoding/module_01_never_trust_input/README.md`](LiveCoding/module_01_never_trust_input/README.md) | Module 01 : ne jamais faire confiance aux entrées |
| [`LiveCoding/module_02_fail_fast_ROR/README.md`](LiveCoding/module_02_fail_fast_ROR/README.md) | Module 02 : échouer tôt et explicitement (Result, railway) |
| [`LiveCoding/module_03_contracts_invariants/README.md`](LiveCoding/module_03_contracts_invariants/README.md) | Module 03 : contrats et invariants (`Expression`) |
| [`LiveCoding/module_04_ext_dep/README.md`](LiveCoding/module_04_ext_dep/README.md) | Module 04 : dépendances externes |

## Installation

```bash
poetry install
```

## Lancer les tests

Depuis la racine du dépôt. `pytest` est configuré avec `--import-mode=importlib`.

```bash
# Module 01
poetry run pytest LiveCoding/module_01_never_trust_input

# Module 02
poetry run pytest LiveCoding/module_02_fail_fast_ROR

# Module 03
poetry run pytest LiveCoding/module_03_contracts_invariants

# Module 04
poetry run pytest LiveCoding/module_04_ext_dep

# Tout
poetry run pytest LiveCoding
```

Une étape précise :

```bash
poetry run pytest LiveCoding/module_03_contracts_invariants/1_live/test_ecriture_2_result_explicite.py
```

Certains tests de démonstration échouent volontairement (modules 01 et 04, noms contenant `FAILS` ou `NOT_caught`). Ils montrent le défaut avant sa correction.

## Vérifier les types

Les configs sont versionnées à côté du code. Exemple pour le module 03 :

```bash
cd LiveCoding/module_03_contracts_invariants/1_live/typage
poetry run pyright -p pyright.ecriture_2.json
poetry run mypy --config-file mypy.ecriture_2.ini
```

Les modules 01 et 02 ont leurs configs dans `2_pour_aller_plus_loin/3_erreurs_typees` et `1_live/typage`. Le mode strict y signale des erreurs que les READMEs de module décrivent.

## Progression du typage

Le typage se durcit au fil de l'atelier :

| Module | `pyright` strict | Pourquoi |
|---|---|---|
| 01, 02 | non, par choix | Modules d'introduction : `returns`, le `Result` maison du module 02 et les écritures « avant » y déclenchent des erreurs que l'on laisse visibles. Le mode strict y signale des dizaines d'erreurs, décrites dans les READMEs de module |
| 03 | oui, 0 erreur | Types précis dès l'écriture : `Expression`, Value Objects, `match` exhaustif |
| 04 | oui, 0 erreur | Ports, adaptateurs et `Result` covariant : le typage strict garde les frontières propres |

```bash
cd LiveCoding/module_04_ext_dep/typage
poetry run pyright -p pyright.module04.json
```

## CI

`.github/workflows/ci.yml` lance sur chaque PR : les tests des quatre modules (sans les démos rouges volontaires) et `pyright` strict sur les modules 03 et 04.
