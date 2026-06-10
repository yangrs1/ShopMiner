import sqlite3
from contextlib import contextmanager


class DBUtil:
    def __init__(self, db_uri="sqlite:///shopminer.db"):
        if db_uri.startswith("sqlite:///"):
            self.db_path = db_uri.replace("sqlite:///", "")
        else:
            self.db_path = db_uri

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def query_one(self, sql, params=None):
        with self._connect() as conn:
            cursor = conn.execute(sql, params or [])
            return dict(cursor.fetchone() or {})

    def query_all(self, sql, params=None):
        with self._connect() as conn:
            cursor = conn.execute(sql, params or [])
            return [dict(row) for row in cursor.fetchall()]

    def count(self, table, where="1=1", params=None):
        sql = f"SELECT COUNT(*) as cnt FROM {table} WHERE {where}"
        result = self.query_one(sql, params)
        return result.get("cnt", 0)

    def exists(self, table, where, params=None):
        return self.count(table, where, params) > 0

    def get_user_by_email(self, email):
        return self.query_one("SELECT * FROM user WHERE email = ?", [email])

    def get_cart_items(self, user_id):
        return self.query_all("SELECT * FROM cart_item WHERE user_id = ?", [user_id])

    def get_orders_by_user(self, user_id):
        return self.query_all("SELECT * FROM \"order\" WHERE user_id = ?", [user_id])

    def get_product_by_id(self, product_id):
        return self.query_one("SELECT * FROM product WHERE id = ?", [product_id])
