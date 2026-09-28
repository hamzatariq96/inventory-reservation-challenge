from datetime import datetime

from pydantic import BaseModel, Field

from .models import ReservationStatus


class ProductCreate(BaseModel):
    sku: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=200)
    total_stock: int = Field(ge=0)


class ProductOut(BaseModel):
    id: int
    sku: str
    name: str
    total_stock: int
    available: int


class ReservationCreate(BaseModel):
    product_id: int
    quantity: int = Field(ge=1, le=1000)
    idempotency_key: str = Field(min_length=8, max_length=128)


class ReservationOut(BaseModel):
    id: int
    product_id: int
    quantity: int
    status: ReservationStatus
    created_at: datetime
    expires_at: datetime
