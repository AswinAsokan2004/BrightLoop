from fastapi import APIRouter, status

from app.models.enums import ProductType
from app.routes.deps import AdminUser, DbSession, Paging, StaffUser
from app.schemas.catalog import (
    AttributeCreate,
    AttributeRead,
    AttributeValueCreate,
    AttributeValueRead,
    AttributeValueUpdate,
    ProductCreate,
    ProductRead,
    ProductUpdate,
    TaxCreate,
    TaxRead,
    TaxUpdate,
    VariantCreate,
    VariantRead,
    VariantUpdate,
)
from app.schemas.common import Page, to_page
from app.services.catalog import CatalogService

router = APIRouter(tags=["Catalog"])

# --- Products ------------------------------------------------------------------


@router.get("/products", response_model=Page[ProductRead])
def list_products(
    _: StaffUser,
    db: DbSession,
    paging: Paging,
    q: str | None = None,
    product_type: ProductType | None = None,
    active: bool | None = None,
):
    items, total = CatalogService(db).list_products(q, product_type, active, paging)
    return to_page(ProductRead, items, total, paging)


@router.post("/products", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
def create_product(data: ProductCreate, admin: AdminUser, db: DbSession):
    return CatalogService(db).create_product(data, admin)


@router.get("/products/{product_id}", response_model=ProductRead)
def get_product(product_id: int, _: StaffUser, db: DbSession):
    return CatalogService(db).get_product(product_id)


@router.patch("/products/{product_id}", response_model=ProductRead)
def update_product(product_id: int, data: ProductUpdate, _: AdminUser, db: DbSession):
    return CatalogService(db).update_product(product_id, data)


@router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(product_id: int, _: AdminUser, db: DbSession) -> None:
    CatalogService(db).delete_product(product_id)


# --- Variants ------------------------------------------------------------------


@router.post("/products/{product_id}/variants", response_model=VariantRead, status_code=status.HTTP_201_CREATED)
def create_variant(product_id: int, data: VariantCreate, _: AdminUser, db: DbSession):
    """Price = product sales price + the extra price of each chosen attribute value."""
    return CatalogService(db).create_variant(product_id, data)


@router.patch("/variants/{variant_id}", response_model=VariantRead)
def update_variant(variant_id: int, data: VariantUpdate, _: AdminUser, db: DbSession):
    return CatalogService(db).update_variant(variant_id, data)


# --- Attributes ----------------------------------------------------------------


@router.get("/attributes", response_model=list[AttributeRead])
def list_attributes(_: StaffUser, db: DbSession):
    return CatalogService(db).list_attributes()


@router.post("/attributes", response_model=AttributeRead, status_code=status.HTTP_201_CREATED)
def create_attribute(data: AttributeCreate, _: AdminUser, db: DbSession):
    return CatalogService(db).create_attribute(data)


@router.post(
    "/attributes/{attribute_id}/values", response_model=AttributeValueRead, status_code=status.HTTP_201_CREATED
)
def add_attribute_value(attribute_id: int, data: AttributeValueCreate, _: AdminUser, db: DbSession):
    return CatalogService(db).add_attribute_value(attribute_id, data)


@router.patch("/attribute-values/{value_id}", response_model=AttributeValueRead)
def update_attribute_value(value_id: int, data: AttributeValueUpdate, _: AdminUser, db: DbSession):
    return CatalogService(db).update_attribute_value(value_id, data)


# --- Taxes ---------------------------------------------------------------------


@router.get("/taxes", response_model=list[TaxRead])
def list_taxes(_: StaffUser, db: DbSession, active: bool | None = None):
    return CatalogService(db).list_taxes(active)


@router.post("/taxes", response_model=TaxRead, status_code=status.HTTP_201_CREATED)
def create_tax(data: TaxCreate, _: AdminUser, db: DbSession):
    return CatalogService(db).create_tax(data)


@router.patch("/taxes/{tax_id}", response_model=TaxRead)
def update_tax(tax_id: int, data: TaxUpdate, _: AdminUser, db: DbSession):
    return CatalogService(db).update_tax(tax_id, data)
