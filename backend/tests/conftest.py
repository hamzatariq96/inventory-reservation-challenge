import os
from collections.abc import Iterator
from datetime import datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.clock import FixedClock
from app.db import Base
from app.main import create_app

# Every test starts at the same instant, so expiry assertions are exact.
START = datetime(2026, 1, 1, 12, 0, 0)
TTL = timedelta(minutes=10)


@pytest.fixture
def clock() -> FixedClock:
    return FixedClock(START)


@pytest.fixture
def app(clock: FixedClock) -> Iterator[FastAPI]:
    # Defaults to in-memory SQLite; Docker Compose points this at PostgreSQL.
    url = os.environ.get("TEST_DATABASE_URL", "sqlite://")
    application = create_app(database_url=url, clock=clock, reservation_ttl=TTL)
    yield application
    # Fresh schema per test: no state leaks between tests, whatever the order.
    Base.metadata.drop_all(application.state.engine)
    application.state.engine.dispose()


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def product(client: TestClient) -> dict:
    response = client.post("/products", json={"sku": "KB-001", "name": "Mechanical Keyboard", "total_stock": 10})
    assert response.status_code == 201
    return response.json()


def reserve(client: TestClient, product_id: int, quantity: int, key: str):
    return client.post(
        "/reservations",
        json={"product_id": product_id, "quantity": quantity, "idempotency_key": key},
    )


def available(client: TestClient, product_id: int) -> int:
    products = {p["id"]: p for p in client.get("/products").json()}
    return products[product_id]["available"]
