from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Simple API", version="1.0.0")

# --- Modèles ---

class Item(BaseModel):
    name: str
    price: float


# Stockage en mémoire (dict simple)
items: dict[int, Item] = {}
_next_id = 1


# --- Routes ---

@app.get("/")
def root() -> dict:
    return {"message": "API opérationnelle", "version": "1.0.0"}


@app.get("/items")
def list_items() -> dict:
    return {"items": {k: v.model_dump() for k, v in items.items()}}


@app.get("/items/{item_id}")
def get_item(item_id: int) -> dict:
    if item_id not in items:
        raise HTTPException(status_code=404, detail="Item introuvable")
    return items[item_id].model_dump()


@app.post("/items", status_code=201)
def create_item(item: Item) -> dict:
    global _next_id
    items[_next_id] = item
    created = {"id": _next_id, **item.model_dump()}
    _next_id += 1
    return created


@app.delete("/items/{item_id}", status_code=204)
def delete_item(item_id: int) -> None:
    if item_id not in items:
        raise HTTPException(status_code=404, detail="Item introuvable")
    del items[item_id]
