from datetime import datetime
from decimal import Decimal
from enum import Enum as PyEnum

from sqlalchemy import DateTime, Enum, Identity, Numeric, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    type_annotation_map = {
        Decimal: Numeric(12, 2),  # money; never float
        datetime: DateTime(timezone=True),
    }


def pg_enum(enum_cls: type[PyEnum], name: str) -> Enum:
    """Map to an existing Postgres enum type (the migrations create the types)."""
    return Enum(enum_cls, name=name, values_callable=lambda members: [m.value for m in members])


class IdMixin:
    id: Mapped[int] = mapped_column(Identity(), primary_key=True)


class CreatedAtMixin:
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class TimestampMixin(CreatedAtMixin):
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
