---
marp: true
theme: default
paginate: true
title: Module 01 — Never trust input
---

<!--
Présentation de fin de démo, au format Marp (une diapositive = un bloc entre `---`).
Affichage : extension VS Code « Marp for VS Code », ou `npx @marp-team/marp-cli presentation.md --html`.
Les notes de l'instructeur sont dans les commentaires HTML sous chaque diapositive.
-->

# Never trust input

## Module 01 — Defensive Programming from the Trenches

> « Le monde est plein de menteurs. Les appelants de votre fonction n'y font pas exception. »

<!-- Accroche : question à la salle, puis votre war story (voir module_01_never_trust_input.md). 90 s. -->

---

# Le problème

```python
def create_user(data: dict) -> None:
    name = data["name"]
    age = data["age"]
    db.insert(name=name, age=age)
```

- `{"name": "", "age": -5}` entre dans la base sans résistance
- `{"name": "Bob"}` donne un `KeyError` technique, loin de la source
- La donnée invalide corrompt l'état avant qu'on s'en aperçoive

<!-- Fichier : 1_live/0_probleme_confiance_aveugle.py. Le lancer, montrer la ligne enregistrée. -->

---

# La boundary

```
[ Monde extérieur ]  ──►  [ BOUNDARY ]  ──►  [ Votre domaine ]
  users, APIs,              parser ici,         objets typés,
  queues, fichiers,         une seule fois      de confiance
  env vars, CLI
```

Après la boundary, le code n'a plus à se demander « et si c'est `None` ? ».

---

# Où sont les boundaries ?

```python
request.json()           # endpoint HTTP
os.environ["DB_URL"]     # variable d'environnement
open("config.json")      # lecture de fichier
queue.receive_message()  # message queue
sys.argv[1]              # argument CLI
db.fetchone()            # base externe dont on ne maîtrise pas le schéma
```

Chacune de ces lignes est une boundary. Chacune demande un parsing.

---

# Écriture 1 — Pythonic : Pydantic lève une exception

```python
class UserInput(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    age: int = Field(..., ge=0, le=150)
    email: str = Field(..., min_length=1)

user = UserInput(name="", age=30, email="alice@example.com")
# lève ValidationError
```

- Les règles sont déclaratives et solides
- La signature annonce `UserInput`, l'appel peut pourtant lever
- Chaque appelant doit penser au `try/except ValidationError`

<!-- Fichier : 1_live/ecriture_1_pydantic_exception.py. La signature « ment par omission ». -->

---

# Écriture 2 — FP : `parse_user` retourne un `Result`

```python
def parse_user(name: str, age: int, email: str) -> Result[UserInput, str]:
    try:
        validated = _UserSchema(name=name, age=age, email=email)
        return Success(UserInput(validated.name, validated.age, validated.email))
    except ValidationError as e:
        first = e.errors()[0]
        return Failure(f"{first['loc'][0]}: {first['msg']}")
```

- Pydantic fait toujours la validation
- Les exceptions restent confinées dans une seule fonction
- Le type de retour dit toute la vérité

<!-- Fichier : 1_live/ecriture_2_parse_user_result.py. Le schéma Pydantic reste privé (_UserSchema) à la boundary. -->

---

# Côté appelant

```python
match parse_user(name="", age=30, email="alice@example.com"):
    case Success(user):
        ...  # `user` est un UserInput de confiance
    case Failure(message):
        ...  # message : "name: ..."
```

Aucun `try/except`. Le type checker force le traitement des deux cas.

---

# Comparaison

| | Exception | `Result` |
|---|---|---|
| Chemin d'erreur visible dans la signature | Non | Oui |
| L'appelant peut ignorer l'échec | Oui | Non |
| Composable avec d'autres étapes | Non | Oui (`bind`) |
| Tests | `pytest.raises` partout | `isinstance(result, Failure)` |

Le raising reste correct quand le framework gère `ValidationError` (réponse 422).
Le `Result` apporte le plus quand vous possédez le chemin d'erreur.

---

# Les tests prouvent la règle

```python
@given(st.text(alphabet=" \t\n\r", min_size=1, max_size=100))
def test_property_whitespace_only_name_returns_failure(name):
    result = parse_user(name=name, age=25, email="a@b.com")
    assert isinstance(result, Failure)
```

- Les tests par exemple fixent les cas connus (`""`, `-1`, `"notanemail"`)
- Le test de propriété (hypothesis) balaie des centaines d'entrées

<!-- Lancer : pytest LiveCoding/module_01_never_trust_input/1_live -->

---

# Whitelist plutôt que blacklist

```python
class UserRole(str, Enum):
    VIEWER = "viewer"
    EDITOR = "editor"
    ADMIN = "admin"

class UserInput(BaseModel):
    role: UserRole   # "superadmin" → ValidationError
```

Définir ce qui est valide. Rejeter le reste.
Une blacklist rate toujours un cas (`"ADMIN"`, `" admin"`).

---

# Valider à la main : vos hypothèses sur les données sont fausses

Un « falsehood » est une croyance fausse que beaucoup de développeurs partagent sur un type de donnée.
Chacune mène à une règle de validation qui rejette des valeurs légitimes. Quelques exemples :

- Noms : peut contenir des espaces, tirets, apostrophes, unicode, une seule lettre
- Téléphones : prendre en comptes les  indicatifs, zéros initiaux, extensions
- Dates : il y a des timezones, DST, calendriers non grégoriens
- Adresses : nombre de lignes variable, pas de code postal obligatoire
- Âges : 0, 130+, inconnu
- Chaînes « vides » : `""`, `" "`, `"\t"`, `"\n"` sont quatre cas

Chaque règle « évidente » a des contre-exemples réels. Appuyez-vous sur une source qui les a déjà rencontrés :

- **Bibliothèque** : `email-validator` (derrière `EmailStr` de Pydantic), `phonenumbers` (port de libphonenumber de Google)
- **Norme** : RFC 5322 (syntaxe d'une adresse email), RFC 3339 (format des dates et timestamps)
- **Lecture** : *Falsehoods Programmers Believe About Names*, Patrick McKenzie, 2010

<!--
Les « falsehoods » sont des croyances fausses mais répandues. Le billet de McKenzie est un article de blog (kalzumeus.com, 2010) et non un livre. Il liste une quarantaine de croyances sur les noms.

Citations (en anglais, traduction libre en dessous) :
- « People's names fit within a certain defined amount of space. » (n° 6) → un nom a une longueur maximale. Faux : un champ `VARCHAR(20)` tronque des noms réels.
- « People's names do not change. » (n° 7) → un nom ne change jamais. Faux : mariage, divorce, changement d'état civil. Un nom n'est pas une clé stable.
- « People's names are written in ASCII. » (n° 9) → un nom s'écrit en ASCII. Faux : une regex `[A-Za-z ]+` rejette `Zoë`, `José`, `李`.
- Et l'auteur : « I have never seen a computer system which handles names properly and doubt one exists, anywhere. »

Apport d'une bibliothèque : `email-validator` applique la syntaxe d'une adresse (partie locale, domaine, internationalisation), normalise le résultat et peut vérifier que le domaine existe. `EmailStr` de Pydantic l'appelle : ajouter `EmailStr` à `_UserSchema` remplace le test `"@" in email`. `phonenumbers` connaît les plans de numérotation de chaque pays, ce qu'aucune regex maison ne couvre.

Apport d'une RFC : une spécification écrite par des gens qui ont listé les cas limites. La RFC 5322 (section 3.4.1, `addr-spec`) définit ce qu'est une adresse email : guillemets dans la partie locale, caractères permis, commentaires. La RFC 3339 fixe un profil ISO 8601 pour les timestamps (`2026-11-16T10:30:00+01:00`) : l'offset est obligatoire, ce qui évite l'ambiguïté du fuseau.

À dire : pour les noms, il n'existe pas de bibliothèque. La bonne règle est de les accepter presque tels quels (texte libre, longueur raisonnable, pas de caractères de contrôle). Une validation stricte y fait plus de mal que de bien.
-->

---

# À retenir

1. Parse at the boundary. Aucun `dict` brut dans la logique du domaine.
2. Les schémas Pydantic restent à la boundary, on les convertit en objets du domaine.
3. Un échec attendu se retourne en `Result`, il ne se cache pas dans une exception.
4. Whitelist ce qui est valide.
5. Une bibliothèque vaut mieux qu'une regex écrite à la main.
6. Après la boundary, plus personne ne se demande « et si c'est `None` ? ».

---

# Exercice (5 min)

Écrire `ProductInput` à partir de ce payload HTTP :

```python
{"name": "Widget Pro", "price": "29.99", "stock": -3,
 "category": "ELECTRONICS", "description": "  "}
```

- `price` arrive en `str` et doit devenir un `float` positif
- `stock` est un entier ≥ 0
- `category` appartient à un ensemble fixe, stockée en minuscules
- `description` blanche devient `None`
- Bonus : renvoyer un `Result[ProductInput, str]`

Dossier : `exercises/module_01_never_trust_input/3.exercise_product_input/`

---

# Pour aller plus loin

Dossier `2_pour_aller_plus_loin/` :

1. `1_exceptions_contre_exemple/` : la cascade d'exceptions dans un flux d'inscription
2. `2_dataclass_sans_pydantic/` : même contrat avec la stdlib seule
3. `3_erreurs_typees/` : `Result[T, ErrorADT]` au lieu de `str`
4. `4_composition_flow_bind/` : un parser par champ, composés avec `flow` et `bind`
5. `5_chaines_registration/` : les deux chaînes d'inscription, côte à côte

Les points 3 et 4 prolongent le module 02 (*Fail fast, fail loud*).
