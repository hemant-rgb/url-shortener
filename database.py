"""Database setup and models for the URL shortener."""

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).parent / "shortener.db"


def get_connection() -> sqlite3.Connection:
    """Get a database connection with row factory."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def get_db():
    """Context manager for database connections."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Initialize the database schema."""
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS urls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                short_code TEXT UNIQUE NOT NULL,
                original_url TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                is_active INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS clicks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url_id INTEGER NOT NULL,
                clicked_at TEXT NOT NULL DEFAULT (datetime('now')),
                ip_address TEXT,
                user_agent TEXT,
                referrer TEXT,
                FOREIGN KEY (url_id) REFERENCES urls(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_urls_short_code ON urls(short_code);
            CREATE INDEX IF NOT EXISTS idx_clicks_url_id ON clicks(url_id);
            CREATE INDEX IF NOT EXISTS idx_clicks_clicked_at ON clicks(clicked_at);
        """)
