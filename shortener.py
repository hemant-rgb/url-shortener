"""Core URL shortening logic."""

import secrets
import string
from datetime import datetime, timezone

from database import get_db

# Characters used for generating short codes (URL-safe, no ambiguous chars)
ALPHABET = string.ascii_letters + string.digits
SHORT_CODE_LENGTH = 6


def generate_short_code(length: int = SHORT_CODE_LENGTH) -> str:
    """Generate a random short code."""
    return "".join(secrets.choice(ALPHABET) for _ in range(length))


def create_short_url(original_url: str, custom_code: str | None = None) -> dict:
    """
    Create a shortened URL.

    Args:
        original_url: The URL to shorten.
        custom_code: Optional custom short code.

    Returns:
        Dictionary with the URL record.

    Raises:
        ValueError: If the custom code is already taken.
    """
    with get_db() as conn:
        if custom_code:
            existing = conn.execute(
                "SELECT id FROM urls WHERE short_code = ?", (custom_code,)
            ).fetchone()
            if existing:
                raise ValueError(f"Short code '{custom_code}' is already taken.")
            short_code = custom_code
        else:
            # Generate unique code with collision check
            for _ in range(10):
                short_code = generate_short_code()
                existing = conn.execute(
                    "SELECT id FROM urls WHERE short_code = ?", (short_code,)
                ).fetchone()
                if not existing:
                    break
            else:
                raise RuntimeError("Failed to generate a unique short code.")

        conn.execute(
            "INSERT INTO urls (short_code, original_url) VALUES (?, ?)",
            (short_code, original_url),
        )

        row = conn.execute(
            "SELECT * FROM urls WHERE short_code = ?", (short_code,)
        ).fetchone()

        return dict(row)


def get_url_by_code(short_code: str) -> dict | None:
    """Look up a URL by its short code."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM urls WHERE short_code = ? AND is_active = 1",
            (short_code,),
        ).fetchone()
        return dict(row) if row else None


def record_click(
    url_id: int,
    ip_address: str | None = None,
    user_agent: str | None = None,
    referrer: str | None = None,
):
    """Record a click/visit for analytics."""
    with get_db() as conn:
        conn.execute(
            """INSERT INTO clicks (url_id, ip_address, user_agent, referrer)
               VALUES (?, ?, ?, ?)""",
            (url_id, ip_address, user_agent, referrer),
        )


def get_url_stats(short_code: str) -> dict | None:
    """Get analytics for a shortened URL."""
    with get_db() as conn:
        url_row = conn.execute(
            "SELECT * FROM urls WHERE short_code = ?", (short_code,)
        ).fetchone()
        if not url_row:
            return None

        url = dict(url_row)

        # Total clicks
        total = conn.execute(
            "SELECT COUNT(*) as count FROM clicks WHERE url_id = ?", (url["id"],)
        ).fetchone()
        url["total_clicks"] = total["count"]

        # Clicks per day (last 30 days)
        daily_clicks = conn.execute(
            """SELECT DATE(clicked_at) as date, COUNT(*) as count
               FROM clicks
               WHERE url_id = ?
               GROUP BY DATE(clicked_at)
               ORDER BY date DESC
               LIMIT 30""",
            (url["id"],),
        ).fetchall()
        url["daily_clicks"] = [dict(r) for r in daily_clicks]

        # Top referrers
        referrers = conn.execute(
            """SELECT referrer, COUNT(*) as count
               FROM clicks
               WHERE url_id = ? AND referrer IS NOT NULL AND referrer != ''
               GROUP BY referrer
               ORDER BY count DESC
               LIMIT 10""",
            (url["id"],),
        ).fetchall()
        url["top_referrers"] = [dict(r) for r in referrers]

        # Recent clicks
        recent = conn.execute(
            """SELECT clicked_at, ip_address, user_agent, referrer
               FROM clicks
               WHERE url_id = ?
               ORDER BY clicked_at DESC
               LIMIT 20""",
            (url["id"],),
        ).fetchall()
        url["recent_clicks"] = [dict(r) for r in recent]

        return url


def list_all_urls(page: int = 1, per_page: int = 20) -> dict:
    """List all shortened URLs with pagination and click counts."""
    offset = (page - 1) * per_page
    with get_db() as conn:
        total = conn.execute("SELECT COUNT(*) as count FROM urls").fetchone()["count"]

        rows = conn.execute(
            """SELECT u.*, COUNT(c.id) as total_clicks
               FROM urls u
               LEFT JOIN clicks c ON u.id = c.url_id
               GROUP BY u.id
               ORDER BY u.created_at DESC
               LIMIT ? OFFSET ?""",
            (per_page, offset),
        ).fetchall()

        return {
            "urls": [dict(r) for r in rows],
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": max(1, (total + per_page - 1) // per_page),
        }


def delete_url(short_code: str) -> bool:
    """Deactivate a shortened URL."""
    with get_db() as conn:
        result = conn.execute(
            "UPDATE urls SET is_active = 0 WHERE short_code = ?", (short_code,)
        )
        return result.rowcount > 0
