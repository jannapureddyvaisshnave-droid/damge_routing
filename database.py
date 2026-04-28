"""
database.py — CargoPath SQLite  (Users + Route History)
=========================================================
Uses Python's built-in sqlite3 — no extra install needed.

Tables
------
users
    id               INTEGER  PRIMARY KEY AUTOINCREMENT
    full_name        TEXT     NOT NULL
    email            TEXT     NOT NULL  UNIQUE
    password_hash    TEXT     NOT NULL  (sha-256 hex)
    created_at       TEXT     NOT NULL  (ISO-8601 UTC)

route_history
    id               INTEGER  PRIMARY KEY AUTOINCREMENT
    user_id          INTEGER  REFERENCES users(id)   ← NULL for anonymous
    searched_at      TEXT     ISO-8601 timestamp (UTC)
    start_code / start_name / dest_code / dest_name
    cargo_name / cargo_category / fragility / units
    total_distance_km / total_weighted_cost / total_roughness_sum
    path_codes       TEXT     JSON array  e.g. '["HYD","CHE","BLR"]'
    segments         TEXT     JSON array of segment dicts
    revenue_inr / fuel_cost_inr / driver_cost_inr
    handling_cost_inr / damage_loss_inr / total_cost_inr
    net_profit_inr / profitable / ai_explanation
"""

import sqlite3
import json
import os
import hashlib
from datetime import datetime, timezone

# DB file sits next to app.py
DB_PATH = os.path.join(os.path.dirname(__file__), "cargopath.db")


def get_connection() -> sqlite3.Connection:
    """Return a thread-safe connection with row_factory set."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row          # rows behave like dicts
    conn.execute("PRAGMA journal_mode=WAL") # safe for concurrent reads
    conn.execute("PRAGMA foreign_keys=ON")  # enforce FK constraints
    return conn


def init_db() -> None:
    """Create / migrate tables on startup."""
    with get_connection() as conn:
        # ── users ──────────────────────────────────────────────
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name     TEXT    NOT NULL,
                email         TEXT    NOT NULL UNIQUE,
                password_hash TEXT    NOT NULL,
                created_at    TEXT    NOT NULL
            )
        """)

        # ── route_history ──────────────────────────────────────
        conn.execute("""
            CREATE TABLE IF NOT EXISTS route_history (
                id                   INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id              INTEGER REFERENCES users(id) ON DELETE SET NULL,
                searched_at          TEXT    NOT NULL,
                start_code           TEXT    NOT NULL,
                start_name           TEXT    NOT NULL,
                dest_code            TEXT    NOT NULL,
                dest_name            TEXT    NOT NULL,
                cargo_name           TEXT    NOT NULL,
                cargo_category       TEXT    NOT NULL,
                fragility            INTEGER NOT NULL,
                units                INTEGER NOT NULL,
                total_distance_km    REAL,
                total_weighted_cost  REAL,
                total_roughness_sum  REAL,
                path_codes           TEXT,
                segments             TEXT,
                revenue_inr          REAL,
                fuel_cost_inr        REAL,
                driver_cost_inr      REAL,
                handling_cost_inr    REAL,
                damage_loss_inr      REAL,
                total_cost_inr       REAL,
                net_profit_inr       REAL,
                profitable           INTEGER,
                ai_explanation       TEXT
            )
        """)

        # Add user_id column to existing DBs that pre-date this migration
        try:
            conn.execute("ALTER TABLE route_history ADD COLUMN user_id INTEGER REFERENCES users(id) ON DELETE SET NULL")
        except sqlite3.OperationalError:
            pass  # column already exists

        # Index for fast per-user lookups
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_route_history_user_id
            ON route_history(user_id)
        """)
        conn.commit()


# ── Auth helpers ───────────────────────────────────────────────────────────────

def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def register_user(full_name: str, email: str, password: str) -> dict:
    """Create a new user. Returns dict with success/error + user info."""
    now = datetime.now(timezone.utc).isoformat()
    try:
        with get_connection() as conn:
            cur = conn.execute(
                "INSERT INTO users (full_name, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
                (full_name.strip(), email.strip().lower(), _hash_password(password), now)
            )
            conn.commit()
            user_id = cur.lastrowid
        return {
            "success": True,
            "user": {"id": user_id, "full_name": full_name.strip(), "email": email.strip().lower()}
        }
    except sqlite3.IntegrityError:
        return {"success": False, "error": "An account with this email already exists."}


def login_user(email: str, password: str) -> dict:
    """Verify credentials. Returns dict with success/error + user info."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE email = ?", (email.strip().lower(),)
        ).fetchone()
    if not row:
        return {"success": False, "error": "No account found with that email address."}
    if row["password_hash"] != _hash_password(password):
        return {"success": False, "error": "Incorrect password. Please try again."}
    return {
        "success": True,
        "user": {"id": row["id"], "full_name": row["full_name"], "email": row["email"]}
    }


def get_user_by_id(user_id: int) -> dict | None:
    """Return a user dict by primary key, or None."""
    with get_connection() as conn:
        row = conn.execute("SELECT id, full_name, email, created_at FROM users WHERE id = ?", (user_id,)).fetchone()
    return dict(row) if row else None


# ── Route history helpers ──────────────────────────────────────────────────────

def save_route(
    start_code: str,
    start_name: str,
    dest_code: str,
    dest_name: str,
    cargo_name: str,
    cargo_category: str,
    fragility: int,
    units: int,
    route: dict,
    profit: dict,
    ai_explanation: str,
    user_id: int | None = None,   # ← NEW optional param
) -> int:
    """
    Insert one route into route_history.
    Pass user_id when a logged-in user triggers the route.
    Returns the new row's id.
    """
    now = datetime.now(timezone.utc).isoformat()

    with get_connection() as conn:
        cur = conn.execute("""
            INSERT INTO route_history (
                user_id,
                searched_at, start_code, start_name,
                dest_code, dest_name,
                cargo_name, cargo_category, fragility, units,
                total_distance_km, total_weighted_cost, total_roughness_sum,
                path_codes, segments,
                revenue_inr, fuel_cost_inr, driver_cost_inr,
                handling_cost_inr, damage_loss_inr,
                total_cost_inr, net_profit_inr, profitable,
                ai_explanation
            ) VALUES (
                ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?,
                ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?,
                ?
            )
        """, (
            user_id,
            now,
            start_code, start_name,
            dest_code, dest_name,
            cargo_name, cargo_category, fragility, units,
            route.get("total_distance_km"),
            route.get("total_cost"),
            route.get("total_roughness_sum"),
            json.dumps(route.get("path", [])),
            json.dumps(route.get("segments", [])),
            profit.get("revenue_inr"),
            profit.get("fuel_cost_inr"),
            profit.get("driver_cost_inr"),
            profit.get("handling_cost_inr"),
            profit.get("damage_loss_inr"),
            profit.get("total_cost_inr"),
            profit.get("net_profit_inr"),
            1 if profit.get("profitable") else 0,
            ai_explanation,
        ))
        conn.commit()
        return cur.lastrowid


# ── Global history (admin / all routes) ───────────────────────────────────────

def get_history(limit: int = 50, offset: int = 0) -> list[dict]:
    """Return recent routes across ALL users, newest first."""
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT rh.*, u.full_name AS user_full_name, u.email AS user_email
            FROM route_history rh
            LEFT JOIN users u ON rh.user_id = u.id
            ORDER BY rh.id DESC
            LIMIT ? OFFSET ?
        """, (limit, offset)).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_route_by_id(route_id: int) -> dict | None:
    """Return a single route by primary key, or None."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM route_history WHERE id = ?", (route_id,)
        ).fetchone()
    return _row_to_dict(row) if row else None


def delete_route(route_id: int) -> bool:
    """Delete a single route. Returns True if a row was deleted."""
    with get_connection() as conn:
        cur = conn.execute("DELETE FROM route_history WHERE id = ?", (route_id,))
        conn.commit()
        return cur.rowcount > 0


def get_stats() -> dict:
    """Aggregate stats across ALL saved routes."""
    with get_connection() as conn:
        row = conn.execute("""
            SELECT
                COUNT(*)                         AS total_routes,
                COUNT(DISTINCT cargo_name)       AS unique_cargos,
                ROUND(SUM(total_distance_km), 2) AS total_distance_km,
                ROUND(AVG(total_distance_km), 2) AS avg_distance_km,
                ROUND(SUM(net_profit_inr), 2)    AS total_net_profit,
                SUM(profitable)                  AS profitable_count
            FROM route_history
        """).fetchone()
        top = conn.execute("""
            SELECT cargo_name, COUNT(*) AS cnt
            FROM route_history
            GROUP BY cargo_name
            ORDER BY cnt DESC
            LIMIT 1
        """).fetchone()
    result = dict(row) if row else {}
    result["top_cargo"] = dict(top) if top else None
    return result


# ── Per-user history ───────────────────────────────────────────────────────────

def get_user_history(user_id: int, limit: int = 50, offset: int = 0) -> list[dict]:
    """Return routes belonging to a specific user, newest first."""
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT * FROM route_history
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT ? OFFSET ?
        """, (user_id, limit, offset)).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_user_stats(user_id: int) -> dict:
    """Aggregate stats for a single user's routes."""
    with get_connection() as conn:
        row = conn.execute("""
            SELECT
                COUNT(*)                        AS total_routes,
                COUNT(DISTINCT cargo_name)      AS unique_cargos,
                ROUND(AVG(total_distance_km),2) AS avg_distance_km,
                ROUND(SUM(net_profit_inr),2)    AS total_net_profit_inr,
                SUM(profitable)                 AS profitable_count,
                MIN(searched_at)                AS first_route_at,
                MAX(searched_at)                AS last_route_at
            FROM route_history
            WHERE user_id = ?
        """, (user_id,)).fetchone()
    return dict(row) if row else {}


def delete_user_route(route_id: int, user_id: int) -> bool:
    """Delete a route only if it belongs to the given user."""
    with get_connection() as conn:
        cur = conn.execute(
            "DELETE FROM route_history WHERE id = ? AND user_id = ?",
            (route_id, user_id)
        )
        conn.commit()
        return cur.rowcount > 0


# ── Internal helper ────────────────────────────────────────────────────────────

def _row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    for col in ("path_codes", "segments"):
        if d.get(col):
            try:
                d[col] = json.loads(d[col])
            except (json.JSONDecodeError, TypeError):
                pass
    if "profitable" in d:
        d["profitable"] = bool(d["profitable"])
    return d