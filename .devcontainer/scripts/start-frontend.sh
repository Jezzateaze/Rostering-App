#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../../frontend" 2>/dev/null || cd frontend

corepack enable || true
if [ -f yarn.lock ]; then
  CMD="yarn dev --host 0.0.0.0 --port 5173"
  if yarn run | grep -q "\bpreview\b"; then PREVIEW="yarn preview --host 0.0.0.0 --port 5173"; fi
else
  CMD="npm run dev -- --host 0.0.0.0 --port 5173"
  if npm run | grep -q "\bpreview\b"; then PREVIEW="npm run preview -- --host 0.0.0.0 --port 5173"; fi
fi

echo "▶️ Starting frontend dev server on 0.0.0.0:5173 ..."
exec ${CMD}
