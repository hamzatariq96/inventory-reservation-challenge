"""Overselling check under real concurrency.

Runs only against PostgreSQL, where row locks actually apply. The assertion is
deterministic even though thread scheduling is not: whatever the interleaving,
exactly `stock` reservations may succeed.
"""

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import pytest
from fastapi import FastAPI
from sqlalchemy.orm import sessionmaker

from app import services
from app.clock import FixedClock

pytestmark = pytest.mark.skipif(
    not os.environ.get("TEST_DATABASE_URL", "").startswith("postgresql"),
    reason="needs PostgreSQL row locking",
)


def test_parallel_reservations_never_oversell(app: FastAPI, clock: FixedClock) -> None:
    make_session = sessionmaker(bind=app.state.engine, expire_on_commit=False)
    stock, attempts = 5, 20

    with make_session() as db:
        product_id = services.create_product(db, "RACE-1", "Contended item", stock).id

    def attempt(i: int) -> bool:
        with make_session() as db:
            try:
                services.reserve(db, clock, product_id, 1, f"race-key-{i:04d}", timedelta(minutes=10))
                return True
            except services.Conflict:
                return False

    with ThreadPoolExecutor(max_workers=10) as pool:
        results = list(pool.map(attempt, range(attempts)))

    assert results.count(True) == stock
    with make_session() as db:
        product = db.get(services.Product, product_id)
        assert services.available_stock(db, product, clock.now()) == 0
