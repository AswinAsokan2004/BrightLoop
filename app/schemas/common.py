from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Annotated, Any, Generic, TypeVar

from fastapi import Query
from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, Field

Money = Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=2)]
PositiveMoney = Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=2)]
Email = Annotated[EmailStr, AfterValidator(str.lower)]


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Message(BaseModel):
    message: str


T = TypeVar("T", bound=BaseModel)


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    size: int


@dataclass
class PageParams:
    page: int = Query(1, ge=1)
    size: int = Query(20, ge=1, le=100)


def to_page(schema: type[T], items: Sequence[Any], total: int, params: PageParams) -> Page[T]:
    return Page[schema](
        items=[schema.model_validate(item) for item in items],
        total=total,
        page=params.page,
        size=params.size,
    )
