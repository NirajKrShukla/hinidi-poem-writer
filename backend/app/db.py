import sqlite3
from pathlib import Path
from datetime import datetime
import os
import hashlib

from .config import settings

# Use configurable DB path from settings for easier deployment
DB_PATH = Path(settings.db_path).resolve()
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def get_conn():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            first_name TEXT,
            last_name TEXT,
            mobile TEXT UNIQUE,
            dob TEXT,
            email TEXT UNIQUE,
            password_hash TEXT,
            salt TEXT,
            created_at TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS oauth_states (
            state TEXT PRIMARY KEY,
            created_at TEXT
        )
        """
    )
    conn.commit()
    conn.close()


def hash_password(password: str, salt: bytes) -> str:
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return dk.hex()


def create_user(first_name, last_name, mobile, dob, email, password=None):
    conn = get_conn()
    cur = conn.cursor()
    salt = None
    password_hash = None
    if password:
        salt = os.urandom(16)
        password_hash = hash_password(password, salt)
    try:
        cur.execute(
            "INSERT INTO users (first_name,last_name,mobile,dob,email,password_hash,salt,created_at) VALUES (?,?,?,?,?,?,?,?)",
            (first_name, last_name, mobile, dob, email, password_hash, salt.hex() if salt else None, datetime.utcnow().isoformat()),
        )
        conn.commit()
        user_id = cur.lastrowid
        conn.close()
        return get_user_by_id(user_id)
    except Exception:
        # Integrity errors (duplicate mobile/email) or other DB errors
        conn.rollback()
        conn.close()
        raise


def get_user_by_id(user_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_by_mobile(mobile):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE mobile = ?", (mobile,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_by_email(email):
    if not email:
        return None
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE email = ?", (email,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def verify_password(stored_hash, stored_salt_hex, password) -> bool:
    if not stored_hash or not stored_salt_hex:
        return False
    salt = bytes.fromhex(stored_salt_hex)
    return hash_password(password, salt) == stored_hash


def save_state(state: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO oauth_states (state, created_at) VALUES (?,?)", (state, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()


def pop_state(state: str) -> bool:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT state FROM oauth_states WHERE state = ?", (state,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return False
    # Check expiry: only accept states created within last 5 minutes
    cur.execute("SELECT created_at FROM oauth_states WHERE state = ?", (state,))
    row2 = cur.fetchone()
    created_at = None
    try:
        created_at = datetime.fromisoformat(row2["created_at"]) if row2 and row2["created_at"] else None
    except Exception:
        created_at = None
    if created_at:
        if (datetime.utcnow() - created_at).total_seconds() > 300:
            # expired
            cur.execute("DELETE FROM oauth_states WHERE state = ?", (state,))
            conn.commit()
            conn.close()
            return False
    cur.execute("DELETE FROM oauth_states WHERE state = ?", (state,))
    conn.commit()
    conn.close()
    return True


# Initialize DB on import
init_db()
