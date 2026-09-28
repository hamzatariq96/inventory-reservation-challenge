from fastapi.testclient import TestClient


def test_health(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}


def test_new_product_is_fully_available(client: TestClient, product: dict) -> None:
    assert product["total_stock"] == 10
    assert product["available"] == 10


def test_products_are_listed_in_creation_order(client: TestClient) -> None:
    for sku in ["A-1", "B-2", "C-3"]:
        client.post("/products", json={"sku": sku, "name": sku, "total_stock": 1})
    assert [p["sku"] for p in client.get("/products").json()] == ["A-1", "B-2", "C-3"]


def test_duplicate_sku_is_rejected(client: TestClient, product: dict) -> None:
    response = client.post("/products", json={"sku": "KB-001", "name": "Other", "total_stock": 1})
    assert response.status_code == 409


def test_negative_stock_is_rejected(client: TestClient) -> None:
    response = client.post("/products", json={"sku": "X-1", "name": "X", "total_stock": -1})
    assert response.status_code == 422
