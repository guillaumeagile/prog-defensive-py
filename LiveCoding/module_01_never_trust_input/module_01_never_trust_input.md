# Module 01 — Never Trust Input
## Detailed Lesson Plan · ~8 minutes live · Defensive Programming from the Trenches

---

## Overview

| | |
|---|---|
| **Duration** | 8 minutes (live) + 5 min exercise if async |
| **Core principle** | Validate at the boundary. Once. Loudly. |
| **Python focus** | `pydantic` v2, `dataclasses`, type hints, `__post_init__` |
| **Audience takeaway** | I know exactly where to put validation, and what tools to reach for |

---

## How to navigate this folder

This module uses **two different labels**:

- **Part 1/2/3/4/5** = the teaching timeline in this lesson plan
- **Approach A/B/C** = the validation style used in code examples

Think of it as:

- **Part = when in the lesson**
- **Approach = how validation is implemented**

### Mapping: folders, parts, and approaches

| Folder / doc | Where it fits in the lesson | What it covers | Approach labels |
|---|---|---|---|
| `1.quick_first_view/` | Part 3 (Live Code, Steps 1–3) | Compare exception-based vs Result-based boundary parsing | Approach A + B |
| `2.dataclass_post_init/` | Part 3 (Live Code, Step 4) | Show stdlib-only alternative to Pydantic | Approach C |
| `3.exercise_product_input/` | Exercise after Part 3 | Apply the same boundary contract to a richer payload | Approach B |

Parts 1, 2, 4, and 5 are mostly facilitator/script content in this file; they do not each have a matching subfolder.

---

## Learning Objectives

By the end of this module, participants will be able to:

1. Identify where the **trust boundary** is in any system they work on
2. Apply **pydantic v2** validators for boundary validation
3. Distinguish **whitelist** from **blacklist** strategies — and know which to use
4. Name at least 3 real-world "falsehood" categories that bite developers

---

## Facilitator Timing

```
00:00 — 00:90   Hook: war story or question (90 sec)
01:30 — 03:00   Concept: what is the boundary? (90 sec)
03:00 — 06:30   Live code: bad → better → best (3.5 min)
06:30 — 07:30   Whitelist vs blacklist principle (60 sec)
07:30 — 08:00   Falsehoods + exercise brief (30 sec)
```

---

## Part 1 — Hook (90 sec)

**Open with this question to the room:**

> "Has anyone here spent more than 30 minutes debugging a bug that turned out to be unexpected input — a None, an empty string, a negative number — that came in three layers back and corrupted something quietly?"

*(Pause. Let hands go up. That's your audience.)*

**Then deliver your war story.** Use the slot below — your own incident is worth 10x a hypothetical.

### ⚔ War story slot

> *Fill in before the session. Suggested angle: a None or malformed value that entered the system unvalidated, passed through 2–3 layers of logic, and either:*
> - *corrupted a database record silently*
> - *caused a wrong calculation that only surfaced in production*
> - *triggered a crash far from the actual source*
>
> *Structure: what entered → where it should have been caught → where it actually failed → how long it took to trace back.*

**Punchline to land after the story:**

> "The problem wasn't the bug itself. It was that we trusted the caller. And in production, no caller can be trusted — not a user, not a frontend, not another service you wrote yourself."

---

## Part 2 — Concept: The Trust Boundary (90 sec)

**Draw this on a whiteboard or say it verbally:**

```
[ Outside world ]  ──►  [ BOUNDARY ]  ──►  [ Your domain logic ]
  users, APIs,           ← validate           clean, typed,
  queues, files,           here, once          trusted objects
  env vars, CLI
```

**Key points to make:**

- The boundary is anywhere data **enters** your system: HTTP endpoints, CLI args, message queue consumers, file readers, environment variables, database reads from external sources
- Validation inside domain logic means you're patching symptoms, not fixing the disease
- After the boundary, your code should be able to trust its inputs completely — that's the **contract** the boundary enforces

**What counts as "the boundary":**

```python
# These are ALL boundaries — validate at every one
request.json()           # HTTP endpoint
os.environ["DB_URL"]     # environment variable
open("config.json")      # file read
queue.receive_message()  # message queue
sys.argv[1]              # CLI argument
db.fetchone()            # external DB (you don't control the schema)
```

---

## Part 3 — Live Code (3.5 min)

> **Facilitator note**: Type these live. Don't paste. The act of writing them signals "this is simple enough to do in real work."

### Step 1: The bad code (60 sec)

```python
# ❌ Trusting the caller completely
def create_user(data: dict):
    name  = data["name"]
    age   = data["age"]
    email = data["email"]
    db.insert(name=name, age=age, email=email)
```

**Ask the room:** "What can go wrong here?"

Expected answers to draw out:
- `data["name"]` raises `KeyError` if key is missing
- `age` could be `"thirty-two"`, `-1`, `None`, `9999`
- `email` could be `"not-an-email"` or an empty string
- `name` could be `""` or `"   "` (whitespace-only)
- `data` itself could be `None`

**The failure mode isn't a crash here — it's a corrupt database row. That's worse.**

---

### Step 2: Naive improvement — still bad (30 sec)

```python
# ❌ Better, but still fragile — manual, scattered, incomplete
def create_user(data: dict):
    if not data:
        raise ValueError("data is required")
    if "name" not in data or not data["name"].strip():
        raise ValueError("name is required")
    if "age" not in data or not isinstance(data["age"], int):
        raise ValueError("age must be an integer")
    # ... this grows forever, never covers all cases
    db.insert(**data)
```

**Say:** "This is the path most devs take. It's brittle, it grows, it misses cases, and it mixes validation with logic. There's a better tool."

---

### Step 3: Pydantic v2 — the right tool (90 sec)

```python
# ✅ Validation at the boundary with pydantic v2
from pydantic import BaseModel, Field, field_validator, EmailStr

class UserInput(BaseModel):
    name:  str   = Field(..., min_length=1, max_length=100)
    age:   int   = Field(..., ge=0, le=150)
    email: EmailStr

    @field_validator("name")
    @classmethod
    def strip_and_require(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("name cannot be blank or whitespace-only")
        return stripped

def create_user(data: dict) -> None:
    user = UserInput(**data)        # raises ValidationError immediately if invalid
    db.insert(                      # db layer receives clean, typed, trusted values
        name=user.name,
        age=user.age,
        email=user.email
    )
```

**Demo: call these live and show the output**

```python
# Good input — works cleanly
create_user({"name": "  Alice  ", "age": 30, "email": "alice@example.com"})
# name is stored as "Alice" (stripped)

# Bad inputs — all caught immediately with clear messages
create_user({"name": "",    "age": 30,   "email": "alice@example.com"})
# ValidationError: name cannot be blank or whitespace-only

create_user({"name": "Bob", "age": -5,   "email": "alice@example.com"})
# ValidationError: age: Input should be greater than or equal to 0

create_user({"name": "Bob", "age": 30,   "email": "not-an-email"})
# ValidationError: email: value is not a valid email address

create_user({"name": "Bob", "age": "thirty"})
# ValidationError: age: Input should be a valid integer
```

**Key things to say:**
- One place for all validation logic — the model class
- Errors are **descriptive and immediate** — not buried three calls later
- The `db.insert()` call is now completely clean — it gets trusted data or nothing at all
- `EmailStr` is one import away — don't rewrite email validation yourself

---

### Step 4: Without pydantic — `dataclass` + `__post_init__` (45 sec)

> *"If you can't or won't add pydantic to a project, here's the equivalent pattern."*

```python
from dataclasses import dataclass
import re

@dataclass
class UserInput:
    name:  str
    age:   int
    email: str

    def __post_init__(self):
        self.name = self.name.strip()
        if not self.name:
            raise ValueError("name cannot be blank")
        if not (0 <= self.age <= 150):
            raise ValueError(f"age {self.age} is out of range [0, 150]")
        if not re.match(r"[^@]+@[^@]+\.[^@]+", self.email):
            raise ValueError(f"invalid email: {self.email}")
```

**Say:** "Same idea — validate on construction, fail immediately. Pydantic gives you more for free; `__post_init__` gives you control. Pick based on your project's needs."

---

## Part 4 — Whitelist vs Blacklist (60 sec)

**The principle:**

> "Define what is **valid**. Reject everything else. Never define what is **invalid** — you'll always miss something."

```python
ALLOWED_ROLES = {"viewer", "editor", "admin"}

# ❌ Blacklist — you will miss something
def set_role(role: str):
    if role == "superadmin":          # what about "ADMIN", "Admin", " admin"?
        raise ValueError("not allowed")
    db.set_role(role)

# ✅ Whitelist — explicit, exhaustive, closed
def set_role(role: str):
    if role not in ALLOWED_ROLES:
        raise ValueError(f"role must be one of {ALLOWED_ROLES}, got: {role!r}")
    db.set_role(role)
```

**For structured data, use an Enum:**

```python
from enum import Enum

class UserRole(str, Enum):
    VIEWER = "viewer"
    EDITOR = "editor"
    ADMIN  = "admin"

# pydantic will validate and coerce automatically
class UserInput(BaseModel):
    role: UserRole   # "superadmin" → ValidationError. Period.
```

**Say:** "The `str, Enum` pattern means you can use `UserRole.ADMIN` in your code but still accept `"admin"` from JSON. Best of both worlds."

---

## Part 5 — Falsehoods (30 sec)

> *"The last thing to leave you with: your intuition about 'valid' data is wrong in ways you don't expect."*

**Name these quickly — don't explain, just list:**

- Names can contain spaces, hyphens, apostrophes, unicode, and be a single character (`"O"` is a valid surname)
- Phone numbers: country codes, leading zeros, extensions, spaces, dots
- Dates: timezones, DST, leap seconds, non-Gregorian calendars
- Addresses: no fixed number of lines, no required postal code, no required city
- Ages: can be 0, can be 130+, can be unknown
- "Empty" strings: `""`, `" "`, `"\t"`, `"\n"` — all different

**Punchline:** "If you're hand-rolling validation for any of these, you're probably wrong. Use a library, use an RFC, or at minimum read the Falsehoods post before shipping."

*(Reference: kalzumeus.com/2010/06/17/falsehoods-programmers-believe-about-names/)*

---

## Exercise (solo or pair, 5 min)

### Setup

```python
# Install: pip install pydantic[email]
from pydantic import BaseModel, Field, field_validator, EmailStr
```

### Task

The following raw input comes from an HTTP API. Write a `pydantic` model called `ProductInput` that validates it at the boundary.

```python
# Sample raw payload (from request.json())
raw = {
    "name":        "Widget Pro",
    "price":       "29.99",          # comes in as a string
    "stock":       -3,               # should never be negative
    "category":    "ELECTRONICS",    # should be lowercased and from a fixed set
    "description": "  ",             # whitespace-only — should be treated as absent
}
```

**Requirements:**

1. `name`: required, 1–200 characters, strip whitespace
2. `price`: a positive float (note: it arrives as a string — pydantic should coerce it)
3. `stock`: non-negative integer
4. `category`: must be one of `electronics`, `clothing`, `food`, `other` — case-insensitive input, stored lowercase
5. `description`: optional, strip whitespace, store as `None` if blank

### Starter

```python
from pydantic import BaseModel, Field, field_validator
from typing import Optional

class ProductInput(BaseModel):
    name:        str
    price:       float
    stock:       int
    category:    str
    description: Optional[str] = None

    # Your validators here
```

### Expected behaviour

```python
# All of these should work:
ProductInput(**raw)
# ProductInput(name='Widget Pro', price=29.99, stock=???, ...)
# ^ stock=-3 should raise ValidationError

ProductInput(name="T-shirt", price=9.99, stock=100, category="CLOTHING")
# category stored as "clothing"

ProductInput(name="Bread", price=2.0, stock=50, category="food", description="  ")
# description stored as None
```

### Solution (reveal after exercise)

```python
from pydantic import BaseModel, Field, field_validator
from typing import Optional

VALID_CATEGORIES = {"electronics", "clothing", "food", "other"}

class ProductInput(BaseModel):
    name:        str            = Field(..., min_length=1, max_length=200)
    price:       float          = Field(..., gt=0)
    stock:       int            = Field(..., ge=0)
    category:    str
    description: Optional[str] = None

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("name cannot be blank")
        return stripped

    @field_validator("category")
    @classmethod
    def normalise_category(cls, v: str) -> str:
        lower = v.strip().lower()
        if lower not in VALID_CATEGORIES:
            raise ValueError(f"category must be one of {VALID_CATEGORIES}, got {v!r}")
        return lower

    @field_validator("description")
    @classmethod
    def blank_to_none(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        stripped = v.strip()
        return stripped if stripped else None
```

**Discussion points after the exercise:**

- Where does this model live in a real project? (`schemas/`, `models/`, `api/inputs/`)
- Who is responsible for calling it? (The controller/handler — not the service layer)
- What do you do with the `ValidationError`? (Catch it at the HTTP layer, return 422 with the error body)

---

## Mixing Pydantic and Result — an elegant combination

The solution code does something deliberate: it uses two libraries together, each for what it
does best.

**Pydantic** excels at the mechanical work of boundary parsing — coercion, field constraints,
nested models. But its error surface is exceptions, which leak implementation details to callers.

**`returns.Result`** gives you an explicit, composable error type. But it has no built-in
vocabulary for field-level validation rules.

The combination captures the strengths of both:

```python
# _ProductSchema is private — callers cannot reach it
# Pydantic's exception-based world is fully contained inside one function
def parse_product_input(...) -> Result[ProductInput, str]:
    try:
        validated = _ProductSchema(...)    # Pydantic does the hard work here
        return Success(ProductInput(...))  # clean domain object escapes
    except ValidationError as e:
        return Failure(...)                # exception converted, never leaks out
```

The result: **declarative validation rules** (Pydantic) AND **an honest return type** (Result).
Neither library achieves this alone.

### The trade-off to be aware of

We only surface the **first** validation failure. If you need all errors at once — useful for
form validation where you want to show the user every problem in one response — you would need
to map `e.errors()` into a richer error type than `str`. That is a deliberate choice here, not
an oversight. For API boundaries returning 422, returning all errors is often the right call.

---

## Key Takeaways (say these out loud at the end)

1. **Validate at the boundary.** Once. Not inside business logic.
2. **Pydantic turns validation into a data structure**, not scattered if-statements.
3. **Whitelist what's valid** — never blacklist what's invalid.
4. **Your intuition about valid data is wrong.** Use libraries, not hand-rolled regexes.
5. After the boundary, your code should never have to ask "but what if this is None?"
6. **Pydantic and Result compose elegantly** — use Pydantic for rules, Result for the contract.

---

## Common Questions

**Q: Should I validate inside service methods too?**
> Use `assert` for internal invariants your own code controls. Reserve `pydantic`/`raise` for data coming from outside. The goal is: by the time you reach service logic, you're working with a `UserInput` object you fully trust.

**Q: Isn't pydantic slow? We have a high-throughput service.**
> Pydantic v2 is written in Rust — it's fast. For ultra-high-throughput validation, benchmark first before optimizing. In most cases it's not your bottleneck.

**Q: We use Django / FastAPI / Flask — do we still need this?**
> FastAPI uses pydantic natively — your request models ARE the boundary validators. Django REST Framework has serializers that serve the same role. The principle is the same; the tool differs.

**Q: What about validating data coming from our own database?**
> If you control the schema and the write path is validated: trust it. If you're reading from a legacy system, a shared DB, or any external store: validate it. Assume the DB can contain anything.

**Q: Why only return the first error? What if I need all of them?**
> Map `e.errors()` into a list instead of taking `[0]`. Change the return type to
> `Result[ProductInput, list[str]]`. The pattern stays the same — only the error payload widens.

---

## References

- Pydantic v2 docs — https://docs.pydantic.dev/latest/
- Falsehoods Programmers Believe About Names — kalzumeus.com
- Falsehoods About Phone Numbers — github.com/googlei18n/libphonenumber
- Python `dataclasses` docs — `__post_init__` validation pattern
- *A Philosophy of Software Design* — Ousterhout, Chapter 10

---

*Module 01 of 6 · Defensive Programming from the Trenches*
