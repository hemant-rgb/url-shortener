"""FastAPI URL Shortener — main application."""

from fastapi import FastAPI, Request, Form, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

from database import init_db
from shortener import (
    create_short_url,
    get_url_by_code,
    record_click,
    get_url_stats,
    list_all_urls,
    delete_url,
)

app = FastAPI(title="URL Shortener", version="1.0.0")
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

# Initialize database on startup
init_db()


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Landing page with the shorten form."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, page: int = Query(1, ge=1)):
    """Dashboard showing all URLs and analytics."""
    data = list_all_urls(page=page)
    return templates.TemplateResponse("dashboard.html", {"request": request, **data})


@app.get("/stats/{short_code}", response_class=HTMLResponse)
async def stats_page(request: Request, short_code: str):
    """Detailed analytics page for a specific URL."""
    stats = get_url_stats(short_code)
    if not stats:
        raise HTTPException(status_code=404, detail="URL not found")
    return templates.TemplateResponse("stats.html", {"request": request, "stats": stats})


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------


@app.post("/api/shorten")
async def api_shorten(request: Request):
    """Shorten a URL. Accepts JSON or form data."""
    content_type = request.headers.get("content-type", "")

    if "application/json" in content_type:
        body = await request.json()
        original_url = body.get("url", "").strip()
        custom_code = body.get("custom_code", "").strip() or None
    else:
        form = await request.form()
        original_url = form.get("url", "").strip()
        custom_code = form.get("custom_code", "").strip() or None

    if not original_url:
        raise HTTPException(status_code=400, detail="URL is required.")

    # Basic URL validation
    if not original_url.startswith(("http://", "https://")):
        original_url = "https://" + original_url

    try:
        url_record = create_short_url(original_url, custom_code)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    base_url = str(request.base_url).rstrip("/")
    short_url = f"{base_url}/{url_record['short_code']}"

    # If it's a form submission, redirect back to home with the result
    if "application/json" not in content_type:
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "short_url": short_url,
                "original_url": url_record["original_url"],
                "short_code": url_record["short_code"],
            },
        )

    return JSONResponse(
        {
            "short_code": url_record["short_code"],
            "short_url": short_url,
            "original_url": url_record["original_url"],
            "created_at": url_record["created_at"],
        }
    )


@app.get("/api/stats/{short_code}")
async def api_stats(short_code: str):
    """Get analytics for a shortened URL (JSON)."""
    stats = get_url_stats(short_code)
    if not stats:
        raise HTTPException(status_code=404, detail="URL not found")
    return stats


@app.delete("/api/urls/{short_code}")
async def api_delete(short_code: str):
    """Deactivate a shortened URL."""
    if not delete_url(short_code):
        raise HTTPException(status_code=404, detail="URL not found")
    return {"detail": "URL deactivated"}


# ---------------------------------------------------------------------------
# Redirect handler — must be last to avoid catching other routes
# ---------------------------------------------------------------------------


@app.get("/{short_code}")
async def redirect_to_url(request: Request, short_code: str):
    """Redirect to the original URL and record the click."""
    url = get_url_by_code(short_code)
    if not url:
        raise HTTPException(status_code=404, detail="Short URL not found")

    # Record analytics
    record_click(
        url_id=url["id"],
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        referrer=request.headers.get("referer"),
    )

    return RedirectResponse(url=url["original_url"], status_code=307)
