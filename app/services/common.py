from pydantic import BaseModel


def apply_updates(obj: object, data: BaseModel, exclude: set[str] | None = None) -> None:
    """Copy only the fields the client actually sent (PATCH semantics)."""
    for field, value in data.model_dump(exclude_unset=True, exclude=exclude).items():
        setattr(obj, field, value)
