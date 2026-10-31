from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import Email, ORMModel


class CustomerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    company_name: str | None = Field(None, max_length=150)
    email: Email
    phone: str | None = Field(None, max_length=30)
    address_line1: str | None = Field(None, max_length=255)
    address_line2: str | None = Field(None, max_length=255)
    city: str | None = Field(None, max_length=100)
    state: str | None = Field(None, max_length=100)
    postal_code: str | None = Field(None, max_length=20)
    country: str | None = Field(None, min_length=2, max_length=2, description="ISO code, e.g. IN")
    tax_id: str | None = Field(None, max_length=50, description="GSTIN / VAT number")


class CustomerUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=150)
    company_name: str | None = Field(None, max_length=150)
    email: Email | None = None
    phone: str | None = Field(None, max_length=30)
    address_line1: str | None = Field(None, max_length=255)
    address_line2: str | None = Field(None, max_length=255)
    city: str | None = Field(None, max_length=100)
    state: str | None = Field(None, max_length=100)
    postal_code: str | None = Field(None, max_length=20)
    country: str | None = Field(None, min_length=2, max_length=2)
    tax_id: str | None = Field(None, max_length=50)


class CustomerRead(ORMModel):
    id: int
    name: str
    company_name: str | None
    email: str
    phone: str | None
    address_line1: str | None
    address_line2: str | None
    city: str | None
    state: str | None
    postal_code: str | None
    country: str | None
    tax_id: str | None
    created_at: datetime
    updated_at: datetime


class PaymentTermCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    due_days: int = Field(0, ge=0)


class PaymentTermRead(ORMModel):
    id: int
    name: str
    due_days: int
