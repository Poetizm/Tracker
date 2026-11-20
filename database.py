# database.py
import sqlite3
from datetime import datetime


class Database:
    def __init__(self, path="inventory.db"):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        cur = self.conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS operations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                op_type TEXT NOT NULL CHECK(op_type IN ('PURCHASE','SALE')),
                quantity REAL NOT NULL,
                price REAL NOT NULL,
                total REAL NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(product_id) REFERENCES products(id)
            )
        """)
        self.conn.commit()

    # ---------- Товары ----------
    def add_product(self, name):
        cur = self.conn.cursor()
        cur.execute("INSERT OR IGNORE INTO products(name) VALUES(?)", (name,))
        self.conn.commit()
        return self.get_product_by_name(name)

    def get_product_by_name(self, name):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM products WHERE name = ?", (name,))
        return cur.fetchone()

    def get_all_products(self):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM products ORDER BY name")
        return cur.fetchall()

    def update_product(self, product_id, new_name):
        cur = self.conn.cursor()
        cur.execute("UPDATE products SET name = ? WHERE id = ?", (new_name, product_id))
        self.conn.commit()

    def delete_product(self, product_id):
        cur = self.conn.cursor()
        cur.execute("DELETE FROM operations WHERE product_id = ?", (product_id,))
        cur.execute("DELETE FROM products WHERE id = ?", (product_id,))
        self.conn.commit()

    # ---------- Операции ----------
    def add_operation(self, product_id, op_type, quantity, price):
        total = quantity * price
        created_at = datetime.now().isoformat(timespec="seconds")
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO operations(product_id, op_type, quantity, price, total, created_at)
            VALUES(?,?,?,?,?,?)
        """, (product_id, op_type, quantity, price, total, created_at))
        self.conn.commit()
        return cur.lastrowid

    def get_last_price(self, product_id, op_type):
        """Последняя известная цена по товару и типу операции."""
        cur = self.conn.cursor()
        cur.execute("""
            SELECT price FROM operations
            WHERE product_id = ? AND op_type = ?
            ORDER BY id DESC LIMIT 1
        """, (product_id, op_type))
        row = cur.fetchone()
        return row["price"] if row else None

    def get_all_operations(self):
        cur = self.conn.cursor()
        cur.execute("""
            SELECT o.*, p.name AS product_name
            FROM operations o JOIN products p ON p.id = o.product_id
            ORDER BY o.id DESC
        """)
        return cur.fetchall()

    def delete_operation(self, op_id):
        cur = self.conn.cursor()
        cur.execute("DELETE FROM operations WHERE id = ?", (op_id,))
        self.conn.commit()

    # ---------- Вкладка 1: Главная ----------
    def get_totals(self):
        cur = self.conn.cursor()
        cur.execute("SELECT COALESCE(SUM(total),0) AS s FROM operations WHERE op_type='PURCHASE'")
        purchased = cur.fetchone()["s"]
        cur.execute("SELECT COALESCE(SUM(total),0) AS s FROM operations WHERE op_type='SALE'")
        sold = cur.fetchone()["s"]
        return {
            "purchased_total": purchased,
            "sold_total": sold,
            "profit": sold - purchased,
        }

    # ---------- Вкладка 2: Закупки по товарам ----------
    def get_purchases_summary(self):
        cur = self.conn.cursor()
        cur.execute("""
            SELECT p.id, p.name,
                COALESCE(SUM(o.quantity),0) AS qty,
                CASE WHEN COALESCE(SUM(o.quantity),0) > 0
                     THEN COALESCE(SUM(o.total),0) / SUM(o.quantity)
                     ELSE 0 END AS avg_price,
                COALESCE(SUM(o.total),0) AS total_rub
            FROM products p
            LEFT JOIN operations o ON o.product_id = p.id AND o.op_type='PURCHASE'
            GROUP BY p.id, p.name
            ORDER BY p.name
        """)
        return cur.fetchall()

    # ---------- Вкладка 3: Продажи по товарам ----------
    def get_sales_summary(self):
        cur = self.conn.cursor()
        cur.execute("""
            SELECT p.id, p.name,
                COALESCE(SUM(o.quantity),0) AS qty,
                CASE WHEN COALESCE(SUM(o.quantity),0) > 0
                     THEN COALESCE(SUM(o.total),0) / SUM(o.quantity)
                     ELSE 0 END AS avg_price,
                COALESCE(SUM(o.total),0) AS total_rub
            FROM products p
            LEFT JOIN operations o ON o.product_id = p.id AND o.op_type='SALE'
            GROUP BY p.id, p.name
            ORDER BY p.name
        """)
        return cur.fetchall()

    # ---------- Вкладка 4: Остаток по товарам ----------
    def get_stock_summary(self):
        cur = self.conn.cursor()
        cur.execute("""
            SELECT p.id, p.name,
                COALESCE(SUM(CASE WHEN o.op_type='PURCHASE' THEN o.quantity END),0)
              - COALESCE(SUM(CASE WHEN o.op_type='SALE' THEN o.quantity END),0) AS stock
            FROM products p
            LEFT JOIN operations o ON o.product_id = p.id
            GROUP BY p.id, p.name
            ORDER BY p.name
        """)
        return cur.fetchall()

    def get_operations_by_type(self, op_type):
        cur = self.conn.cursor()
        cur.execute("""
            SELECT o.*, p.name AS product_name
            FROM operations o JOIN products p ON p.id = o.product_id
            WHERE o.op_type = ?
            ORDER BY o.id DESC
        """, (op_type,))
        return cur.fetchall()


    def close(self):
        self.conn.close()