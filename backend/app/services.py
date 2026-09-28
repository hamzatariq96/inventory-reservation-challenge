"""Reservation rules. This is the file candidates implement in the challenge.

Availability for a product is:

    total_stock - (confirmed quantity + quantity of active, unexpired reservations)

A reservation is "expired" as soon as now >= expires_at, even before anything
writes that status to the database. Expiry is evaluated lazily, so the service
needs no background worker and the tests need no sleeps.
"""

from datetime import datetime, timedelta

from sqlalchemy import and_, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .clock import Clock
from .models import Product, Reservation, ReservationStatus


class ServiceError(Exception):
    pass


class NotFound(ServiceError):
    pass


class Conflict(ServiceError):
    pass


def effective_status(reservation: Reservation, now: datetime) -> ReservationStatus:
    status = ReservationStatus(reservation.status)
    if status is ReservationStatus.ACTIVE and now >= reservation.expires_at:
        return ReservationStatus.EXPIRED
    return status


def available_stock(db: Session, product: Product, now: datetime) -> int:
    held = db.scalar(
        select(func.coalesce(func.sum(Reservation.quantity), 0)).where(
            Reservation.product_id == product.id,
            or_(
                Reservation.status == ReservationStatus.CONFIRMED.value,
                and_(
                    Reservation.status == ReservationStatus.ACTIVE.value,
                    Reservation.expires_at > now,
                ),
            ),
        )
    )
    return product.total_stock - int(held or 0)


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


def _replay(existing: Reservation, product_id: int, quantity: int) -> Reservation:
    if existing.product_id != product_id or existing.quantity != quantity:
        raise Conflict("idempotency key was already used with a different request")
    return existing


def reserve(
    db: Session,
    clock: Clock,
    product_id: int,
    quantity: int,
    idempotency_key: str,
    ttl: timedelta,
) -> tuple[Reservation, bool]:
    """Returns (reservation, created). created is False for an idempotent replay."""
    existing = db.scalar(select(Reservation).where(Reservation.idempotency_key == idempotency_key))
    if existing is not None:
        return _replay(existing, product_id, quantity), False

    # Lock the product row so two concurrent reservations cannot both pass the
    # availability check (no-op on SQLite, which serialises writes anyway).
    product = db.scalar(select(Product).where(Product.id == product_id).with_for_update())
    if product is None:
        raise NotFound(f"product {product_id} not found")

    now = clock.now()
    available = available_stock(db, product, now)
    if quantity > available:
        raise Conflict(f"only {available} unit(s) available")

    reservation = Reservation(
        product_id=product_id,
        quantity=quantity,
        status=ReservationStatus.ACTIVE.value,
        idempotency_key=idempotency_key,
        created_at=now,
        expires_at=now + ttl,
    )
    db.add(reservation)
    try:
        db.commit()
    except IntegrityError:
        # Another request with the same key won the race.
        db.rollback()
        existing = db.scalar(select(Reservation).where(Reservation.idempotency_key == idempotency_key))
        if existing is None:
            raise
        return _replay(existing, product_id, quantity), False
    return reservation, True


def confirm(db: Session, clock: Clock, reservation_id: int) -> Reservation:
    reservation = get_reservation(db, reservation_id)
    status = effective_status(reservation, clock.now())

    if status is ReservationStatus.CONFIRMED:
        return reservation
    if status is ReservationStatus.EXPIRED:
        reservation.status = ReservationStatus.EXPIRED.value
        db.commit()
        raise Conflict("reservation has expired")
    if status is not ReservationStatus.ACTIVE:
        raise Conflict(f"cannot confirm a {status.value} reservation")

    reservation.status = ReservationStatus.CONFIRMED.value
    db.commit()
    return reservation


def release(db: Session, clock: Clock, reservation_id: int) -> Reservation:
    reservation = get_reservation(db, reservation_id)
    status = effective_status(reservation, clock.now())

    if status is ReservationStatus.CONFIRMED:
        raise Conflict("cannot release a confirmed reservation")
    if status is ReservationStatus.ACTIVE:
        reservation.status = ReservationStatus.RELEASED.value
    elif status is ReservationStatus.EXPIRED:
        reservation.status = ReservationStatus.EXPIRED.value
    db.commit()
    return reservation
