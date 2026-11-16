# Python et le style fonctionnel

Guide pour les développeurs qui viennent du monde fonctionnel (F#, Haskell, Scala) ou de C#. État au 2026-11-16, Python 3.14.

## Ce que Python fournit sans bibliothèque

| Besoin | Outil Python | Équivalent C# / F# |
|---|---|---|
| Valeur immuable | `@dataclass(frozen=True)` | `record` |
| Type somme | union `A \| B` de dataclasses | union discriminée F#, `OneOf` en C# |
| Filtrage | `match` / `case` (3.10) | `switch` expression, `match` F# |
| Alias de type | `type AccountError = str \| InsufficientFunds` (3.12) | alias F# |
| Fonction de première classe | `def`, `lambda`, `functools.partial` | délégués, `Func<>` |
| Annotation sans guillemets avant définition | PEP 649 (3.14) | résolution par le compilateur |

Ce qui manque : un type `Result` ou `Option` dans la bibliothèque standard, l'optimisation des appels terminaux, et un opérateur de pipe. Les exceptions restent l'idiome de la bibliothèque standard.

## Les types sont des annotations

En C# le compilateur refuse un programme mal typé. En Python l'interpréteur ignore les annotations à l'exécution. `PositiveAmount.create(x)` retourne ce qu'il veut, quoi que dise la signature.

Le contrôle de types est un outil séparé, lancé en CI ou dans l'éditeur. Sans lui, un `Result[T, E]` n'oblige personne à traiter l'échec. Ce guide suppose qu'un vérificateur de types tourne.

## mypy et pyright : deux vérificateurs, pas de compilateur unique

| | mypy | pyright |
|---|---|---|
| Origine | projet historique de la communauté Python | Microsoft, moteur de Pylance dans VS Code |
| Extensions | plugins (API de plugin mypy) | aucun plugin |
| Mode strict | `strict = True` | `"typeCheckingMode": "strict"` |
| Lancement | `mypy --config-file x.ini` | `pyright --project x.json` |

La spécification des types Python est écrite à part, et chaque outil l'implémente à sa manière. Les deux divergent sur les cas limites : inférence, exhaustivité des `match`, variance, types d'ordre supérieur. En C# il y a un seul compilateur, donc cette question n'existe pas.

### Ce que nous avons mesuré dans ce dépôt

Même code, mode strict, Python 3.14. Module 03, étape 2 : `PositiveAmount.create(x).bind(account.withdraw)` où `create` échoue avec `str` et `withdraw` avec `InsufficientFunds`.

| Bibliothèque | mypy strict | pyright strict |
|---|---|---|
| `returns` 0.27 | erreur `arg-type` sur le `bind` | erreur sur le `bind`, `match` non exhaustif |
| `Expression` 6.0.1 | aucune erreur | aucune erreur |

Cause pour `returns` : `Result[T, E]` y est une classe générique dont le type d'erreur est invariant, et la bibliothèque émule les types d'ordre supérieur (`KindN`) avec un plugin `mypy`. `pyright` n'exécute pas ce plugin. Pour que les deux vérificateurs acceptent le code, il faut déclarer un type d'erreur commun (`type AccountError = str | InsufficientFunds`) dans toutes les fonctions chaînées.

### Variance, pour ceux qui viennent de C#

En C#, `IEnumerable<out T>` est covariant : un `IEnumerable<Dog>` se range dans un `IEnumerable<Animal>`. `List<T>` est invariant : `List<Dog>` ne se range pas dans `List<Animal>`.

`Expression` déclare `Result[T, E]` covariant sur `T` et sur `E`. `Ok[T] | Error[E1]` et `Ok[U] | Error[E2]` se combinent en union. `returns` déclare le type d'erreur invariant dans la signature de `bind`, donc `E1` et `E2` doivent être identiques.

### Conseils pratiques

1. Choisir un vérificateur comme juge en CI. Garder l'autre comme avis dans l'éditeur (Pylance embarque pyright).
2. Préférer les bibliothèques qui se vérifient sans plugin.
3. Versionner la config du vérificateur à côté du code (`typage/` dans les modules du dépôt).
4. Désactiver une règle par fichier de config, avec une phrase d'explication, plutôt que de la contourner dans le code. Exemple : `reportPrivateUsage` dans `pyright.ecriture_3.json`.

## Bibliothèques fonctionnelles

Données PyPI au 2026-11-16.

| Bibliothèque | Version | Python | Dernière release | Remarque |
|---|---|---|---|---|
| `Expression` | 6.0.1 | ≥ 3.12 | 2026-11-12 | inspirée de F# : `Result`, `Option`, pipe, effets |
| `returns` | 0.30.0 | ≥ 3.11 | 2026-10-27 | `Result`, `Maybe`, `IO`, `@safe`, `flow`. Vise `mypy` en priorité |
| `oslash` | 3.0.0 | ≥ 3.12 | 2026-11-14 | monades façon Haskell |
| `result` | 0.17.0 | ≥ 3.8 | 2024-06-02 | style Rust, pas de classifier 3.14 |
| `PyMonad` | 2.4.0 | ≥ 3.7 | 2021-05-14 | non maintenue |

Le dépôt fige `returns = "^0.27.0"` alors que la 0.30.0 existe. Les tests du module 02 et du module 03 passent en 3.14.7 avec la version figée.

### Sans bibliothèque

Une union de dataclasses plus `match` suffit pour un `Result` : c'est le choix du module 02 (`Ok` / `Err` écrits à la main). On gagne la compréhension du mécanisme et aucune dépendance. On perd `map`, `bind`, `pipe` et le travail de typage déjà fait.

## Choix dans ce dépôt

| Module | Approche | Raison |
|---|---|---|
| 02 | `Result` maison, puis `returns` | démystifier le type, puis montrer l'outil connu |
| 03 | `Expression` | version moderne : union fermée, covariance, aucun contournement pour `mypy` ni `pyright` |

## Voir aussi

- [`LiveCoding/module_02_fail_fast_ROR/README.md`](LiveCoding/module_02_fail_fast_ROR/README.md)
- [`LiveCoding/module_03_contracts_invariants/README.md`](LiveCoding/module_03_contracts_invariants/README.md)
