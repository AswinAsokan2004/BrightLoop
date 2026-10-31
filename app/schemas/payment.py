from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.enums import PaymentMethod, PaymentStatus
from app.schemas.common import ORMModel, PositiveMoney


class PaymentCreate(BaseModel):
    method: PaymentMethod
    amount: PositiveMoney
    payment_date: date = Field(default_factory=date.today)
    reference: str | None = Field(None, max_length=120, description="Bank ref / cheque no.")
    note: str | None = None


class PaymentRead(ORMModel):
    id: int
    invoice_id: int
    customer_id: int
    method: PaymentMethod
    amount: Decimal
    payment_date: date
    reference: str | None
    note: str | None
    status: PaymentStatus
    recorded_by: int | None
    created_at: datetime
