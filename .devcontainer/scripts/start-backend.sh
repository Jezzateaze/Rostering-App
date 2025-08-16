#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../../backend" 2>/dev/null || cd backend

export PORT="${PORT:-8000}"
export HOST="0.0.0.0"

# Try FastAPI common entry points
if [ -f main.py ]; then
  if grep -q "FastAPI" main.py 2>/dev/null; then
    echo "▶️ Starting FastAPI (main:app) on $HOST:$PORT ..."
    exec uvicorn main:app --host "$HOST" --port "$PORT" --reload
  fi
fi
if [ -f app.py ]; then
  if grep -q "FastAPI" app.py 2>/dev/null; then
    echo "▶️ Starting FastAPI (app:app) on $HOST:$PORT ..."
    exec uvicorn app:app --host "$HOST" --port "$PORT" --reload
  fi
fi

# Flask fallbacks (requires flask / gunicorn or flask run)
if [ -f app.py ]; then
  if python3 - <<'PY' 2>/dev/null; then
import importlib.util, sys
spec = importlib.util.spec_from_file_location("app", "app.py")
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
ok = hasattr(mod, "app")
sys.exit(0 if ok else 1)
PY
  then
    if command -v gunicorn >/dev/null 2>&1; then
      echo "▶️ Starting Flask with gunicorn (app:app) on $HOST:$PORT ..."
      exec gunicorn "app:app" --bind "$HOST:$PORT"
    else
      echo "▶️ Starting Flask dev server (FLASK_APP=app.py) on $HOST:$PORT ..."
      export FLASK_APP=app.py
      exec flask run --host "$HOST" --port "$PORT"
    fi
  fi
fi

# Plain Python script fallback
if ls *.py >/dev/null 2>&1; then
  file="$(ls *.py | head -n1)"
  echo "⚠️  Unknown backend type — running 'python $file' (dev only) ..."
  exec python3 "$file"
fi

echo "❌ Could not find a backend entry point. Please edit .devcontainer/scripts/start-backend.sh to match your module."
exit 1
