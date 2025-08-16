from fastapi import FastAPI, HTTPException, Depends, Security, Request
from fastapi.security import APIKeyHeader
from fastapi.responses import JSONResponse
import sqlite3
from pydantic import BaseModel
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

TEST_MOKE_API_KEY = os.getenv("TEST_MOKE_API_KEY")

app = FastAPI(title="Order API with Auth & SQLite")

# ---------------- API Key Auth ----------------
API_KEY = TEST_MOKE_API_KEY
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def get_api_key(api_key_header: str = Security(api_key_header)):
    if api_key_header == API_KEY:
        return api_key_header
    raise HTTPException(status_code=403, detail="Invalid or missing API Key")

# ---------------- DB Helper ----------------
DB_NAME = "orders.db"

def init_db():
    """Initialize the database with users, products, and orders"""
    with sqlite3.connect(DB_NAME, check_same_thread=False, timeout=10) as conn:
        cursor = conn.cursor()
        
        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                role TEXT NOT NULL
            )
        """)
        
        # Products table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                product_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                price REAL NOT NULL
            )
        """)
        
        # Orders table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                order_id INTEGER PRIMARY KEY,
                user_id INTEGER,
                product_id INTEGER,
                quantity INTEGER,
                address TEXT,
                payment_method TEXT,
                FOREIGN KEY(user_id) REFERENCES users(user_id),
                FOREIGN KEY(product_id) REFERENCES products(product_id)
            )
        """)

        # Insert sample users
        cursor.execute("INSERT OR IGNORE INTO users (user_id, name, role) VALUES (1, 'Karthick', 'QA Engineer')")
        cursor.execute("INSERT OR IGNORE INTO users (user_id, name, role) VALUES (2, 'Priya', 'Developer')")

        # Insert sample products
        cursor.execute("INSERT OR IGNORE INTO products (product_id, name, price) VALUES (1, 'Laptop', 1200.50)")
        cursor.execute("INSERT OR IGNORE INTO products (product_id, name, price) VALUES (2, 'Mouse', 25.75)")

        conn.commit()

# Run on startup
init_db()

# ---------------- Pydantic Models ----------------
class Order(BaseModel):
    order_id: int
    user_id: int
    product_id: int
    quantity: int
    address: str
    payment_method: str

# ---------------- GET APIs ----------------
@app.get("/api/fixeddata", dependencies=[Depends(get_api_key)])
def get_fixed_data():
    try:
        with sqlite3.connect(DB_NAME, check_same_thread=False, timeout=10) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT user_id, name, role FROM users LIMIT 1")
            row = cursor.fetchone()
        return {
            "status": "success",
            "code": 200,
            "message": "Fixed data retrieved from users table",
            "data": {"id": row[0], "name": row[1], "role": row[2]} if row else {}
        }
    except sqlite3.OperationalError:
        raise HTTPException(status_code=500, detail="Database is locked")

@app.get("/api/orders", dependencies=[Depends(get_api_key)])
def get_orders():
    try:
        with sqlite3.connect(DB_NAME, check_same_thread=False, timeout=10) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT o.order_id, u.name, p.name, o.quantity, o.address, o.payment_method
                FROM orders o
                JOIN users u ON o.user_id = u.user_id
                JOIN products p ON o.product_id = p.product_id
            """)
            rows = cursor.fetchall()
        return {
            "status": "success",
            "code": 200,
            "message": "Orders fetched successfully",
            "data": [
                {
                    "order_id": r[0],
                    "user": r[1],
                    "product": r[2],
                    "quantity": r[3],
                    "address": r[4],
                    "payment_method": r[5]
                }
                for r in rows
            ]
        }
    except sqlite3.OperationalError:
        raise HTTPException(status_code=500, detail="Database is locked")

# ---------------- POST API ----------------
@app.post("/api/orders", dependencies=[Depends(get_api_key)])
def create_order(order: Order):
    try:
        with sqlite3.connect(DB_NAME, check_same_thread=False, timeout=10) as conn:
            cursor = conn.cursor()

            # Ensure user exists
            cursor.execute("SELECT 1 FROM users WHERE user_id=?", (order.user_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=400, detail="Invalid user_id")

            # Ensure product exists
            cursor.execute("SELECT 1 FROM products WHERE product_id=?", (order.product_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=400, detail="Invalid product_id")

            cursor.execute(
                "INSERT INTO orders (order_id, user_id, product_id, quantity, address, payment_method) VALUES (?, ?, ?, ?, ?, ?)",
                (order.order_id, order.user_id, order.product_id, order.quantity, order.address, order.payment_method)
            )
            conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Order ID already exists")
    except sqlite3.OperationalError:
        raise HTTPException(status_code=500, detail="Database is locked")

    return {
        "status": "success",
        "code": 201,
        "message": "Order created successfully",
        "data": order.dict()
    }

# ---------------- Global Error Handlers ----------------
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "code": exc.status_code,
            "message": str(exc.detail)
        }
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "code": 500,
            "message": "Internal Server Error"
        }
    )

