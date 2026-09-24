"""Orders API: the system under test.

A small FastAPI service with API-key auth and SQLite storage, so the test
framework has a real HTTP API to run against, both locally and in CI.
Run it on its own with:

    uvicorn sut.orders_api:app --port 8000
"""

from __future__ import annotations

import os
import sqlite3
from contextlib import asynccontextmanager
from enum import Enum
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Request, Security
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException as StarletteHTTPException

API_KEY = os.getenv("ORDERS_API_KEY", "local-dev-key")
DB_PATH = os.getenv("ORDERS_DB", "orders.db")


# ---------------- Database ----------------
def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                name    TEXT NOT NULL,
                role    TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS products (
                product_id INTEGER PRIMARY KEY,
                name       TEXT NOT NULL,
                price      REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS orders (
                order_id       INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id        INTEGER NOT NULL REFERENCES users(user_id),
                product_id     INTEGER NOT NULL REFERENCES products(product_id),
                quantity       INTEGER NOT NULL,
                payment_method TEXT NOT NULL,
                address        TEXT NOT NULL,
                pincode        TEXT NOT NULL,
                total          REAL NOT NULL
            );
            INSERT OR IGNORE INTO users VALUES (1, 'Karthick', 'QA Engineer');
            INSERT OR IGNORE INTO users VALUES (2, 'Priya', 'Developer');
            INSERT OR IGNORE INTO products VALUES (1, 'Laptop', 1200.50);
            INSERT OR IGNORE INTO products VALUES (2, 'Mouse', 25.75);
            """
        )


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="Orders API", version="2.0.0", lifespan=lifespan)


# ---------------- Auth ----------------
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(key: Optional[str] = Security(api_key_header)) -> str:
    if key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid or missing API key")
    return key


# ---------------- Models ----------------
class PaymentMethod(str, Enum):
    card = "card"
    upi = "upi"
    cod = "cod"


class Delivery(BaseModel):
    address: str = Field(min_length=5, max_length=200)
    pincode: str = Field(pattern=r"^[1-9][0-9]{5}$")


class OrderIn(BaseModel):
    user_id: int
    product_id: int
    quantity: int = Field(ge=1, le=100)
    payment_method: PaymentMethod
    delivery: Delivery


def ok(code: int, message: str, data) -> JSONResponse:
    return JSONResponse(
        status_code=code,
        content={"status": "success", "code": code, "message": message, "data": data},
    )


def order_row(row: sqlite3.Row) -> dict:
    return {
        "order_id": row["order_id"],
        "user_id": row["user_id"],
        "product_id": row["product_id"],
        "quantity": row["quantity"],
        "payment_method": row["payment_method"],
        "delivery": {"address": row["address"], "pincode": row["pincode"]},
        "total": round(row["total"], 2),
    }


# ---------------- Endpoints ----------------
@app.get("/health")
def health():
    return ok(200, "healthy", {"service": "orders-api", "version": app.version})


@app.get("/api/products", dependencies=[Depends(require_api_key)])
def list_products():
    with connect() as conn:
        rows = conn.execute("SELECT product_id, name, price FROM products").fetchall()
    return ok(200, "Products fetched", [dict(r) for r in rows])


@app.get("/api/users/{user_id}", dependencies=[Depends(require_api_key)])
def get_user(user_id: int):
    with connect() as conn:
        row = conn.execute("SELECT user_id, name, role FROM users WHERE user_id = ?", (user_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="User not found")
    return ok(200, "User fetched", dict(row))


@app.get("/api/orders", dependencies=[Depends(require_api_key)])
def list_orders():
    with connect() as conn:
        rows = conn.execute("SELECT * FROM orders ORDER BY order_id").fetchall()
    return ok(200, "Orders fetched", [order_row(r) for r in rows])


@app.get("/api/orders/{order_id}", dependencies=[Depends(require_api_key)])
def get_order(order_id: int):
    with connect() as conn:
        row = conn.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return ok(200, "Order fetched", order_row(row))


@app.post("/api/orders", dependencies=[Depends(require_api_key)])
def create_order(order: OrderIn):
    with connect() as conn:
        if conn.execute("SELECT 1 FROM users WHERE user_id = ?", (order.user_id,)).fetchone() is None:
            raise HTTPException(status_code=400, detail="Invalid user_id")
        product = conn.execute("SELECT price FROM products WHERE product_id = ?", (order.product_id,)).fetchone()
        if product is None:
            raise HTTPException(status_code=400, detail="Invalid product_id")

        cur = conn.execute(
            "INSERT INTO orders (user_id, product_id, quantity, payment_method, address, pincode, total)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                order.user_id,
                order.product_id,
                order.quantity,
                order.payment_method.value,
                order.delivery.address,
                order.delivery.pincode,
                product["price"] * order.quantity,
            ),
        )
        row = conn.execute("SELECT * FROM orders WHERE order_id = ?", (cur.lastrowid,)).fetchone()
    return ok(201, "Order created", order_row(row))


@app.delete("/api/orders/{order_id}", dependencies=[Depends(require_api_key)])
def delete_order(order_id: int):
    with connect() as conn:
        cur = conn.execute("DELETE FROM orders WHERE order_id = ?", (order_id,))
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="Order not found")
    return ok(200, "Order deleted", {"order_id": order_id})


# ---------------- Error envelope ----------------
def error(code: int, message: str, details=None) -> JSONResponse:
    body = {"status": "error", "code": code, "message": message}
    if details is not None:
        body["details"] = details
    return JSONResponse(status_code=code, content=body)


# Registered on Starlette's base class so routing errors (unknown path, wrong method)
# get the same envelope as errors raised by the endpoints.
@app.exception_handler(StarletteHTTPException)
async def http_error(_: Request, exc: StarletteHTTPException):
    return error(exc.status_code, str(exc.detail))


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError):
    details = [{"field": ".".join(str(p) for p in e["loc"] if p != "body"), "error": e["msg"]} for e in exc.errors()]
    return error(422, "Validation failed", details)


@app.exception_handler(Exception)
async def unexpected_error(_: Request, __: Exception):
    return error(500, "Internal Server Error")
