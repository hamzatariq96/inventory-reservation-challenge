"""Starter version of backend/app/services.py handed to candidates.

Copy this file over backend/app/services.py to turn the repo into the challenge:

    cp starter/app/services.py backend/app/services.py

The API layer, models and test suite stay as they are. Implement every
function marked TODO until `make test-backend` passes. See CHALLENGE.md.
"""

from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from .clock import Clock
from .models import Product, Reservation, ReservationStatus


class ServiceError(Exception):
    pass


class NotFound(ServiceError):
    """Mapped to HTTP 404 by the API layer."""


class Conflict(ServiceError):
    """Mapped to HTTP 409 by the API layer. The message becomes the response detail."""


def effective_status(reservation: Reservation, now: datetime) -> ReservationStatus:
    """Status as the client should see it at `now`.

    TODO: an ACTIVE reservation whose expires_at is at or before `now` is EXPIRED.
    """
    raise NotImplementedError


def available_stock(db: Session, product: Product, now: datetime) -> int:
    """TODO: total_stock minus confirmed quantity minus active, unexpired quantity."""
    raise NotImplementedError


def create_product(db: Session, sku: str, name: str, total_stock: int) -> Product:
    if db.scalar(select(Product).where(Product.sku == sku)):
        raise Conflict(f"product with sku '{sku}' already exists")
    product = Product(sku=sku, name=name, total_stock=total_stock)
    db.add(product)
    db.commit()
    return product


def list_products(db: Session) -> list[Product]:
    return list(db.scalars(select(Product).order_by(Product.id)))


def get_reservation(db: Session, reservation_id: int) -> Reservation:
    reservation = db.get(Reservation, reservation_id)
    if reservation is None:
        raise NotFound(f"reservation {reservation_id} not found")
    return reservation


def reserve(
    db: Session,
    clock: Clock,
    product_id: int,
    quantity: int,
    idempotency_key: str,
    ttl: timedelta,
) -> tuple[Reservation, bool]:
    """Hold `quantity` units for `ttl`. Returns (reservation, created).

    TODO:
      - same idempotency_key + same payload -> return the original, created=False
      - same idempotency_key + different payload -> Conflict
      - unknown product -> NotFound
      - not enough stock -> Conflict("only N unit(s) available")
      - must not oversell when called concurrently on PostgreSQL
    """
    raise NotImplementedError


def confirm(db: Session, clock: Clock, reservation_id: int) -> Reservation:
    """TODO: active -> confirmed. Confirming twice is fine. Expired -> Conflict("reservation has expired")."""
    raise NotImplementedError


def release(db: Session, clock: Clock, reservation_id: int) -> Reservation:
    """TODO: active -> released. Releasing twice is fine. Confirmed -> Conflict."""
    raise NotImplementedError
