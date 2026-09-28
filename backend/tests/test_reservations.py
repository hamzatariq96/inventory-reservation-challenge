from fastapi.testclient import TestClient

from app.clock import FixedClock

from .conftest import START, TTL, available, reserve


class TestReserve:
    def test_reservation_holds_stock(self, client: TestClient, product: dict) -> None:
        response = reserve(client, product["id"], 3, "order-0001")

        assert response.status_code == 201
        body = response.json()
        assert body["status"] == "active"
        assert body["created_at"] == START.isoformat()
        assert body["expires_at"] == (START + TTL).isoformat()
        assert available(client, product["id"]) == 7

    def test_cannot_reserve_more_than_available(self, client: TestClient, product: dict) -> None:
        assert reserve(client, product["id"], 8, "order-0001").status_code == 201

        response = reserve(client, product["id"], 3, "order-0002")

        assert response.status_code == 409
        assert response.json()["detail"] == "only 2 unit(s) available"
        assert available(client, product["id"]) == 2

    def test_can_reserve_exactly_the_remaining_stock(self, client: TestClient, product: dict) -> None:
        assert reserve(client, product["id"], 10, "order-0001").status_code == 201
        assert available(client, product["id"]) == 0

    def test_unknown_product_returns_404(self, client: TestClient) -> None:
        assert reserve(client, 999, 1, "order-0001").status_code == 404

    def test_quantity_must_be_positive(self, client: TestClient, product: dict) -> None:
        assert reserve(client, product["id"], 0, "order-0001").status_code == 422


class TestIdempotency:
    def test_replay_returns_same_reservation_without_holding_more_stock(
        self, client: TestClient, product: dict
    ) -> None:
        first = reserve(client, product["id"], 4, "order-0001")
        replay = reserve(client, product["id"], 4, "order-0001")

        assert first.status_code == 201
        assert replay.status_code == 200
        assert replay.json()["id"] == first.json()["id"]
        assert available(client, product["id"]) == 6

    def test_same_key_with_different_payload_is_rejected(self, client: TestClient, product: dict) -> None:
        reserve(client, product["id"], 4, "order-0001")

        response = reserve(client, product["id"], 5, "order-0001")

        assert response.status_code == 409
        assert available(client, product["id"]) == 6


class TestExpiry:
    def test_reservation_is_active_one_second_before_expiry(
        self, client: TestClient, clock: FixedClock, product: dict
    ) -> None:
        reservation = reserve(client, product["id"], 5, "order-0001").json()

        clock.advance(seconds=TTL.total_seconds() - 1)

        assert client.get(f"/reservations/{reservation['id']}").json()["status"] == "active"
        assert available(client, product["id"]) == 5

    def test_reservation_expires_exactly_at_ttl_and_returns_stock(
        self, client: TestClient, clock: FixedClock, product: dict
    ) -> None:
        reservation = reserve(client, product["id"], 5, "order-0001").json()

        clock.advance(seconds=TTL.total_seconds())

        assert client.get(f"/reservations/{reservation['id']}").json()["status"] == "expired"
        assert available(client, product["id"]) == 10

    def test_expired_stock_can_be_reserved_again(
        self, client: TestClient, clock: FixedClock, product: dict
    ) -> None:
        reserve(client, product["id"], 10, "order-0001")
        clock.advance(minutes=10)

        assert reserve(client, product["id"], 10, "order-0002").status_code == 201


class TestConfirm:
    def test_confirmed_reservation_keeps_stock_after_ttl(
        self, client: TestClient, clock: FixedClock, product: dict
    ) -> None:
        reservation = reserve(client, product["id"], 3, "order-0001").json()

        response = client.post(f"/reservations/{reservation['id']}/confirm")
        clock.advance(hours=1)

        assert response.status_code == 200
        assert response.json()["status"] == "confirmed"
        assert available(client, product["id"]) == 7

    def test_confirm_is_idempotent(self, client: TestClient, product: dict) -> None:
        reservation = reserve(client, product["id"], 3, "order-0001").json()
        client.post(f"/reservations/{reservation['id']}/confirm")

        response = client.post(f"/reservations/{reservation['id']}/confirm")

        assert response.status_code == 200
        assert response.json()["status"] == "confirmed"

    def test_cannot_confirm_expired_reservation(
        self, client: TestClient, clock: FixedClock, product: dict
    ) -> None:
        reservation = reserve(client, product["id"], 3, "order-0001").json()
        clock.advance(minutes=10)

        response = client.post(f"/reservations/{reservation['id']}/confirm")

        assert response.status_code == 409
        assert response.json()["detail"] == "reservation has expired"

    def test_cannot_confirm_released_reservation(self, client: TestClient, product: dict) -> None:
        reservation = reserve(client, product["id"], 3, "order-0001").json()
        client.post(f"/reservations/{reservation['id']}/release")

        assert client.post(f"/reservations/{reservation['id']}/confirm").status_code == 409

    def test_unknown_reservation_returns_404(self, client: TestClient) -> None:
        assert client.post("/reservations/999/confirm").status_code == 404


class TestRelease:
    def test_release_returns_stock(self, client: TestClient, product: dict) -> None:
        reservation = reserve(client, product["id"], 6, "order-0001").json()

        response = client.post(f"/reservations/{reservation['id']}/release")

        assert response.json()["status"] == "released"
        assert available(client, product["id"]) == 10

    def test_release_is_idempotent(self, client: TestClient, product: dict) -> None:
        reservation = reserve(client, product["id"], 6, "order-0001").json()
        client.post(f"/reservations/{reservation['id']}/release")

        response = client.post(f"/reservations/{reservation['id']}/release")

        assert response.status_code == 200
        assert available(client, product["id"]) == 10

    def test_cannot_release_confirmed_reservation(self, client: TestClient, product: dict) -> None:
        reservation = reserve(client, product["id"], 6, "order-0001").json()
        client.post(f"/reservations/{reservation['id']}/confirm")

        assert client.post(f"/reservations/{reservation['id']}/release").status_code == 409
        assert available(client, product["id"]) == 4
