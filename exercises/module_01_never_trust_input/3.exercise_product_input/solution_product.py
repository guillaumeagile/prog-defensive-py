from dataclasses import dataclass

from pydantic import BaseModel, Field, ValidationError, field_validator
from returns.result import Failure, Result, Success

VALID_CATEGORIES = {"electronics", "clothing", "food", "other"}


@dataclass(frozen=True)
class ProductInput:
    name: str
    price: float
    stock: int
    category: str
    description: str | None = None


class _ProductSchema(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    price: float = Field(..., gt=0)
    stock: int = Field(..., ge=0)
    category: str
    description: str | None = None

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("name cannot be blank")
        return stripped

    @field_validator("price", mode="before")
    @classmethod
    def coerce_price(cls, v: object) -> float:
        try:
            return float(v)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            raise ValueError(f"price must be a number, got {v!r}")

    @field_validator("category")
    @classmethod
    def normalise_category(cls, v: str) -> str:
        lower = v.strip().lower()
        if lower not in VALID_CATEGORIES:
            raise ValueError(f"category must be one of {VALID_CATEGORIES}, got {v!r}")
        return lower

    @field_validator("description")
    @classmethod
    def blank_to_none(cls, v: str | None) -> str | None:
        if v is None:
            return None
        stripped = v.strip()
        return stripped if stripped else None


def parse_product_input(
    name: str,
    price: float,
    stock: int,
    category: str,
    description: str | None = None,
) -> Result[ProductInput, str]:
    try:
        validated = _ProductSchema(
            name=name, price=price, stock=stock,
            category=category, description=description,
        )
        return Success(ProductInput(
            name=validated.name,
            price=validated.price,
            stock=validated.stock,
            category=validated.category,
            description=validated.description,
        ))
    except ValidationError as e:
        first = e.errors()[0]
        field = str(first["loc"][0])
        msg = str(first["msg"])
        return Failure(f"{field}: {msg}")
