from collections.abc import Sequence
from typing import Generic, TypeVar

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session
from sqlalchemy.orm.interfaces import LoaderOption

from app.models.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """Data access only: queries and persistence. Business rules and commits live in services."""

    model: type[ModelT]

    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, id_: int) -> ModelT | None:
        return self.db.get(self.model, id_)

    def get_many(self, ids: Sequence[int]) -> list[ModelT]:
        if not ids:
            return []
        return list(self.db.scalars(select(self.model).where(self.model.id.in_(ids))))

    def add(self, obj: ModelT) -> ModelT:
        self.db.add(obj)
        self.db.flush()
        return obj

    def delete(self, obj: ModelT) -> None:
        self.db.delete(obj)
        self.db.flush()

    def paginate(
        self,
        stmt: Select,
        page: int,
        size: int,
        options: Sequence[LoaderOption] = (),
    ) -> tuple[list[ModelT], int]:
        total = self.db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
        items = self.db.scalars(stmt.options(*options).limit(size).offset((page - 1) * size)).all()
        return list(items), total
