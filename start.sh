#!/usr/bin/env bash
# ==============================================================
#  Subvalore – one-shot startup script (Linux / macOS)
#  Run from the project root: ./start.sh
#
#  Prerequisites:
#    - Docker (with Compose plugin) running
#    - Python 3.11+ on PATH
#
#  Flags:
#    --skip-install   Skip pip install (faster restarts)
#    --no-browser     Don't try to open browser
# ==============================================================

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKIP_INSTALL=false
NO_BROWSER=false

for arg in "$@"; do
  case $arg in
    --skip-install) SKIP_INSTALL=true ;;
    --no-browser)   NO_BROWSER=true ;;
  esac
done

# ── Helpers ──────────────────────────────────────────────────
step() { echo; echo ">> $1"; }
ok()   { echo "   OK: $1"; }
warn() { echo "   WARN: $1"; }
fail() { echo; echo "!! ERROR: $1" >&2; exit 1; }

echo
echo "  ================================="
echo "        S U B V A L O R E          "
echo "    Financial Data Platform         "
echo "  ================================="
echo

# ── Step 1: .env ─────────────────────────────────────────────
step "Checking environment file"
if [ ! -f "$ROOT/.env" ]; then
  cp "$ROOT/.env.example" "$ROOT/.env"
  ok ".env created from .env.example (default credentials)"
else
  ok ".env already exists"
fi

# ── Step 2: Docker / PostgreSQL ───────────────────────────────
step "Starting PostgreSQL via Docker Compose"
docker compose -f "$ROOT/docker-compose.yml" up -d \
  || fail "docker compose failed. Is Docker running?"

echo "   Waiting for PostgreSQL to become healthy..."
MAX_WAIT=60
ELAPSED=0
while true; do
  HEALTH=$(docker inspect subvalore_postgres --format "{{.State.Health.Status}}" 2>/dev/null || echo "unknown")
  if [ "$HEALTH" = "healthy" ]; then
    ok "PostgreSQL is healthy"
    break
  fi
  if [ "$ELAPSED" -ge "$MAX_WAIT" ]; then
    warn "Health check timed out after ${ELAPSED}s – continuing anyway"
    break
  fi
  sleep 2
  ELAPSED=$((ELAPSED + 2))
done

# ── Step 3: Python virtual environment ────────────────────────
step "Python virtual environment"
VENV="$ROOT/backend/.venv"
if [ ! -d "$VENV" ]; then
  echo "   Creating virtual environment..."
  python3 -m venv "$VENV" \
    || fail "python3 -m venv failed. Is Python 3.11+ on your PATH?"
  ok "Virtual environment created"
else
  ok "Virtual environment already exists"
fi

PIP="$VENV/bin/pip"
ALEMBIC="$VENV/bin/alembic"
UVICORN="$VENV/bin/uvicorn"

# ── Step 4: Install dependencies ─────────────────────────────
step "Python dependencies"
if [ "$SKIP_INSTALL" = true ]; then
  warn "Skipping pip install (--skip-install flag)"
else
  "$PIP" install -r "$ROOT/backend/requirements.txt" --quiet \
    || fail "pip install failed"
  ok "Dependencies installed"
fi

# ── Step 5: Database migrations ──────────────────────────────
step "Database migrations"

MIGRATION_COUNT=$(find "$ROOT/migrations/versions" -name "*.py" 2>/dev/null | wc -l)
if [ "$MIGRATION_COUNT" -eq 0 ]; then
  echo "   No migration files found – generating initial schema..."
  (cd "$ROOT" && "$ALEMBIC" revision --autogenerate -m "initial schema") \
    || fail "alembic revision failed"
fi

(cd "$ROOT" && "$ALEMBIC" upgrade head) \
  || fail "alembic upgrade head failed"
ok "Migrations applied"

# ── Step 6: Open browser (optional) ──────────────────────────
if [ "$NO_BROWSER" = false ]; then
  sleep 1
  if command -v xdg-open &>/dev/null; then
    xdg-open "http://localhost:8000" &>/dev/null & true
  elif command -v open &>/dev/null; then
    open "http://localhost:8000" & true
  fi
fi

# ── Step 7: Start backend ─────────────────────────────────────
step "Starting Subvalore backend"
echo
echo "  App:      http://localhost:8000"
echo "  API docs: http://localhost:8000/docs"
echo "  Health:   http://localhost:8000/api/health"
echo
echo "  Press Ctrl+C to stop."
echo

cd "$ROOT/backend"
"$UVICORN" app.main:app --reload --host 0.0.0.0 --port 8000
