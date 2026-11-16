# Module 01 — Synthèse : deux approches du parsing à la boundary

Le même parser de boundary, écrit deux fois. Voici pourquoi la seconde version est plus claire.

---

## Place dans le Module 01

- **Étapes live concernées :** `../../1_live/ecriture_1_pydantic_exception.py` (approche A) et `../../1_live/ecriture_2_parse_user_result.py` (approche B)
- **Ce dossier :** la cascade d'exceptions dans un flux d'inscription (`DEMO_registration_with_exceptions.py`) et ses tests de fragilité
- **Concepts renforcés :** parse, don't validate ; contrats d'échec explicites
- **Chaînes complètes côte à côte :** `../5_chaines_registration/`
- **Suite :** `../2_dataclass_sans_pydantic/` (approche C), puis `../3_erreurs_typees/` (approche D)

---

## Approche A — Exceptions (`1_live/ecriture_1_pydantic_exception.py`)

```python
user = UserInput(name="", age=30, email="alice@example.com")
# lève ValidationError — rien dans la signature ne l'annonce
```

L'appelant ne peut savoir que l'appel échoue qu'en lisant l'implémentation ou la documentation.
Il doit entourer chaque appel d'un `try/except ValidationError`, faute de quoi il obtient un crash à l'exécution.

**Le chemin d'erreur est invisible.**

---

## Approche B — Result (`1_live/ecriture_2_parse_user_result.py`)

```python
result = parse_user(name="", age=30, email="alice@example.com")
# retourne Result[UserInput, str] — la signature raconte toute l'histoire
match result:
    case Success(user): ...
    case Failure(msg):  ...
```

Le type de retour `Result[UserInput, str]` est un contrat : « cette opération produit une valeur
ou un message d'erreur ». L'appelant doit traiter les deux cas, par le type et sans convention à respecter.

**Le chemin d'erreur est explicite.**

---

## L'argument du code propre

| | Approche A | Approche B |
|---|---|---|
| Chemin d'erreur visible dans la signature | Non | Oui |
| L'appelant peut ignorer les échecs | Oui (oubli du try/except) | Non (il faut unwrap le Result) |
| Composable avec d'autres opérations faillibles | Non (l'exception casse la chaîne) | Oui (`bind` enchaîne les Result) |
| Tests lisibles comme des specs | Non (`pytest.raises` est bruyant) | Oui (`isinstance(result, Failure)`) |
| Surprises en production | Probables | Improbables |

Un code propre se comprend **en lisant la signature**.
`parse_user(...) -> Result[UserInput, str]` dit tout.
`UserInput(...)` ne dit rien sur l'échec.

---

## La règle pour la suite

> Parsez l'entrée brute de la boundary en objets typés de confiance, le plus tôt possible.
>
> Les exceptions servent aux échecs **inattendus** : ce qui ne devrait jamais arriver en fonctionnement
> normal (un bug, un environnement corrompu, un chemin de code inatteignable).
>
> Les échecs attendus (entrée invalide, enregistrement manquant, contrainte violée) vont dans le
> **type de retour**. Utilisez `Result[T, str]`. Rendez le contrat visible.

Quand les erreurs en `str` ne suffisent plus, passez à `Result[T, ErrorADT]` (approche D).

C'est la base sur laquelle s'appuient tous les modules suivants.
