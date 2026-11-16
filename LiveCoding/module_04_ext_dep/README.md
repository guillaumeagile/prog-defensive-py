# Module 04 — Handling external dependencies

Point d'entrée de l'instructeur. Le plan détaillé (accroche, war story, timing, parties 1 à 10) se trouve dans [`module_04_external_dependencies.md`](module_04_external_dependencies.md), en anglais pour l'instant.

Source de pilotage : [`../../defensive_programming_live_coding_guide.md`](../../defensive_programming_live_coding_guide.md) (Module 04) et [`../../guideline.md`](../../guideline.md).

Le module 03 (Contracts & invariants) n'existe pas encore dans `LiveCoding/`. Le module 04 s'appuie sur les modules 01 (valider à la frontière) et 02 (échecs explicites avec `Result`).

## Par où commencer

1. Lire `module_04_external_dependencies.md` (10 min de préparation).
2. Ouvrir `1_live/` : c'est le seul dossier à taper en direct.
3. Garder `2_pour_aller_plus_loin/` pour les questions de la salle.

## Déroulé live (~10 min)

Le code vit dans `1_live/`, organisé en trois couches : `ports/` (le contrat), `core/` (la logique métier), `adapters/` (le monde extérieur et ses doublures).

| Min | Étape | Fichiers | Message |
|---|---|---|---|
| 0–1,5 | Accroche et concept : l'extérieur est hostile | `module_04_external_dependencies.md` (parties 1-2) | La frontière du module 01, à l'échelle du réseau |
| 1,5–3,5 | Dessiner la couture : `Protocol` comme interface | `ports/payment_gateway.py`, `ports/dtos.py` | On conçoit l'interface avant l'implémentation |
| 3,5–5 | Le faux : une implémentation complète sans bibliothèque de mock | `adapters/fake_payment_gateway.py`, `adapters/fake_stripe_api.py` | Un fake est plus fidèle qu'un mock |
| 5–6 | Tests contre le faux : cas heureux et malheureux | `test_solution_external_dependencies.py` (classe `TestFakePaymentGateway`) | Tous les comportements du contrat sont testés |
| 6–7 | L'adaptateur Stripe réel | `adapters/stripe_payment_gateway.py`, `adapters/stripe_response.py` | Timeout, parsing défensif, aucune exception ne fuit |
| 7–8 | Même suite de tests, deux implémentations | `test_solution_external_dependencies.py` | Le faux et le réel respectent le même contrat |
| 8–9 | Timeout, retry, idempotence : où ils vivent | `module_04_external_dependencies.md` (partie 9) | Ces politiques appartiennent à l'adaptateur |
| 9–10 | Fournisseur défaillant : injection de pannes | `adapters/malfunctioning_stripe_api.py`, `test_stripe_adapter_fault_injection.py` | Quatre principes, aucun `monkeypatch` |

`solution_external_dependencies.py` ré-exporte l'API publique du module (`Result`, ports, adaptateurs). Les tests l'importent pour rester courts.

## Pour aller plus loin (hors live)

Dossier `2_pour_aller_plus_loin/`.

| Dossier | Contenu |
|---|---|
| `1_faute_transport_http/` | Injection de pannes au niveau du transport : le vrai `httpx` tourne, seule la socket TCP est remplacée par `FaultyStripeTransport`. Il couvre les pannes qui n'apparaissent que lorsque le vrai code de parsing HTTP s'exécute |

Ce dossier est autonome : il a son propre `result.py` et ses propres `dtos.py`, copies simplifiées de ceux de `1_live/`.

## Lancer les tests

Depuis la racine du dépôt :

```bash
pytest LiveCoding/module_04_ext_dep/1_live                              # tout est vert (23 tests)
pytest LiveCoding/module_04_ext_dep                                     # 29 verts, 2 échecs volontaires, voir ci-dessous
```

## Échecs volontaires

Ces tests échouent exprès. Ils montrent ce qui arrive quand l'adaptateur fait confiance au fournisseur. Ne pas les « réparer ».

| Test | Raison |
|---|---|
| `2_pour_aller_plus_loin/1_faute_transport_http/test_http_stripe_fault_injection.py::test_FAILS_naive_adapter_trusts_200_as_success` | L'adaptateur naïf prend un HTTP 200 pour un succès, même quand le corps contient une erreur |
| `2_pour_aller_plus_loin/1_faute_transport_http/test_http_stripe_fault_injection.py::test_FAILS_leaky_adapter_lets_connect_error_escape` | L'adaptateur qui fuit laisse `httpx.ConnectError` remonter jusqu'à l'appelant |
