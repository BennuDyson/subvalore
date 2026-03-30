# Subvalore

A modern financial data platform. Data is fetched from **yfinance**, stored in **PostgreSQL**, and served instantly to the frontend on every request. A background scheduler keeps all data fresh automatically.

---

## Architecture

```
yfinance API  (fetched once, then refreshed every 24h by scheduler)
      │
      ▼
PostgreSQL  ◄──── Background scheduler (APScheduler, configurable interval)
      │
      ▼
FastAPI backend  (reads DB only — never waits on yfinance for a user request)
      │
      ▼
Frontend (HTML/CSS/JS)  ──  instant response, always from DB
```

---

## Quick start (one command)

```powershell
.\start.ps1
```

That's it. The script handles everything: PostgreSQL, virtual environment, dependencies, migrations, and the backend server.

> **First time only:** if PowerShell blocks the script, run this once then retry:
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```

### Script flags

| Flag | Effect |
|------|--------|
| `.\start.ps1` | Full startup (recommended) |
| `.\start.ps1 -SkipInstall` | Skip `pip install` for faster restarts |
| `.\start.ps1 -NoBrowser` | Don't auto-open the browser |

---

## Manual setup (step by step)

If you prefer to run each step yourself:

### 1. Copy environment file

```powershell
Copy-Item .env.example .env
```

Edit `.env` if you want custom database credentials (defaults work fine for local dev).

### 2. Start PostgreSQL

```powershell
docker compose up -d
docker compose ps        # confirm it shows healthy
```

### 3. Create virtual environment and install dependencies

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 4. Run database migrations

Run from the **project root** (where `alembic.ini` lives):

```powershell
cd ..   # back to project root if you are inside backend/

# Generate migration file (first time only)
alembic revision --autogenerate -m "initial schema"

# Apply migrations
alembic upgrade head
```

### 5. Start the backend

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 6. Open the app

```
http://localhost:8000/
```

---

## Project structure

```
subvalore/
├── start.ps1                    ← one-shot startup script
├── docker-compose.yml           ← PostgreSQL container
├── .env.example                 ← copy to .env
├── alembic.ini                  ← migration config
├── migrations/                  ← Alembic migration files
│   └── versions/
├── backend/
│   ├── requirements.txt
│   └── app/
│       ├── main.py              ← FastAPI app + lifespan
│       ├── config.py            ← settings (reads .env)
│       ├── database.py          ← SQLAlchemy engine + session
│       ├── models/              ← ORM table definitions
│       ├── schemas/             ← Pydantic schemas
│       ├── routers/             ← API route handlers
│       │   ├── health.py
│       │   ├── ticker.py
│       │   └── scheduler.py
│       ├── services/
│       │   ├── ingestion.py     ← yfinance fetch + normalize
│       │   ├── ticker_service.py← DB read/write
│       │   └── scheduler.py     ← background refresh job
│       └── utils/
│           └── serializers.py   ← pandas/numpy → JSON
└── frontend/
    ├── index.html
    ├── styles.css
    └── script.js
```

---

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Liveness + DB connectivity check |
| GET | `/api/ticker/{symbol}/all` | All datasets for a ticker (auto-refreshes if stale) |
| POST | `/api/ticker/{symbol}/refresh` | Force a fresh yfinance fetch |
| GET | `/api/ticker/{symbol}/status` | Last refresh time, staleness flag |
| GET | `/api/scheduler/status` | Scheduler state, next/last run times |
| POST | `/api/scheduler/run-now` | Trigger an immediate full refresh of all tickers |
| GET | `/api/debug/{symbol}` | Raw yfinance diagnostic (dev only) |

Interactive docs: **http://localhost:8000/docs**

---

## How data refresh works

| Scenario | What happens |
|----------|-------------|
| First search for a ticker | Fetches from yfinance → stores in DB → returns data (~5–15s) |
| Same ticker, data fresh | Reads from PostgreSQL only (instant) |
| Same ticker, data stale | Re-fetches from yfinance → updates DB → returns fresh data |
| Scheduler fires (every 24h) | Refreshes every known ticker in the background automatically |
| `POST /api/ticker/AAPL/refresh` | Forces immediate yfinance fetch for that ticker |
| `POST /api/scheduler/run-now` | Forces immediate refresh of **all** tickers |

Staleness threshold is controlled by `DATA_STALE_MINUTES` in `.env` (default: 60 minutes).

---

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql://subvalore:subvalore_secret@localhost:5432/subvalore` | SQLAlchemy connection URL |
| `POSTGRES_DB` | `subvalore` | Database name (Docker Compose) |
| `POSTGRES_USER` | `subvalore` | Database user (Docker Compose) |
| `POSTGRES_PASSWORD` | `subvalore_secret` | Database password (Docker Compose) |
| `DATA_STALE_MINUTES` | `60` | Minutes before cached data is considered stale |
| `SCHEDULER_ENABLED` | `true` | Enable/disable the background refresh scheduler |
| `REFRESH_INTERVAL_HOURS` | `24` | How often the scheduler refreshes all tickers |
| `APP_ENV` | `development` | Environment name |
| `LOG_LEVEL` | `INFO` | Python logging level |

---

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (for PostgreSQL)
- [Python 3.11+](https://www.python.org/downloads/)
- PowerShell 5.1+ (comes with Windows 10/11)

---

## Implementation phases

| Phase | Status | Description |
|-------|--------|-------------|
| 1 | ✅ Done | Scaffolding, DB models, health endpoint |
| 2 | ✅ Done | yfinance ingestion, all datasets, `/all` `/refresh` `/status` |
| 3 | ✅ Done | Scheduler, daily auto-refresh, `/scheduler/status` |
| 4 | Planned | Full frontend rendering for all 22 tabs |
