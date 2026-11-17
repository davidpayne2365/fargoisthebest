"""Order storage (SQLite, survives restarts)."""
import json
import secrets
import sqlite3
import threading
import time

# Order lifecycle:
#   new      -> waiting for bartender approval / payment (skipped if payment_mode: none)
#   queued   -> approved, waiting for the robot
#   pouring  -> robot is pouring it right now
#   ready    -> in the cup, waiting to be picked up
#   done     -> picked up
#   cancelled
ACTIVE = ("new", "queued", "pouring", "ready")


class OrderStore:
    def __init__(self, path):
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.lock = threading.Lock()
        with self.lock:
            self.db.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    token TEXT NOT NULL,
                    created REAL NOT NULL,
                    updated REAL NOT NULL,
                    guest TEXT NOT NULL,
                    recipe_id TEXT NOT NULL,
                    recipe_name TEXT NOT NULL,
                    glass_key TEXT NOT NULL,
                    glass_name TEXT NOT NULL,
                    strength TEXT NOT NULL,
                    steps TEXT NOT NULL,
                    price REAL NOT NULL,
                    status TEXT NOT NULL,
                    note TEXT NOT NULL DEFAULT ''
                )""")
            # A crash mid-pour leaves a half-filled cup: flag it for the bartender.
            self.db.execute(
                "UPDATE orders SET status='queued', note='Interrupted (restart) — dump the cup before re-pouring' "
                "WHERE status='pouring'")
            self.db.commit()

    def _row(self, r):
        if r is None:
            return None
        d = dict(r)
        d["steps"] = json.loads(d["steps"])
        return d

    def create(self, guest, recipe, glass_key, glass_name, strength, steps, price, status):
        now = time.time()
        token = secrets.token_urlsafe(8)
        with self.lock:
            cur = self.db.execute(
                "INSERT INTO orders (token, created, updated, guest, recipe_id, recipe_name, glass_key,"
                " glass_name, strength, steps, price, status) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (token, now, now, guest, recipe["id"], recipe["name"], glass_key, glass_name,
                 strength, json.dumps(steps), price, status))
            self.db.commit()
            return self.get(cur.lastrowid)

    def get(self, order_id):
        return self._row(self.db.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone())

    def set_status(self, order_id, status, note=None):
        with self.lock:
            if note is None:
                self.db.execute("UPDATE orders SET status=?, updated=? WHERE id=?",
                                (status, time.time(), order_id))
            else:
                self.db.execute("UPDATE orders SET status=?, note=?, updated=? WHERE id=?",
                                (status, note, time.time(), order_id))
            self.db.commit()

    def active(self):
        rows = self.db.execute(
            f"SELECT * FROM orders WHERE status IN ({','.join('?' * len(ACTIVE))}) ORDER BY id",
            ACTIVE).fetchall()
        return [self._row(r) for r in rows]

    def next_queued(self):
        return self._row(self.db.execute(
            "SELECT * FROM orders WHERE status='queued' ORDER BY id LIMIT 1").fetchone())

    def queue_position(self, order_id):
        """1 = next to pour. None if not waiting."""
        o = self.get(order_id)
        if not o or o["status"] not in ("new", "queued"):
            return None
        n = self.db.execute(
            "SELECT COUNT(*) FROM orders WHERE status IN ('new','queued') AND id < ?",
            (order_id,)).fetchone()[0]
        return n + 1

    def recent(self, limit=50):
        rows = self.db.execute("SELECT * FROM orders ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [self._row(r) for r in rows]
