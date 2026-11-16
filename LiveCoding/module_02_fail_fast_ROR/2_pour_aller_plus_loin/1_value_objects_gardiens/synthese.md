# Module 02 — Synthèse : Value Objects comme gardiens

## Place dans le Module 02

- **Étape :** hors live, approfondissement après les écritures 1 à 3
- **S'appuie sur :** `../../1_live/ecriture_3_returns.py` (`Success`, `Failure`, `flow`, `bind`)
- **Fichiers :** `a_solution_value_objects.py` (le type `Amount`), `solution_ror_with_amount.py` (le ROP qui l'utilise), `test_value_object.py`
- **Prépare :** le Module 03 du guide (*Contracts & invariants*, états illégaux impossibles)

---

## Rendre les états invalides impossibles

Un value object peut jouer le rôle de **gardien** : il impose ses invariants au niveau du type, et une donnée invalide ne peut jamais être créée.

### Approche classique (problématique)

```python
def withdraw(account, amount):
    if amount < 0:
        raise ValueError("Amount cannot be negative")
    if amount > account.balance:
        raise ValueError("Insufficient funds")
    # ... logique métier
```

Défauts :
- La validation se fait dans la logique métier
- Une donnée invalide peut se propager dans le système
- La même validation doit être répétée partout
- Les erreurs apparaissent tard dans l'exécution

### Approche gardienne (value objects)

```python
@dataclass(frozen=True)
class Amount:
    _value: float

    def __post_init__(self):
        if self._value < 0:
            raise AmountNegative(self._value)
        if self._value == 0:
            raise AmountZero()
```

Avantages :
- La validation se fait à la création de l'objet
- Les états invalides sont impossibles à représenter
- Une seule source de vérité pour la validation
- Les erreurs apparaissent immédiatement

---

## Concepts clés

### 1. Le value object garde l'invariant
- Il encapsule la logique de validation
- Il impose les invariants métier au niveau du type
- Une fois créé, l'objet est garanti valide

### 2. Fail fast à la création
```python
# Échoue immédiatement : le montant négatif n'entre jamais dans le système
amount = Amount(-10.0)  # lève AmountNegative

# Avec l'approche classique, -10.0 pourrait traverser la logique métier
# avant d'être attrapé, loin de la source
```

### 3. Garantie d'immutabilité
- Une dataclass frozen interdit la mutation
- Valide une fois, valide toujours
- Sûr entre threads par construction

### 4. Sécurité composable
```python
def process_withdrawal(user_id: int, amount_value: float) -> Result[Amount, Exception]:
    # Le garde contre les montants négatifs se trouve ici, à la boundary
    amount = Amount.create(amount_value)._unwrap()

    # La logique métier peut supposer que amount est toujours valide
    account = find_user(user_id)
    account.withdraw(amount)  # inutile de revérifier amount >= 0
```

---

## Patterns d'implémentation

### Pattern 1 : garde dans le constructeur (⚠️ contredit les règles de constructeur)

```python
@dataclass(frozen=True)
class Amount:
    _value: float

    def __post_init__(self):
        if self._value < 0:
            raise AmountNegative(self._value)
```

**Problème :** ce pattern enfreint des règles importantes :
- **Un constructeur ne devrait pas contenir de logique métier** : la validation a sa place ailleurs
- **Un constructeur ne devrait pas planter** : la création d'objet doit être sûre et prévisible
- **La création devient risquée** : `Amount(-10.0)` lève une exception
- **Le fail fast se déplace** : l'erreur survient pendant la construction, loin des boundaries du système

### Pattern 2 : factory method avec Result (✅ recommandé)

```python
@dataclass(frozen=True)
class Amount:
    _value: float

    @classmethod
    def create(cls, value: float) -> Result["Amount", AmountError]:
        """Factory method qui retourne un Result au lieu de lever une exception."""
        if value < 0:
            return Failure(AmountNegative(value))
        if value == 0:
            return Failure(AmountZero())
        return Success(cls(value))
```

**Avantages :**
- **Le constructeur reste pur** : aucune validation dans `__post_init__`
- **Création sûre** : ne lève jamais d'exception
- **Gestion d'erreur explicite** : un `Result` se compose
- **Fail fast respecté** : la validation se fait à la boundary du système
- **Composable** : s'intègre naturellement au Railway Oriented Programming

### Pattern 3 : constructeur privé + factory (le plus robuste)

```python
@dataclass(frozen=True)
class Amount:
    _value: float

    def __init__(self, value: float):
        # Constructeur privé : appelé uniquement par les factory methods
        object.__setattr__(self, '_value', value)

    @classmethod
    def create(cls, value: float) -> Result["Amount", AmountError]:
        """Factory method publique avec validation."""
        if value < 0:
            return Failure(AmountNegative(value))
        if value == 0:
            return Failure(AmountZero())
        return Success(cls(value))

    @classmethod
    def unsafe_create(cls, value: float) -> "Amount":
        """Constructeur non sûr, pour un usage interne quand la valeur est déjà validée."""
        return cls(value)
```

**Avantages :**
- **La factory devient le passage obligé** : le constructeur privé empêche l'instanciation directe
- **Séparation nette** : validation dans la factory, construction dans le constructeur
- **Optimisation interne** : `unsafe_create` pour les valeurs déjà validées
- **Sûreté de type** : impossible de créer un `Amount` invalide

### Pattern 4 : opérations arithmétiques sûres

```python
def __add__(self, other: "Amount") -> "Amount":
    return Amount(self._value + other._value)  # préserve l'invariant

def __sub__(self, other: "Amount") -> "Amount":
    result = self._value - other._value
    return Amount(result)  # lève si le résultat est négatif
```

---

## Bénéfices des value objects gardiens

### 1. Fin des vérifications défensives répétées
```python
# Avant : chaque fonction doit valider
def transfer(from_account, to_account, amount):
    if amount < 0:
        raise ValueError("Invalid amount")
    # ... d'autres validations
    # ... logique métier

# Après : la validation est garantie par le type
def transfer(from_account, to_account, amount: Amount):
    # amount est garanti valide : aucune validation nécessaire
    # ... logique métier seulement
```

### 2. Localisation claire de l'erreur
- Quand la validation échoue, on sait tout de suite où
- Inutile de remonter la logique métier pour trouver l'échec
- Les erreurs sont attrapées à la boundary du système

### 3. Application cohérente
- Les mêmes règles s'appliquent partout où le value object est utilisé
- Aucune chance d'« oublier » la validation sur un chemin de code
- Une seule source de vérité pour les règles métier

### 4. Code auto-documenté
```python
def process_payment(amount: Amount) -> Receipt:
    # La signature indique un montant validé
    # Aucun commentaire de validation supplémentaire nécessaire
```

---

## Quand utiliser un value object gardien

### ✅ Bons candidats
- **Contraintes numériques** (nombres positifs, plages)
- **Formats de chaîne** (emails, numéros de téléphone, identifiants)
- **Règles métier** (limites d'âge, montants minimaux)
- **Machines à états** (transitions de statut)
- **Invariants composites** (date de début < date de fin)

### ❌ Mauvais candidats
- Primitives simples sans règle métier
- Données très mutables
- Chemins critiques en performance où le coût de création compte
- Données par nature non validées (entrée utilisateur brute)

---

## Intégration avec d'autres patterns

### Avec le Railway Oriented Programming
```python
def process_withdrawal(user_id: int, amount_value: float) -> Result[Amount, Exception]:
    return (
        Amount.create(amount_value)
        .bind(lambda amount: find_user_result(user_id).bind(lambda user:
            withdraw_from_account(user, amount)))
    )
```

### Avec l'injection de dépendances
```python
# Un value object peut s'injecter comme dépendance
class PaymentService:
    def __init__(self, minimum_payment: Amount):
        self.minimum_payment = minimum_payment
```

---

## Tester les value objects gardiens

### Tester les invariants
```python
def test_negative_amount_raises_exception():
    with pytest.raises(AmountNegative):
        Amount(-10.0)

def test_zero_amount_raises_exception():
    with pytest.raises(AmountZero):
        Amount(0.0)
```

### Tester la factory method
```python
def test_factory_returns_result():
    assert isinstance(Amount.create(10.0), Success)
    assert isinstance(Amount.create(-10.0), Failure)
```

### Tester que la logique métier suppose la validité
```python
def test_business_logic_needs_no_validation():
    # Avec un Amount valide, la logique métier marche sans vérification supplémentaire
    amount = Amount(50.0)
    account = Account(1, Amount(100.0))

    account.withdraw(amount)
    assert account.balance.value == 50.0
```

---

## Comparaison avec les autres approches

| Approche | Lieu de la validation | Découverte de l'erreur | Duplication de code |
|---|---|---|---|
| Vérifications manuelles | Logique métier | Tardive | Forte |
| Décorateurs | Frontière de fonction | Précoce | Moyenne |
| Value objects | Construction du type | Immédiate | Aucune |

---

## Règle pratique

Un value object gardien déplace la défense au bon endroit :

1. **États invalides impossibles à construire** : un `Amount` existant est un `Amount` valide
2. **Échec immédiat** : le problème est attrapé à la création de l'objet
3. **Moins de code défensif** : la logique métier suppose la validité
4. **Une seule source de vérité** : la validation vit en un lieu
5. **Types auto-documentés** : la signature annonce la contrainte

Combiné au Railway Oriented Programming, cela donne un système où les échecs sont explicites et où les états invalides n'existent pas. Le Module 03 du guide développe cette direction (contrats, invariants, *illegal states unrepresentable*).
