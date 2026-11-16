# Module 04 — Gérer les dépendances externes
## Plan détaillé · ~10 minutes en live · Defensive Programming from the Trenches

> *« Tout ce qui est hors de votre process est hostile : APIs, files de messages, système de fichiers, le temps lui-même.*
> *L'hostilité est ici de l'indifférence : ce monde sera lent, indisponible, de forme inattendue, et il réussira au premier appel pour échouer au retry. »*

---

## Vue d'ensemble

| | |
|---|---|
| **Durée** | 10 minutes en live |
| **Principe central** | Le monde extérieur est une entrée non fiable à grande échelle : appliquer la frontière du M01 et les échecs explicites du M02 à chaque traversée de process |
| **Focus Python** | `typing.Protocol`, pattern adaptateur, `httpx` async, retry avec `stamina`, fake plutôt que mock, injection de dépendances avec pytest |
| **S'appuie sur** | M01 (valider à la frontière), M02 (échecs explicites sous forme de `Result`) |
| **Message pour l'audience** | Concevoir l'interface d'abord, la simuler pour les tests, brancher le réel par injection : la même suite de tests tourne sur les deux |

---

## Objectifs d'apprentissage

1. Concevoir une interface d'adaptateur avec `typing.Protocol` comme couture entre votre code et le monde extérieur
2. Écrire un fake maison qui implémente toute l'interface, sans bibliothèque de mock
3. Écrire des tests contre le fake qui couvrent tous les comportements : chemins heureux et malheureux
4. Appliquer la même suite de tests à l'implémentation de production via une fixture pytest paramétrée
5. Poser timeouts, retry borné et validation des réponses dans l'adaptateur
6. Expliquer pourquoi les fakes valent mieux que les mocks pour tester un contrat

---

## Timing de l'animateur

```
00:00 — 00:45   Accroche : le monde extérieur hostile (45 s)
00:45 — 01:30   Concept : M01 + M02 à la frontière (45 s)
01:30 — 02:30   Le pattern adaptateur : dessiner la couture d'abord (60 s)
02:30 — 03:30   Protocol comme interface (60 s)
03:30 — 05:00   L'implémentation fake (90 s)
05:00 — 06:00   Tests contre le fake : tous les cas de comportement (60 s)
06:00 — 07:00   L'adaptateur Stripe réel (60 s)
07:00 — 08:00   Injection en test : même suite, deux implémentations (60 s)
08:00 — 09:00   Timeout + retry dans l'adaptateur (60 s)
09:00 — 09:30   Circuit breaker + idempotence (30 s)
09:30 — 10:00   Conclusion (30 s)
```

---

## Partie 1 — Accroche (45 s)

**Ouvrir avec :**

> « Tout ce que nous avons vu jusqu'ici (valider à la frontière, échouer explicitement, encoder l'échec dans le type) suppose que *vous* avez écrit l'autre côté. Vous maîtrisez le modèle de données. Vous maîtrisez ce qui entre et ce qui sort. »

**Pause.**

> « Les dépendances externes cassent complètement cette hypothèse. Une API HTTP peut renvoyer 200 avec une erreur dans le corps. Elle peut se bloquer 30 secondes avant d'expirer. Elle peut réussir au premier appel et échouer au retry, parce que votre retry a déclenché un second débit. »

**Le cadre :**

> « Le monde extérieur est indifférent à votre exactitude. Votre travail consiste à bâtir un périmètre défensif à chaque point où votre code franchit une frontière de process, et à le concevoir de façon à le tester sans toucher au vrai service. »

### ⚔ Emplacement de la war story

> *Votre histoire ici. Pistes à forte valeur :*
> - *Un retry sans idempotence qui a débité un client deux fois*
> - *Un appel sans timeout qui a retenu un thread du pool de connexions pendant 40 minutes*
> - *Un déploiement chez un tiers qui a renommé un champ : des `None` propagés en silence en aval*
> - *Un mock qui passait les tests mais ne correspondait pas à ce que l'API réelle renvoyait*

---

## Partie 2 — Concept : M01 + M02 à la frontière (45 s)

**Pont depuis M01 et M02 :**

```
M01 — valider à la frontière :  réponse d'API = entrée non fiable. Valider la forme.
M02 — échecs explicites :       erreurs réseau = Result[T, E]. Pas d'exceptions.
M04 — les deux, sous pression : lent, de forme inattendue, menteur, et vous le rejouez.
```

**Les trois règles :**

> 1. Chaque appel externe a un timeout. Toujours.
> 2. Chaque réponse est validée. Ne jamais faire confiance à la forme.
> 3. Chaque opération qui change un état est conçue pour être rejouable sans danger.

**Et une règle d'aujourd'hui :**

> 4. Concevoir l'interface d'abord. L'implémentation réelle est un plugin.

---

## Partie 3 — Le pattern adaptateur : dessiner la couture d'abord (60 s)

L'idée centrale : **votre logique métier ne doit jamais savoir qu'elle parle à Stripe**.

Elle parle à une abstraction `PaymentGateway` (port sortant). Votre adaptateur de production (adaptateur piloté) se branche dessus comme une implémentation séparée.

```
[ core/ (cœur hexagonal) ]   ──────►   [ ports/ (abstractions) ]
- payment_processor.py                 - payment_gateway.py (Protocol)
- result.py                            - dtos.py (contrats de données)
                                                     ▲
                                                     │
                                       [ adapters/ (plugins) ]
                                       - fake_payment_gateway.py
                                       - stripe_payment_gateway.py
```

**Pourquoi c'est important :**

- Votre logique de domaine (`core/`) est entièrement pure : elle n'importe aucun client réseau, aucun framework, ni Stripe.
- Changer de fournisseur de paiement revient à écrire un nouvel adaptateur dans `adapters/`, sans toucher à la logique métier de `core/`.
- L'interface et ses contrats (`ports/`) fixent les frontières strictes de ce qui entre et sort de votre système.
- La suite de tests qui tourne contre le fake tourne *aussi* contre Stripe : même contrat, autre adaptateur.

**À dire :** « L'interface est la décision de conception la plus importante que vous prendrez sur cette dépendance. Si l'interface est juste, le reste est un détail. »

---

## Partie 4 — Protocol comme interface (60 s)

Python offre deux façons de définir une interface. On commence par `Protocol`.

### `typing.Protocol` — sous-typage structurel

```python
from typing import Protocol
from dataclasses import dataclass

# Types valeur — ce qui circule à travers l'interface
@dataclass(frozen=True)
class ChargeRequest:
    amount_cents:    int      # toujours en centimes : flottants et argent ne se mélangent pas
    currency:        str      # "EUR", "USD", "GBP"
    customer_id:     str
    idempotency_key: str      # à la charge de l'appelant de la générer

@dataclass(frozen=True)
class ChargeResult:
    charge_id:   str
    amount_cents: int
    currency:     str
    status:       str         # "succeeded", "pending"

@dataclass(frozen=True)
class RefundRequest:
    charge_id:       str
    amount_cents:    int      # remboursement partiel possible
    idempotency_key: str

@dataclass(frozen=True)
class RefundResult:
    refund_id:    str
    charge_id:    str
    amount_cents: int
    status:       str

# Types d'erreur
@dataclass(frozen=True)
class PaymentDeclined:
    reason: str

@dataclass(frozen=True)
class PaymentServiceError:
    message: str

ChargeOutcome = Ok[ChargeResult] | Err[PaymentDeclined | PaymentServiceError]
RefundOutcome = Ok[RefundResult] | Err[PaymentServiceError]

# L'interface — structurelle, sans héritage
class PaymentGateway(Protocol):
    async def charge(self, request: ChargeRequest) -> ChargeOutcome: ...
    async def refund(self, request: RefundRequest) -> RefundOutcome: ...
```

**À dire :** « Protocol est du sous-typage structurel : du duck typing avec vérification de types. Toute classe qui implémente `charge` et `refund` avec les bonnes signatures *est* un `PaymentGateway`, sans en hériter. mypy le vérifie. Aucun enregistrement, aucune classe de base. »

### ABC — l'alternative (à mentionner brièvement)

```python
from abc import ABC, abstractmethod

class PaymentGateway(ABC):
    @abstractmethod
    async def charge(self, request: ChargeRequest) -> ChargeOutcome: ...
    @abstractmethod
    async def refund(self, request: RefundRequest) -> RefundOutcome: ...

# Différence : héritage explicite requis, vérifié à l'instanciation
# ABC : quand on veut une garantie à l'exécution même sans mypy
# Protocol : quand on veut du typage structurel et un maximum de souplesse
```

**À dire :** « ABC impose le contrat à l'instanciation : un `TypeError` apparaît si vous oubliez une méthode, même sans vérificateur de types. Protocol l'impose au moment du type-check. Dans une base de code bien typée, Protocol est plus propre. Dans une base mixte ou héritée, ABC offre un filet de sécurité à l'exécution. »

---

## Partie 5 — L'implémentation fake (90 s)

> *« Un fake est une vraie implémentation : légère, en mémoire, sans réseau. Un mock remplace des appels par des assertions. Un fake remplace le système par un système plus simple qui se comporte correctement. »*

```python
import uuid

class FakePaymentGateway:
    """
    Passerelle de paiement en mémoire pour les tests et le développement local.
    Implémente tout le Protocol PaymentGateway.
    Aucun réseau. Aucun état externe. Entièrement pilotable.
    """

    def __init__(self):
        self._charges: dict[str, ChargeResult] = {}
        self._refunds:  dict[str, RefundResult] = {}
        # Points de contrôle pour les tests — configurer les pannes depuis le test
        self.decline_next:   bool = False
        self.decline_reason: str  = "insufficient_funds"
        self.fail_next:      bool = False

    async def charge(self, request: ChargeRequest) -> ChargeOutcome:
        # Idempotence — même clé, même résultat
        if request.idempotency_key in self._charges:
            return Ok(self._charges[request.idempotency_key])

        # Modes de panne configurables — les tests les activent
        if self.fail_next:
            self.fail_next = False
            return Err(PaymentServiceError("gateway unavailable"))

        if self.decline_next:
            self.decline_next = False
            return Err(PaymentDeclined(self.decline_reason))

        # Préconditions — le fake impose le même contrat que le réel
        if request.amount_cents <= 0:
            return Err(PaymentDeclined("amount must be positive"))
        if request.currency not in {"EUR", "USD", "GBP"}:
            return Err(PaymentDeclined(f"unsupported currency: {request.currency}"))

        result = ChargeResult(
            charge_id=f"fake_ch_{uuid.uuid4().hex[:8]}",
            amount_cents=request.amount_cents,
            currency=request.currency,
            status="succeeded",
        )
        self._charges[request.idempotency_key] = result
        return Ok(result)

    async def refund(self, request: RefundRequest) -> RefundOutcome:
        # Idempotence
        if request.idempotency_key in self._refunds:
            return Ok(self._refunds[request.idempotency_key])

        if self.fail_next:
            self.fail_next = False
            return Err(PaymentServiceError("gateway unavailable"))

        # Retrouver le débit d'origine
        charge = next(
            (c for c in self._charges.values() if c.charge_id == request.charge_id),
            None,
        )
        if charge is None:
            return Err(PaymentServiceError(f"charge {request.charge_id!r} not found"))
        if request.amount_cents > charge.amount_cents:
            return Err(PaymentServiceError("refund exceeds original charge amount"))

        result = RefundResult(
            refund_id=f"fake_re_{uuid.uuid4().hex[:8]}",
            charge_id=request.charge_id,
            amount_cents=request.amount_cents,
            status="succeeded",
        )
        self._refunds[request.idempotency_key] = result
        return Ok(result)
```

**Points clés à dire :**

- `decline_next` et `fail_next` sont des **points de contrôle pour les tests** : le test lève un drapeau, l'appel suivant se comporte en conséquence. Ni bibliothèque de mock, ni patch, ni magie.
- L'idempotence est implémentée dans le fake : même clé, même résultat. Le test vérifie ce comportement, que Stripe garantit aussi.
- Le fake impose les mêmes préconditions que le réel : `amount_cents > 0`, devises supportées. Un fake trop permissif laisse passer les violations de contrat dans vos tests.

---

## Partie 6 — Tests contre le fake : tous les cas de comportement (60 s)

```python
import pytest
import uuid

def make_key() -> str:
    return str(uuid.uuid4())

@pytest.fixture
def gateway() -> FakePaymentGateway:
    return FakePaymentGateway()

# Chemin heureux
async def test_charge_succeeds(gateway):
    result = await gateway.charge(ChargeRequest(
        amount_cents=1000, currency="EUR",
        customer_id="cust_1", idempotency_key=make_key(),
    ))
    assert isinstance(result, Ok)
    assert result.value.amount_cents == 1000
    assert result.value.status == "succeeded"

# Chemin malheureux — carte refusée
async def test_charge_declined(gateway):
    gateway.decline_next = True
    gateway.decline_reason = "insufficient_funds"
    result = await gateway.charge(ChargeRequest(
        amount_cents=1000, currency="EUR",
        customer_id="cust_1", idempotency_key=make_key(),
    ))
    assert isinstance(result, Err)
    assert isinstance(result.error, PaymentDeclined)
    assert result.error.reason == "insufficient_funds"

# Chemin malheureux — passerelle indisponible
async def test_charge_service_error(gateway):
    gateway.fail_next = True
    result = await gateway.charge(ChargeRequest(
        amount_cents=1000, currency="EUR",
        customer_id="cust_1", idempotency_key=make_key(),
    ))
    assert isinstance(result, Err)
    assert isinstance(result.error, PaymentServiceError)

# Idempotence — même clé, même résultat, deux appels
async def test_charge_idempotent(gateway):
    key = make_key()
    request = ChargeRequest(amount_cents=500, currency="USD",
                            customer_id="cust_2", idempotency_key=key)
    first  = await gateway.charge(request)
    second = await gateway.charge(request)
    assert isinstance(first, Ok)
    assert isinstance(second, Ok)
    assert first.value.charge_id == second.value.charge_id  # même résultat

# Remboursement, chemin heureux
async def test_refund_succeeds(gateway):
    key = make_key()
    charge = await gateway.charge(ChargeRequest(
        amount_cents=2000, currency="EUR",
        customer_id="cust_3", idempotency_key=key,
    ))
    assert isinstance(charge, Ok)

    refund = await gateway.refund(RefundRequest(
        charge_id=charge.value.charge_id,
        amount_cents=500,                   # remboursement partiel
        idempotency_key=make_key(),
    ))
    assert isinstance(refund, Ok)
    assert refund.value.amount_cents == 500

# Remboursement supérieur au débit — violation de contrat
async def test_refund_exceeds_charge(gateway):
    key = make_key()
    charge = await gateway.charge(ChargeRequest(
        amount_cents=1000, currency="EUR",
        customer_id="cust_4", idempotency_key=key,
    ))
    assert isinstance(charge, Ok)

    refund = await gateway.refund(RefundRequest(
        charge_id=charge.value.charge_id,
        amount_cents=9999,                  # plus que le montant débité
        idempotency_key=make_key(),
    ))
    assert isinstance(refund, Err)
    assert isinstance(refund.error, PaymentServiceError)
```

**À dire :** « Ces tests couvrent tout le contrat de comportement de l'interface : l'implémentation de Stripe et les appels HTTP restent hors champ. Ils tournent en millisecondes, sans réseau ni identifiants. Dans un instant, les mêmes tests tourneront contre le vrai Stripe. »

---

## Partie 7 — L'adaptateur Stripe réel (60 s)

```python
import httpx
import stamina
from pydantic import BaseModel

# Modèles Pydantic pour les formes réelles des réponses de Stripe
class StripeCharge(BaseModel):
    id:       str
    amount:   int
    currency: str
    status:   str

class StripeRefund(BaseModel):
    id:       str
    charge:   str
    amount:   int
    status:   str

class StripePaymentGateway:
    """Adaptateur de production : enveloppe l'API de Stripe derrière le Protocol PaymentGateway."""

    def __init__(self, api_key: str):
        self._client = httpx.AsyncClient(
            base_url="https://api.stripe.com/v1",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=httpx.Timeout(connect=2.0, read=10.0),
        )

    @stamina.retry(on=(httpx.TimeoutException, httpx.TransportError), attempts=3, wait_initial=0.5, wait_jitter=0.2)
    async def charge(self, request: ChargeRequest) -> ChargeOutcome:
        try:
            response = await self._client.post(
                "/payment_intents",
                data={
                    "amount":   request.amount_cents,
                    "currency": request.currency.lower(),
                    "customer": request.customer_id,
                    "confirm":  "true",
                },
                headers={"Idempotency-Key": request.idempotency_key},
            )

            if response.status_code == 402:           # carte refusée
                body = response.json()
                return Err(PaymentDeclined(
                    body.get("error", {}).get("decline_code", "unknown")
                ))

            response.raise_for_status()
            stripe_charge = StripeCharge.model_validate(response.json())

            return Ok(ChargeResult(
                charge_id=stripe_charge.id,
                amount_cents=stripe_charge.amount,
                currency=stripe_charge.currency.upper(),
                status=stripe_charge.status,
            ))

        except httpx.HTTPStatusError as e:
            return Err(PaymentServiceError(f"Stripe error {e.response.status_code}"))
        except httpx.TimeoutException:
            return Err(PaymentServiceError("Stripe request timed out"))

    @stamina.retry(on=(httpx.TimeoutException, httpx.TransportError), attempts=3, wait_initial=0.5, wait_jitter=0.2)
    async def refund(self, request: RefundRequest) -> RefundOutcome:
        try:
            response = await self._client.post(
                "/refunds",
                data={
                    "charge": request.charge_id,
                    "amount": request.amount_cents,
                },
                headers={"Idempotency-Key": request.idempotency_key},
            )
            response.raise_for_status()
            stripe_refund = StripeRefund.model_validate(response.json())

            return Ok(RefundResult(
                refund_id=stripe_refund.id,
                charge_id=stripe_refund.charge,
                amount_cents=stripe_refund.amount,
                status=stripe_refund.status,
            ))

        except httpx.HTTPStatusError as e:
            return Err(PaymentServiceError(f"Stripe refund error {e.response.status_code}"))
        except httpx.TimeoutException:
            return Err(PaymentServiceError("Stripe refund timed out"))

    async def aclose(self):
        await self._client.aclose()
```

**À dire :** « Regardez ce que contient l'adaptateur : timeouts, retry, validation des réponses avec pydantic, types `Result` explicites. Tout le défensif reste ici. La logique métier ne voit jamais un appel httpx. Elle appelle `charge()` et reçoit un `ChargeOutcome`. »

---

## Partie 8 — Injection en test : même suite, deux implémentations (60 s)

```python
# conftest.py

import asyncio
import pytest
import os

def pytest_addoption(parser):
    parser.addoption(
        "--gateway",
        default="fake",
        choices=["fake", "stripe"],
        help="Implémentation de la passerelle de paiement à tester",
    )

@pytest.fixture
def gateway(request) -> PaymentGateway:
    mode = request.config.getoption("--gateway")

    if mode == "stripe":
        api_key = os.environ["STRIPE_TEST_API_KEY"]
        gw = StripePaymentGateway(api_key=api_key)
        yield gw
        # nettoyage : annuler les payment intents de test
        asyncio.run(gw.aclose())
    else:
        yield FakePaymentGateway()
```

```bash
# Contre le fake : rapide, sans identifiants, toujours exécuté en CI
pytest tests/payment/

# Contre l'environnement de test de Stripe : lent, identifiants requis, à la demande
pytest tests/payment/ --gateway=stripe
```

**À dire :** « Le fichier de tests ne change pas. La fixture change. Le drapeau `--gateway` décide quelle implémentation est injectée. Chaque test qui passe contre le fake est une affirmation sur le contrat, et lancer la même suite contre Stripe vérifie que l'adaptateur réel respecte ce contrat. »

**L'idée à faire passer :**

> « Le fake est le test de la conception de l'interface. S'il est difficile à écrire, votre interface est trop large. Si le fake doit connaître HTTP, votre abstraction fuit. Le fake est un retour d'information. »

---

## Partie 9 — Timeout, retry, idempotence : où ils vivent (30 s)

**La réponse : dans l'adaptateur. Toujours.**

```
[ Logique métier ]   charge(request)          Result[ChargeResult, ...]
        │            ──────────────────────►   ◄──────────────────────
        │
[ StripePaymentGateway ]
    - timeout de connexion : 2 s    ← ici
    - timeout de lecture : 10 s     ← ici
    - retry sur erreur transitoire : 3x ← ici
    - clé d'idempotence : transmise ← l'appelant la génère, l'adaptateur la fait passer
    - validation de la réponse      ← ici
    - enveloppe Result              ← ici
```

**À dire :** « La logique métier génère la clé d'idempotence, car elle possède l'identité de l'opération. L'adaptateur gère tout le transport. C'est la séparation nette que donne le pattern adaptateur. »

---

## Partie 10 — Tester l'adaptateur contre un fournisseur défaillant

> *« Le fake teste le contrat. Mais qui teste l'adaptateur, la couche de traduction entre votre interface et la réalité de Stripe ? Il faut un moyen de simuler un Stripe défaillant, sans Stripe. »*

### Le principe : injecter le transport, pas le client

Le `StripePaymentGateway` dépend de `httpx.AsyncClient`. Ce client est la couture pour l'injection de pannes du fournisseur. On le remplace par un transport pilotable : pas de réseau, contrôle total sur ce que « renvoie » Stripe.

```python
# httpx permet d'injecter un transport personnalisé — pas de monkeypatching
import httpx

class FaultyStripeTransport(httpx.AsyncBaseTransport):
    """Simule un Stripe défaillant au niveau du transport HTTP."""

    def __init__(self, behaviour: str):
        self.behaviour = behaviour  # "timeout" | "500" | "200_with_error" | "garbled"

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        match self.behaviour:
            case "timeout":
                raise httpx.ReadTimeout("Stripe did not respond", request=request)
            case "500":
                return httpx.Response(500, json={"error": {"message": "internal error"}})
            case "200_with_error":
                # Le classique : HTTP 200, le corps annonce une erreur
                return httpx.Response(200, json={"status": "error", "code": "processing_error"})
            case "garbled":
                # Forme de réponse complètement fausse : champ renommé, manquant
                return httpx.Response(200, json={"charge_id": "ch_123"})  # pas la forme StripeCharge
            case _:
                raise ValueError(f"unknown behaviour: {self.behaviour}")
```

### L'adaptateur accepte un client injectable

```python
class StripePaymentGateway:
    def __init__(self, api_key: str, client: httpx.AsyncClient | None = None):
        self._client = client or httpx.AsyncClient(
            base_url="https://api.stripe.com/v1",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=httpx.Timeout(connect=2.0, read=10.0),
        )
```

### Tests de pannes du fournisseur : courts, explicites, exhaustifs

```python
def make_stripe(behaviour: str) -> StripePaymentGateway:
    transport = FaultyStripeTransport(behaviour)
    client = httpx.AsyncClient(
        base_url="https://api.stripe.com/v1",
        transport=transport,
    )
    return StripePaymentGateway(api_key="sk_test_fake", client=client)

# Principe 1 : timeout → PaymentServiceError, aucune exception ne fuit
async def test_adapter_timeout_returns_result():
    gw = make_stripe("timeout")
    result = await gw.charge(ChargeRequest(
        amount_cents=1000, currency="EUR",
        customer_id="cust_1", idempotency_key="key_1",
    ))
    assert isinstance(result, Err)
    assert isinstance(result.error, PaymentServiceError)
    assert "timed out" in result.error.message

# Principe 2 : 500 → PaymentServiceError, jamais un HTTPStatusError non géré
async def test_adapter_500_returns_result():
    gw = make_stripe("500")
    result = await gw.charge(ChargeRequest(
        amount_cents=1000, currency="EUR",
        customer_id="cust_1", idempotency_key="key_1",
    ))
    assert isinstance(result, Err)
    assert isinstance(result.error, PaymentServiceError)

# Principe 3 : 200 avec un corps d'erreur → PaymentServiceError (jamais Ok)
async def test_adapter_200_with_error_body():
    gw = make_stripe("200_with_error")
    result = await gw.charge(ChargeRequest(
        amount_cents=1000, currency="EUR",
        customer_id="cust_1", idempotency_key="key_1",
    ))
    assert isinstance(result, Err)   # Ok serait faux : l'adaptateur doit vérifier le corps

# Principe 4 : réponse corrompue → PaymentServiceError, aucune ValidationError ne fuit
async def test_adapter_garbled_response():
    gw = make_stripe("garbled")
    result = await gw.charge(ChargeRequest(
        amount_cents=1000, currency="EUR",
        customer_id="cust_1", idempotency_key="key_1",
    ))
    assert isinstance(result, Err)
    assert isinstance(result.error, PaymentServiceError)
    # Une ValidationError de pydantic ne doit jamais franchir la frontière de l'adaptateur
```

### Les quatre principes que ces tests imposent

**1. Aucune exception ne sort de l'adaptateur.** Timeouts, erreurs réseau, erreurs HTTP : tout devient `Err(PaymentServiceError(...))`. La logique métier n'attrape jamais d'exceptions httpx. Elle ne doit jamais avoir à le faire.

**2. HTTP 200 ne signifie pas succès.** L'adaptateur vérifie le corps. Un 200 avec une charge utile d'erreur donne `Err`. Les incidents de production se nichent dans ce piège.

**3. Une violation de schéma est un échec de l'adaptateur.** Si Stripe change la forme de sa réponse, pydantic lève `ValidationError`. L'adaptateur l'attrape et retourne `Err(PaymentServiceError(...))`. Une `ValidationError` ne regarde jamais l'appelant.

**4. Le transport est la couture pour l'injection de pannes.** Ni monkeypatching ni `unittest.mock.patch`. On injecte un transport, on contrôle le comportement, on teste la réponse de l'adaptateur. Explicite et sans magie.

---

## Circuit breaker — en une phrase (15 s)

> « Pour les dépendances à fort volume, ajoutez un circuit breaker autour de l'adaptateur. Quand Stripe est en panne, échouez vite : inutile de rejouer 3 fois chaque requête de votre file. Laissez au service le temps de se rétablir. »

---

## Conclusion (15 s)

> « Concevoir l'interface. La simuler. Tester le contrat. Brancher le réel. Lancer les mêmes tests. C'est la boucle complète, et elle s'applique à chaque dépendance externe que vous écrirez. »

---

## Points clés

1. **Concevoir l'interface d'abord** : votre logique métier ne doit jamais savoir qu'elle parle à Stripe.
2. **`typing.Protocol`** est du sous-typage structurel : toute classe qui a la bonne forme *est* l'interface.
3. **Des fakes plutôt que des mocks** : un fake est une vraie implémentation, légère et pilotable. Un mock teste l'appel, le fake teste le contrat.
4. **Le fake est un retour sur la conception** : difficile à écrire, il signale une interface trop large ou qui fuit.
5. **Mêmes tests, deux implémentations** : l'injection par fixture pytest lance la suite de contrat sur le fake et sur le réel.
6. **Toute la mécanique défensive vit dans l'adaptateur** : timeout, retry, validation, enveloppe Result.
7. **L'appelant génère la clé d'idempotence**, l'adaptateur la transmet. Le retry est sûr.

---

## Notes pour les slides (phase 2)

Visuels clés de ce module :
- Le schéma de la couture : logique métier → Protocol → [Fake | Stripe]
- Le flux d'injection en test : même fichier de tests, drapeau `--gateway`, deux chemins de fixture
- Points de contrôle du fake : `decline_next`, `fail_next`, à montrer comme un simple interrupteur d'état
- Où vit la mécanique défensive : diagramme annoté de la classe adaptateur

---

## Références

- `typing.Protocol` — PEP 544, Python 3.8+
- Documentation `httpx` async — https://www.python-httpx.org
- Bibliothèque `stamina` — https://stamina.hynek.me
- Documentation du mode test de Stripe — https://stripe.com/docs/testing
- *Growing Object-Oriented Software, Guided by Tests* — Freeman & Pryce (l'argument fake contre mock, de façon définitive)
- *Working Effectively with Legacy Code* — Feathers (théorie des coutures)

---

*Module 04 sur 6 · Defensive Programming from the Trenches*
