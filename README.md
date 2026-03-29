# Subvalore

A modern financial data platform.  Data is fetched once from **yfinance**, stored in **PostgreSQL**, and served instantly to the frontend on every subsequent request.

---

## Architecture

```
Frontend (HTML/CSS/JS)
        │  HTTP
        ▼
Backend (FastAPI)
        │  SQLAlchemy
        ▼
PostgreSQL  ◄──── yfinance (fetched on demand / scheduled refresh)
```

---

## Project structure

```
subvalore/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI application entrypoint
│   │   ├── config.py        # Pydantic settings (reads .env)
│   │   ├── database.py      # SQLAlchemy engine, session, Base
│   │   ├── models/          # ORM models (one file per table)
│   │   ├── schemas/         # Pydantic request/response schemas
│   │   ├── services/        # Business logic (ingestion, queries)
│   │   ├── routers/         # FastAPI routers (one per feature area)
│   │   └── utils/           # Shared helpers (serialisation etc.)
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── styles.css
│   └── script.js
├── migrations/              # Alembic migrations
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
├── alembic.ini
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## Local development setup

### 1. Copy environment file

```bash
cp .env.example .env
# Edit .env if you want different credentials
```

### 2. Start PostgreSQL with Docker Compose

```bash
docker compose up -d
# Verify it is healthy
docker compose ps
```

### 3. Create a Python virtual environment and install dependencies

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 4. Run database migrations

From the **project root** (where `alembic.ini` lives):

```bash
cd ..   # back to project root if you are in backend/
source backend/.venv/bin/activate

# First time: let Alembic create the initial migration automatically
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
```

Or, for development convenience, the app auto-creates tables on startup via
`create_all_tables()` — but Alembic is preferred for production.

### 5. Run the backend

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API docs available at: http://localhost:8000/docs

### 6. Open the frontend

The frontend is served by FastAPI as static files.  Open:

```
http://localhost:8000/
```

No build step required — plain HTML/CSS/JS.

---

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Liveness check including DB connectivity |
| GET | `/api/ticker/{symbol}/all` | All datasets for a ticker (serves from DB; refreshes if stale) |
| POST | `/api/ticker/{symbol}/refresh` | Force a fresh fetch from yfinance and update DB |
| GET | `/api/ticker/{symbol}/status` | Ticker existence in DB, last refresh time, staleness flag |

---

## Data refresh logic

1. `GET /api/ticker/{symbol}/all` checks `tickers.last_refreshed_at`.
2. If data is **missing or older than `DATA_STALE_MINUTES`** (default 60 min), it triggers a yfinance fetch, stores results in PostgreSQL, then returns the fresh data.
3. If data is **fresh**, it reads directly from PostgreSQL — no yfinance call.
4. `POST /api/ticker/{symbol}/refresh` **always** forces a yfinance fetch regardless of freshness.

---

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql://subvalore:subvalore_secret@localhost:5432/subvalore` | Full SQLAlchemy DB URL |
| `POSTGRES_DB` | `subvalore` | DB name (used by Docker Compose) |
| `POSTGRES_USER` | `subvalore` | DB user (used by Docker Compose) |
| `POSTGRES_PASSWORD` | `subvalore_secret` | DB password (used by Docker Compose) |
| `DATA_STALE_MINUTES` | `60` | Minutes before cached data is considered stale |
| `APP_ENV` | `development` | Environment name |
| `LOG_LEVEL` | `INFO` | Python log level |

---

## Implementation phases

| Phase | Status | Description |
|-------|--------|-------------|
| 1 | ✅ Complete | Scaffolding, DB setup, models, health endpoint |
| 2 | Planned | yfinance ingestion, price_history, dividend_history, metrics, `/all`, `/refresh` |
| 3 | Planned | Remaining datasets, staleness logic, `/status` endpoint |
| 4 | Planned | Full frontend rendering for all 22 tabs |
