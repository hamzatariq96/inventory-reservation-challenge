import os
from collections.abc import Iterator
from datetime import timedelta

from fastapi import Depends, FastAPI, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session, sessionmaker

from . import services
from .clock import Clock, SystemClock
from .db import Base, make_engine
from .models import Product, Reservation
from .schemas import ProductCreate, ProductOut, ReservationCreate, ReservationOut


def create_app(
    database_url: str | None = None,
    clock: Clock | None = None,
    reservation_ttl: timedelta | None = None,
) -> FastAPI:
    url = database_url or os.environ.get("DATABASE_URL", "sqlite:///./local.db")
    ttl = reservation_ttl or timedelta(seconds=int(os.environ.get("RESERVATION_TTL_SECONDS", "600")))

    engine = make_engine(url)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    app = FastAPI(title="Inventory Reservation Service", version="1.0.0")
    app.state.engine = engine
    app.state.clock = clock or SystemClock()

    def get_db() -> Iterator[Session]:
        with session_factory() as session:
            yield session

    def get_clock() -> Clock:
        return app.state.clock

    @app.exception_handler(services.NotFound)
    async def not_found(_: Request, exc: services.NotFound) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(services.Conflict)
    async def conflict(_: Request, exc: services.Conflict) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    def product_out(db: Session, product: Product, clock: Clock) -> ProductOut:
        return ProductOut(
            id=product.id,
            sku=product.sku,
            name=product.name,
            total_stock=product.total_stock,
            available=services.available_stock(db, product, clock.now()),
        )

    def reservation_out(reservation: Reservation, clock: Clock) -> ReservationOut:
        return ReservationOut(
            id=reservation.id,
            product_id=reservation.product_id,
            quantity=reservation.quantity,
            status=services.effective_status(reservation, clock.now()),
            created_at=reservation.created_at,
            expires_at=reservation.expires_at,
        )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/products", status_code=status.HTTP_201_CREATED, response_model=ProductOut)
    def create_product(
        body: ProductCreate, db: Session = Depends(get_db), clock: Clock = Depends(get_clock)
    ) -> ProductOut:
        product = services.create_product(db, body.sku, body.name, body.total_stock)
        return product_out(db, product, clock)

    @app.get("/products", response_model=list[ProductOut])
    def list_products(db: Session = Depends(get_db), clock: Clock = Depends(get_clock)) -> list[ProductOut]:
        return [product_out(db, p, clock) for p in services.list_products(db)]

    @app.post("/reservations", status_code=status.HTTP_201_CREATED, response_model=ReservationOut)
    def create_reservation(
        body: ReservationCreate,
        response: Response,
        db: Session = Depends(get_db),
        clock: Clock = Depends(get_clock),
    ) -> ReservationOut:
        reservation, created = services.reserve(
            db, clock, body.product_id, body.quantity, body.idempotency_key, ttl
        )
        if not created:
            response.status_code = status.HTTP_200_OK
        return reservation_out(reservation, clock)

    @app.get("/reservations/{reservation_id}", response_model=ReservationOut)
    def get_reservation(
        reservation_id: int, db: Session = Depends(get_db), clock: Clock = Depends(get_clock)
    ) -> ReservationOut:
        return reservation_out(services.get_reservation(db, reservation_id), clock)

    @app.post("/reservations/{reservation_id}/confirm", response_model=ReservationOut)
    def confirm_reservation(
        reservation_id: int, db: Session = Depends(get_db), clock: Clock = Depends(get_clock)
    ) -> ReservationOut:
        return reservation_out(services.confirm(db, clock, reservation_id), clock)

    @app.post("/reservations/{reservation_id}/release", response_model=ReservationOut)
    def release_reservation(
        reservation_id: int, db: Session = Depends(get_db), clock: Clock = Depends(get_clock)
    ) -> ReservationOut:
        return reservation_out(services.release(db, clock, reservation_id), clock)

    return app
