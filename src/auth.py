from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets
import sqlite3
import time
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.getenv("LETMESEE_DB_PATH", str(PROJECT_ROOT / "data" / "letmesee.sqlite3")))
DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL")
USE_POSTGRES = bool(DATABASE_URL)
SESSION_TTL = 60 * 60 * 24 * 30
PASSWORD_ITERATIONS = 310_000


def _connect() -> Any:
    if USE_POSTGRES:
        import psycopg
        from psycopg.rows import dict_row

        return psycopg.connect(DATABASE_URL, connect_timeout=10, row_factory=dict_row)
    if os.getenv("VERCEL") == "1":
        raise RuntimeError("Set DATABASE_URL to a persistent Postgres database in Vercel project settings.")
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _execute(db: Any, query: str, params: tuple[Any, ...] = ()) -> Any:
    if USE_POSTGRES:
        query = query.replace("?", "%s")
    return db.execute(query, params)


def init_auth_db() -> None:
    if os.getenv("VERCEL") == "1" and not USE_POSTGRES:
        return
    with _connect() as db:
        if USE_POSTGRES:
            for statement in (
                """
                CREATE TABLE IF NOT EXISTS users (
                    id BIGSERIAL PRIMARY KEY,
                    email TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    created_at BIGINT NOT NULL
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    token_hash TEXT PRIMARY KEY,
                    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    expires_at BIGINT NOT NULL
                )
                """,
                "CREATE INDEX IF NOT EXISTS sessions_user_id_idx ON sessions(user_id)",
            ):
                db.execute(statement)
        else:
            db.executescript(
                """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sessions (
                token_hash TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                expires_at INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS sessions_user_id_idx ON sessions(user_id);
            """
            )


def normalize_email(email: str) -> str:
    normalized = email.strip().lower()
    if len(normalized) > 254 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", normalized):
        raise ValueError("Enter a valid email address.")
    return normalized


def _password_hash(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS)
    return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${salt.hex()}${digest.hex()}"


def _password_matches(password: str, stored: str) -> bool:
    try:
        scheme, iterations, salt_hex, digest_hex = stored.split("$", 3)
        if scheme != "pbkdf2_sha256":
            return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iterations))
        return hmac.compare_digest(actual.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


def _new_session(db: Any, user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    now = int(time.time())
    _execute(db, "DELETE FROM sessions WHERE expires_at <= ?", (now,))
    _execute(db, "INSERT INTO sessions (token_hash, user_id, expires_at) VALUES (?, ?, ?)", (token_hash, user_id, now + SESSION_TTL))
    return token


def create_account(email: str, password: str) -> tuple[dict[str, Any], str]:
    email = normalize_email(email)
    if len(password) < 8:
        raise ValueError("Use a password with at least 8 characters.")
    if len(password) > 128:
        raise ValueError("Password must be 128 characters or fewer.")
    try:
        with _connect() as db:
            insert = "INSERT INTO users (email, password_hash, created_at) VALUES (?, ?, ?)"
            if USE_POSTGRES:
                insert += " RETURNING id"
            cursor = _execute(db, insert, (email, _password_hash(password), int(time.time())))
            user_id = int(cursor.fetchone()["id"] if USE_POSTGRES else cursor.lastrowid)
            token = _new_session(db, user_id)
    except Exception as exc:
        duplicate = (USE_POSTGRES and getattr(exc, "sqlstate", None) == "23505") or (
            not USE_POSTGRES and isinstance(exc, sqlite3.IntegrityError)
        )
        if not duplicate:
            raise
        raise ValueError("An account with this email already exists.") from exc
    return {"id": user_id, "email": email}, token


def sign_in(email: str, password: str) -> tuple[dict[str, Any], str]:
    email = normalize_email(email)
    with _connect() as db:
        user = _execute(db, "SELECT id, email, password_hash FROM users WHERE email = ?", (email,)).fetchone()
        if user is None or not _password_matches(password, user["password_hash"]):
            raise ValueError("Email or password is incorrect.")
        token = _new_session(db, int(user["id"]))
    return {"id": int(user["id"]), "email": user["email"]}, token


def find_session(token: str | None) -> dict[str, Any] | None:
    if not token:
        return None
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    now = int(time.time())
    with _connect() as db:
        row = _execute(db,
            "SELECT users.id, users.email FROM sessions JOIN users ON users.id = sessions.user_id "
            "WHERE sessions.token_hash = ? AND sessions.expires_at > ?",
            (token_hash, now),
        ).fetchone()
        if row is None:
            _execute(db, "DELETE FROM sessions WHERE token_hash = ? OR expires_at <= ?", (token_hash, now))
            return None
        return {"id": int(row["id"]), "email": row["email"]}


def end_session(token: str | None) -> None:
    if not token:
        return
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    with _connect() as db:
        _execute(db, "DELETE FROM sessions WHERE token_hash = ?", (token_hash,))


init_auth_db()
