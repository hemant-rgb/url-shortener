# ⚡ SnipLink — URL Shortener

A fast, lightweight URL shortener built with **FastAPI** and **SQLite**.

## Features

- 🔗 **Shorten URLs** — paste any URL, get a short link
- 🎯 **Custom aliases** — choose your own short code
- 📊 **Click analytics** — track total clicks, daily breakdown, referrers, user agents
- 🖥️ **Dashboard** — view all links with stats at a glance
- 🔌 **REST API** — JSON API for programmatic access

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the server
python -m uvicorn main:app --reload --port 8000
```

Open **http://localhost:8000** in your browser.

## API Endpoints

| Method   | Endpoint               | Description              |
|----------|------------------------|--------------------------|
| `POST`   | `/api/shorten`         | Shorten a URL            |
| `GET`    | `/api/stats/{code}`    | Get analytics (JSON)     |
| `DELETE` | `/api/urls/{code}`     | Deactivate a link        |
| `GET`    | `/{code}`              | Redirect to original URL |

### Shorten a URL

```bash
curl -X POST http://localhost:8000/api/shorten \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/long-url", "custom_code": "my-link"}'
```

### Get stats

```bash
curl http://localhost:8000/api/stats/my-link
```

## Project Structure

```
url-shortener/
├── main.py            # FastAPI app & routes
├── database.py        # SQLite setup & schema
├── shortener.py       # Core shortening logic
├── requirements.txt   # Python dependencies
├── shortener.db       # SQLite database (auto-created)
└── templates/
    ├── base.html      # Base layout
    ├── index.html     # Home page / shorten form
    ├── dashboard.html # All links overview
    └── stats.html     # Per-link analytics
```
