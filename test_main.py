import pytest
from fastapi.testclient import TestClient

from main import _next_id, app, items  # noqa: F401


@pytest.fixture(autouse=True)
def clear_items():
    """Remet le store à zéro avant chaque test."""
    import main
    main.items.clear()
    main._next_id = 1
    yield
    main.items.clear()
    main._next_id = 1


client = TestClient(app)


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["message"] == "API opérationnelle"


def test_list_items_empty():
    response = client.get("/items")
    assert response.status_code == 200
    assert response.json() == {"items": {}}


def test_create_item():
    payload = {"name": "Baguette", "price": 1.20}
    response = client.post("/items", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["id"] == 1
    assert data["name"] == "Baguette"
    assert data["price"] == 1.20


def test_get_item():
    client.post("/items", json={"name": "Croissant", "price": 0.90})
    response = client.get("/items/1")
    assert response.status_code == 200
    assert response.json()["name"] == "Croissant"


def test_get_item_not_found():
    response = client.get("/items/999")
    assert response.status_code == 404


def test_delete_item():
    client.post("/items", json={"name": "Pain au chocolat", "price": 1.10})
    response = client.delete("/items/1")
    assert response.status_code == 204
    assert client.get("/items/1").status_code == 404


def test_delete_item_not_found():
    response = client.delete("/items/999")
    assert response.status_code == 404


def test_list_items_after_create():
    client.post("/items", json={"name": "Éclair", "price": 2.50})
    client.post("/items", json={"name": "Mille-feuille", "price": 3.00})
    response = client.get("/items")
    assert response.status_code == 200
    assert len(response.json()["items"]) == 2
